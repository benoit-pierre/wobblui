
import sdl2 as sdl

from wobblui.window import all_windows

def get_modifiers():
    result = set()
    sdl_modstate = sdl.SDL_GetModState()
    if ((sdl_modstate & sdl.KMOD_LSHIFT) != 0 or
            (sdl_modstate & sdl.KMOD_RSHIFT) != 0):
        result.add("shift")
    if ((sdl_modstate & sdl.KMOD_LCTRL) != 0 or
            (sdl_modstate & sdl.KMOD_RCTRL) != 0):
        result.add("ctrl")
    if ((sdl_modstate & sdl.KMOD_LALT) != 0 or
            (sdl_modstate & sdl.KMOD_RALT) != 0):
        result.add("alt")
    return result

current_text_events_widget = None
def internal_update_text_events():
    global current_text_events_widget, all_windows
    if current_text_events_widget is None:
        return

    # If widget taking text input has no keyboard focus, stop input:
    if not current_text_events_widget.focused:
        sdl.SDL_StopTextInput()
        current_text_events_widget = None

    seen_windows = []
    for win_ref in all_windows:
        win = win_ref()
        if win == None:
            continue
        seen_windows.append(win)
        if not win.focused or win.hidden:
            # If parent of widget taking input is hidden, stop input:
            if current_text_events_widget != None and \
                    current_text_events_widget.parent_window == win:
                sdl.SDL_StopTextInput()
                current_text_events_widget = None
            continue

    # If parent window of widget taking text input is gone, stop input:
    if current_text_events_widget != None and \
            not current_text_events_widget.parent_window in seen_windows:
        sdl.SDL_StopTextInput()
        current_text_events_widget = None

def enable_text_events(widget):
    global current_text_events_widget
    if current_text_events_widget == widget:
        return
    if widget != None and not widget.focused:
        raise ValueError("cannot enable text events " +
            "for a widget without keyboard focus")
    if current_text_events_widget != None:
        if widget != None:
            sdl.SDL_StopTextInput()
        current_text_events_widget = widget
        return
    current_text_events_widget = widget
    if widget != None:
        sdl.SDL_StartTextInput()

def get_active_text_widget():
    global current_text_events_widget
    internal_update_text_events()
    return current_text_events_widget

