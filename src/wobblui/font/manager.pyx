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

from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
import ctypes
import functools
from libc.stdlib cimport malloc, free
import sdl2 as sdl
import sdl2.sdlttf as sdlttf
import threading
import time

from wobblui.cache cimport KeyValueCache
from wobblui.color import Color
import wobblui.font.info
cimport wobblui.font.sdlfont as sdlfont
from wobblui.sdlinit import initialize_sdl
from wobblui.texture import Texture
from wobblui.woblog import logdebug, logerror, loginfo, logwarning

DRAW_SCALE_GRANULARITY_FACTOR=1000

render_size_cache = KeyValueCache(size=500)

rendered_words_cache = KeyValueCache(size=50,
    destroy_func=lambda x: x._force_unload())

_reuse_draw_rect = sdl.SDL_Rect()
cdef class Font(object):
    cdef public int italic, bold
    cdef public double px_size
    cdef char* font_family_bytes
    cdef char* _unique_key
    cdef double _avg_letter_width
    cdef object _sdl_font, mutex

    def __init__(self, str font_family,
            double pixel_size, int italic=False, int bold=False):
        assert(font_family != None)
        font_family_bytes = font_family.encode("utf-8", "replace")
        array = <char *>PyMem_Malloc((len(font_family_bytes) + 1) * sizeof(char))
        if not array:
            raise MemoryError()
        cdef int i = 0
        while i < len(font_family_bytes):
            array[i] = font_family_bytes[i]
            i += 1
        array[len(font_family_bytes)] = 0
        self.font_family_bytes = array
        self.px_size = pixel_size
        self.italic = italic
        self.bold = bold
        self._avg_letter_width = 0
        self._sdl_font = None
        self.mutex = threading.Lock()

    def __dealloc__(self):
        PyMem_Free(self.font_family_bytes)
        PyMem_Free(self._unique_key)

    @property
    def font_family(self):
        return self.font_family_bytes.decode("utf-8", "replace")

    @staticmethod
    def clear_global_cache_textures():
        logdebug("Clearing global texture cache [wobblui.font.manager]")
        rendered_words_cache.clear()

    def __repr__(self):
        return "<Font family='" + str(
            self.font_family) + "' px_size=" +\
            str(round(self.px_size)) +\
            " bold=" + str(self.bold) +\
            " italic=" + str(self.italic) + ">"

    @property
    def unique_key(self):
        if self._unique_key != NULL:
            return self._unique_key
        key_bytes = str(self.__repr__()).encode("utf-8", "replace")
        array = <char *>PyMem_Malloc((len(key_bytes) + 1) * sizeof(char))
        if not array:
            raise MemoryError()
        cdef int i = 0
        while i < len(key_bytes):
            array[i] = key_bytes[i]
            i += 1
        array[len(key_bytes)] = 0
        self._unique_key = array
        return self._unique_key

    def render_size(self, str text):
        global render_size_cache
        if len(text) == 0:
            return (0, 0)
        unique_key = self.unique_key
        text_bytes = text.encode("utf-8", "replace")
        result = render_size_cache.get(str((unique_key, text_bytes)))
        if result != None:
            return result
        font = self.get_sdl_font()
        result = sdlfont.get_thread_safe_render_size(font, text_bytes)
        render_size_cache.add(str((unique_key, text_bytes)), result)
        return result

    def draw_at(self, renderer, str text, int x, int y, color=Color.black):
        if len(text) == 0:
            return
        global _reuse_draw_rect
        tex = self.get_cached_rendered_texture(renderer, text)
        tex.set_color(color)
        tex.draw(x, y)

    def get_cached_rendered_texture(self, renderer, str text):
        global rendered_words_cache
        cdef str key = str((self.font_family, self.italic, self.bold,
            self.px_size, str(ctypes.addressof(
                renderer.contents)))) + "_" + text
        value = rendered_words_cache.get(key)
        if value != None:
            return value
        font = self.get_sdl_font()
        c = sdl.SDL_Color(255, 255, 255)
        try:
            text_bytes = text.encode("utf-8", "replace")
        except AttributeError:
            pass
        surface = sdlttf.TTF_RenderUTF8_Blended(
            font.font, text_bytes, c)
        if not surface:
            raise RuntimeError("failed to render text: " +
                str(text_bytes))
        tex = Texture.new_from_sdl_surface(renderer, surface)
        sdl.SDL_FreeSurface(surface)
        rendered_words_cache.add(key, tex)
        return tex

    def get_sdl_font(self):
        self.mutex.acquire()
        if self._sdl_font != None:
            self.mutex.release()
            return self._sdl_font
        try:
            path = self.get_font_file_path()
            self._sdl_font = sdlfont.\
                get_thread_safe_sdl_font(path,
                round(self.px_size))
            result = self._sdl_font
        finally:
            self.mutex.release()
        return result

    def get_font_file_path(self):
        if self._sdl_font != None:
            return self._sdl_font
        initialize_sdl()
        variant = "Regular"
        if self.italic and not self.bold:
            variant = "Italic"
        elif self.bold and not self.italic:
            variant = "Bold"
        elif self.bold and self.italic:
            variant = "BoldItalic"
        font_paths = wobblui.font.info.get_font_paths_by_name(
            self.font_family + " " + variant, cached=True)
        for (variant_name, font_path) in font_paths:
            if font_path.endswith(".ttf"):
                return font_path
        raise ValueError("TTF font not found: " +
            str(self.font_family + " " + variant))

    def get_average_letter_width(self):
        self.mutex.acquire()
        if self._avg_letter_width > 0:
            result = self._avg_letter_width
            self.mutex.release()
            return result
        self.mutex.release()
        test_str = "This is a test test."
        (width, height) = self.render_size(test_str)
        result = (width / float(len(test_str)))
        self.mutex.acquire()
        self._avg_letter_width = max(0.001, result)
        self.mutex.release()
        return result

cdef class FontManager(object):
    """ MEMBERS ARE IN font/manager.pxd """

    def __init__(self):
        self.font_by_sizedpistyle_cache = dict()
        self.font_by_sizedpistyle_cache_times = dict()
        self.font_metrics_by_styledpi_cache = dict()
        self.load_debug_info_shown = dict()
        self.missing_fonts = dict()
        self.avg_letter_width_cache = dict()
        self.cache_size = 20
        self.mutex = threading.Lock()

    def _limit_cache(self):
        if len(self.font_by_sizedpistyle_cache.values()) <= \
                self.cache_size:
            return
        usage_refs = []
        for entry in self.font_by_sizedpistyle_cache:
            last_use = self.font_by_sizedpistyle_cache_times[entry]
            usage_refs.append((last_use, entry))
        def soonest_to_latest(a, b):
            return b[0] - a[0]
        usage_refs = sorted(usage_refs,
            key=functools.cmp_to_key(soonest_to_latest))
        remove_these = usage_refs[self.cache_size:]
        for remove_this in remove_these:
            del(self.font_by_sizedpistyle_cache[remove_this[1]])
            del(self.font_by_sizedpistyle_cache_times[remove_this[1]])

    def get_word_size(self, str word, str font_name,
            int bold=False, int italic=False,
            int px_size=12, int display_dpi=96):
        return self.get_font(font_name, bold, italic,
            px_size=px_size, display_dpi=display_dpi).render_size(word)

    def get_font(self, str name,
            int bold=False, int italic=False, double px_size=12,
            double draw_scale=1.0, int display_dpi=96):
        cdef int unified_draw_scale = round(draw_scale *
            DRAW_SCALE_GRANULARITY_FACTOR)
        self.mutex.acquire()
        result = None
        try:
            result = self._load_font_info(name, bold, italic,
                px_size=px_size,
                draw_scale=draw_scale,
                display_dpi=display_dpi)
        except ValueError as e:
            if name.lower() == "sans" or \
                    name.lower() == "sans serif" or \
                    name.lower() == "arial":
                self.mutex.release()
                return self.get_font("Tex Gyre Adventor",
                    bold=bold, italic=italic, px_size=px_size,
                    draw_scale=draw_scale, display_dpi=display_dpi)
            elif name.lower() == "serif" or \
                    name.lower() == "times new roman":
                self.mutex.release()
                return self.get_font("Tex Gyre Heros",
                    bold=bold, italic=italic, px_size=px_size,
                    draw_scale=draw_scale, display_dpi=display_dpi)
            self.mutex.release()
            raise e
        self.mutex.release()
        return result

    def _load_font_info(self,
            str name, int bold, int italic, double px_size=12,
            double draw_scale=1.0, int display_dpi=96):
        display_dpi = round(display_dpi)
        style = (name, bold, italic, round(px_size * 10))
        unified_draw_scale = round(draw_scale *
            DRAW_SCALE_GRANULARITY_FACTOR)
        actual_px_size = ((display_dpi / 96.0) *
            (unified_draw_scale /
            float(DRAW_SCALE_GRANULARITY_FACTOR))) * px_size

        self.font_by_sizedpistyle_cache_times[
            (unified_draw_scale, display_dpi, style)] =\
            time.monotonic()
        if not (unified_draw_scale, display_dpi,
                style) in \
                self.font_by_sizedpistyle_cache:
            f = Font(name, actual_px_size,
                italic=italic,
                bold=bold)
            self.font_by_sizedpistyle_cache[(
                unified_draw_scale, display_dpi, style
                )] = f
            self._limit_cache()
        return self.font_by_sizedpistyle_cache[(
            unified_draw_scale, display_dpi,
            style)]

cdef object font_manager_singleton = None
cdef FontManager c_font_manager():
    global font_manager_singleton
    if font_manager_singleton is None:
        font_manager_singleton = FontManager()
    return font_manager_singleton

def font_manager():
    return c_font_manager()

