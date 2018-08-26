
import math
import sdl2 as sdl

from wobblui.color import Color
from wobblui.font.manager import font_manager

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
            x + w - min(border, w), y, h, border,
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

def draw_dashed_line(renderer, x1, y1, x2, y2, color=None,
        dash_length=7.0, thickness=3.0):
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
        tex = font.render_text_as_sdl_texture(renderer, text, color)
        if tex != None:
            w = ctypes.c_int32()
            h = ctypes.c_int32()
            sdl.SDL_QueryTexture(tex, None, None,
                ctypes.byref(w), ctypes.byref(h))
            tg_rect = sdl.SDL_Rect() 
            tg_rect.x = x
            tg_rect.y = y
            tg_rect.w = w.value
            tg_rect.h = h.value
            sdl.SDL_RenderCopy(renderer, tex, None, tg)
            sdl.SDL_DestroyTexture(tex)

