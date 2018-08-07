
import ctypes
import functools
import sdl2 as sdl
import sdl2.sdlttf as sdlttf
import time

from applog import logdebug, logerror, loginfo, logwarning
from osintegration import is_android
import wobblui.font.info

DRAW_SCALE_GRANULARITY_FACTOR=1000

class Font(object):
    def __init__(self, font_family,
            pixel_size, italic=False, bold=False):
        self.font_family = font_family
        self.pixel_size = pixel_size
        self.italic = italic
        self.bold = bold
        self._qt_font = None
        self._qt_metrics = None
        self._avg_letter_width = None
        self._sdl_font = None

    def __del__(self):
        if self._sdl_font != None:
            sdlttf.TTF_CloseFont(self._sdl_font)
            self._sdl_font = None

    def render_size(self, text):
        if len(text) == 0:
            return (0, 0)
        font = self.get_sdl_font()
        width = ctypes.c_int32()
        height = ctypes.c_int32()
        try:
            text = text.encode("utf-8", "replace")
        except AttributeError:
            pass
        if sdlttf.TTF_SizeText(font, text, ctypes.byref(
                width), ctypes.byref(height)) != 0:
            raise RuntimeError("TTF_SizeText failed")
        return (int(width.value), int(height.value))

    def render_text_as_sdl_texture(self, renderer, text, color=None):
        font = self.get_sdl_font()
        if color != None:
            c = sdl.SDL_Color(color.red, color.blue, color.green)
        else:
            c = sdl.SDL_Color(0, 0, 0)
        try:
            text = text.encode("utf-8", "replace")
        except AttributeError:
            pass
        surface = sdlttf.TTF_RenderText_Blended(font, text, c)
        texture = sdl.SDL_CreateTextureFromSurface(renderer, surface)
        sdl.SDL_FreeSurface(surface)
        return texture

    def get_sdl_font(self):
        if self._sdl_font != None:
            return self._sdl_font
        variant = "Regular"
        if self.italic and not self.bold:
            variant = "Italic"
        elif self.bold and not self.italic:
            variant = "Bold"
        elif self.bold and self.italic:
            variant = "BoldItalic"
        font_paths = wobblui.font.info.get_font_paths_by_name(
            self.font_family + " " + variant)
        for font_path in font_paths:
            if font_path.endswith(".ttf"):
                f = sdlttf.TTF_OpenFont(font_path.encode("utf-8"),
                    round(self.pixel_size))
                if f is None:
                    error_msg = sdlttf.TTF_GetError()
                    raise ValueError("couldn't load TTF " +
                        "font: " + str(error_msg))
                self._sdl_font = f
                return f
        raise ValueError("TTF font not found: " +
            str(self.font_family + " " + variant))

    def get_average_letter_width(self):
        if self._avg_letter_width != None:
            return self._avg_letter_width
        if not is_android():
            test_str = "This is a test test."
            width = self.get_qt_font_metrics().width(test_str)
            self._avg_letter_width = width
            return self._avg_letter_width
        raise NotImplementedError("oopsies")

    def get_qt_font_metrics(self):
        if self._qt_metrics is None:
            from PySide2 import QtCore, QtGui, QtWidgets
            self._qt_metrics = QtGui.QFontMetrics(self.qt_font)
        return self._qt_metrics

    @property
    def qt_font(self):
        if self._qt_font != None:
            return self._qt_font
        from PySide2 import QtCore, QtGui, QtWidgets
        f = QtGui.QFont()
        f.setStyleHint(QtGui.QFont.AnyStyle, QtGui.QFont.PreferAntialias)
        f.setFamily(self.font_family)
        f.setPixelSize(self.pixel_size)
        f.setBold(False)
        f.setItalic(False)
        if self.bold:
            f.setBold(True)
        if self.italic:
            f.setItalic(True)
        self._qt_font = f
        return self._qt_font

class FontManager(object):
    def __init__(self):
        self.font_by_sizedpistyle_cache = dict()
        self.font_by_sizedpistyle_cache_times = dict()
        self.font_metrics_by_styledpi_cache = dict()
        self.load_debug_info_shown = dict()
        self.missing_fonts = dict()
        self.avg_letter_width_cache = dict()
        self.cache_size = 50

    def limit_cache(self):
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

    def get_word_width(self, word, font_name, bold=False, italic=False,
            px_size=12, display_dpi=96):
        metrics = self.get_qt_font_metrics(font_name, bold, italic,
            px_size=px_size, dpi=display_dpi)
        return metrics.width(word)

    def get_word_height(self, word, font_name, bold=False, italic=False,
            px_size=12, display_dpi=96):
        metrics = self.get_qt_font_metrics(font_name, bold, italic,
            px_size=px_size, dpi=display_dpi)
        return metrics.height()

    def get_qt_font_metrics(self, font_name, bold=False, italic=False,
            px_size=12, dpi=96):
        return self.get_font(font_name, bold, italic,
            px_size=px_size, display_dpi=dpi).get_qt_font_metrics()

    def get_font(self, name, bold=False, italic=False, px_size=12,
            draw_scale=1.0, display_dpi=96):
        display_dpi = round(display_dpi)
        self.load_font_info(name, bold, italic,
            px_size=px_size,
            draw_scale=draw_scale,
            display_dpi=display_dpi)
        unified_draw_scale = round(draw_scale *
            DRAW_SCALE_GRANULARITY_FACTOR)
        return self.font_by_sizedpistyle_cache[
            (unified_draw_scale, display_dpi,
            (name, bold, italic,
            round(px_size * 10)))]

    def load_font_info(self, name, bold, italic, px_size=12,
            draw_scale=1.0, display_dpi=96):
        display_dpi = round(display_dpi)
        style = (name, bold, italic, round(px_size * 10))
        unified_draw_scale = round(draw_scale *
            DRAW_SCALE_GRANULARITY_FACTOR)
        actual_px_size = ((display_dpi / 72) *
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

            if False:
                # Output some debug info for font family choice:
                finfo = QtGui.QFontInfo(f.qt_font)
                missing = False
                if str(finfo.family()).lower() != style.font_family.lower() and \
                        str(finfo.family()).lower() != \
                        style.font_family.lower() + " [ukwn]":
                    self.missing_fonts.add(style.font_family)
                    missing = True
                if not style.font_family in self.load_debug_info_shown:
                    self.load_debug_info_shown[style.font_family] = True
                    logdebug("requested font family '" + str(
                        style.font_family) + "', got font family '" +
                        str(finfo.family()) + "'",
                        section="FontManager")
                    if missing:
                        logwarning("requested font is missing: " +
                            str(style.font_family),
                            section="FontManager")
        self.limit_cache()


font_manager_singleton = None
def font_manager():
    global font_manager_singleton
    if font_manager_singleton is None:
        font_manager_singleton = FontManager()
    return font_manager_singleton

