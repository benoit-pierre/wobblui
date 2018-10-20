
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
from wobblui.perf import Perf
from wobblui.uiconf import config
from wobblui.woblog import logdebug, logerror, loginfo, logwarning

all_textures = []

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

class Texture(object):
    def __init__(self, renderer, width, height, _dontcreate=False):
        if renderer is None:
            raise ValueError("not a valid renderer, is None")
        global all_textures
        self._texture = None
        self.renderer = renderer
        self.renderer_key = str(ctypes.addressof(self.renderer.contents))
        if not _dontcreate:
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

    def __repr__(self):
        return "<Texture " + str((str(id(self)), self.width,
                self.height)) + ">"

    def draw(self, x, y, w=None, h=None):
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
        if hasattr(self, "_texture") and self._texture != None:
            try:
                if config.get("debug_texture_references"):
                    logdebug("Texture._force_unload: " +
                        "definite dump of texture " + str(self))
            finally:
                sdl.SDL_DestroyTexture(self._texture)
                self._texture = None

    def __del__(self):
        self._force_unload()

    def internal_clean_if_renderer(self, renderer):
        if self.renderer_key != str(
                ctypes.addressof(self.renderer.contents)):
            return
        self._force_unload()

    def set_as_rendertarget(self):
        raise TypeError("this is not a render target")

    def unset_as_rendertarget(Self):
        raise TypeError("this is not a render target")

    @staticmethod
    def new_from_sdl_surface(renderer, srf):
        if not renderer:
            raise ValueError("need a valid renderer! not NULL / None")
        if not srf:
            raise ValueError("need valid surface! not NULL / None")
        tex = Texture(renderer, srf.contents.w, srf.contents.h,
            _dontcreate=True)
        tex._texture = sdl.SDL_CreateTextureFromSurface(renderer, srf)
        return tex

class RenderTarget(Texture):
    def __init__(self, renderer, width, height):
        super().__init__(renderer, width, height, _dontcreate=True)
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
        self.set_as_target = False
        self.previous_target = None
        self.ever_rendered_to = False

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

