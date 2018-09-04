
import sdl2 as sdl
import time
import weakref

from wobblui.color import Color
from wobblui.event import Event
from wobblui.gfx import draw_rectangle
from wobblui.keyboard import register_global_shortcut,\
    shortcut_to_text
from wobblui.list import ListBase, ListEntry
from wobblui.timer import schedule
from wobblui.widget import Widget

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
    def __init__(self, unfocus_on_trigger=True):
        super().__init__(render_as_menu=True,
            triggered_by_single_click=True)
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
            if self._disabled:
                return
            self.focus(user_callbacks_only=True, ignore_disabled=True)
        self.menu.focus.register(menu_focused)
        def menu_unfocused():
            if self._disabled:
                return
            self.unfocus(user_callbacks_only=True, ignore_disabled=True)
        self.menu.unfocus.register(menu_unfocused)
        super().add(self.menu)

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
        if new_x < 0:
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

    def open_menu(self):
        if self.slide_animation_target == "open":
            return
        self.menu.selected_index = -1
        self.slide_animation_target = "open"
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
            schedule(anim_do, 0.05)

    def animate(self, passed_time):
        if self.slide_animation_target is None:
            return
        target_x = None
        if self.slide_animation_target == "open":
            target_x = self.menu.width
        elif self.slide_animation_target == "closed":
            target_x = 0
        else:
            print('warning: unknown slide animation target: ' +
                str(self.slide_animation_target), file=sys.stderr,
                flush=True)
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
            self.menu.get_natural_width() * 1.5),
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

    

