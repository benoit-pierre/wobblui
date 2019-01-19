#cython: language_level=3

'''
wobblui - Copyright 2018 wobblui team, see AUTHORS.md

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
import io
import os
import PIL.Image
import PIL.ImageDraw
import platform
import sdl2 as sdl
import sdl2.sdlimage as sdlimage
import time

from wobblui.color cimport Color
from wobblui.osinfo import is_android
from wobblui.sdlinit cimport initialize_sdl
from wobblui.texture cimport Texture
from wobblui.widget import Widget

sdlimage_initialized = False

def stock_image(name):
    p = os.path.join(os.path.abspath(os.path.dirname(__file__)),
        "img", name)
    if name.find(".") < 0:
        if os.path.exists(p + ".png"):
            return (p + ".png")
        elif os.path.exists(p + ".jpg"):
            return (p + ".jpg")
    return p

def _internal_image_to_sdl_surface(pil_image, retries=5):
    global sdlimage_initialized
    initialize_sdl()
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
            return _internal_image_to_sdl_surface(
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

cdef class RenderImage(object):
    def __init__(self, object pil_image, render_low_res=False):
        initialize_sdl()
        self.surface = None
        self.pil_image = pil_image.copy()
        self.render_size = tuple(self.pil_image.size)
        self.render_low_res = (render_low_res is True)
        self._color = Color.white()
        self.force_update_image()

    @classmethod
    def new_from_size(self, width, height):
        if round(width) <= 0 or round(height) <= 0:
            raise RuntimeError("invalid image size: " +
                str((width, height)))
        pil_image = PIL.Image.new('RGBA', (max(1,round(width)),
            max(1, round(height))), (0, 0, 0, 0))
        return RenderImage(pil_image, render_low_res=False)

    def force_update_image(self):
        if self.surface is not None:
            sdl.SDL_FreeSurface(self.surface)
            self.surface = None
        self.pil_image_scaled = None
        if self.render_low_res:
            (w, h) = self.pil_image.size
            scale_f = (512 + 512) / (w + h)
            new_w = max(1, round(w * scale_f))
            new_h = max(1, round(h * scale_f))
            if scale_f < 0.95 and (new_w != w or new_h != h):
                self.pil_image_scaled = self.pil_image.resize(
                    (new_w, new_h))
        if self.pil_image_scaled is None:
            self.surface = _internal_image_to_sdl_surface(
                self.pil_image)
            
        else:
            self.surface = _internal_image_to_sdl_surface(
                self.pil_image_scaled)
        self._texture = None

    def draw_filled_rectangle_onto_image(self,
            x, y, w, h, color=Color.black(),
            alpha=255):
        draw = PIL.ImageDraw.Draw(self.pil_image)
        draw.rectangle((round(x), round(y),
            max(0, round(w)), max(0, round(h))),
            fill=(
            color.value_red, color.value_green, color.value_blue,
            255))
        self.force_update_image()

    def as_png(self):
        byteobj = io.BytesIO()
        self.pil_image.save(byteobj, format="PNG")
        byteobj.flush()
        return byteobj.getvalue()

    def __dealloc__(self):
        if self.surface is not None:
            sdl.SDL_FreeSurface(self.surface)
        self.surface = None

    def to_texture(self, renderer):
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

    def draw(self, renderer, int x, int y, w=None, h=None):
        tex = self.to_texture(renderer)
        if w is None:
            w = self.render_size[0]
        if h is None:
            h = self.render_size[1]
        tex.draw(x, y, w, h)

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
        self.pil_image = pil_image.copy()
        self.pil_image_small = pil_image
        max_size = 4096
        if is_android():
            max_size = 1024
        (imgw, imgh) = self.pil_image_small.size
        if imgw > max_size or imgh > max_size:
            scaledown_w = (max_size / imgw)
            scaledown_h = (max_size / imgh)
            scaledown = min(scaledown_w, scaledown_h)
            self.pil_image_small = self.pil_image_small.resize(
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
        if self.renderer is None:
            return
        if self.render_image is None:
            self.render_image = RenderImage(self.pil_image_small)
        (imgw, imgh) = self.pil_image.size
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
        (w, h) = self.pil_image.size
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

