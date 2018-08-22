
import copy
import ctypes
import functools
import math
import sdl2 as sdl
import sys
import time
import traceback
import weakref

from wobblui.color import Color
from wobblui.event import DummyEvent, Event
from wobblui.gfx import draw_dashed_line
from wobblui.keyboard import enable_text_events
from wobblui.uiconf import config
from wobblui.widgetman import add_widget, all_widgets, \
    get_widget_id, get_add_id, tab_sort

class WidgetBase(object):
    def __init__(self, is_container=False,
            can_get_focus=False,
            takes_text_input=False):
        self.type = "unknown"
        self._focusable = can_get_focus
        self.needs_redraw = True
        self._invisible = False

        self.id = get_widget_id()
        self.added_order = get_add_id()

        self.needs_relayout = True
        self.last_mouse_move_was_inside = False
        self.last_mouse_down_presses = set()
        self.last_mouse_click_with_time = dict()
        self._x = 0
        self._y = 0
        self._width = 64
        self._height = 64
        self._max_width = None
        self._max_height = None
        self.is_container = is_container
        self._children = []
        self._parent = None
        self._renderer = None
        self._disabled = False
        self_ref = weakref.ref(self)
        self.sdl_texture = None
        self.sdl_texture_width = -1
        self.sdl_texture_height = -1

        self.restore_old_target = -1
        def start_redraw():
            self_value = self_ref()
            if self_value is None or self_value.renderer is None:
                return
            if self_value.needs_relayout:
                self_value.relayout()
            if self_value.restore_old_target != -1:
                raise RuntimeError("nested redraw on " +
                    str(self_value) + ", this is forbidden")
            dpi_scale = self_value.style.dpi_scale
            tex_x = max(1, math.ceil(self_value.width + 1.0))
            tex_y = max(1, math.ceil(self_value.height + 1.0))
            if self_value.sdl_texture is None or \
                    self_value.sdl_texture_width != tex_x or \
                    self_value.sdl_texture_height != tex_y:
                if self_value.renderer is None or \
                        tex_x <= 0 or tex_y <= 0:
                    if self_value.renderer is None:
                        self.needs_redraw = True
                    return
                if self_value.sdl_texture != None:
                    sdl.SDL_DestroyTexture(self_value.sdl_texture)
                    self_value.sdl_texture = None 
                self_value.sdl_texture = sdl.SDL_CreateTexture(
                    self_value.renderer,
                    sdl.SDL_PIXELFORMAT_RGBA8888,
                    sdl.SDL_TEXTUREACCESS_TARGET,
                    tex_x, tex_y)
                if self_value.sdl_texture is None:
                    print("warning: failed to create texture in " +
                        "wobblui.widget_base.WidgetBase",
                        file=sys.stderr, flush=True)
                    self_value.needs_redraw = False
                    return
                sdl.SDL_SetTextureBlendMode(self_value.sdl_texture,
                    sdl.SDL_BLENDMODE_BLEND)
                self_value.sdl_texture_width = tex_x
                self_value.sdl_texture_height = tex_y
            self_value.restore_old_target = \
                sdl.SDL_GetRenderTarget(self_value.renderer)
            sdl.SDL_SetRenderTarget(self_value.renderer,
                self_value.sdl_texture)
            sdl.SDL_SetRenderDrawColor(self_value.renderer, 0, 0, 0, 0)
            sdl.SDL_RenderClear(self_value.renderer)
            sdl.SDL_SetRenderDrawColor(self_value.renderer,
                255, 255, 255, 255)
        def end_redraw():
            self_value = self_ref()
            if self_value is None or self_value.renderer is None:
                return
            sdl.SDL_SetRenderDrawColor(self_value.renderer,
                255, 255, 255, 255)
            if hasattr(self_value, "do_redraw"):
                self_value.do_redraw()
            sdl.SDL_RenderPresent(self_value.renderer)
            sdl.SDL_SetRenderTarget(self_value.renderer,
                self_value.restore_old_target)
            self_value.restore_old_target = -1
            self_value.post_redraw()
        self.redraw = Event("redraw", owner=self,
            special_post_event_func=end_redraw,
            special_pre_event_func=start_redraw)
        self.post_redraw = Event("post_redraw", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False)
        self.focus_index = None
        self._is_focused = False

        # Note: textinput event can't be a dummy event even if
        # widget doesn't take text input, because Window instnaces
        # need this event to be working even not marked as widgets
        # taking text input (which would cause them to prompt the
        # virtual keyboard on Android/iOS merely by existing).
        # Therefore, the event must always work, but the window
        # won't actually dispatch it to any widget if it's not
        # marked with .takes_text_input = True
        self.textinput = Event("textinput", owner=self)
        if not can_get_focus or not takes_text_input:
            self.takes_text_input = False
        else:
            self.takes_text_input = True

        self.parentchanged = Event("parentchanged", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False)
        self.mousemove = Event("mousemove", owner=self)
        self.mousedown = Event("mousedown", owner=self)
        self.mousewheel = Event("mousewheel", owner=self)
        self.stylechanged = Event("stylechanged", owner=self)
        self.keydown = Event("keydown", owner=self)
        self.click = Event("click", owner=self)
        self.doubleclick = Event("doubleclick", owner=self)
        self.mouseup = Event("mouseup", owner=self)
        self.relayout = Event("relayout", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False)
        self.moved = Event("moved", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False)
        self.resized = Event("resized", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False)
        self.focus = Event("focus", owner=self,
                allow_preventing_widget_callback_by_user_callbacks=False)
        if can_get_focus:
            self.unfocus = Event("unfocus", owner=self,
                allow_preventing_widget_callback_by_user_callbacks=False)
        else:
            self.unfocus = DummyEvent("unfocus", owner=self)
        add_widget(self)

    def set_invisible(self, v):
        self.invisible = v

    @property
    def invisible(self):
        return self._invisible

    @invisible.setter
    def invisible(self, v):
        v = (v is True)
        if self._invisible != v:
            self._invisible = v
            if self.focused:
                if hasattr(self, "focus_next"):
                    self.focus_next()
                if self.focused:
                    self.unfocus()
            self.needs_relayout = True
            if self.parent != None:
                self.parent.needs_relayout = True
            self.update()

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, v):
        v = (v is True)
        if self._disabled != v:
            self._disabled = v
            if self.focused:
                if hasattr(self, "focus_next"):
                    self.focus_next()
                if self.focused:
                    self.unfocus()
            self.update()

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, v):
        if self._x != v:
            self._x = v
            self.moved()

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, v):
        if self._y != v:
            self._y = v
            self.moved()

    def _internal_on_relayout(self, internal_data=None):
        self.needs_relayout = False
        need_parent_relayout = True
        current_natural_width = self.get_natural_width()
        current_natural_height = self.get_natural_height(
            given_width=current_natural_width)
        if hasattr(self, "_cached_previous_natural_width"):
            if self._cached_previous_natural_width == \
                    current_natural_width and \
                    self._cached_previous_natural_height ==\
                    current_natural_height:
                need_parent_relayout = False
        self._cached_previous_natural_width = current_natural_width
        self._cached_previous_natural_height = current_natural_height
        if self.parent != None and need_parent_relayout:
            self.parent.needs_relayout = True
            self.parent.needs_redraw = True

    def _internal_on_mousedown(self, mouse_id, button, x, y,
            internal_data=None):
        self._post_mouse_event_handling("mousedown",
            [mouse_id, button, x, y],
            internal_data=internal_data)

    def _internal_on_mouseup(self, mouse_id, button, x, y,
            internal_data=None):
        self._post_mouse_event_handling("mouseup",
            [mouse_id, button, x, y],
            internal_data=internal_data)

    def _internal_on_mousemove(self, mouse_id, x, y, internal_data=None):
        self._post_mouse_event_handling("mousemove", [mouse_id, x, y],
            internal_data=internal_data)

    def _internal_on_mousewheel(self, mouse_id, x, y, internal_data=None):
        self._post_mouse_event_handling("mousewheel",
            [mouse_id, x, y],
            internal_data=internal_data)

    @property
    def abs_x(self):
        x = self.x
        p = self.parent
        while p != None:
            x += p.x
            p = p.parent
        return x

    @property
    def abs_y(self):
        y = self.y
        p = self.parent
        while p != None:
            y += p.y
            p = p.parent
        return y

    def _post_mouse_event_handling(self, event_name,
            event_args, internal_data=None):
        # If we arrived here, the internal event wasn't prevented from
        # firing / propagate. Inform all children that are inside the
        # mouse bounds:
        wx = None
        wy = None
        x = None
        y = None
        mouse_id = event_args[0]
        if event_name == "mousedown" or event_name == "mouseup":
            x = event_args[2]
            y = event_args[3]
        elif event_name == "mousemove":
            x = event_args[1]
            y = event_args[2]
        elif event_name == "mousewheel":
            wx = event_args[1]
            wy = event_args[2]
            if (not hasattr(self, "parent_window") or
                    self.parent_window == None) and \
                    not hasattr(self, "get_mouse_pos"):
                # Wheel with no parent window. bail out, that's useless
                return
            if hasattr(self, "get_mouse_pos"):
                (x, y) = self.get_mouse_pos(event_args[0])
            else:
                (x, y) = self.parent_window.get_mouse_pos(event_args[0])

        coords_are_abs = False
        if internal_data != None:
            coords_are_abs = True
            x = internal_data[0]
            y = internal_data[1]
        inside_parent = False
        if (coords_are_abs and x >= self.x and y >= self.y and
                x < self.x + self.width and y < self.y + self.width) or \
                (not coords_are_abs and x >= 0 and y >= 0 and
                    x < self.width and y < self.width):
            inside_parent = True

        # See if we want to focus this widget:
        if event_name == "mousedown":
            event_descends_into_child = False
            for child in self.children:
                rel_x = x
                rel_y = y
                if coords_are_abs:
                    rel_x = x - self.abs_x
                    rel_y = y - self.abs_y
                if rel_x >= child.x and rel_y >= child.y and \
                        rel_x < child.x + child.width and \
                        rel_y < child.y + child.height:
                    event_descends_into_child = True
                    break
            if not event_descends_into_child:
                if self.focusable and not self.focused:
                    self.focus()
                else:
                    p = self.parent
                    while p != None and not p.focusable:
                        p = p.parent
                    if p != None and not p.focused:
                        p.focus()

        # Pass on event to child widgets:
        child_list = self.children
        check_widget_overlap = False
        if hasattr(self, "get_children_in_strict_mouse_event_order"):
            child_list = self.get_children_in_strict_mouse_event_order()
            check_widget_overlap = True
        force_no_more_matches = False
        for child in child_list:
            rel_x = x
            rel_y = y
            if coords_are_abs:
                rel_x = x - self.abs_x
                rel_y = y - self.abs_y
            if not force_no_more_matches and \
                    rel_x >= child.x and rel_y >= child.y and \
                    rel_x < child.x + child.width and \
                    rel_y < child.y + child.height and \
                    not child.invisible and \
                    (not child.disabled or event_name != "mousedown"):
                # If we're in strict ordered mouse event mode, this
                # widget will be treated as obscuring the next ones:
                if check_widget_overlap:
                    force_no_more_matches = True
                # Track some side effects, to make sure e.g. mouse move
                # events get followed up by one last outside-of-widget
                # event when mouse leaves, or that mouse down changes
                # the keyboard focus:
                if event_name == "mousemove":
                    child.last_mouse_move_was_inside = True
                elif event_name == "mousedown":
                    child.last_mouse_down_presses.add((event_args[0],
                        event_args[1]))
                elif event_name == "mouseup" and \
                        (event_args[0], event_args[1]) in \
                        child.last_mouse_down_presses:
                    # Special click event:
                    child.last_mouse_down_presses.discard(
                        (event_args[0], event_args[1]))

                    # See if this is a double-click:
                    t = time.monotonic() - 10.0
                    if (event_args[0], event_args[1]) in \
                            child.last_mouse_click_with_time:
                        t = child.last_mouse_click_with_time[
                            (event_args[0], event_args[1])]
                    if t > time.monotonic() - config.get("doubleclick_time"):
                        # It's a double click!
                        del(child.last_mouse_click_with_time[
                            (event_args[0], event_args[1])])
                        child.doubleclick(mouse_id, event_args[1],
                            rel_x - child.x,
                            rel_y - child.y)
                    else:
                        # Just a normal click.
                        child.last_mouse_click_with_time[
                            (event_args[0], event_args[1])] = \
                            time.monotonic()
                        child.click(mouse_id, event_args[1],
                            rel_x - child.x,
                            rel_y - child.y,
                            internal_data=internal_data)
                # Trigger actual event on the child widget:
                if event_name == "mousemove":
                    if not child.mousemove(mouse_id,
                            rel_x - child.x, rel_y - child.y,
                            internal_data=internal_data):
                        return True
                elif event_name == "mousewheel":
                    if not child.mousewheel(mouse_id, wx,  wy,
                            internal_data=internal_data):
                        return True
                else:
                    if not getattr(child, event_name)(mouse_id,
                            event_args[1],
                            rel_x - child.x, rel_y - child.y,
                            internal_data=internal_data):
                        return True
            else:
                if child.last_mouse_move_was_inside:
                    child.last_mouse_move_was_inside = False
                    if force_no_more_matches:
                        # Need to use true outside fake coordinates
                        # to remove focus etc
                        child.mousemove(mouse_id, -5, -5)
                    else:
                        child.mousemove(mouse_id,
                            rel_x - child.x, rel_y - child.y,
                            internal_data=internal_data)
                if event_name == "mouseup" and \
                        (event_args[0], event_args[1]) in \
                        child.last_mouse_down_presses:
                    child.last_mouse_down_presses.discard(
                        (event_args[0], event_args[1]))
                    child.mouseup(mouse_id, event_args[1],
                        rel_x - child.x, rel_y - child.y,
                        internal_data=internal_data)
        # Done!

    def __del__(self):
        if hasattr(self, "sdl_texture") and \
                self.sdl_texture != None:
            sdl.SDL_DestroyTexture(self.sdl_texture)
            self.sdl_texture = None
        return

    def renderer_update(self):
        if self.sdl_texture != None:
            sdl.SDL_DestroyTexture(self.sdl_texture)
            self.sdl_texture = None
        for child in self.children:
            child.renderer_update()

    @property
    def style(self):
        return self.get_style()

    def get_style(self):
        return None

    def recursive_needs_redraw(self):
        self.needs_redraw = True
        for child in self.children:
            child.recursive_needs_redraw()

    @property
    def dpi_scale(self):
        s = self.style
        if s != None:
            return s.dpi_scale
        return 1.0

    def get_natural_width(self):
        return 64

    def get_natural_height(self, given_width=None):
        return 64

    def draw_children(self):
        for child in self.children:
            child.redraw_if_necessary()
            sdl.SDL_SetRenderDrawColor(self.renderer,
                255, 255, 255, 255)
            child.draw(child.x, child.y)

    def draw(self, x, y):
        if self.invisible:
            return
        self.redraw_if_necessary()
        if self.sdl_texture is None:
            if self._width < 0 or self._height < 0 or \
                    self.renderer is None:
                return
            self.redraw()
            if self.sdl_texture is None:
                return
        w = ctypes.c_int32()
        h = ctypes.c_int32()
        sdl.SDL_QueryTexture(self.sdl_texture, None, None,
            ctypes.byref(w), ctypes.byref(h))
        tg = sdl.SDL_Rect()
        tg.x = round(x)
        tg.y = round(y)
        tg.w = max(1, round(w.value))
        tg.h = max(1, round(h.value))
        src = sdl.SDL_Rect()
        src.x = 0
        src.y = 0
        src.w = tg.w
        src.h = tg.h
        sdl.SDL_SetRenderDrawColor(self.renderer,
            255, 255, 255, 255)
        sdl.SDL_RenderCopy(self.renderer, self.sdl_texture, src, tg)

    def relayout_if_necessary(self):
        changed = False
        for child in self.children:
            if child.relayout_if_necessary():
                changed = True
        if self.needs_relayout:
            changed = True
            self.relayout()
        return changed

    def redraw_if_necessary(self):
        for child in self.children:
            if child.redraw_if_necessary():
                self.needs_redraw = True
        if self.needs_redraw:
            self.needs_redraw = False
            self.redraw()
            return True
        return (self.needs_redraw is True)

    def do_redraw(self):
        pass

    def set_max_width(self, w):
        if w != None:
            w = max(0, int(w))
        if self._max_width == w:
            return
        self._max_width = w
        self.resized()

    def set_max_height(self, w):
        if w != None:
            w = max(0, int(w))
        if self._max_height == w:
            return
        self._max_height = w
        self.resized()

    @property
    def width(self):
        if self._max_width != None:
            return min(self._max_width, self._width)
        return self._width

    @property
    def height(self):
        if self._max_height != None:
            return min(self._max_height, self._height)
        return self._height

    @width.setter
    def width(self, v):
        if self._width != v:
            self.size_change(v, self.height)

    @height.setter
    def height(self, h):
        if self._height != h:
            self.size_change(self.width, h)

    @staticmethod
    def focus_candidates(group_widget):
        global all_widgets
        assert(group_widget != None)
        group_widgets = group_widget
        if type(group_widgets) != list:
            group_widgets = [group_widgets]
        candidates = []
        for w_ref in all_widgets:
            w = w_ref()
            if w is None or not w.focusable:
                continue
            is_in_group = False
            for group_widget in group_widgets:
                if w.shares_focus_group(group_widget) and \
                        group_widget.shares_focus_group(w):
                    is_in_group = True
                    break
            if not is_in_group:
                continue
            assert(w != None)
            candidates.append(w)
        for group_widget in group_widgets:
            if not group_widget in candidates and \
                    group_widget.focusable:
                candidates.append(group_widget)
        sorted_candidates = sorted(candidates,
            key=functools.cmp_to_key(tab_sort))
        return sorted_candidates

    def size_change(self, w, h):
        self._width = w
        self._height = h
        self.needs_relayout = True
        self.needs_redraw = True
        self.resized()

    @staticmethod
    def get_focused_widget(group_widget):
        global all_widgets
        for w_ref in all_widgets:
            w = w_ref()
            if w is None or not w.focused or \
                    not w.shares_focus_group(group_widget) or \
                    not group_widget.shares_focus_group(w):
                continue
            return w
        return None

    @staticmethod
    def get_focused_widget_by_window(window):
        global all_widgets
        for w_ref in all_widgets:
            w = w_ref()
            if w is None or not w.focused \
                    or not hasattr(w, "parent_window") \
                    or w.parent_window != window:
                continue
            return w

    def _internal_on_stylechanged(self, internal_data=None):
        self.needs_redraw = True

    @property
    def focusable(self):
        return (self._focusable and not self.disabled and \
            not self.invisible)

    @property
    def focused(self):
        return self._is_focused

    def shares_focus_group(self, widget):
        return True

    def _internal_on_unfocus(self, internal_data=None):
        if not self.focused:
            raise RuntimeError("not focused")
        self._is_focused = False
        self.needs_redraw = True

    def update(self):
        self.needs_relayout = True
        self.needs_redraw = True

    def focus_next(self):
        raise RuntimeError("not implemented for this " +
            "type of widget")

    def focus_previous(self):
        raise RuntimeError("not implemented for this " +
            "type of widget")

    def on_focus(self):
        if self.focused:
            return
        def unfocus_focused():
            global all_widgets
            for w_ref in all_widgets:
                w = w_ref()
                if w is None or w is self or \
                        not w.shares_focus_group(self):
                    continue
                if w.focused:
                    w.unfocus()
        if self.disabled or self.invisible:
            return True  # prevent focus entirely
        if not self.focusable:
            # See if a child can be focused:
            def try_children_focus(w):
                tab_index_sorted = sorted(w.children,
                    key=functools.cmp_to_key(tab_sort))
                for child in tab_index_sorted:
                    if child.disabled:
                        continue
                    if not child.focusable:
                        if try_children_focus(child):
                            return True
                    else:
                        child.focus()
                        return True
                return False
            if not try_children_focus(self):
                return True  # prevent focus
        else:
            do_event = False
            if not self.focused:
                try:
                    unfocus_focused()
                finally:
                    self._is_focused = True
                    self.needs_redraw = True
                    if self.takes_text_input:
                        enable_text_events(self)

    def set_focus_index(self, index):
        self.focus_index = index

    def set_sdl_renderer(self, renderer):
        self._renderer = renderer

    def get_renderer(self):
        return self._renderer

    def draw_keyboard_focus(self, x, y, width, height):
        focus_border_thickness = 1.0
        c = Color.red
        if c != None:
            c = Color(self.style.get("focus_border"))
        draw_dashed_line(self.renderer,
            x + 0.5 * focus_border_thickness * self.dpi_scale,
            y,
            x + 0.5 * focus_border_thickness * self.dpi_scale,
            y + height,
            dash_length=(7.0 * self.dpi_scale),
            thickness=(focus_border_thickness * self.dpi_scale),
            color=c)
        draw_dashed_line(self.renderer,
            x + width - 0.5 * focus_border_thickness * self.dpi_scale,
            y,
            x + width - 0.5 * focus_border_thickness * self.dpi_scale,
            y + height,
            dash_length=(7.0 * self.dpi_scale),
            thickness=(focus_border_thickness * self.dpi_scale),
            color=c)
        draw_dashed_line(self.renderer,
            x,
            y + 0.5 * focus_border_thickness * self.dpi_scale,
            x + width,
            y + 0.5 * focus_border_thickness * self.dpi_scale,
            dash_length=(7.0 * self.dpi_scale),
            thickness=(focus_border_thickness * self.dpi_scale),
            color=c)
        draw_dashed_line(self.renderer,
            x,
            y + height - 0.5 * focus_border_thickness * self.dpi_scale,
            x + width,
            y + height - 0.5 * focus_border_thickness * self.dpi_scale,
            dash_length=(7.0 * self.dpi_scale),
            thickness=(focus_border_thickness * self.dpi_scale),
            color=c)

    @property
    def renderer(self):
        return self.get_renderer()

    def remove(self, item, error_if_not_present=True):
        if not self.is_container:
            raise RuntimeError("this widget is " +
                "not a container, can't remove children")
        if not item in self._children:
            if error_if_not_present:
                raise ValueError("child is not contained: " +
                    str(item))
            return
        if item.parent == self:
            item.internal_override_parent(None)
        self._children.remove(item)

    def add(self, item, trigger_resize=True):
        if not self.is_container:
            raise RuntimeError("this widget is " +
                "not a container, can't add children")
        # Check that this nesting is valid:
        if item == self:
            raise ValueError("cannot add widget to itself")
        item_p = item.parent
        while item_p != None:
            if item_p == self:
                raise ValueError("cannot add widget here, " +
                    "this results in a cycle")
            item_p = item_p.parent

        # Remove item from previous parent if any:
        if item.parent != None:
            item.parent.remove(item, error_if_not_present=False)
        self._children.append(item)
        self.needs_relayout = True
        item.internal_override_parent(self)
        self.needs_redraw = True
        item.relayout()
        if trigger_resize:
            self.resized()

    def internal_override_parent(self, parent):
        if self._parent == parent:
            return
        prev_style = self.get_style()
        old_parent = self._parent
        self._parent = parent
        self.needs_redraw = True
        self.parentchanged()
        if prev_style != self.get_style():
            def recursive_style_event(item):
                item.stylechanged()
                for child in item.children:
                    recursive_style_event(child)
            recursive_style_event(self) 

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return copy.copy(self.get_children())

    def get_children(self):
        return self._children


