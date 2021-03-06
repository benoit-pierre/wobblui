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
import functools
from libc.math cimport round as cround
import threading
import time

from wobblui.cache cimport KeyValueCache
from wobblui.color cimport Color
import wobblui.font.info
cimport wobblui.font.sdlfont as sdlfont
from wobblui.sdlinit cimport initialize_sdl
from wobblui.texture cimport Texture
from wobblui.woblog cimport logdebug, logerror, loginfo, logwarning

cdef int DRAW_SCALE_GRANULARITY_FACTOR = 1000

render_size_cache = KeyValueCache(size=500)

rendered_words_cache = KeyValueCache(size=50,
    destroy_func=lambda x: x._force_unload())


cdef class Font:
    cdef public int italic, bold
    cdef public double px_size
    cdef public str font_family
    cdef str _unique_key
    cdef double _avg_letter_width
    cdef int _space_char_width
    cdef object _sdl_font, mutex

    def __init__(self, str font_family,
            double pixel_size, int italic=False, int bold=False,
            ):
        assert(font_family != None)
        self.font_family = font_family
        self.px_size = pixel_size
        self.italic = italic
        self.bold = bold
        self._unique_key = ""
        self._avg_letter_width = -1
        self._space_char_width = -1
        self._sdl_font = None
        self.mutex = threading.Lock()

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
        if len(self._unique_key) > 0:
            return self._unique_key
        self._unique_key = str(self.__repr__())
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

    def draw_at(self, renderer, str text, int x, int y, color=Color.black()):
        if len(text) == 0:
            return
        tex = self.get_cached_rendered_texture(renderer, text)
        tex.set_color(color)
        tex.draw(x, y)

    def get_cached_rendered_texture(self, renderer, str text):
        global rendered_words_cache
        import sdl2 as sdl
        import sdl2.sdlttf as sdlttf
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
                cround(self.px_size))
            result = self._sdl_font
        finally:
            self.mutex.release()
        return result

    @staticmethod
    def fallback_suggestions(name):
        for variant in ["Regular", "Italic", "Bold", "BoldItalic",
                "ItalicBold", "Oblique", "ObliqueBold",
                "BoldOblique"]:
            if name.lower().endswith(" " + variant.lower()):
                name = name.rpartition(" ")[0]
                break
            if name.lower().endswith("-" + variant.lower()):
                name = name.rpartition("-")[0]
                break
            if name.lower().endswith("_" + variant.lower()):
                name = name.rpartition("_")[0]
                break
            if name.lower().endswith(variant.lower()):
                name = name[:-len(variant)]
                break
        # The following will always suggest what should be available as
        # built-in (in src/wobblui/fon/packaged-fonts/) and then suggest
        # other fallbacks that might be commonly installed.
        if name.lower() in ["comic sans"]:
            return ["Comic Neue", "Comic Sans"]
        if name.lower() in ["sans", "sans serif", "arial",
                "helvetica", "impact"]:
            return ["Tex Gyre Adventor", "Liberal Sans", "Arial"]
        if name.lower() in ["monospace", "mono", "terminal",
                "courier", "courier new",
                "droid mono", "droid sans mono",
                "dejavu mono", "dejavu sans mono"]:
            return ["Source Code Pro"]
        if name.lower() in ["times new roman", "serif", "georgia", "times"]:
            return ["Tex Gyre Adventor", "Liberal Serif", "Times New Roman"]
        return None

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

    def ensure_availability(self):
        # Actually locate the TTF file:
        fpath = self.get_font_file_path()
        # If we get here, then it was lcoated.
        return

    def get_space_character_width(self):
        self.mutex.acquire()
        if self._space_char_width > 0:
            result = self._space_char_width
            self.mutex.release()
            return result
        self.mutex.release()
        (width, height) = self.render_size(" ")
        self.mutex.acquire()
        self._space_char_width = max(round(width), 1)
        self.mutex.release()
        return max(round(width), 1)

    def get_average_letter_width(self):
        self.mutex.acquire()
        if self._avg_letter_width >= 0:
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


cdef class FontManager:
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
        self.next_limit_cache_counter = 0

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
            double draw_scale=1.0, int display_dpi=96,
            int fallback_for_common_missing_fonts=True):
        cdef int unified_draw_scale = round(draw_scale *
            DRAW_SCALE_GRANULARITY_FACTOR)
        self.mutex.acquire()
        result = None
        try:
            result = self._load_font_info(
                name, bold, italic,
                px_size=px_size,
                draw_scale=draw_scale,
                display_dpi=display_dpi
            )
        except ValueError as e:
            if not fallback_for_common_missing_fonts:
                self.mutex.release()
                raise e
            alternatives = Font.fallback_suggestions(name)
            result = None
            if len(alternatives) > 0:
                for alternative in alternatives:
                    try:
                        result = self._load_font_info(
                            alternative, bold, italic,
                            px_size=px_size,
                            draw_scale=draw_scale,
                            display_dpi=display_dpi
                        )
                        break
                    except ValueError as e2:
                        continue
            if result is None:
                self.mutex.release()
                raise e
        self.mutex.release()
        return result

    def _load_font_info(self,
            str name, int bold, int italic, double px_size=12,
            double draw_scale=1.0, int display_dpi=96):
        style = (name, bold, italic, cround(px_size * 10))
        unified_draw_scale = cround(
            draw_scale *
            DRAW_SCALE_GRANULARITY_FACTOR
        )
        actual_px_size = cround(
            ((display_dpi / 96.0) *
            (unified_draw_scale /
            (DRAW_SCALE_GRANULARITY_FACTOR * 1.0))) * px_size
        )
        key = (unified_draw_scale, display_dpi, style)

        self.font_by_sizedpistyle_cache_times[key] =\
            time.monotonic()
        if key not in self.font_by_sizedpistyle_cache:
            f = Font(name, actual_px_size,
                italic=italic,
                bold=bold)
            f.ensure_availability()
            self.font_by_sizedpistyle_cache[key] = f
            self.next_limit_cache_counter += 1
            if self.next_limit_cache_counter > 10:
                self.next_limit_cache_counter = 0
                self._limit_cache()
        return self.font_by_sizedpistyle_cache[key]


cdef object font_manager_singleton = None
cdef FontManager c_font_manager():
    global font_manager_singleton
    if font_manager_singleton is None:
        font_manager_singleton = FontManager()
    return font_manager_singleton


def font_manager():
    return c_font_manager()
