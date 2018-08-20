
import sdl2 as sdl

from wobblui.widgetman import all_windows

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

# All widgets that have focus in their respective window and take text input:
current_text_events_widgets = []

# Current state of text input:
text_input_suspended = True

def internal_update_text_events():
    global current_text_events_widgets, \
        all_windows,\
        text_input_suspended

    # Throw out all widgets that have lost keyboard focus or lost
    # their parent window:
    seen_windows = []
    for w_ref in all_windows:
        w = w_ref()
        if w != None:
            seen_windows.append(w)
    new_list = []
    for widget in current_text_events_widgets:
        if not widget.focused or \
                not widget.parent_window in seen_windows:
            continue
        new_list.append(widget)
    current_text_events_widgets = new_list

    # See which widgets which want text input are in active windows:
    current_text_events_active_widgets = []
    for widget in current_text_events_widgets:
        if widget.parent_window.focused and \
                not widget.parent_window.hidden:
            current_text_events_active_widgets.append(widget)

    # Udpate SDL text input state accordingly to available active widgets:
    if len(current_text_events_active_widgets) > 0 and \
            text_input_suspended:
        sdl.SDL_StartTextInput()
        text_input_suspended = False
    elif len(current_text_events_active_widgets) == 0 and \
            not text_input_suspended:
        sdl.SDL_StopTextInput()
        text_input_suspended = True

    return current_text_events_active_widgets

def enable_text_events(widget):
    global current_text_events_widgets
    if widget in current_text_events_widgets:
        return
    if widget != None and not widget.focused:
        raise ValueError("cannot enable text events " +
            "for a widget without keyboard focus")
    assert(hasattr(widget, "parent_window"))
    current_text_events_widgets.append(widget)
    internal_update_text_events()

def get_active_text_widget():
    global current_text_events_widget
    widgets = internal_update_text_events()
    if len(widgets) == 0:
        return None
    return widgets[0]

