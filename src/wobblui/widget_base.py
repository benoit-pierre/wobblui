
import copy
import ctypes
import functools
import math
import sdl2 as sdl
import sys
import weakref

from wobblui.event import DummyEvent, Event

last_wid = -1
all_widgets = list()

def tab_sort(a, b):
    if a.focus_index is None and b.focus_index != None:
        return 1
    if b.focus_index is None and a.focus_index != None:
        return -1
    if a.focus_index != b.focus_index:
        return (a.focus_index - b.focus_index)
    return (a.id - b.id)

class WidgetBase(object):
    def __init__(self, is_container=False,
            can_get_focus=False):
        global all_widgets, last_wid
        self._focusable = can_get_focus
        self.padding = 8
        self.needs_redraw = True
        self.id = last_wid + 1
        self.last_mouse_move_was_inside = False
        self.last_mouse_down_presses = set()
        self.x = 0
        self.y = 0
        self._width = 64
        self._height = 64
        self._max_width = None
        self._max_height = None
        last_wid += 1
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
            if self_value is None:
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
        self.click = Event("click", owner=self)
        self.mouseup = Event("mouseup", owner=self)
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

    def _post_mouse_event_handling(self, event_name,
            event_args, internal_data=None):
        # If we arrived here, the internal event wasn't prevented from
        # firing / propagate. Inform all children that are inside the
        # mouse bounds:
        x = None
        y = None
        mouse_id = event_args[0]
        if event_name == "mousedown" or event_name == "mouseup":
            x = event_args[2]
            y = event_args[3]
        elif event_name == "mousemove":
            x = event_args[1]
            y = event_args[2]
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
        for child in self.children:
            rel_x = x
            rel_y = y
            if coords_are_abs:
                rel_x = x - self.x
                rel_y = y - self.y
            if rel_x >= child.x and rel_y >= child.y and \
                    rel_x < child.x + child.width and \
                    rel_y < child.y + child.height:
                if event_name == "mousemove":
                    child.last_mouse_move_was_inside = True
                elif event_name == "mousedown":
                    child.last_mouse_down_presses.add((event_args[0],
                        event_args[1]))
                    # Try to focus this if it's the most inner clicked:
                    if inside_parent is False:
                        if child.focusable:
                            child.focus()
                        else:
                            p = child.parent
                            while parent != None and not p.focusable:
                                p = p.parent
                            if p != None:
                                p.focus()
                elif event_name == "mouseup" and \
                        (event_args[0], event_args[1]) in \
                        child.last_mouse_down_presses:
                    # Special click event:
                    child.click(mouse_id, rel_x - child.x,
                        rel_y - child.y,
                        internal_data=internal_data)
                    child.last_mouse_down_presses.discard(
                        (event_args[0], event_args[1]))
                if event_name == "mousemove":
                    if not getattr(child, event_name)(mouse_id,
                            rel_x - child.x, rel_y - child.y,
                            internal_data=internal_data):
                        # Propagation was stopped. Signal that we took
                        # care of this event to our caller:
                        return True
                else:
                    if not getattr(child, event_name)(mouse_id,
                            event_args[1],
                            rel_x - child.x, rel_y - child.y,
                            internal_data=internal_data):
                        # Propagation was stopped. Signal that we took
                        # care of this event to our caller:
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
        tg = sdl.SDL_Rect()
        tg.x = x
        tg.y = y
        tg.w = max(1, round(self.width))
        tg.h = max(1, round(self.height))
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

    def set_focus_index(self, index):
        self.focus_index = index

    def set_sdl_renderer(self, renderer):
        self._renderer = renderer

    def get_renderer(self):
        return self._renderer

    @property
    def renderer(self):
        return self.get_renderer()

    def add(self, item):
        if not self.is_container:
            raise RuntimeError("this widget is " +
                "not a container, can't add children")
        self._children.append(item)
        item.internal_override_parent(self)
        self.needs_redraw = True
        self.resized()

    def internal_override_parent(self, parent):
        self._parent = parent

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return copy.copy(self.get_children())

    def get_children(self):
        return self._children


