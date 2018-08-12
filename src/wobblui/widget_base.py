
import copy
import ctypes
import functools
import math
import sdl2 as sdl
import sys
import weakref

from wobblui.color import Color
from wobblui.event import DummyEvent, Event
from wobblui.gfx import draw_dashed_line

last_wid = -1
last_add = -1
all_widgets = list()

def tab_sort(a, b):
    if a.focus_index is None and b.focus_index != None:
        return 1
    if b.focus_index is None and a.focus_index != None:
        return -1
    if a.focus_index != b.focus_index:
        return (a.focus_index - b.focus_index)
    return (a.added_order - b.added_order)

class WidgetBase(object):
    def __init__(self, is_container=False,
            can_get_focus=False):
        global all_widgets

        self.type = "unknown"
        self._focusable = can_get_focus
        self.padding = 8
        self.needs_redraw = True

        global last_wid
        self.id = last_wid + 1
        last_wid += 1
        global last_add
        self.added_order = last_add + 1
        last_add += 1

        self.last_mouse_move_was_inside = False
        self.last_mouse_down_presses = set()
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
        self.disabled = False
        self_ref = weakref.ref(self)
        self.sdl_texture = None
        self.sdl_texture_width = -1
        self.sdl_texture_height = -1
        def do_redraw():
            self_value = self_ref()
            if self_value is None or self_value.renderer is None:
                return
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
            old_target = sdl.SDL_GetRenderTarget(self_value.renderer)
            sdl.SDL_SetRenderTarget(self_value.renderer,
                self_value.sdl_texture)
            sdl.SDL_SetRenderDrawColor(self_value.renderer, 0, 0, 0, 0)
            sdl.SDL_RenderClear(self_value.renderer)
            sdl.SDL_SetRenderDrawColor(self_value.renderer,
                255, 255, 255, 255)
            if hasattr(self_value, "do_redraw"):
                self_value.do_redraw()
            sdl.SDL_RenderPresent(self_value.renderer)
            sdl.SDL_SetRenderTarget(self_value.renderer, old_target)
            self_value.post_redraw()
        self.redraw = Event("redraw", owner=self,
            special_post_event_func=do_redraw)
        self.post_redraw = Event("post_redraw", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False)
        self.focus_index = None
        self._is_focused = False
        self.mousemove = Event("mousemove", owner=self)
        self.mousedown = Event("mousedown", owner=self)
        self.mousewheel = Event("mousewheel", owner=self)
        self.keydown = Event("keydown", owner=self)
        self.click = Event("click", owner=self)
        self.mouseup = Event("mouseup", owner=self)
        self.moved = Event("moved", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False)
        self.resized = Event("resized", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False)
        if can_get_focus:
            self.focus = Event("focus", owner=self,
                allow_preventing_widget_callback_by_user_callbacks=False)
            self.unfocus = Event("unfocus", owner=self,
                allow_preventing_widget_callback_by_user_callbacks=False)
        else:
            self.focus = DummyEvent("focus", owner=self)
            self.unfocus = DummyEvent("unfocus", owner=self)
        all_widgets.append(weakref.ref(self))

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
                    rel_x = x - self.x
                    rel_y = y - self.y
                if rel_x >= child.x and rel_y >= child.y and \
                        rel_x < child.x + child.width and \
                        rel_y < child.y + child.height:
                    event_descends_into_child = True
                    break
            if not event_descends_into_child:
                if self.focusable:
                    self.focus()
                else:
                    p = self.parent
                    while p != None and not p.focusable:
                        p = p.parent
                    if p != None and not p.focused:
                        p.focus()

        # Pass on event to child widgets:
        for child in self.children:
            rel_x = x
            rel_y = y
            if coords_are_abs:
                rel_x = x - self.x
                rel_y = y - self.y
            if rel_x >= child.x and rel_y >= child.y and \
                    rel_x < child.x + child.width and \
                    rel_y < child.y + child.height:
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
                    child.click(mouse_id, rel_x - child.x,
                        rel_y - child.y,
                        internal_data=internal_data)
                    child.last_mouse_down_presses.discard(
                        (event_args[0], event_args[1]))
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
                    if event_name == "mousedown" and \
                            not self.focused:
                        self.focus()
                    if not getattr(child, event_name)(mouse_id,
                            event_args[1],
                            rel_x - child.x, rel_y - child.y,
                            internal_data=internal_data):
                        return True
            else:
                if child.last_mouse_move_was_inside:
                    child.last_mouse_move_was_inside = False
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
        return self.width

    def get_natural_height(self, given_width=None):
        return self.height

    def draw_children(self):
        for child in self.children:
            child.redraw_if_necessary()
            sdl.SDL_SetRenderDrawColor(self.renderer,
                255, 255, 255, 255)
            child.draw(child.x, child.y)

    def draw(self, x, y):
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
        sdl.SDL_RenderCopy(self.renderer,
            self.sdl_texture, src, tg)

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

    @property
    def focusable(self):
        return self._focusable

    @property
    def focused(self):
        return self._is_focused

    def shares_focus_group(self, widget):
        return True

    def on_unfocus(self):
        if not self.focused:
            raise RuntimeError("not focused")
        self._is_focused = False
        self.needs_redraw = True

    def update(self):
        self.needs_redraw = True

    def focus_next(self):
        raise RuntimeError("not implemented for this " +
            "type of widget")

    def focus_previous(self):
        raise RuntimeError("not implemented for this " +
            "type of widget")

    def on_focus(self):
        def unfocus_focused():
            global all_widgets
            for w_ref in all_widgets:
                w = w_ref()
                if w is None or not w.shares_focus_group(self):
                    continue
                if w.focused:
                    w.unfocus()
        if self.disabled:
            return True  # prevent focus
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

    def add(self, item, trigger_resize=True):
        if not self.is_container:
            raise RuntimeError("this widget is " +
                "not a container, can't add children")
        self._children.append(item)
        item.internal_override_parent(self)
        self.needs_redraw = True
        if trigger_resize:
            self.resized()

    def internal_override_parent(self, parent):
        self._parent = parent
        self.needs_redraw = True

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return copy.copy(self.get_children())

    def get_children(self):
        return self._children


