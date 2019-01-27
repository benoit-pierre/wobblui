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
import math
import sdl2 as sdl
import weakref

from wobblui.color import Color
from wobblui.perf cimport CPerf as Perf
from wobblui.uiconf import config
from wobblui.woblog import logdebug, logerror, loginfo, logwarning

all_textures = []
sdl_tex_count = 0

def mark_textures_invalid(sdl_renderer):
    global all_textures
    new_refs = []
    for tex_ref in all_textures:
        tex = tex_ref()
        if tex is None:
            continue
        new_refs.append(tex_ref)
        tex.internal_clean_if_renderer(sdl_renderer)
    all_textures[:] = new_refs

cdef class Texture(object):
    def __init__(self, object renderer, int width, int height,
            int _dontcreate=False):
        if not renderer or renderer is None:
            raise ValueError("not a valid renderer, is None or " +
                "null pointer")
        global all_textures, sdl_tex_count
        self._texture = None
        self.renderer = renderer
        self.renderer_key = str(ctypes.addressof(self.renderer.contents))
        if not _dontcreate:
            sdl_tex_count += 1
            self._texture = sdl.SDL_CreateTexture(
                self.renderer,
                sdl.SDL_PIXELFORMAT_RGBA8888,
                0,
                width, height)
            if self._texture is None:
                raise RuntimeError("texture creation " +
                    "unexpectedly failed!")
        self.width = width
        self.height = height
        all_textures.append(weakref.ref(self))

    def is_for_renderer(self, renderer):
        renderer_cmp_key = str(
            ctypes.addressof(renderer))
        if self.renderer_key != renderer_cmp_key:
            return False
        return True

    def is_unloaded(self):
        return (self._texture is None)

    def set_color(self, o):
        if isinstance(o, Color):
            sdl.SDL_SetTextureColorMod(
                self._texture, o.value_red, o.value_green, o.value_blue)
        elif len(o) == 3:
            sdl.SDL_SetTextureColorMod(
                self._texture, round(o[0]), round(o[1]), round(o[2]))
        else:
            raise ValueError("color value must be wobblui.color.Color " +
                "or tuple")

    def __repr__(self):
        return "<Texture " + str((str(id(self)), self.width,
                self.height)) + ">"

    def draw(self, int x, int y, w=None, h=None):
        if (w != None and w <= 0) or (
                h != None and h <= 0):
            return
        if self._texture is None or self.renderer is None:
            raise ValueError("invalid dumped texture. " +
                "did you observe renderer_update()??")
        tg = sdl.SDL_Rect()
        tg.x = round(x)
        tg.y = round(y)
        tg.w = max(1, round(w or self.width))
        tg.h = max(1, round(h or self.height))
        src = sdl.SDL_Rect()
        src.x = 0
        src.y = 0
        src.w = self.width
        src.h = self.height
        sdl.SDL_SetRenderDrawColor(self.renderer,
            255, 255, 255, 255)
        sdl.SDL_RenderCopy(self.renderer, self._texture, src, tg)

    def _force_unload(self):
        global sdl_tex_count
        if self._texture is not None:
            try:
                if config.get("debug_texture_references"):
                    logdebug("Texture._force_unload: " +
                        "definite dump of texture " + str(self) +
                        ", total still loaded: " + str(sdl_tex_count))
            finally:
                if sdl_tex_count is not None:
                    sdl_tex_count -= 1
                try:
                    sdl.SDL_DestroyTexture(self._texture)
                except (TypeError, AttributeError):
                    # Most likely, we're shutting down -> SDL already gone
                    pass
                self._texture = None

    def __del__(self):
        self._force_unload()

    def __dealloc__(self):
        self._force_unload()

    def internal_clean_if_renderer(self, renderer):
        if self.renderer_key != str(
                ctypes.addressof(self.renderer.contents)):
            return
        self._force_unload()

    def set_as_rendertarget(self):
        raise TypeError("this is not a render target")

    def unset_as_rendertarget(self):
        raise TypeError("this is not a render target")

    @staticmethod
    def new_from_sdl_surface(renderer, srf):
        global sdl_tex_count
        if not renderer:
            raise ValueError("need a valid renderer! not NULL / None, " +
                "got: " + str(renderer))
        if not srf:
            raise ValueError("need valid surface! not NULL / None")
        tex = Texture(renderer, srf.contents.w, srf.contents.h,
            _dontcreate=True)
        sdl_tex_count += 1
        assert(tex._texture is None)
        tex._texture = sdl.SDL_CreateTextureFromSurface(renderer, srf)
        return tex

cdef class RenderTarget(Texture):
    def __init__(self, renderer, width, height):
        global sdl_tex_count
        super().__init__(renderer, width, height, _dontcreate=True)
        self.set_as_target = False
        self.previous_target = None
        self.ever_rendered_to = False
        sdl_tex_count += 1
        assert(self._texture is None)
        self._texture = sdl.SDL_CreateTexture(
            renderer,
            sdl.SDL_PIXELFORMAT_RGBA8888,
            sdl.SDL_TEXTUREACCESS_TARGET,
            width, height)
        if self._texture is None:
            raise RuntimeError("render target creation " +
                "unexpectedly failed!")
        sdl.SDL_SetTextureBlendMode(self._texture,
            sdl.SDL_BLENDMODE_BLEND)

    def __del__(self):
        if self.set_as_target:
            sdl.SDL_SetRenderTarget(self.renderer, None)
        self.set_as_target = False
        super().__del__()

    def __dealloc__(self):
        if self.set_as_target:
            sdl.SDL_SetRenderTarget(self.renderer, None)
        self.set_as_target = False

    def draw(self, x, y, w=None, h=None):
        assert(x != None and y != None)
        if not self.ever_rendered_to:
            raise RuntimeError("RenderTarget was never used - " +
                "this would draw uninitialized memory!!")
        super().draw(x, y, w=w, h=h)

    def set_as_rendertarget(self, clear=True):
        if self._texture is None or self.renderer is None:
            raise ValueError("invalid render target, " +
                "was cleaned up. did you observe renderer_update()??")
        if self.set_as_target:
            raise ValueError("this is already set as render target!")
        self.set_as_target = True
        self.previous_target = sdl.SDL_GetRenderTarget(self.renderer)
        sdl.SDL_SetRenderTarget(self.renderer, self._texture)
        self.ever_rendered_to = True
        if clear:
            sdl.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 0)
            sdl.SDL_RenderClear(self.renderer)
            sdl.SDL_SetRenderDrawColor(self.renderer, 255,
                255,255,255)

    def unset_as_rendertarget(self):
        if self._texture is None or self.renderer is None:
            raise ValueError("invalid render target, " +
                "was cleaned up. did you observe renderer_update()??")
        if not self.set_as_target:
            raise ValueError("this is not set as render target yet!")
        self.set_as_target = False
        sdl.SDL_SetRenderTarget(self.renderer, self.previous_target)
        sdl.SDL_SetRenderDrawColor(self.renderer,
            255, 255, 255, 255)

