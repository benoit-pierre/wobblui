
import ctypes
import sdl2 as sdl
import sdl2.sdlttf as sdlttf
import weakref

from wobblui.color import Color
from wobblui.event import Event
from wobblui.widget_base import WidgetBase
from wobblui.style import AppStyleDark

SDL_initialized=False

all_windows = []

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
        if style is None:
            style = AppStyleDark()
        self._style = style
        super().__init__(is_container=True, can_get_focus=True,
            autofocus=False)
        global all_windows, SDL_initialized
        if not SDL_initialized:
            SDL_initialized = True
            sdl.SDL_Init(sdl.SDL_INIT_VIDEO|sdl.SDL_INIT_TIMER)
            sdlttf.TTF_Init()
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

    def internal_app_reopen(self):
        self._sdl_window = sdl.SDL_CreateWindow(
            self._title.encode("utf-8", "replace"),
            sdl.SDL_WINDOWPOS_CENTERED, sdl.SDL_WINDOWPOS_CENTERED,
            self.next_reopen_width,
            self.next_reopen_height, sdl.SDL_WINDOW_SHOWN |
            sdl.SDL_WINDOW_RESIZABLE)
        self._renderer = \
            sdl.SDL_CreateRenderer(self._sdl_window, -1, 0)
        self._unclosable = False
        self.update_to_real_sdlw_size()

    def handle_sdlw_close(self):
        self.next_reopen_width = self._width
        self.next_reopen_height = self._height
        if self._renderer != None:
            self._renderer = None
            for child in self.children:
                child.renderer_update()
            sdl.SDL_DestroyRenderer(self._renderer)
        self._renderer = None
        sdl.SDL_DestroyWindow(self._sdl_window)
        self._sdl_window = None
        if not self._unclosable:
            self.is_closed = True
            del(self._children)
            self._children = []
            self.destroyed()

    def update_to_real_sdlw_size(self):
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
            focus_item = WidgetBase.\
                get_focused_widget(self._children[0])
            if focus_item is None:
                for child in self._children:
                    if child.focusable:
                        self._children[0].focus()
                        break
        return return_value

    def do_redraw(self):
        self.draw_children()

    def _internal_on_resized(self):
        for child in self.children:
            child.width = self.width
            child.height = self.height

    def _internal_on_post_redraw(self):
        sdl.SDL_SetRenderTarget(self.renderer, None)
        c = Color.white
        if self.style != None:
            c = Color(self.style.get("window_bg"))
        sdl.SDL_SetRenderDrawColor(self.renderer, c.red,
            c.blue, c.green, 255)
        sdl.SDL_RenderClear(self.renderer)
        if self.sdl_texture != None:
            self.draw(0, 0)
        sdl.SDL_RenderPresent(self.renderer)

    @property
    def unclosable(self):
        return self._unclosable

    def set_unclosable(self):
        self._unclosable = True

    def shares_focus_group(self, other_obj):
        if not isinstance(other_obj, Window):
            return False
        return True

