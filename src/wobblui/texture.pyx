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
import cython
import math
import sys
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


cdef _sdl_RenderCopyType _sdl_RenderCopy = NULL
cdef _sdl_SetRenderDrawColorType _sdl_SetRenderDrawColor = NULL
cdef _sdl_RenderClearType _sdl_RenderClear = NULL
cdef _sdl_SetRenderTargetType _sdl_SetRenderTarget = NULL
cdef _sdl_GetRenderTargetType _sdl_GetRenderTarget = NULL
cdef _sdl_DestroyTextureType _sdl_DestroyTexture = NULL
cdef object texture_render_rect_1, texture_render_rect_2
cdef ptrdiff_t texture_render_rect_1_addr, texture_render_rect_2_addr
texture_render_rect_1_addr = 0
texture_render_rect_2_addr = 0


cdef class Texture:
    def __init__(self, object renderer, int width, int height,
            int _dontcreate=False):
        if not renderer or renderer is None:
            raise ValueError("not a valid renderer, is None or " +
                "null pointer")
        global all_textures, sdl_tex_count

        # Make sure global functions are available:
        global _sdl_SetRenderDrawColor, _sdl_RenderCopy, _sdl_RenderClear
        global _sdl_SetRenderTarget, _sdl_GetRenderTarget,\
               _sdl_DestroyTexture
        if not _sdl_SetRenderDrawColor:
            import sdl2 as sdl
            _sdl_SetRenderDrawColor = <_sdl_SetRenderDrawColorType>(
                cython.operator.dereference(<ptrdiff_t*>(
                <ptrdiff_t>ctypes.addressof(sdl.SDL_SetRenderDrawColor)
                ))
            )
        self.sdl_func_set_render_draw_color = _sdl_SetRenderDrawColor
        if not _sdl_RenderCopy:
            import sdl2 as sdl
            _sdl_RenderCopy = <_sdl_RenderCopyType>(
                cython.operator.dereference(<ptrdiff_t*>(
                <ptrdiff_t>ctypes.addressof(sdl.SDL_RenderCopy)
                ))
            )
        self.sdl_func_render_copy = _sdl_RenderCopy
        if not _sdl_RenderClear:
            import sdl2 as sdl
            _sdl_RenderClear = <_sdl_RenderClearType>(
                cython.operator.dereference(<ptrdiff_t*>(
                <ptrdiff_t>ctypes.addressof(sdl.SDL_RenderClear)
                ))
            )
        if not _sdl_SetRenderTarget:
            import sdl2 as sdl
            _sdl_SetRenderTarget = <_sdl_SetRenderTargetType>(
                cython.operator.dereference(<ptrdiff_t*>(
                <ptrdiff_t>ctypes.addressof(sdl.SDL_SetRenderTarget)
                ))
            )
        if not _sdl_GetRenderTarget:
            import sdl2 as sdl
            _sdl_GetRenderTarget = <_sdl_GetRenderTargetType>(
                cython.operator.dereference(<ptrdiff_t*>(
                <ptrdiff_t>ctypes.addressof(sdl.SDL_GetRenderTarget)
                ))
            )
        if not _sdl_DestroyTexture:
            import sdl2 as sdl
            _sdl_DestroyTexture = <_sdl_DestroyTextureType>(
                cython.operator.dereference(<ptrdiff_t*>(
                <ptrdiff_t>ctypes.addressof(sdl.SDL_DestroyTexture)
                ))
            )

        self._texture = None
        self.texture_address = 0
        self.renderer = renderer
        self.renderer_address = <ptrdiff_t>(
            ctypes.addressof(self.renderer.contents)
        )
        if not _dontcreate:
            import sdl2 as sdl
            sdl_tex_count += 1
            self._texture = sdl.SDL_CreateTexture(
                self.renderer,
                sdl.SDL_PIXELFORMAT_RGBA8888,
                0,
                width, height)
            if self._texture is None:
                self.texture_address = 0
                raise RuntimeError("texture creation " +
                    "unexpectedly failed!")
            self.texture_address = <ptrdiff_t>(
                ctypes.addressof(self.renderer.contents)
            )
            sdl.SDL_SetTextureBlendMode(self._texture,
                sdl.SDL_BLENDMODE_BLEND)
        self.width = width
        self.height = height
        all_textures.append(weakref.ref(self))

    def is_for_renderer(self, renderer):
        cdef ptrdiff_t other_renderer_addr = <ptrdiff_t>(
            ctypes.addressof(renderer.contents)
        )
        if self.renderer_address != other_renderer_addr:
            return False
        return True

    def is_unloaded(self):
        return (self._texture is None)

    def set_color(self, o):
        import sdl2 as sdl
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
        return ("<Texture " + str((str(id(self)), self.width,
                self.height)) +
                (" UNLOADED" if self._texture is None else "") +
                ">")

    def draw(self, int x, int y, w=None, h=None):
        global texture_render_rect_1, texture_render_rect_2, \
            texture_render_rect_1_addr, texture_render_rect_2_addr
        if (w != None and w <= 0) or (
                h != None and h <= 0):
            return
        if self.texture_address == 0 or self.renderer_address == 0:
            raise ValueError("invalid dumped texture. " +
                "did you observe renderer_update()??")
        if texture_render_rect_1_addr == 0:
            import sdl2 as sdl
            texture_render_rect_1 = sdl.SDL_Rect()
            texture_render_rect_2 = sdl.SDL_Rect()
            texture_render_rect_1_addr = <ptrdiff_t>(
                ctypes.addressof(texture_render_rect_1)
            )
            texture_render_rect_2_addr = <ptrdiff_t>(
                ctypes.addressof(texture_render_rect_2)
            )
        r1 = texture_render_rect_1
        r2 = texture_render_rect_2
        r1.x = round(x)
        r1.y = round(y)
        r1.w = max(1, round(w or self.width))
        r1.h = max(1, round(h or self.height))
        r2.x = 0
        r2.y = 0
        r2.w = self.width
        r2.h = self.height
        cdef ptrdiff_t renderer_address = self.renderer_address
        cdef ptrdiff_t texture_address = self.texture_address
        cdef ptrdiff_t r1_address = texture_render_rect_1_addr
        cdef ptrdiff_t r2_address = texture_render_rect_2_addr
        cdef _sdl_SetRenderDrawColorType setrendercolor =\
            self.sdl_func_set_render_draw_color
        cdef _sdl_RenderCopyType rendercopy = self.sdl_func_render_copy
        with nogil:
            setrendercolor(
                <void*>renderer_address, 255, 255, 255, 255
            )
            rendercopy(
                <void*>renderer_address,
                <void*>texture_address,
                <void*>r2_address,
                <void*>r1_address
            )

    def _force_unload(self):
        import sdl2 as sdl
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
                    _sdl_DestroyTexture(<void*>self.texture_address)
                except (NameError, TypeError, AttributeError):
                    # Most likely, we're shutting down -> SDL already gone
                    print("warning: texture unload failed. "
                          "are some modules already unloaded?",
                          file=sys.stderr)
                self._texture = None
                self.texture_address = 0

    def __dealloc__(self):
        self._force_unload()

    def internal_clean_if_renderer(self, renderer):
        if not self.is_for_renderer(renderer):
            return
        self._force_unload()

    def set_as_rendertarget(self):
        raise TypeError("this is not a render target")

    def unset_as_rendertarget(self):
        raise TypeError("this is not a render target")

    @staticmethod
    def new_from_sdl_surface(renderer, srf):
        import sdl2 as sdl
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
        tex.texture_address = <ptrdiff_t>(
            ctypes.addressof(tex._texture.contents)
        )
        return tex

cdef class RenderTarget(Texture):
    def __init__(self, renderer, width, height):
        import sdl2 as sdl
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
            self.texture_address = 0
            raise RuntimeError("render target creation " +
                "unexpectedly failed!")
        self.texture_address = <ptrdiff_t>(
            ctypes.addressof(self._texture.contents)
        )
        sdl.SDL_SetTextureBlendMode(self._texture,
            sdl.SDL_BLENDMODE_BLEND)

    def __dealloc__(self):
        if self.set_as_target:
            import sdl2 as sdl
            sdl.SDL_SetRenderTarget(self.renderer, None)
        try:
            self._force_unload()
        finally:
            self.set_as_target = False

    def draw(self, x, y, w=None, h=None):
        assert(x != None and y != None)
        if not self.ever_rendered_to:
            raise RuntimeError("RenderTarget was never used - " +
                "this would draw uninitialized memory!!")
        super().draw(x, y, w=w, h=h)

    def set_as_rendertarget(self, clear=True):
        global _SDL_RenderClear
        global _sdl_SetRenderTarget, _sdl_GetRenderTarget
        if self._texture is None or self.renderer is None:
            raise ValueError("invalid render target, " +
                "was cleaned up. did you observe renderer_update()??")
        if self.set_as_target:
            raise ValueError("this is already set as render target!")

        cdef ptrdiff_t renderer_address = (<ptrdiff_t>(
            ctypes.addressof(self.renderer.contents)
        ))
        cdef ptrdiff_t texture_address = (<ptrdiff_t>(
            ctypes.addressof(self._texture.contents)
        ))
        cdef _sdl_SetRenderDrawColorType set_render_draw_color = NULL
        cdef _sdl_RenderClearType render_clear = NULL

        self.set_as_target = True
        self.previous_target = (<ptrdiff_t>_sdl_GetRenderTarget(
            <void*>renderer_address
        ))
        _sdl_SetRenderTarget(<void*>renderer_address, <void*>texture_address)
        self.ever_rendered_to = True
        if clear:
            set_render_draw_color = self.sdl_func_set_render_draw_color
            render_clear = _sdl_RenderClear
            with nogil:
                set_render_draw_color(<void*>renderer_address, 0, 0, 0, 0)
                render_clear(<void*>renderer_address)
                set_render_draw_color(
                    <void*>renderer_address, 255,
                    255,255,255
                )

    def unset_as_rendertarget(self):
        global _sdl_SetRenderDrawColor
        global _sdl_SetRenderTarget, _sdl_GetRenderTarget
        if self._texture is None or self.renderer is None:
            raise ValueError("invalid render target, " +
                "was cleaned up. did you observe renderer_update()??")
        if not self.set_as_target:
            raise ValueError("this is not set as render target yet!")
        self.set_as_target = False
        cdef ptrdiff_t renderer_address = (<ptrdiff_t>(
            ctypes.addressof(self.renderer.contents)
        ))
        cdef ptrdiff_t prevtarget_address = (<ptrdiff_t>(self.previous_target))
        _sdl_SetRenderTarget(<void*>renderer_address,
                             <void*>prevtarget_address)
        _sdl_SetRenderDrawColor(
            <void*>renderer_address, 255, 255, 255, 255
        )

