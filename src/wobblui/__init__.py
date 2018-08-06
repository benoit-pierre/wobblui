
import sdl2 as sdl
import sdl2.ext as sdl_ext
import time

from wobblui.window import all_windows, get_focused_window,\
    get_window_by_sdl_id

def redraw_windows():
    for w_ref in all_windows:
        w = w_ref()
        if w is None or w.hidden:
            continue
        w.redraw_if_necessary()

def event_loop():
    event_loop_ms = 20
    while True:
        events = sdl_ext.get_events()
        redraw_windows()
        if len(events) == 0:
            if event_loop_ms < 400:
                event_loop_ms = min(
                    event_loop_ms + 10,
                    400)
            continue
        else:
            if event_loop_ms > 20:
                event_loop_ms = 20
        for event in events:
            if event.type == sdl.SDL_QUIT:
                window = get_focused_window()
                if window != None and w.focused:
                    window.unfocus()
                for w_ref in all_windows:
                    w = w_ref()
                    if w is None:
                        continue
                    w.closed()
                return
            elif event.type == sdl.SDL_WINDOWEVENT:
                if event.window.event == \
                        sdl.SDL_WINDOWEVENT_FOCUS_GAINED:
                    w = get_window_by_sdl_id(event.window.windowID)
                    if w != None and not w.focused:
                        w.focus()
                        w.redraw()
                elif event.window.event == \
                        sdl.SDL_WINDOWEVENT_FOCUS_LOST:
                    w = get_window_by_sdl_id(event.window.windowID)
                    if w != None:
                        w.unfocus()

