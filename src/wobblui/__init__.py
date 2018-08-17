
import ctypes
import sdl2 as sdl
import sys
import time
import traceback

from wobblui.keyboard import internal_update_text_events,\
    get_active_text_widget, get_modifiers
from wobblui.timer import internal_trigger_check
from wobblui.window import all_windows, get_focused_window,\
    get_window_by_sdl_id

def redraw_windows(layout_only=False):
    for w_ref in all_windows:
        w = w_ref()
        if w is None or w.hidden:
            continue
        i = 0
        while i < 10:
            if not w.relayout_if_necessary():
                break
            i += 1
        if i == 10:
            print("WARNING: a widget appears to be causing a " +
                "relayout() loop", file=sys.stderr, flush=True)
        w.redraw_if_necessary()

def sdl_vkey_map(key):
    if key >= sdl.SDLK_0 and key <= sdl.SDLK_9:
        return chr(ord("0") + (key - sdl.SDLK_0))
    if key >= sdl.SDLK_a and key <= sdl.SDLK_z:
        return chr(ord("a") + (key - sdl.SDLK_a))
    if key == sdl.SDLK_KP_TAB or key == sdl.SDLK_TAB:
        return "tab"
    if key == sdl.SDLK_LALT or key == sdl.SDLK_RALT:
        return "alt"
    if key == sdl.SDLK_LCTRL or key == sdl.SDLK_RCTRL:
        return "ctrl"
    if key == sdl.SDLK_DOWN:
        return "down"
    if key == sdl.SDLK_UP:
        return "up"
    if key == sdl.SDLK_LEFT:
        return "left"
    if key == sdl.SDLK_RIGHT:
        return "right"
    if key == sdl.SDLK_ESCAPE:
        return "escape"
    if key == sdl.SDLK_RETURN or \
            key == sdl.SDLK_RETURN2:
        return "return"
    if key == sdl.SDLK_BACKSPACE:
        return "backspace"
    if key == sdl.SDLK_SPACE:
        return "space"
    return str("scancode-" + str(key))

def sdl_key_map(key):
    if key >= sdl.SDL_SCANCODE_0 and key <= sdl.SDL_SCANCODE_9:
        return chr(ord("0") + (key - sdl.SDL_SCANCODE_0))
    if key >= sdl.SDL_SCANCODE_A and key <= sdl.SDL_SCANCODE_Z:
        return chr(ord("a") + (key - sdl.SDL_SCANCODE_A))
    if key == sdl.SDL_SCANCODE_KP_TAB or key == sdl.SDL_SCANCODE_TAB:
        return "tab"
    if key == sdl.SDL_SCANCODE_DOWN:
        return "down"
    if key == sdl.SDL_SCANCODE_UP:
        return "up"
    if key == sdl.SDL_SCANCODE_LEFT:
        return "left"
    if key == sdl.SDL_SCANCODE_RIGHT:
        return "right"
    if key == sdl.SDL_SCANCODE_ESCAPE:
        return "escape"
    if key == sdl.SDL_SCANCODE_RETURN or \
            key == sdl.SDL_SCANCODE_RETURN2:
        return "return"
    if key == sdl.SDL_SCANCODE_BACKSPACE:
        return "backspace"
    if key == sdl.SDL_SCANCODE_SPACE:
        return "space"
    return str("scancode-" + str(key))

def event_loop():
    event_loop_ms = 10
    while True:
        time.sleep(event_loop_ms * 0.001)
        events = []
        while True:
            ev = sdl.SDL_Event()
            result = sdl.SDL_PollEvent(ctypes.byref(ev))
            if result == 1:
                events.append(ev)
                continue
            break
        if len(events) == 0:
            if event_loop_ms < 300:
                event_loop_ms = min(
                    event_loop_ms + 1,
                    300)
            internal_trigger_check()
            redraw_windows()
            continue
        else:
            if event_loop_ms > 10:
                event_loop_ms = 10
        for event in events:
            try:
                if handle_event(event) is False:
                    # App termination.
                    return
            except Exception as e:
                print("*** ERROR IN EVENT HANDLER ***",
                    file=sys.stderr, flush=True)
                print(str(traceback.format_exc()))
        redraw_windows(layout_only=True)
        internal_trigger_check()
        internal_update_text_events()
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
    elif event.type == sdl.SDL_MOUSEWHEEL:
        sdl_touch_mouseid = -1
        if hasattr(sdl, "SDL_TOUCH_MOUSEID"):
            sdl_touch_mouseid = sdl.SDL_TOUCH_MOUSEID
        if event.wheel.which == sdl_touch_mouseid:
            # We handle this separately.
            return
        x = int(event.wheel.x)
        y = int(event.wheel.y)
        if event.wheel.direction == sdl.SDL_MOUSEWHEEL_FLIPPED:
            x = -x
            y = -y
        w = get_window_by_sdl_id(event.button.windowID)
        if w is None or w.is_closed:
            return
        if w.hidden:
            w.set_hidden(False)
        w.mousewheel(int(event.wheel.which),
            float(x), float(y))
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
    elif event.type == sdl.SDL_TEXTINPUT:
        text = event.text.text.decode("utf-8", "replace")
        widget = get_active_text_widget()
        if widget != None and hasattr(widget, "on_text"):
            widget.on_text(text, get_modifiers())
    elif event.type == sdl.SDL_KEYDOWN:
        virtual_key = sdl_vkey_map(event.key.keysym.sym)
        physical_key = sdl_key_map(event.key.keysym.scancode)
        shift = ((event.key.keysym.mod & sdl.KMOD_RSHIFT) != 0) or \
            ((event.key.keysym.mod & sdl.KMOD_LSHIFT) != 0)
        ctrl = ((event.key.keysym.mod & sdl.KMOD_RCTRL) != 0) or \
            ((event.key.keysym.mod & sdl.KMOD_LCTRL) != 0)
        alt = ((event.key.keysym.mod & sdl.KMOD_RALT) != 0) or \
            ((event.key.keysym.mod & sdl.KMOD_LALT) != 0)
        w = get_window_by_sdl_id(event.motion.windowID)
        if w is None or w.is_closed:
            return
        if w.hidden:
            w.set_hidden(False)
        modifiers = set()
        if shift:
            modifiers.add("shift")
        if ctrl:
            modifiers.add("ctrl")
        if alt:
            modifiers.add("alt")
        w.keydown(virtual_key, physical_key, modifiers)
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

