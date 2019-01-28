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
import weakref

from wobblui.color cimport Color
from wobblui.event cimport Event
from wobblui.gfx cimport draw_rectangle
from wobblui.keyboard import register_global_shortcut,\
    shortcut_to_text
from wobblui.list cimport ListBase, ListEntry
from wobblui.timer import schedule
from wobblui.widget cimport Widget
from wobblui.woblog cimport logdebug, logerror, loginfo, logwarning

cdef class MenuSeparator(ListEntry):
    cdef double padding_horizontal, padding_vertical
    cdef double line_thickness
    cdef public int needs_size_update

    def __init__(self, style, is_alternating=False):
        assert(is_alternating != None)
        super().__init__("---", style,
            is_alternating=is_alternating)
        self.needs_size_update = True
        self.disabled = True
        self.padding_horizontal = 0.0
        self.padding_vertical = 3.0
        self.line_thickness = 1.0
        self.update_size()

    def copy(self):
        li = MenuSeparator(self.style)
        li.max_width = self.max_width
        li.width = self.width
        li.needs_size_update = True
        return li

    def draw(self, renderer, x, y,
            draw_selected=False,
            draw_hover=False,
            draw_soft_hover=False,
            draw_keyboard_focus=False,
            draw_no_bg=False):
        dpi_scale = 1.0
        if self.style != None:
            dpi_scale = self.style.dpi_scale
        c = Color((0, 0, 0))
        if self.style != None:
            c = Color(self.style.get("widget_text"))
            if self.style.has("widget_disabled_text"):
                c = Color(self.style.get("widget_disabled_text"))
        draw_w = (round(self.width) - round(self.padding_horizontal
            * dpi_scale) * 2)
        draw_h = max(1, round(self.line_thickness * dpi_scale))
        if draw_w < 1:
            return
        draw_x = round(x + self.padding_horizontal * dpi_scale)
        draw_y = round(y + self.padding_vertical * dpi_scale)
        draw_rectangle(renderer, draw_x, draw_y,
            draw_w, draw_h, color=c)

    def get_desired_width(self):  # NOT a widget (where it's "natural_width")
        if self.style != 0.0:
            return round(20.0 * self.style.dpi_scale)
        return 20

    def update_size(self):
        dpi_scale = 1.0
        if self.style != None:
            dpi_scale = self.style.dpi_scale
        self._height = round(
            self.padding_vertical * dpi_scale) * 2 +\
            max(1, round(self.line_thickness * dpi_scale))
    

cdef class Menu(ListBase):
    cdef public object callback_funcs, defocus_on_trigger

    def __init__(self, unfocus_on_trigger=True,
            fixed_one_line_entries=False):
        super().__init__(render_as_menu=True,
            triggered_by_single_click=True,
            fixed_one_line_entries=fixed_one_line_entries)
        self.callback_funcs = []
        self.defocus_on_trigger = unfocus_on_trigger

    def on_triggered(self):
        item_id = self.selected_index
        if item_id >= 0:
            f = None
            if item_id < len(self.callback_funcs):
                if self.callback_funcs[item_id] != None:
                    f = self.callback_funcs[item_id]
            if self.focused and self.defocus_on_trigger:
                self.focus_next()
            if f != None:
                f()

    def add_separator(self):
        self.add("---")
        sep_entry = MenuSeparator(
            self._entries[-1].style,
            is_alternating=self._entries[-1].is_alternating)
        self._entries = self._entries[:-1]
        self._entries.append(sep_entry)
        self._entries[-1].disabled = True
        self.needs_relayout = True

    def add(self, text, func_callback=None,
            global_shortcut_func=None,
            global_shortcut=[]):
        side_text = None
        if len(global_shortcut) > 0:
            side_text = shortcut_to_text(global_shortcut)
        super().add(text, side_text=side_text)
        self.callback_funcs.append(func_callback)
        if len(global_shortcut) > 0 and \
                global_shortcut_func != None:
            register_global_shortcut(global_shortcut,
                global_shortcut_func, self)

    def on_keydown(self, virtual_key, physical_key, modifiers):
        if virtual_key == "escape":
            self.focus_next()
            return True
        return super().on_keydown(virtual_key, physical_key, modifiers)

class ContainerWithSlidingMenu(Widget):
    def __init__(self):
        super().__init__(can_get_focus=False,
            is_container=True)
        self.menu = Menu()
        self.menu_slid_out_x = 0
        self.is_opened = False
        self.continue_infinite_scroll_when_unfocused = True
        self.slide_animation_target = None
        self.animation_callback_scheduled = False
        self.needs_relayout = True
        self.needs_redraw = True
        def menu_focused():
            if self.disabled:
                return
            self.focus(user_callbacks_only=True)
        self.menu.focus.register(menu_focused)
        def menu_unfocused():
            if self.disabled:
                return
            self.unfocus(user_callbacks_only=True)
        self.menu.unfocus.register(menu_unfocused)
        self.menu.extra_focus_check_callback =\
            lambda: self.menu_focus_check()
        super().add(self.menu)

    def menu_focus_check(self):
        return (self.menu_slid_out_x > 0)

    def on_click(self, mouse_id, button, x, y):
        if not self.menu.focused:
            self.stop_infinite_scroll()
            self.close_menu()

    def on_mousewheel(self, mouse_id, x, y):
        if self.menu_slid_out_x < 5 and \
                self.slide_animation_target == "closed":
            self.stop_infinite_scroll()
            return
        scroll_amount = x * 50.0
        self.slide_animation_target = None
        new_x = self.menu_slid_out_x + scroll_amount
        if new_x <= 0:
            if self.menu.focused:
                self.menu.unfocus()
            self.menu_slid_out_x = 0
            self.slide_animation_target = "closed"
        elif new_x >= self.menu.width:
            self.menu_slid_out_x = self.menu.width
            self.slide_animation_target = "open"
        else:
            self.menu_slid_out_x = new_x
        self.menu.x = min(0, round(-self.menu.width +
            self.menu_slid_out_x))
        self.needs_redraw = True
        self.needs_relayout = True

    def get_children_in_strict_mouse_event_order(self):
        return self._children

    def open_menu(self, focus=True):
        if self.slide_animation_target == "open":
            return
        self.menu.selected_index = -1
        self.slide_animation_target = "open"
        self.menu_slid_out_x = max(1,
            self.menu_slid_out_x)
        if focus and not self.menu.focused:
            self.menu.focus()
        self.schedule_animation()

    def close_menu(self):
        if self.slide_animation_target == "closed":
            return
        self.menu.selected_index = -1
        self.slide_animation_target = "closed"
        self.schedule_animation()

    def schedule_animation(self):
        if not self.animation_callback_scheduled:
            self.animation_callback_scheduled = True
            self_ref = weakref.ref(self)
            start_ts = time.monotonic()
            def anim_do():
                self_value = self_ref()
                if self_value is None:
                    return
                self_value.animation_callback_scheduled = False
                self_value.animate(max(0.01, time.monotonic() -
                    start_ts))
            schedule(anim_do, 0.01)

    def animate(self, passed_time):
        if self.slide_animation_target is None:
            return
        target_x = None
        if self.slide_animation_target == "open":
            target_x = self.menu.width
        elif self.slide_animation_target == "closed":
            target_x = 0
        else:
            logwarning('menu.py: unknown slide animation target: ' +
                str(self.slide_animation_target))
            self.slide_animation_target = None
            return
        move = passed_time * self.menu.width * 6.0
        done = False
        if target_x > self.menu_slid_out_x:
            self.menu_slid_out_x += move
            if self.menu_slid_out_x > target_x:
                self.menu_slid_out_x = target_x
                done = True
        elif target_x <= self.menu_slid_out_x:
            self.menu_slid_out_x -= move
            if self.menu_slid_out_x < target_x:
                self.menu_slid_out_x = target_x
                if self.menu.focused:
                    self.menu.unfocus()
                done = True
        if done:
            if self.slide_animation_target == "open":
                self.is_opened = True
            else:
                self.is_opened = False
            self.slide_animation_target = None
        else:
            self.schedule_animation()
        self.menu.x = min(0, round(-self.menu.width +
            self.menu_slid_out_x))
        self.needs_relayout = True
        self.needs_redraw = True

    def on_redraw(self):
        # Draw actual children behind menu, if any:
        if len(self._children) >= 2:
            for child in self._children[1:]:
                child.redraw_if_necessary()
                sdl.SDL_SetRenderDrawColor(self.renderer,
                    255, 255, 255, 255)
                child.draw(child.x, child.y)
        # Draw menu:
        if len(self._children) >= 1:
            child = self._children[0]
            child.redraw_if_necessary()
            sdl.SDL_SetRenderDrawColor(self.renderer,
                255, 255, 255, 255)
            child.draw(child.x, child.y)

    def on_relayout(self):
        self.menu.width = min(int(
            self.menu.get_desired_width() * 1.5),
            self.width)
        self.menu.height = self.height
        if not self.is_opened:
            self.menu.x = min(0, round(-self.menu.width +
                self.menu_slid_out_x))
        else:
            self.menu_x = 0
        self.menu.y = 0
        if len(self._children) >= 2:
            self._children[1].x = 0
            self._children[1].y = 0
            self._children[1].width = self.width
            self._children[1].height = self.height

    def add(self, obj_or_text, func_callback=None,
            global_shortcut_func=None,
            global_shortcut=[]):
        if not isinstance(obj_or_text, str) and \
                func_callback != None or \
                len(global_shortcut) > 0:
            raise ValueError("the provided value is not a string " +
                "and therefore can't be added as menu entry, " +
                "but function callback and/or global shortcut " +
                "for a menu entry were specified") 
        if not isinstance(obj_or_text, str):
            if len(self._children) >= 2:
                raise ValueError("only one layout child is supported")
            super().add(obj_or_text)
        else:
            self.menu.add(obj_or_text, func_callback=func_callback,
                global_shortcut_func=global_shortcut_func,
                global_shortcut=global_shortcut)
        self.needs_relayout = True
        self.needs_redraw = True

    

