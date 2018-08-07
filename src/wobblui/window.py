
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
        self.closed = Event("closed", owner=self)
        self._sdl_window = sdl.SDL_CreateWindow(
            title.encode("utf-8", "replace"),
            sdl.SDL_WINDOWPOS_CENTERED, sdl.SDL_WINDOWPOS_CENTERED,
            width, height, sdl.SDL_WINDOW_SHOWN |
            sdl.SDL_WINDOW_RESIZABLE)
        self._renderer = \
            sdl.SDL_CreateRenderer(self._sdl_window, -1, 0)
        self._unclosable = False
        self.update_to_real_sdlw_size()
        all_windows.append(weakref.ref(self))

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

