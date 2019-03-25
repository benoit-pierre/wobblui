#cython: language_level=3

'''
wobblui - Copyright 2018-2019 wobblui team, see AUTHORS.md

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.
'''

import ctypes
import cython
import io
from libc.stdint cimport uintptr_t
import os
import PIL.Image
import PIL.ImageDraw
import platform
import subprocess
import sys
import tempfile
import time

from wobblui.color cimport Color
from wobblui.font.manager cimport c_font_manager
from wobblui.osinfo import is_android
from wobblui.sdlinit cimport initialize_sdl
from wobblui.texture cimport Texture
from wobblui.widget cimport Widget

sdlimage_initialized = False

ctypedef void* (*_sdl_FreeSurfaceType)(
    void *srf
) nogil
cdef _sdl_FreeSurfaceType _sdl_FreeSurface = NULL


cpdef str stock_image(name):
    p = os.path.join(os.path.abspath(os.path.dirname(__file__)),
        "img", name)
    if name.find(".") < 0:
        if os.path.exists(p + ".png"):
            return (p + ".png")
        elif os.path.exists(p + ".jpg"):
            return (p + ".jpg")
    return p

def _internal_sdl_surface_to_pil_image(sdl_surface):
    import sdl2 as sdl
    (fd, fpath) = tempfile.mkstemp(
        prefix="wobblui-srf-to-pil-", suffix=".bmp"
    )
    try:
        try:
            os.close(fd)
        except OSError:
            pass
        result = sdl.SDL_SaveBMP(
            sdl_surface,
            fpath.encode('utf-8', 'replace')
        )
        if result != 0:
            raise RuntimeError("SDL_SaveBMP returned error")
        pil_image = PIL.Image.open(fpath)
        return pil_image
    finally:
        os.remove(fpath)

def _internal_pil_image_to_sdl_surface(pil_image, retries=5):
    global sdlimage_initialized
    initialize_sdl()
    import sdl2 as sdl
    import sdl2.sdlimage as sdlimage

    if not sdlimage_initialized:
        sdlimage_initialized = True
        if not platform.system().lower() == "windows":
            flags = sdlimage.IMG_INIT_JPG|sdlimage.IMG_INIT_PNG
        else:
            flags = sdlimage.IMG_INIT_TIF
        sdlimage.IMG_Init(flags)
    sdl_image = None

    # Write image to ctypes buffer:
    bytes_obj = io.BytesIO()
    if platform.system().lower() != "windows":
        pil_image.save(bytes_obj, format="PNG")
    else:
        pil_image.save(bytes_obj, format="TIFF")
    bytes_obj.flush()
    bytes_value = bytearray(bytes_obj.getvalue())
    del(bytes_obj)
    if len(bytes_value) == 0:
        raise RuntimeError("saved image unexpectedly empty")
    ctypes_bytes = (ctypes.c_uint8 * len(bytes_value)).\
        from_buffer(bytes_value)

    # Create SDL RW Ops and load with SDL_Image from that:
    rwops = sdl.SDL_RWFromMem(ctypes.byref(ctypes_bytes),
        len(bytes_value))
    sdl_image = sdlimage.IMG_Load_RW(rwops, 0)
    sdl.SDL_FreeRW(rwops)
    del(rwops)

    # Handle error:
    if sdl_image is None or not sdl_image:  # ptr will evaluate False if NULL
        if retries > 0:
            retries -= 1
            time.sleep(0.1)
            return _internal_pil_image_to_sdl_surface(
                pil_image,
                retries=(retries - 1))
        err_msg = sdlimage.IMG_GetError()
        try:
            err_msg = err_msg.decode("utf-8", "replace")
        except AttributeError:
            pass
        raise ValueError(
            "failed to load image with SDL Image: " +
            str(err_msg))
    return sdl_image

cdef class RenderImage:
    """ A mutable image object for use in widget draw callbacks.
        This RenderImage can be created either from a PIL
        image or a disk file path. Rendering a RenderImage with
        draw() is fast after it was rendered at least once, all
        other operations like the editing manipulation are SLOW.

        Modification / editing of a RenderImage
        ---------------------------------------

        The RenderImage object supports slow but flexible editing
        operations. Check them out:

        - draw_text_onto_image
        - draw_filled_rectangle_onto_image
        - draw_other_image_onto_image
    """

    def __init__(self, object pil_image, render_low_res=False):
        global _sdl_FreeSurface
        initialize_sdl()
        if not _sdl_FreeSurface:
            import sdl2 as sdl
            _sdl_FreeSurface = <_sdl_FreeSurfaceType>(
                cython.operator.dereference(<uintptr_t*>(
                <uintptr_t>ctypes.addressof(sdl.SDL_FreeSurface)
                ))
            )
        if type(pil_image) == str:
            pil_image = PIL.Image.open(pil_image)
        self.surface = None
        self._pil_image = pil_image.copy()
        self._render_size = tuple(self._pil_image.size)
        self.internal_image_size = tuple(self._render_size)
        self.render_low_res = (render_low_res is True)
        self._color = Color.white()

        if self.render_low_res:
            (w, h) = self._pil_image.size
            scale_f = (512 + 512) / (w + h)
            new_w = max(1, round(w * scale_f))
            new_h = max(1, round(h * scale_f))
            if scale_f < 0.95 and (new_w != w or new_h != h):
                self._pil_image = self._pil_image.resize(
                    (new_w, new_h))
        self.surface = _internal_pil_image_to_sdl_surface(
            self._pil_image)
        self.internal_image_size = tuple(self._pil_image.size)
        self._texture = None

    def show_image(self):
        cmd = [sys.executable, "-c",
            "from wobblui.imageviewer import launch_viewer; " +
            "import sys; " +
            "launch_viewer(sys.argv[1], delete_source=True)"]
        (fd, fpath) = tempfile.mkstemp(prefix="wobblui-img-view-",
            suffix=".png")
        try:
            with open(fpath, "wb") as f:
                f.write(self.as_png())
            subprocess.Popen(cmd + [fpath])
        except Exception as e:
            os.remove(fpath) 

    @classmethod
    def new_from_size(self, width, height):
        if round(width) <= 0 or round(height) <= 0:
            raise RuntimeError("invalid image size: " +
                str((width, height)))
        pil_image = PIL.Image.new('RGBA', (max(1,round(width)),
            max(1, round(height))), (0, 0, 0, 0))
        return RenderImage(pil_image, render_low_res=False)

    def _clip_rect_to_image(self, x, y, w, h):
        x = round(x)
        y = round(y)
        w = round(w) - min(0, -x)
        h = round(h) - min(0, -y)
        x = min(self._render_size[0], max(0, x))
        y = min(self._render_size[1], max(0, y))
        w = min(w, self._render_size[0] - x)
        h = min(h, self._render_size[1] - y)
        return (x, y, w, h)

    def draw_rectangle_onto_image(self,
            x, y, w, h, color=Color.black(),
            alpha=1.0, filled=True
            ):
        import sdl2 as sdl
        if self.render_low_res:
            raise TypeError("cannot modify low-res rendered image")
        if not filled:
            raise NotImplementedError("filled=False not implemented")

        # Process input values:
        (x, y, w, h) = self._clip_rect_to_image(x, y, w, h)
        if w <= 0 or h <= 0:
            return
        alpha = max(0, min(255, round(255.0 * alpha)))
        if alpha == 0:
            return
        if not isinstance(color, Color):
            color = Color(color)

        # Do rectangle drawing:
        if alpha == 255:
            # Render directly onto our internal surface:
            rect = sdl.SDL_Rect()
            rect.x = x
            rect.y = y
            rect.w = w
            rect.h = h
            scolor = sdl.SDL_MapRGBA(self.surface.contents.format,
                max(0, min(255, round(color.value_red))),
                max(0, min(255, round(color.value_green))),
                max(0, min(255, round(color.value_blue))),
                255
            )
            self._texture = None
            self._pil_image = None    
            result = sdl.SDL_FillRect(self.surface, rect, scolor)
            if result != 0:
                raise RuntimeError("SDL_FillRect returned an error")
            return
        # Work around broken alpha handling by rendering to a surface copy:
        copied_srf = sdl.SDL_ConvertSurface(
            self.surface,
            self.surface.contents.format,
            sdl.SDL_SWSURFACE
        )
        try:
            rect = sdl.SDL_Rect()
            rect.x = x
            rect.y = y
            rect.w = w
            rect.h = h
            scolor = sdl.SDL_MapRGBA(copied_srf.contents.format,
                max(0, min(255, round(color.value_red))),
                max(0, min(255, round(color.value_green))),
                max(0, min(255, round(color.value_blue))),
                255
            )
            result = sdl.SDL_FillRect(copied_srf, rect, scolor)
            if result != 0:
                raise RuntimeError("SDL_FillRect returned an error")

            # Now render the copied surface back, but with alpha blending:
            self._texture = None
            sdl.SDL_SetSurfaceBlendMode(copied_srf,
                sdl.SDL_BLENDMODE_BLEND)
            sdl.SDL_SetSurfaceAlphaMod(copied_srf, alpha)
            sdl.SDL_BlitSurface(copied_srf, rect, self.surface, rect)
            if result != 0:
                raise RuntimeError("SDL_BlitSurface returned an error")
        finally:
            sdl.SDL_FreeSurface(copied_srf)
            self._texture = None
            self._pil_image = None

    def draw_text_onto_image(self,
            text, font=None,
            x=0, y=0,
            color=Color.black(),
            alpha=1.0
            ):
        import sdl2 as sdl
        import sdl2.ttf as sdlttf
        if self.render_low_res:
            raise TypeError("cannot modify low-res rendered image")
        try:
            text = text.encode("utf-8", "replace")
        except AttributeError:
            text = bytes(text)
        if font is None:
            font = c_font_manager().get_font("Sans")
        sfont = font.get_sdl_font()
        c = sdl.SDL_Color(255, 255, 255)
        surface = sdlttf.TTF_RenderUTF8_Blended(
            sfont.font, text, c
        )
        if not surface:
            raise RuntimeError("TTF_RenderUTF8_Blended reported error")
        self._texture = None
        try:
            self._draw_srf_onto_image(
                surface, x, y, alpha=alpha,
                color=color)
        finally:
            sdl.SDL_FreeSurface(surface)

    def draw_image_onto_image(self,
            other_image, x, y, alpha=1.0, color=Color.white()
            ):
        self._draw_srf_onto_image(
            other_image.surface, x, y, alpha=alpha, color=color
        )

    def _draw_srf_onto_image(self,
            surface, x, y, alpha=1.0, color=Color.white()
            ):
        import sdl2 as sdl
        if self.render_low_res:
            raise TypeError("cannot modify low-res rendered image")
        alpha = max(0, min(255, round(255.0 * alpha)))
        if alpha == 0:
            return
        if not isinstance(color, Color):
            color = Color(color)
        rect = sdl.SDL_Rect()
        rect.x = round(x)
        rect.y = round(y)
        rect.w = surface.contents.w
        rect.h = surface.contents.h
        self._texture = None
        sdl.SDL_SetSurfaceBlendMode(surface,
            sdl.SDL_BLENDMODE_BLEND)
        sdl.SDL_SetSurfaceAlphaMod(surface, alpha)
        sdl.SDL_SetSurfaceColorMod(surface,
            max(0, min(255, round(color.value_red))),
            max(0, min(255, round(color.value_green))),
            max(0, min(255, round(color.value_blue))),
        )
        result = sdl.SDL_BlitSurface(surface, None, self.surface, rect)
        sdl.SDL_SetSurfaceColorMod(surface, 255, 255, 255)
        sdl.SDL_SetSurfaceAlphaMod(surface, 255)
        if result != 0:
            raise RuntimeError("SDL_BlitSurface returned an error")
        self._pil_image = None

    @property
    def pil_image(self):
        if self._pil_image is not None:
            return self._pil_image
        self._pil_image = _internal_sdl_surface_to_pil_image(
            self.surface
        )
        return self._pil_image

    def as_png(self):
        byteobj = io.BytesIO()
        self.pil_image.save(byteobj, format="PNG")
        byteobj.flush()
        return byteobj.getvalue()

    def __dealloc__(self):
        global _sdl_FreeSurface
        try:
            if self.surface is not None:
                _sdl_FreeSurface(
                    <void*><uintptr_t>int(ctypes.addressof(self.surface.contents))
                )
        except (NameError, TypeError):
            pass  # probably unloading, ignore error
        finally:
            self.surface = None

    def to_texture(self, renderer):
        if renderer is None:
            raise ValueError("renderer cannot be None")
        initialize_sdl()
        if self._texture is None or \
                self._texture.is_unloaded() or \
                not self._texture.is_for_renderer(renderer):
            self._texture = Texture.new_from_sdl_surface(renderer,
                self.surface)
            self._apply_color()
        return self._texture

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, v):
        self.set_color(v)

    def set_color(self, c):
        self._color = Color(c)
        self._apply_color()

    def _apply_color(self):
        if self._texture is not None and not self._texture.is_unloaded():
            self._texture.set_color(self._color)

    def draw(self, renderer,
             int x, int y, w=None, h=None, color=None
             ):
        tex = self.to_texture(renderer)
        if w is None:
            w = self._render_size[0]
        if h is None:
            h = self._render_size[1]
        if color is not None:
            tex.set_color(color)
        tex.draw(x, y, w, h)

    @property
    def render_size(self):
        return tuple(self._render_size)

def image_as_grayscale(pil_image):
    if pil_image.mode.upper() == "RGBA":
        gray_image = pil_image.convert("LA")
        return gray_image
    elif pil_image.mode.upper() == "RGB":
        gray_image = pil_image.convert("L")
        return gray_image
    elif pil_image.mode.upper() == "L" or \
            pil_image.mode.upper() == "LA":
        return pil_image.copy()
    else:
        raise RuntimeError("unsupported mode: " +
            pil_image.mode)

def remove_image_alpha(pil_image):
    if pil_image.mode.upper() == "RGBA":
        no_alpha_img = PIL.Image.new("RGB",
            pil_image.size,
            (255, 255, 255))
        no_alpha_img.paste(pil_image,
            mask=pil_image.split()[3])
        return no_alpha_img
    elif pil_image.mode.upper() == "RGB":
        return pil_image.copy()
    else:
        raise RuntimeError("unsupported mode: " +
            pil_image.mode)

class ImageWidget(Widget):
    def __init__(self, pil_image,
            fit_to_width=None,
            fit_to_height=None):
        super().__init__()
        if type(pil_image) == str or type(pil_image) == bytes:
            pil_image = PIL.Image.open(pil_image)
        elif type(pil_image) == RenderImage:
            pil_image = pil_image.pil_image
        self._pil_image = pil_image.copy()
        self._pil_image_small = pil_image
        max_size = 4096
        if is_android():
            max_size = 1024
        (imgw, imgh) = self._pil_image_small.size
        if imgw > max_size or imgh > max_size:
            scaledown_w = (max_size / imgw)
            scaledown_h = (max_size / imgh)
            scaledown = min(scaledown_w, scaledown_h)
            self._pil_image_small = self._pil_image_small.resize(
                [max(1, round(imgw * scaledown)),
                max(1, round(imgh * scaledown))], PIL.Image.ANTIALIAS)
        self.fit_to_width = fit_to_width
        self.fit_to_height = fit_to_height
        self.render_image = None

    def __del__(self):
        if hasattr(super(), "__del__"):
            super().__del__()

    def update_renderer(self):
        super().update_renderer()

    def on_redraw(self):
        import sdl2 as sdl
        if self.renderer is None:
            return
        if self.render_image is None:
            self.render_image = RenderImage(self._pil_image_small)
        (imgw, imgh) = self._pil_image.size
        scale_w = (self.width / imgw)
        scale_h = (self.height / imgh)
        scale = min(scale_w, scale_h)
        sdl.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
        self.render_image.draw(self.renderer,
            0, 0, w=round(imgw * scale),
            h=round(imgh * scale))

    def get_natural_width(self):
        return self._natural_size()[0]

    def get_natural_height(self, given_width=None):
        (w, h) = self._natural_size()
        if w > given_width:
            reduce_f = (given_width / w)
            return round(h * reduce_f)
        return h

    def _natural_size(self):
        (w, h) = self._pil_image.size
        w *= self.dpi_scale
        h *= self.dpi_scale
        if self.fit_to_width != None:
            max_w = round(self.fit_to_width * self.dpi_scale)
            if w > max_w:
                reduce_f = (max_w / w)
                h = round(h * reduce_f)
                w = max_w
        if self.fit_to_height != None:
            max_h = round(self.fit_to_height * self.dpi_scale)
            if h > max_h:
                reduce_f = (max_h / h)
                w = round(w * reduce_f)
                h = max_h
        return (w, h)

