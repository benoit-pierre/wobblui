
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
from wobblui.font.manager import font_manager
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
            if config.get("debug_texture_references"):
                logdebug("Texture._force_unload: " +
                    "definite dump of texture " + str(self))
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

_rect = sdl.SDL_Rect()
def draw_rectangle(renderer, x, y, w, h, color=None,
        filled=True, unfilled_border_thickness=1.0):
    global _rect
    if color is None:
        color = Color("#aaa")
    if not filled:
        border = max(1, round(unfilled_border_thickness))
        draw_rectangle(renderer,
            x, y, w, min(border, h),
            color=color, filled=True)
        draw_rectangle(renderer,
            x, y + h - border, w, min(border, h),
            color=color, filled=True)
        draw_rectangle(renderer,
            x, y, min(border, w), h,
            color=color, filled=True)
        draw_rectangle(renderer,
            x + w - min(border, w), y, min(border, w), h,
            color=color, filled=True)
        return
    _rect.x = max(0, round(x))
    _rect.y = max(0, round(y))
    _rect.w = round(abs(w) + min(0, x))
    _rect.h = round(abs(h) + min(0, y))
    if _rect.w <= 0 or _rect.h <= 0:
        return
    sdl.SDL_SetRenderDrawColor(renderer,
        round(color.red), round(color.green),
        round(color.blue), 255)
    sdl.SDL_RenderFillRect(renderer, _rect)

dash_tex_dashlength = 10
dash_tex_length = (dash_tex_dashlength * 100)
dash_tex_wide = 32
dashed_texture_store = dict()
def get_dashed_texture(renderer, vertical=False):
    global dashed_texture_store
    renderer_key = str(ctypes.addressof(renderer.contents))
    if (vertical, renderer_key) in dashed_texture_store:
        return dashed_texture_store[(vertical, renderer_key)]
    if not vertical:
        tex = sdl.SDL_CreateTexture(
            renderer, sdl.SDL_PIXELFORMAT_ARGB8888,
            sdl.SDL_TEXTUREACCESS_TARGET, dash_tex_length, dash_tex_wide)
    else:
        tex = sdl.SDL_CreateTexture(
            renderer, sdl.SDL_PIXELFORMAT_ARGB8888,
            sdl.SDL_TEXTUREACCESS_TARGET, dash_tex_wide, dash_tex_length)
    old_t = sdl.SDL_GetRenderTarget(renderer)
    assert(tex != None)
    if sdl.SDL_SetRenderTarget(renderer, tex) != 0:
        raise RuntimeError("failed to change render target: " +
            str(sdl.SDL_GetError()))
    sdl.SDL_SetRenderDrawColor(renderer, 0, 0, 0, 0)
    sdl.SDL_RenderClear(renderer)
    if not vertical:
        _draw_dashed_line_uncached(renderer,
            0, round(dash_tex_wide / 2), dash_tex_length,
            round(dash_tex_wide / 2),
            color=Color.white, dash_length=dash_tex_dashlength,
            thickness=round(dash_tex_wide * 1.5))
    else:
        _draw_dashed_line_uncached(renderer,
            round(dash_tex_wide / 2), 0,
            round(dash_tex_wide / 2), dash_tex_length,
            color=Color.white, dash_length=dash_tex_dashlength,
            thickness=round(dash_tex_wide * 1.5))

    sdl.SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255)
    sdl.SDL_SetRenderTarget(renderer, old_t)
    dashed_texture_store[(vertical, renderer_key)] = tex
    return tex

def clear_renderer(renderer):
    global dashed_texture_store
    renderer_key = str(ctypes.addressof(renderer.contents))
    new_dashed_store = dict()
    for entry in dashed_texture_store:
        if entry[1] == renderer_key:
            sdl.SDL_DestroyTexture(dashed_texture_store[entry])
            continue
        new_dashed_store[entry] = dashed_texture_store[entry]
    dashed_texture_store = new_dashed_store

def draw_dashed_line(
        renderer, x1, y1, x2, y2, color=None,
        dash_length=7.0, thickness=3.0):
    if abs(y1 - y2) > 0.5 and abs(x1 - x2) > 0.5:
        raise NotImplementedError("lines that aren't straight vertical or " +
            "horizontal aren't implemented yet")
    vertical = True
    if abs(x1 - x2) > abs(y1 - y2):
        vertical = False
    tex = get_dashed_texture(renderer, vertical=vertical)
    tex_stretch = (dash_length / float(dash_tex_dashlength))
    draw_x = min(x2, x1)
    draw_y = min(y2, y1)
    length = round(abs(y1 - y2))
    if not vertical:
        draw_y -= thickness / 2.0
        length = round(abs(x1 - x2))
    else:
        draw_x -= thickness / 2.0
    if length <= 0:
        return
    draw_x = round(draw_x)
    draw_y = round(draw_y)
    source_rect = sdl.SDL_Rect()
    target_rect = sdl.SDL_Rect()
    sdl.SDL_SetTextureColorMod(tex,
        color.red, color.blue, color.blue)
    offset = 0
    while offset < length:
        tex_target_uncut_length = max(1,
            round(tex_stretch * dash_tex_length))
        tex_target_length = max(1, min(length - offset,
            tex_target_uncut_length))
        tex_percentage_shown = tex_target_length / \
            float(tex_target_uncut_length)
        tex_source_length = max(1,
            round(tex_percentage_shown * dash_tex_length))
        tex_source_width = max(1, min(dash_tex_wide - 2, round(thickness)))
        tex_target_width = max(1, round(thickness))
        if vertical:
            source_rect.x = 1
            source_rect.y = 0
            source_rect.w = tex_source_width
            source_rect.h = tex_source_length
            target_rect.x = draw_x
            target_rect.y = draw_y + offset
            target_rect.w = tex_target_width
            target_rect.h = tex_target_length
            sdl.SDL_RenderCopy(renderer, tex, source_rect, target_rect)
        else:
            source_rect.x = 0
            source_rect.y = 1
            source_rect.w = tex_source_length
            source_rect.h = tex_source_width
            target_rect.x = draw_x + offset
            target_rect.y = draw_y
            target_rect.w = tex_target_length
            target_rect.h = tex_target_width
            sdl.SDL_RenderCopy(renderer, tex, source_rect, target_rect)
        offset += tex_target_length

def _draw_dashed_line_uncached(
        renderer, x1, y1, x2, y2, color=None,
        dash_length=7.0, thickness=3.0):
    perf_id = Perf.start('draw_drashed_line')
    if color is None:
        color = Color.black
    if abs(y1 - y2) > 0.5 and abs(x1 - x2) > 0.5:
        raise NotImplementedError("lines that aren't straight vertical or " +
            "horizontal aren't implemented yet")
    vertical = True
    start_v = y1
    end_v = y2
    if abs(y1 - y2) < abs(x1 - x2):
        vertical = False
        start_v = x1
        end_v = x2
    if end_v < start_v:
        v = end_v
        end_v = start_v
        start_v = v

    # Draw dashed line:
    x = round(x1 - thickness / 2.0)
    y = round(y1 - thickness / 2.0)
    w = round(thickness)
    h = round(thickness)
    curr_v = start_v
    while curr_v < end_v:
        if dash_length != None:
            next_dash_length = math.floor(
                min(dash_length, end_v - curr_v))
        else:
            next_dash_length = math.floor(curr_v - end_v)
        if vertical:
            y = round(curr_v)
            h = next_dash_length
        else:
            x = round(curr_v)
            w = next_dash_length
        draw_rectangle(renderer, x, y, w, h, color=color)
        if dash_length != None:
            curr_v += dash_length * 2.0
        else:
            curr_v = end_v + 1.0
    Perf.stop(perf_id)

def draw_line(renderer, x1, y1, x2, y2, color=None, thickness=3.0):
    draw_dashed_line(renderer, x1, y1, x2, y2, color=color,
        dash_length=None, thickness=thickness)

def draw_font(renderer, text, x, y,
        font_family="Sans Serif",
        px_size=12, bold=False, italic=False,
        color=None):
    font = font_manager().get_font(font_family,
        bold=bold, italic=italic,
        px_size=px_size)
    if font != None:
        (w, h, tex) = font.\
            get_cached_rendered_sdl_texture(renderer, text,
                color=Color.white)
        if tex != None:
            tg_rect = sdl.SDL_Rect() 
            tg_rect.x = x
            tg_rect.y = y
            tg_rect.w = w
            tg_rect.h = h
            sdl.SDL_SetTextureColorMod(tex,
                round(color.red), round(color.green), round(color.blue))
            sdl.SDL_RenderCopy(renderer, tex, None, tg_rect)

def get_draw_font_size(text,
        font_family="Sans Serif",
        px_size=12, bold=False, italic=False,
        color=None):
    font = font_manager().get_font(font_family,
        bold=bold, italic=italic,
        px_size=px_size)
    return font.render_size(text)
