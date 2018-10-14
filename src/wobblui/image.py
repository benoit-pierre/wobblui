
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
import sdl2 as sdl
import sdl2.sdlimage as sdlimage

from wobblui.osinfo import is_android
from wobblui.sdlinit import initialize_sdl
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

def image_to_sdl_surface(pil_image):
    global sdlimage_initialized
    initialize_sdl()
    if not sdlimage_initialized:
        flags = sdlimage.IMG_INIT_JPG|sdlimage.IMG_INIT_PNG
        sdlimage.IMG_Init(flags)
    sdl_image = None

    # Write image to ctypes buffer:
    bytes_obj = io.BytesIO()
    pil_image.save(bytes_obj, format="PNG")
    bytes_value = bytearray(bytes_obj.getvalue())
    if len(bytes_value) == 0:
        raise RuntimeError("saved image unexpectedly empty")
    ctypes_bytes = (ctypes.c_uint8 * len(bytes_value)).\
        from_buffer(bytes_value)

    # Create SDL RW Ops and load with SDL_Image from that:
    rwops = sdl.SDL_RWFromMem(ctypes.byref(ctypes_bytes),
        len(bytes_value))
    sdl_image = sdlimage.IMG_Load_RW(rwops, 1)

    # Handle error:
    if sdl_image is None:
        err_msg = sdlimage.IMG_GetError()
        try:
            err_msg = err_msg.decode("utf-8", "replace")
        except AttributeError:
            pass
        raise ValueError(
            "failed to load image with SDL Image: " +
            str(err_msg))
    return sdl_image

def image_to_sdl_texture(renderer, pil_image):
    initialize_sdl()
    sdl_image = image_to_sdl_surface(pil_image)
    try:
        texture = sdl.SDL_CreateTextureFromSurface(renderer, sdl_image)
    finally:
        sdl.SDL_FreeSurface(sdl_image)
    return texture

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
            pil_Image.mode)

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
        self.image_texture = None

    def update_renderer(self):
        if self.image_texture != None:
            sdl.SDL_DestroyTexture(self.image_texture)
            self.image_texture = None

    def on_redraw(self):
        if self.renderer is None:
            return
        if self.image_texture is None:
            self.image_texture = image_to_sdl_texture(
                self.renderer, self.pil_image_small)
        tg = sdl.SDL_Rect()
        tg.x = 0
        tg.y = 0
        (imgw, imgh) = self.pil_image.size
        scale_w = (self.width / imgw)
        scale_h = (self.height / imgh)
        scale = min(scale_w, scale_h)
        tg.w = round(imgw * scale)
        tg.h = round(imgh * scale)
        sdl.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
        sdl.SDL_RenderCopy(self.renderer, self.image_texture,
            None, tg)

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

