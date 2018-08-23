
import weakref

from wobblui.color import Color
from wobblui.event import Event
from wobblui.gfx import draw_rectangle
from wobblui.keyboard import register_global_shortcut,\
    shortcut_to_text
from wobblui.list import ListBase, ListEntry

class MenuSeparator(ListEntry):
    def __init__(self, style, is_alternating=False):
        super().__init__("---", style,
            is_alternating=is_alternating)
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

    def draw(self, renderer, x, y, draw_selected=False,
            draw_hover=False,
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

    def get_natural_width(self):
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
    

class Menu(ListBase):
    def __init__(self):
        super().__init__(render_as_menu=True)
        self.callback_funcs = []
        self.triggered_by_single_click = True

    def on_triggered(self):
        item_id = self.selected_index
        if item_id >= 0:
            f = None
            if item_id < len(self.callback_funcs):
                if self.callback_funcs[item_id] != None:
                    f = self.callback_funcs[item_id]
            if self.focused:
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
