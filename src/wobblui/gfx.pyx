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
from libc.stdint cimport uintptr_t
import math
import weakref

from wobblui.color cimport Color
from wobblui.font.manager cimport c_font_manager as font_manager
from wobblui.perf cimport CPerf as Perf
from wobblui.render_lock cimport can_renderer_safely_be_used
from wobblui.uiconf import config
from wobblui.woblog cimport logdebug, logerror, loginfo, logwarning


cdef _sdl_DestroyTextureType _sdl_DestroyTexture = NULL

cdef _load_function_ptrs():
    global _sdl_DestroyTexture
    if not _sdl_DestroyTexture:
        import sdl2 as sdl
        _sdl_DestroyTexture = <_sdl_DestroyTextureType>(
            cython.operator.dereference(<uintptr_t*>(
            <uintptr_t>ctypes.addressof(sdl.SDL_DestroyTexture)
            ))
        )


_rect = None
cpdef draw_rectangle(
        renderer,
        int x, int y, int w, int h,
        object color=None,
        int filled=True,
        double unfilled_border_thickness=1.0,
        double alpha=1.0):
    global _rect
    if not can_renderer_safely_be_used(
            <uintptr_t>ctypes.addressof(renderer.contents)
            ):
        raise RuntimeError("cannot draw now, "
                           "hardware context unavailable")
    import sdl2 as sdl
    if _rect is None:
        _rect = sdl.SDL_Rect()
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
    sdl.SDL_SetRenderDrawColor(
        renderer,
        round(color.value_red),
        round(color.value_green),
        round(color.value_blue),
        max(0, min(255, round(255.0 * alpha)))
        )
    sdl.SDL_SetRenderDrawBlendMode(
        renderer, sdl.SDL_BLENDMODE_BLEND)
    sdl.SDL_RenderFillRect(renderer, _rect)

dash_tex_dashlength = 10
dash_tex_length = (dash_tex_dashlength * 100)
dash_tex_wide = 32
dashed_texture_store = dict()
cdef get_dashed_texture(renderer, int vertical=False):
    global dashed_texture_store
    _load_function_ptrs()
    if not can_renderer_safely_be_used(
            <uintptr_t>ctypes.addressof(renderer.contents)
            ):
        raise RuntimeError("cannot draw now, "
                           "hardware context unavailable")
    import sdl2 as sdl
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
            color=Color.white(), dash_length=dash_tex_dashlength,
            thickness=round(dash_tex_wide * 1.5))
    else:
        _draw_dashed_line_uncached(renderer,
            round(dash_tex_wide / 2), 0,
            round(dash_tex_wide / 2), dash_tex_length,
            color=Color.white(), dash_length=dash_tex_dashlength,
            thickness=round(dash_tex_wide * 1.5))

    sdl.SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255)
    sdl.SDL_SetRenderTarget(renderer, old_t)
    dashed_texture_store[(vertical, renderer_key)] = tex
    return tex

cpdef clear_renderer_gfx(renderer):
    global dashed_texture_store
    if not can_renderer_safely_be_used(
            <uintptr_t>ctypes.addressof(renderer.contents)
            ):
        raise RuntimeError("cannot draw now, "
                           "hardware context unavailable")
    _load_function_ptrs()
    renderer_key = str(ctypes.addressof(renderer.contents))
    new_dashed_store = dict()
    for entry in dashed_texture_store:
        if entry[1] == renderer_key:
            _sdl_DestroyTexture(<void*><uintptr_t>ctypes.addressof(
                dashed_texture_store[entry].contents
            ))
            continue
        new_dashed_store[entry] = dashed_texture_store[entry]
    dashed_texture_store = new_dashed_store

cpdef draw_dashed_line(
        object renderer,
        int x1, int y1, int x2, int y2,
        object color=None,
        double dash_length=7.0,
        double thickness=3.0):
    _load_function_ptrs()
    if not can_renderer_safely_be_used(
            <uintptr_t>ctypes.addressof(renderer.contents)
            ):
        raise RuntimeError("cannot draw now, "
                           "hardware context unavailable")
    import sdl2 as sdl
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
        color.value_red, color.value_green, color.value_blue)
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

cdef _draw_dashed_line_uncached(
        object renderer,
        int x1, int y1, int x2, int y2,
        object color=None,
        double dash_length=7.0,
        double thickness=3.0):
    perf_id = Perf.start('draw_drashed_line')
    if color is None:
        color = Color.black()
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
        if dash_length >= 0:
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
        if dash_length >= 0:
            curr_v += dash_length * 2.0
        else:
            curr_v = end_v + 1.0
    Perf.stop(perf_id)

cpdef draw_line(object renderer,
        int x1, int y1, int x2, int y2,
        object color=None,
        double thickness=3.0):
    draw_dashed_line(renderer, x1, y1, x2, y2, color=color,
        dash_length=-1, thickness=thickness)

cpdef draw_font(renderer, text, x, y,
        font_family="Sans Serif",
        px_size=12, bold=False, italic=False,
        color=None):
    font = font_manager().get_font(font_family,
        bold=bold, italic=italic,
        px_size=px_size)
    if font != None:
        tex = font.\
            get_cached_rendered_texture(renderer, text)
        if color is None:
            color = Color.white()
        tex.set_color(color)
        tex.draw(round(x), round(y))

cpdef is_font_available(font_family, bold=False, italic=False):
    try:
        f = font_manager().get_font(font_family, bold=bold, italic=italic)
        # intentionally unused, will cause error if no such font:
        sdlf = f.get_sdl_font()
    except ValueError:
        return False
    return True

cpdef get_draw_font_size(text,
        font_family="Sans Serif",
        px_size=12, bold=False, italic=False,
        color=None):
    font = font_manager().get_font(font_family,
        bold=bold, italic=italic,
        px_size=px_size)
    return font.render_size(text)

cdef int clipping_is_enabled(object renderer):
    import sdl2 as sdl
    try:
        return (sdl.SDL_RenderIsClipEnabled() == 1)
    except AttributeError:
        # Old PySDL2 versions
        r = sdl.SDL_Rect()
        sdl.SDL_RenderGetClipRect(
            renderer,
            ctypes.byref(r))
        if r.w <=0 and r.h <= 0:
            return False
        return True

previous_clip_stacks_by_renderer = dict()
cpdef push_render_clip(renderer, _x, _y, _w, _h):
    global previous_clip_stacks_by_renderer
    if not can_renderer_safely_be_used(
            <uintptr_t>ctypes.addressof(renderer.contents)
            ):
        raise RuntimeError("cannot use drawing operation, "
                           "hardware context unavailable")
    import sdl2 as sdl

    cdef int x, y, w, h
    x = round(_x)
    y = round(_y)
    w = round(_w)
    h = round(_h)

    renderer_key = str(ctypes.addressof(renderer.contents))
    if renderer_key not in previous_clip_stacks_by_renderer:
        previous_clip_stacks_by_renderer[renderer_key] =\
            list()
    cdef list previous_clip_stack = \
        previous_clip_stacks_by_renderer[renderer_key]

    if clipping_is_enabled(renderer):
        previous_clip_r = sdl.SDL_Rect()
        sdl.SDL_RenderGetClipRect(
            renderer,
            ctypes.byref(previous_clip_r))
        previous_clip_stack.append((
            previous_clip_r.x, previous_clip_r.y,
            previous_clip_r.w, previous_clip_r.h
        ))
        del(previous_clip_r)
    if len(previous_clip_stack) > 0:
        for previous_clip in previous_clip_stack:
            if x < previous_clip[0]:
                move_amount = max(previous_clip[0], x) - x
                x += move_amount
                w = max(0, w - move_amount)
            if y < previous_clip[1]:
                move_amount = max(previous_clip[1], y) - y
                y += move_amount
                h = max(1, h - move_amount)
            w = min(
                max(0, previous_clip[2] - max(0, x - previous_clip[0])),
                w
                )
            h = min(
                max(0, previous_clip[3] - max(0, y - previous_clip[1])),
                h
                )
    _apply_clip_rect(renderer, x, y, w, h)

cdef _apply_clip_rect(object renderer, int x, int y, int w, int h):
    if not can_renderer_safely_be_used(
            <uintptr_t>ctypes.addressof(renderer.contents)
            ):
        raise RuntimeError("cannot use drawing operation, "
                           "hardware context unavailable")
    import sdl2 as sdl
    new_clip = sdl.SDL_Rect()
    new_clip.x = x
    new_clip.y = y
    new_clip.w = max(0, w)
    new_clip.h = max(0, h)
    if sdl.SDL_RenderSetClipRect(renderer, new_clip) != 0:
        raise RuntimeError("failed to apply clip rect")

cpdef pop_render_clip(renderer):
    global previous_clip_stacks_by_renderer
    if not can_renderer_safely_be_used(
            <uintptr_t>ctypes.addressof(renderer.contents)
            ):
        raise RuntimeError("cannot use drawing operation, "
                           "hardware context unavailable")
    import sdl2 as sdl

    renderer_key = str(ctypes.addressof(renderer.contents))
    if renderer_key not in previous_clip_stacks_by_renderer:
        previous_clip_stacks_by_renderer[renderer_key] =\
            list()
    cdef list previous_clip_stack = \
        previous_clip_stacks_by_renderer[renderer_key]

    if len(previous_clip_stack) > 0:
        _apply_clip_rect(renderer,
            previous_clip_stack[-1][0],
            previous_clip_stack[-1][1],
            previous_clip_stack[-1][2],
            previous_clip_stack[-1][3])
        previous_clip_stack = previous_clip_stack[:-1]
    else:
        if not clipping_is_enabled(renderer):
            raise RuntimeError("no clipping active")
        sdl.SDL_RenderSetClipRect(renderer, None)
        if clipping_is_enabled(renderer):
            raise RuntimeError("internal error: " +
                "unexpectedly failed to clear clip")
