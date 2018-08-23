
import ctypes
import math
import sdl2 as sdl
import sdl2.sdlttf as sdlttf
import weakref

from wobblui.color import Color
from wobblui.event import Event
from wobblui.gfx import draw_rectangle
from wobblui.widget_base import all_widgets, WidgetBase
from wobblui.sdlinit import initialize_sdl
from wobblui.style import AppStyleDark
from wobblui.widgetman import all_windows

def get_focused_window():
    global all_windows
    for w_ref in all_windows:
        w = w_ref()
        if w is None or not w.focused:
            continue
        return w
    return None

def get_window_by_sdl_id(sdl_id):
    global all_windows
    for w_ref in all_windows:
        w = w_ref()
        if w is None or w.sdl_window_id != int(sdl_id):
            continue
        return w
    return None

class Window(WidgetBase):
    def __init__(self, title="Untitled", width=640, height=480,
            style=None):
        self.type = "window"
        initialize_sdl()
        if style is None:
            style = AppStyleDark()
        self.mouse_position_cache = dict()
        self._sdl_window = None
        self._style = style
        super().__init__(is_container=True, can_get_focus=True)
        global all_windows
        self._hidden = False
        self._width = width
        self._height = height
        self.hiding = Event("hiding", owner=self)
        self.shown = Event("shown", owner=self)
        self.closing = Event("closing", owner=self)
        self.destroyed = Event("destroyed", owner=self)
        self.is_closed = False
        self._title = title
        self.next_reopen_width = width
        self.next_reopen_height = height
        self.internal_app_reopen()
        all_windows.append(weakref.ref(self))

    def clear(self):
        old_renderer = self._renderer
        self._renderer = None
        for child in self.children:
            child.renderer_update()
            if child.parent == self:
                child.internal_override_parent(None)
        self._children = []
        assert(len(self.children) == 0)
        self._renderer = old_renderer
        self.update()

    def internal_app_reopen(self):
        if self.is_closed:
            return
        unhide = False
        if self._sdl_window is None:
            self._sdl_window = sdl.SDL_CreateWindow(
                self._title.encode("utf-8", "replace"),
                sdl.SDL_WINDOWPOS_CENTERED, sdl.SDL_WINDOWPOS_CENTERED,
                self.next_reopen_width,
                self.next_reopen_height, sdl.SDL_WINDOW_SHOWN |
                sdl.SDL_WINDOW_RESIZABLE)
            unhide = True
            if self._renderer != None:
                sdl.SDL_DestroyRenderer(self._renderer)
                self.renderer = None
        if self._renderer is None:
            self._renderer = \
                sdl.SDL_CreateRenderer(self._sdl_window, -1, 0)
            self.needs_redraw = True
        self.update_to_real_sdlw_size()
        for child in self.children:
            child.renderer_update()
        if unhide:
            self.set_hidden(False)
        self.redraw_if_necessary()

    def handle_sdlw_close(self):
        self.next_reopen_width = self._width
        self.next_reopen_height = self._height

        close_window = False
        if sdl.SDL_GetPlatform().decode("utf-8",
                "replace").lower() != "android":
            print("REGULAR WIN CLOSE")
            if self.closing():
                close_window = True
        else:
            print("ANDROID WIN HIDE")
            if self.focused:
                self.unfocus()
            self.set_hidden(True)

        if close_window or sdl.SDL_GetPlatform().decode("utf-8",
                "replace").lower() == "android":
            if self._renderer != None:
                self._renderer = None
                for child in self.children:
                    child.renderer_update()
                sdl.SDL_DestroyRenderer(self._renderer)
            self._renderer = None
            #if close_window:
            sdl.SDL_DestroyWindow(self._sdl_window)
            self._sdl_window = None
            if close_window:
                self.is_closed = True
                del(self._children)
                self._children = []
                self.destroyed()
            else:
                # Keep it around to be reopened.
                print("ANDROID RENDERER DUMPED. WAITING FOR RESUME.")
                return

    def get_mouse_pos(self, mouse_id):
        if not mouse_id in self.mouse_position_cache:
            return (0, 0)
        return self.mouse_position_cache[mouse_id]

    def _internal_on_mousemove(self, mouse_id, x, y, internal_data=None):
        super()._internal_on_mousemove(mouse_id, x, y,
            internal_data=internal_data)
        self.mouse_position_cache[mouse_id] = (x, y)

    def _internal_on_keydown(self, key, physical_key, modifiers,
            internal_data=None):
        focused_widget = WidgetBase.get_focused_widget_by_window(self)
        if focused_widget is None or \
                focused_widget.keydown(key, physical_key, modifiers):
            # Event was not stopped in user handler. Process focus:
            if key == "tab" and focused_widget != None:
                if not "shift" in modifiers and \
                        hasattr(focused_widget, "focus_next"):
                    focused_widget.focus_next()
                    
                elif "shift" in modifiers and \
                        hasattr(focused_widget, "focus_previous"):
                    focused_widget.focus_previous()
                focused_widget.needs_redraw = True
                new_focused_widget = \
                    WidgetBase.get_focused_widget_by_window(self)
                new_focused_widget.needs_redraw = True

    def _internal_on_textinput(self, text, modifiers, internal_data=None):
        focused_widget = WidgetBase.get_focused_widget_by_window(self)
        if focused_widget != None and focused_widget.takes_text_input:
            focused_widget.textinput(text, modifiers)

    def focus_first_item(self):
        focused_widget = WidgetBase.get_focused_widget_by_window(self)
        if focused_widget != None:
            focused_widget.unfocus()
        self.focus_update()

    def focus_update(self):
        if len(self.children) > 0 and \
                WidgetBase.get_focused_widget_by_window(self) is None:
            sorted_candidates = self.__class__.focus_candidates(
                self.children)
            if len(sorted_candidates) > 0:
                sorted_candidates[0].focus()

    def _internal_on_focus(self, internal_data=None):
        self.focus_update()

    def update_to_real_sdlw_size(self):
        if self._sdl_window is None:
            return
        w = ctypes.c_int32()
        h = ctypes.c_int32()
        sdl.SDL_GetWindowSize(self._sdl_window, ctypes.byref(w),
            ctypes.byref(h))
        self._width = w.value
        self._height = h.value
        self.resized()
        self.needs_redraw = True 

    def get_style(self):
        return self._style

    def set_style(self, style):
        self._style = style
        self.recursive_needs_redraw()
        self.redraw()

    @property
    def sdl_window_id(self):
        if self._sdl_window is None:
            return None
        return int(sdl.SDL_GetWindowID(self._sdl_window))

    @property
    def hidden(self):
        return self._hidden

    def set_hidden(self, new_status):
        new_status = (new_status is True)
        if new_status != self._hidden:
            self._hidden = new_status
            if self.focused and self.hidden:
                self.unfocus()
            if self.hidden:
                self.hiding()
            else:
                self.shown()

    def add(self, *args, **kwargs):
        return_value = super().add(*args, **kwargs)
        if len(self._children) > 0:
            self.focus_update()
        return return_value

    def do_redraw(self):
        if self._sdl_window is None or self.renderer is None:
            return

        # Work around potential SDL bug / race condition
        # (flickering window background)
        c = Color.white
        if self.style != None:
            c = Color(self.style.get("window_bg"))
        draw_rectangle(self.renderer, 0, 0,
            self.width, self.height, color=c)

        self.draw_children()

    def _internal_on_resized(self, internal_data=None):
        self.needs_relayout = True
        for w_ref in all_widgets:
            w = w_ref()
            if w is None or not hasattr(w, "parent_window") or \
                    w.parent_window != self:
                continue
            if hasattr(w, "parentwindowresized"):
                w.parentwindowresized()
        for child in self._children:
            child.needs_relayout = True

    def on_relayout(self):
        changed = False
        if len(self._children) > 0:
            # Make first child fill out the window:
            self._children[0].x = 0
            self._children[0].y = 0
            if self.width != self._children[0].width:
                self._children[0].width = self.width
                changed = True
            if self.height != self._children[0].height:
                self._children[0].height = self.height
                changed = True

            # Let the others float about, but shrink them to
            # window size:
            for child in self._children[1:]:
                child.x = max(0, min(math.floor(self.width) - 1,
                    child.x))
                child.y = max(0, min(math.floor(self.height) - 1,
                    child.y))
                intended_w = min(child.width,
                    max(1, math.floor(self.width) - child.x))
                if child.width != intended_w:
                    changed = True
                    child.width = intended_w
                intended_h = min(child.height,
                    max(1, math.floor(self.height) - child.y))
                if child.height != intended_h:
                    changed = True
                    child.height = intended_h
        if changed:
            self.needs_redraw = True

    def get_children_in_strict_mouse_event_order(self):
        return list(reversed(self._children))

    def _internal_on_post_redraw(self, internal_data=None):
        # Work around double buffering issues by drawing twice:
        i = 0
        while i < 2:
            sdl.SDL_SetRenderTarget(self.renderer, None)
            c = Color.white
            if self.style != None:
                c = Color(self.style.get("window_bg"))
            sdl.SDL_SetRenderDrawColor(self.renderer, c.red,
                c.blue, c.green, 255)
            sdl.SDL_RenderClear(self.renderer)

            # Work around potential SDL bug / race condition:
            # (Flickering texture contents of window)
            draw_rectangle(self.renderer, 0, 0,
                self.width, self.height, color=c)
            if self.sdl_texture != None:
                self.draw(0, 0)
            sdl.SDL_RenderPresent(self.renderer)
            i += 1

    def shares_focus_group(self, other_obj):
        if not isinstance(other_obj, Window):
            return False
        return True

