
import sdl2 as sdl

from wobblui.color import Color
from wobblui.font.manager import font_manager

def draw_rectangle(renderer, x, y, w, h, color=None):
    if color is None:
        color = Color("#aaa")
    rect = sdl.SDL_Rect()
    rect.x = max(0, round(x))
    rect.y = max(0, round(y))
    rect.w = round(abs(w))
    rect.h = round(abs(h))
    sdl.SDL_SetRenderDrawColor(renderer,
        round(color.red), round(color.green),
        round(color.blue), 255)
    sdl.SDL_RenderFillRect(renderer, rect)

def draw_font(renderer, text, x, y,
        px_size=12, bold=False, italic=False,
        color=None):
    font = font_manager().get_font(name, bold=bold, italic=italic,
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

