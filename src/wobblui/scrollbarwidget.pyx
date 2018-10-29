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

from wobblui.color import Color
from wobblui.gfx import draw_rectangle
from wobblui.widget cimport Widget

cdef class ScrollbarDrawingWidget(Widget):
    def draw_scrollbar(self, int scroll_height,
            int visible_height, int y_offset):
        max_scroll_down = max(0, scroll_height - visible_height)
        if max_scroll_down <= 0.0001:
            return

        scroll_percent = max(0.0, min(1.0,
            y_offset / float(max_scroll_down)))
        self.scrollbar_height = round(20.0 * self.dpi_scale)
        self.scrollbar_y = round((self.height -
            self.scrollbar_height) * scroll_percent)
        self.scrollbar_width = round(8.0 * self.dpi_scale)
        self.scrollbar_x = self.width - self.scrollbar_width
        c = Color.white
        if self.style != None:
            c = Color(self.style.get("border"))
        draw_rectangle(self.renderer,
            self.scrollbar_x, self.scrollbar_y,
            self.scrollbar_width, self.scrollbar_height,
            color=c)
        c = Color.black
        if self.style != None:
            c = Color(self.style.get("selected_bg"))
            if self.style.has("scrollbar_knob_fg"):
                c = Color(self.style.get("scrollbar_knob_fg"))
        border_width = max(1, round(1 * self.dpi_scale))
        draw_rectangle(self.renderer,
            self.scrollbar_x + 1 * border_width,
            self.scrollbar_y + 1 * border_width,
            self.scrollbar_width - 2 * border_width,
            self.scrollbar_height - 2 * border_width,
            color=c)

