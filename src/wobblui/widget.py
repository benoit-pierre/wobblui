
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

from wobblui.event import Event
from wobblui.style import AppStyleBright
from wobblui.widget_base import all_widgets, tab_sort, WidgetBase
from wobblui.window import Window

class Widget(WidgetBase):
    def __init__(self, is_container=False, can_get_focus=False,
            takes_text_input=False, generate_double_click_for_touches=False,
            has_native_touch_support=False,
            fake_mouse_even_with_native_touch_support=False):
        super().__init__(is_container=is_container,
            can_get_focus=can_get_focus,
            takes_text_input=takes_text_input,
            generate_double_click_for_touches=\
                generate_double_click_for_touches,
            has_native_touch_support=has_native_touch_support,
            fake_mouse_even_with_native_touch_support=\
                fake_mouse_even_with_native_touch_support)
        self.parentwindowresized = Event("parentwindowresized",
            owner=self)
        self._temp_style = AppStyleBright()

    def update_window(self):
        self.needs_redraw = True

    def get_style(self):
        if self.parent_window == None:
            return self._temp_style
        return self.parent_window.style

    @property
    def parent_window(self):
        p = self.parent
        while p:
            if isinstance(p, Window):
                return p
            p = p.parent

    def focus_next(self):
        if not self.focused:
            raise RuntimeError("widget isn't focused")
        self._advance_focus(True)

    def focus_previous(self):
        if not self.focused:
            raise RuntimeError("widget isn't focused")
        self._advance_focus(False)

    def _advance_focus(self, forward):
        sorted_candidates = self.__class__.focus_candidates(self)
        i = 0
        while i < len(sorted_candidates):
            if sorted_candidates[i] == self:
                if forward:
                    if i + 1 < len(sorted_candidates):
                        sorted_candidates[i + 1].focus()
                    else:
                        sorted_candidates[0].focus()
                else:
                    if i > 0:
                        sorted_candidates[i - 1].focus()
                    else:
                        sorted_candidates[len(sorted_candidates) - 1].\
                            focus()
                return
            i += 1

    def get_renderer(self):
        v = super().get_renderer()
        if v is None:
            w = self.parent_window
            if w != None:
                return w.get_renderer()
        return v

    def shares_focus_group(self, widget):
        if isinstance(widget, Window):
            return False
        if isinstance(widget, Widget):
            return (self.parent_window == widget.parent_window)
        return True
