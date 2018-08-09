
import sdl2 as sdl
import sdl2.ext as sdl_ext
import sys
import time
import traceback

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
            try:
                if not handle_event(event):
                    # App termination.
                    return
            except Exception as e:
                print("*** ERROR IN EVENT HANDLER ***",
                    file=sys.stderr, flush=True)
                print(str(traceback.format_exc()))
        redraw_windows()

def handle_event(event):
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
    elif event.type == sdl.SDL_MOUSEBUTTONDOWN or \
            event.type == sdl.SDL_MOUSEBUTTONUP:
        sdl_touch_mouseid = -1
        if hasattr(sdl, "SDL_TOUCH_MOUSEID"):
            sdl_touch_mouseid = sdl.SDL_TOUCH_MOUSEID
        if event.button.which == sdl_touch_mouseid:
            # We handle this separately.
            return
        w = get_window_by_sdl_id(event.button.windowID)
        if w is None or w.is_closed:
            return
        if w.hidden:
            w.set_hidden(False)
        if event.type == sdl.SDL_MOUSEBUTTONDOWN:
            w.mousedown(int(event.button.which),
                int(event.button.button),
                float(event.button.x), float(event.button.y))
        else:
            w.mouseup(int(event.button.which),
                int(event.button.button),
                float(event.button.x), float(event.button.y))
    elif event.type == sdl.SDL_MOUSEMOTION:
        sdl_touch_mouseid = -1
        if hasattr(sdl, "SDL_TOUCH_MOUSEID"):
            sdl_touch_mouseid = sdl.SDL_TOUCH_MOUSEID
        if event.motion.which == sdl_touch_mouseid:
            # We handle this separately.
            return
        w = get_window_by_sdl_id(event.motion.windowID)
        if w is None or w.is_closed:
            return
        if w.hidden:
            w.set_hidden(False)
        w.mousemove(int(event.motion.which),
            float(event.motion.x), float(event.motion.y))
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
            app_is_gone = True
            for w_ref in all_windows:
                w = w_ref()
                if w != None and not w.is_closed:
                    app_is_gone = False
            if app_is_gone:
                return False
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
        if sdl.SDL_GetPlatform().decode("utf-8", "replace").\
                lower() == "android":
            print("ANDROID IN BACKGROUND. DUMP ALL WINDOW RENDERERS.")
            for w_ref in all_windows:
                w = w_ref()
                if w != None:
                    if w.focused:
                        w.unfocus()
                    w.handle_sdlw_close()
    elif (event.type == sdl.SDL_APP_WILLENTERFOREGROUND):
        print("APP RESUME EVENT")
        for w_ref in all_windows:
            w = w_ref()
            if w != None and not w.is_closed:
                w.internal_app_reopen()
    return True

