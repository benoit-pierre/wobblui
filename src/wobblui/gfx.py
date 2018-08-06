
import sdl2 as sdl

from wobblui.font.manager import font_manager

def draw_font(renderer, text, x, y,
        px_size=12, bold=False, italic=False,
        color=None):
    font = font_manager().get_font(name, bold=bold, italic=italic,
        px_size=px_size)
    if font != None:
        tex = font.render_text_as_sdl_texture(renderer, text, color)
        if tex != None:
            tg_rect = sdl.SDL_Rect() 
            tg_rect.x = x
            tg_rect.y = y
            tg_rect.w = 0
            tg_rect.h = 0
            sdl.SDL_RenderCopy(renderer, 
