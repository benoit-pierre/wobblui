
import ctypes
import sdl2 as sdl
import sdl2.sdlttf as sdlttf
import time

from wobblui.cache import KeyValueCache
from wobblui.color import Color

text_length_cache = KeyValueCache(size=5000)
glyph_cache = KeyValueCache(size=1000,
    destroy_func=lambda x: x.clear())
glyphs_created = 0
glyphs_cache_miss = 0
glyphs_cache_hits = 0

_reuse_rect = sdl.SDL_Rect()
class Glyph(object):
    def __init__(self, glyph, font):
        self._sdl_textures = dict()
        self.font_family = font.font_family
        self.bold = font.bold
        self.italic = font.italic
        self.px_size = font.pixel_size
        self.glyph = str(glyph + "")

    def texture_for_renderer(self, renderer, font):
        global glyphs_created
        renderer_key = str(ctypes.addressof(renderer.contents))
        if renderer_key in self._sdl_textures and \
                self._sdl_textures[renderer_key] != None:
            return self._sdl_textures[renderer_key]
        self._sdl_textures[renderer_key] =\
            font.render_text_as_sdl_texture(
            renderer, self.glyph, color=Color.white)
        glyphs_created += 1
        return self._sdl_textures[renderer_key]

    def draw(self, renderer, font, x, y, color=Color.white):
        global _reuse_rect
        tex = self.texture_for_renderer(renderer, font)
        w = ctypes.c_int32()
        h = ctypes.c_int32()
        w.value = 0
        h.value = 0
        sdl.SDL_QueryTexture(tex, None, None,
            ctypes.byref(w), ctypes.byref(h))
        _reuse_rect.x = x
        _reuse_rect.y = y
        _reuse_rect.w = w.value
        _reuse_rect.h = h.value
        sdl.SDL_SetTextureColorMod(tex,
            color.red, color.green, color.blue)
        sdl.SDL_RenderCopy(renderer, tex, None, _reuse_rect)

    def clear_renderer(self, renderer):
        renderer_key = str(renderer.contents)
        if renderer_key in self._sdl_textures and \
                self._sdl_textures[renderer_key] != None:
            sdl.SDL_DestroyTexture(self._sdl_textures[renderer_key])
            self._sdl_textures[renderer_key] = None    

    def clear(self):
        for k in self._sdl_textures:
            if self._sdl_textures[k] != None:
                sdl.SDL_DestroyTexture(self._sdl_textures[k])
                self._sdl_textures[k] = None

    def __del__(self):
        self.clear()

def _get_glyph(renderer, glyph_text, font):
    global glyph_cache, glyphs_cache_miss, glyphs_cache_hits
    glyph_key = (glyph_text, font.font_family, font.bold,
        font.italic, font.pixel_size)
    glyph = glyph_cache.get(glyph_key)
    if glyph is None:
        glyphs_cache_miss += 1
        glyph = Glyph(glyph_text, font)
        glyph_cache.add(glyph_key, glyph)
    else:
        glyphs_cache_hits += 1
    return glyph

last_debug_output = 0
class GlobalFontDrawer(object):
    @classmethod
    def draw_with_font(cls, renderer, font, text,
            x, y, color=Color.white):
        global glyphs_created, last_debug_output, glyphs_cache_miss
        i = 0
        x_pos = 0
        while i < len(text):
            if i > 0:
                (x_pos, _) = cls.render_size(font, text[:i])
            glyph = _get_glyph(renderer, text[i], font)
            glyph.draw(renderer, font, x + x_pos, y, color=color)
            i += 1
        if last_debug_output + 2.0 < time.monotonic():
            last_debug_output = time.monotonic()
            print("GLYPHS ALLOCATED TOTAL: " + str(glyphs_created) +
                ", CACHE HIT/MISS: " + str(glyphs_cache_hits) +
                "/" + str(glyphs_cache_miss))

    @staticmethod
    def render_size(font, text):
        global text_length_cache
        if len(text) == 0:
            return (0, 0)
        text_key = str(hash((font.font_family, font.bold,
            font.italic, font.pixel_size))) + "_" + text
        size = text_length_cache.get(text_key)
        if size == None:
            sdl_font = font.get_sdl_font()
            width = ctypes.c_int32()
            height = ctypes.c_int32()
            if sdlttf.TTF_SizeUTF8(sdl_font,
                    text.encode("utf-8", "replace"),
                    ctypes.byref(width), ctypes.byref(height)) != 0:
                raise RuntimeError("TTF_SizeUTF8 failed: " +
                    str(sdlttf.TTF_GetError().decode("utf-8", "replace")))
            size = (int(width.value), int(height.value))
            text_length_cache.add(text_key, size)
        return size

    @staticmethod
    def clear_renderer(renderer):
        global glyph_cache
        for glyph in glyph_cache.values():
            glyph.clear_renderer(renderer)


