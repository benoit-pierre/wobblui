
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
                    if w is None or w.is_closed:
                        continue
                    w.destroyed()
                return
            elif event.type == sdl.SDL_WINDOWEVENT:
                if event.window.event == \
                        sdl.SDL_WINDOWEVENT_FOCUS_GAINED:
                    w = get_window_by_sdl_id(event.window.windowID)
                    if w != None and not w.focused and not w.is_closed:
                        w.focus()
                        w.redraw()
                elif event.window.event == \
                        sdl.SDL_WINDOWEVENT_RESIZED:
                    w = get_window_by_sdl_id(event.window.windowID)
                    if w != None and not w.is_closed:
                        w.update_to_real_sdlw_size()
                elif event.window.event == \
                        sdl.SDL_WINDOWEVENT_FOCUS_LOST:
                    w = get_window_by_sdl_id(event.window.windowID)
                    if w != None and w.focused and not w.is_closed:
                        w.unfocus()
                elif event.window.event == \
                        sdl.SDL_WINDOWEVENT_CLOSE:
                    w = get_window_by_sdl_id(event.window.windowID)
                    if w != None:
                        if w.focused:
                            w.unfocus()
                        w.handle_sdlw_close()
                elif (event.window.event ==
                        sdl.SDL_WINDOWEVENT_HIDDEN or
                        event.window.event ==
                        sdl.SDL_WINDOWEVENT_MINIMIZED):
                    w = get_window_by_sdl_id(event.window.windowID)
                    if w != None and not w.hidden and not w.is_closed:
                        w.set_hidden(True)
                elif (event.window.event ==
                        sdl.SDL_WINDOWEVENT_RESTORED or
                        event.window.event ==
                        sdl.SDL_WINDOWEVENT_EXPOSED or
                        event.window.event ==
                        sdl.SDL_WINDOWEVENT_MAXIMIZED):
                    w = get_window_by_sdl_id(event.window.windowID)
                    if w != None and w.hidden and not w.is_closed:
                        w.set_hidden(False)
            elif (event.type == sdl.SDL_APP_DIDENTERBACKGROUND):
                print("APP BACKGROUND EVENT.")
            elif (event.type == sdl.SDL_APP_WILLENTERFOREGROUND):
                print("APP RESUME EVENT")
                for w in all_windows:
                    if not w.is_closed and w.sdl_window is None:
                        w.internal_app_reopen()

