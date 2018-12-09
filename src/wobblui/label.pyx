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

import sdl2 as sdl
import time

from wobblui.button import Button
from wobblui.color cimport Color
from wobblui.image import stock_image
from wobblui.richtext cimport RichText
from wobblui.scrollbarwidget cimport ScrollbarDrawingWidget
from wobblui.woblog cimport logdebug, logerror, loginfo, logwarning

cdef class Label(ScrollbarDrawingWidget):
    cdef double current_draw_scale, text_scale, known_dpi_scale
    cdef str known_font_family, _current_align, _cached_text
    cdef int px_size, _layout_height, _layout_width, _layouted_for_width
    cdef object natural_size_cache, text_obj, _user_set_color

    cdef public int scroll_y_offset

    def __init__(self, text="", color=None,
            text_scale=1.0):
        super().__init__()
        self.no_mouse_events = True
        self.type = "label"
        self.current_draw_scale = self.dpi_scale
        self.text_scale = text_scale
        font_family = self.style.get("widget_font_family")
        self.px_size = self.get_intended_text_size()
        self.known_font_family = font_family
        self._layout_height = -1
        self._layouted_for_width = -1
        self._layout_width = -1
        self.scroll_y_offset = 0
        self.natural_size_cache = dict()
        self.known_dpi_scale = self.dpi_scale
        self.text_obj = RichText(font_family=font_family,
            px_size=self.px_size,
            draw_scale=self.dpi_scale)
        self._current_align = "left"
        self._cached_text = None
        if text.find("<") >= 0 and (text.find("/>") > 0 or
                text.find("/ >") > 0 or
                (text.find("</") > 0 and text.find(">") > 0)):
            self.html = text
        else:
            self.text = text
        self._user_set_color = color

    def __repr__(self):
        t = self.text
        if len(t) > 20:
            t = t + "..."
        t = t.replace("'", "'\"'\"'")
        return "<wobblui.Label at " + str(id(self)) + " text='" + t + "'>"

    def on_stylechanged(self):
        self.font_size_refresh()

    def get_intended_text_size(self):
        if self.style == None:
            return 12
        px_size = round(self.style.get("widget_text_size") *\
            self.text_scale)
        if self.style.has("topbar_text_size") and self.in_topbar():
            px_size = \
                round(self.style.get("topbar_text_size") *\
                self.text_scale)
        return px_size

    def set_text(self, v):
        self.text = v

    def set_html(self, v):
        self.html = v

    def in_topbar(self):
        p = self.parent
        while p != None:
            if p.type == "topbar":
                return (p.widget_is_in_upper_half(self))
            p = p.parent
        return False

    @property
    def color(self):
        if self._user_set_color != None:
            return self._user_set_color
        if self.style is None:
            return Color.black()
        return Color(self.style.get("widget_text"))

    def update_window(self):
        super().update_window()
        self.needs_redraw = True

    def set_alignment(self, alignment):
        if not alignment in ["left", "center", "right", "justified"]:
            raise ValueError("unknown alignment specified: '" +
                str(alignment) + "'")
        if self._current_align == alignment:
            return
        self.natural_size_cache = dict()
        self._current_align = alignment
        self.needs_relayout = True
        self._layouted_for_width = -1
        self._layout_width = -1
        self._layout_height = -1

    def do_redraw(self):
        # Calculate content height:
        content_height = self._layout_height

        # Limit scrolling to reasonable area:
        max_scroll_down = max(0, content_height - self.height)
        if max_scroll_down > 0:
            self.no_mouse_events = False
        else:
            self.no_mouse_events = True
        self.scroll_y_offset = max(0, min(max_scroll_down,
            self.scroll_y_offset))

        # Draw label text:
        for fragment in self.text_obj.fragments:
            # Bail out if we arrived at text below our viewport:
            if fragment.y - self.scroll_y_offset > self.height:
                break
            # Skip if above our viewport:
            if fragment.y - self.scroll_y_offset + fragment.height <\
                    0:
                continue
            # Draw fragment:
            fragment.draw(self.renderer,
                fragment.x, fragment.y - self.scroll_y_offset,
                color=self.color,
                draw_scale=self.dpi_scale)

        # Draw scrollbar:
        self.draw_scrollbar(content_height, self.height,
            self.scroll_y_offset)

    def on_mousewheel(self, mouse_id, x, y):
        self.scroll_y_offset = max(0,
            self.scroll_y_offset -
            y * 50.0 * self.dpi_scale)
        self.needs_redraw = True

    def font_size_refresh(self):
        new_px_size = self.get_intended_text_size()
        new_font_family = self.style.get("widget_font_family")
        if new_px_size != self.px_size or \
                abs(self.dpi_scale - self.current_draw_scale) > 0.001 or \
                new_font_family != self.known_font_family:
            # Font size update!
            self.px_size = new_px_size
            self.natural_size_cache = dict()
            self.known_font_family = new_font_family
            self.text_obj.default_font_family = new_font_family
            # FIXME: font will not actually be updated. fix at some point
            self.text_obj.px_size = self.px_size
            self.text_obj.draw_scale = self.dpi_scale
            self.current_draw_scale = self.dpi_scale
            self._layout_width = -1
            self._layout_height = -1
            self._layouted_for_width = -1

    def on_relayout(self):
        self.font_size_refresh()
        layout_max_width = self.width
        if self._max_width >= 0 and self._max_width < layout_max_width:
            layout_max_width = self._max_width

        # If we don't need to update layout size, don't do it:
        if self._layouted_for_width == layout_max_width and \
                self._layout_width >= 0 and \
                self._layout_height >= 0:
            # We can keep our current values
            return

        # See if we can get dimensions out of natural size cache:
        if "natural_width" in self.natural_size_cache and \
                "natural_height" in self.natural_size_cache and \
                None in self.natural_size_cache["natural_height"]:
            if layout_max_width > self.natural_size_cache["natural_width"] \
                    and self._layout_width == \
                    self.natural_size_cache["natural_width"]:
                # Nothing changed, max width is larger than our natural size
                # and we layouted at this width before.
                # -> We can just copy over the results.
                self._layout_width = self.natural_size_cache["natural_width"]
                self._layout_height = self.natural_size_cache\
                    ["natural_height"][None]
                return

        # Update dimensions:
        self._layouted_for_width = layout_max_width
        (self._layout_width, self._layout_height) = self.text_obj.layout(
            max_width=layout_max_width, align_if_none=self._current_align)
        if not "natural_height" in self.natural_size_cache:
            self.natural_size_cache["natural_height"] = dict()
        self.natural_size_cache["natural_height"][self._layout_width] =\
            self._layout_height
        self.needs_relayout = False  # just to be sure

    def get_natural_width(self):
        if len(self.text_obj.text) == 0:
            return 0
        self.font_size_refresh()
        if "natural_width" in self.natural_size_cache:
            return self.natural_size_cache["natural_width"]

        # Copy full layout for width computation:
        text_obj_copy = self.text_obj.copy()

        # Bailout helpers for really excessively long texts:
        start_time = time.monotonic()
        layout_min_bailout_height = 1000
        if self.parent_window != None:
            layout_min_bailout_height = self.parent_window.height * 2
        bailed_out = False
        def bailout_if_excessively_long(layout_w, layout_h):
            nonlocal bailed_out
            if layout_h > layout_min_bailout_height and \
                    start_time + 1.0 < time.monotonic():
                bailed_out = True
                return True
            return False

        # Run actual layouting to get width:
        (w, h) = text_obj_copy.layout(bailout_func=\
            bailout_if_excessively_long)
        if bailed_out:
            w = int(w * 1.05)  # give headroom since this is inaccurate
        self.natural_size_cache["natural_width"] = w
        if not "natural_height" in self.natural_size_cache:
            self.natural_size_cache["natural_height"] = dict()
        if not bailed_out:
            # If not bailed out, also keep the resulting height cached:
            self.natural_size_cache["natural_height"][None] = h
        return self.natural_size_cache["natural_width"]

    def get_natural_height(self, given_width=None):
        if len(self.text) == 0:
            return 0
        self.font_size_refresh()
        if given_width != None:
            given_width = max(0, round(given_width))
            if "natural_width" in self.natural_size_cache:
                if self.natural_size_cache["natural_width"] < given_width:
                    # Width is irrelevant, the layout is thinner!
                    given_width = None
        if not "natural_height" in self.natural_size_cache:
            self.natural_size_cache["natural_height"] = dict()
        if given_width in self.natural_size_cache\
                ["natural_height"]:
            return self.natural_size_cache\
                ["natural_height"][given_width]
        text_obj_copy = self.text_obj.copy()
        (w, h) = text_obj_copy.layout(max_width=given_width)
        self.natural_size_cache["natural_height"][given_width] = h
        if given_width is None:
            self.natural_size_cache["natural_width"] = w
        return h

    @property
    def text(self):
        if self._cached_text == None:
            self._cached_text = self.text_obj.text
        return self._cached_text

    @text.setter
    def text(self, t):
        if self.text == t:
            return
        self.natural_size_cache = dict()
        self.text_obj.set_text(t)
        self.needs_relayout = True
        self._layout_width = -1
        self._layout_height = -1
        self._layouted_for_width = -1
        self.needs_redraw = True
        self._cached_text = t

    @property
    def html(self):
        return self.text_obj.html

    @html.setter
    def html(self, t):
        if self.html == t:
            return
        self.natural_size_cache = dict()
        self._cached_text = None
        self.text_obj.set_html(t)
        self.needs_relayout = True
        self.needs_redraw = True
        self._layouted_for_width = -1
        self._layout_width = -1
        self._layout_height = -1

class ImageWithLabel(Button):
    def __init__(self, image_path, scale=None, scale_to_width=None,
            color_with_text_color=False):
        super().__init__(with_border=False, clickable=False,
            image_placement="left", text_scale=1.2)
        self.original_image = image_path
        color = Color.white()
        if color_with_text_color:
            color = Color(self.style.get("widget_text"))
            if self.style.has("saturated_widget_text"):
                color = Color(self.style.get("saturated_widget_text"))
        self.color_with_text_color = color_with_text_color
        self.set_image(image_path, scale=scale,
            scale_to_width=scale_to_width)
        self.set_image_color(color)

    def do_redraw(self):
        if self.color_with_text_color:
            color = Color(self.style.get("widget_text"))
            if self.style.has("saturated_widget_text"):
                color = Color(self.style.get("saturated_widget_text"))
            self.image_color = color
        super().do_redraw()

class LoadingLabel(ImageWithLabel):
    def __init__(self, html):
        super().__init__(stock_image("hourglass"), scale_to_width=100,
            color_with_text_color=True)
        self.set_html(html)


