
'''
wobblui - Copyright 2018 wobblui team, see AUTHORS.md

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.
'''

import functools
import sdl2 as sdl
import weakref

from wobblui.widgetman import all_windows

registered_shortcuts = list()

def sanitize_shortcut_keys(shortcut_keys):
    new_keys = []
    for key in shortcut_keys:
        key = key.lower().strip().replace("-", "").\
            replace(" ", "")
        if key.startswith("left"):
            key = "l" + key[len("left"):]
        elif key.startswith("right"):
            key = "r" + key[len("right"):]
        if key.endswith("control"):
            key = key[:-len("control")] + "ctrl"
        if not key in new_keys:
            new_keys.append(key)
    return new_keys

def shortcut_to_text(keys):
    if type(keys) == str:
        keys = [key.strip() for key in keys.split("+")\
            if len(key.strip()) > 0]
    keys = sanitize_shortcut_keys(keys)
    common_modifiers = [
        "Ctrl", "LCtrl", "RCtrl",
        "Shift", "LShift", "RShift",
        "Alt", "LAlt", "RAlt",
        "Super"]
    final_keys = ["Return", "Enter", "Backspace"]
    lowercase_modifiers = [
        p.lower() for p in common_modifiers]
    lowercase_final = [
        p.lower() for p in final_keys]
    def sort_shortcut(a, b):
        if a.lower() in lowercase_final and \
                not b.lower() in lowercase_final:
            return 1
        elif b.lower() in lowercase_final and \
                not a.lower() in lowercase_final:
            return -1
        if a.lower() in lowercase_modifiers and \
                not b.lower() in lowercase_modifiers:
            return -1
        elif not a.lower() in lowercase_modifiers and \
                b.lower() in lowercase_modifiers:
            return 1
        if a.lower() in lowercase_modifiers and \
                b.lower() in lowercase_modifiers:
            return (lowercase_modifiers.index(a.lower()) -
                lowercase_modifiers.index(b.lower()))
        if a.lower() < b.lower():
            return -1
        else:
            return 1
    # Sort in commonly expected order:
    sorted_keys = sorted(list(keys),
        key=functools.cmp_to_key(sort_shortcut))
    # Fix spelling details:
    pretty_keys = []
    for key in sorted_keys:
        key = key.upper()
        if key.lower() in lowercase_modifiers:
            key = common_modifiers[lowercase_modifiers.\
                index(key.lower())]
            if key == "LCtrl":
                key = "Left Control"
            elif key == "RCtrl":
                key = "Right Control"
            elif key == "LAlt":
                key = "Left Alt"
            elif key == "RAlt":
                key == "Right Alt"
            elif key == "LShift":
                key = "Left Shift"
            elif key == "RShift":
                key = "Right Shift"
            elif key == "Ctrl":
                key = "Control"
        elif key.lower() in lowercase_final:
            key = final_keys[lowercase_final.index(
                key.lower())]
        pretty_keys.append(key)
    return " + ".join(pretty_keys)

def register_global_shortcut(shortcut, func, connected_widget):
    global registered_shortcuts
    if func is None:
        return

    # Prepare info for shortcut:
    connected_widget_ref = None
    if connected_widget != None:
        connected_widget_ref = weakref.ref(connected_widget)
    if type(shortcut) == str:
        shortcut = [p.lower().strip() for p in shortcut.split("+")
            if len(p.strip()) > 0]
    shortcut_parts = set(sanitize_shortcut_keys(shortcut))

    # Add new shortcut:
    registered_shortcuts.append([
        shortcut_parts, func, connected_widget_ref])

def clean_global_shortcuts():
    global registered_shortcuts

    # Clean out shortcuts that go to widgets no longer existing,
    # or no longer being added to UI:
    new_registered_shortcuts = list()
    for shortcut in registered_shortcuts:
        if shortcut[2] != None:
            w = shortcut[2]()
            if w is None:
                continue
            if hasattr(w, "parent_window") and w.type != "window" and \
                    w.parent_window is None:
                continue
        new_registered_shortcuts.append(shortcut)
    registered_shortcuts = new_registered_shortcuts

def shortcut_is_active(shortcut):
    if shortcut[2] is None:
        return True
    w = shortcut[2]()
    if w is None or w.effectively_inactive:
        return False
    if w.type != "window" and w.parent_window is None:
        # Widget not visible in any window. --> nope
        return False
    if w.type == "window" and w.is_closed:
        # Shortcut attached to closed window. --> nope
        return False
    return True

def get_matching_shortcuts(keys):
    global registered_shortcuts
    clean_global_shortcuts()
    if len(keys) == 0:
        return
    keys = set(sanitize_shortcut_keys(keys))
    matching = []
    for shortcut in registered_shortcuts:
        if not shortcut_is_active(shortcut):
            continue
        key_pressed_set = keys
        check_key_sets = [set(shortcut[0])]
        def transform_set_to_all_variants(key_set):
            if "ctrl" in key_set:
                new_set = set(key_set)
                new_set.discard("ctrl")
                new_set2 = set(new_set)
                new_set.add("lctrl")
                new_set2.add("rctrl")
                return [new_set, new_set2]
            if "shift" in key_set:
                new_set = set(key_set)
                new_set.discard("shift")
                new_set2 = set(new_set)
                new_set.add("lshift")
                new_set2.add("rshift")
                return [new_set, new_set2]
            if "alt" in key_set:
                new_set = set(key_set)
                new_set.discard("alt")
                new_set2 = set(new_set)
                new_set.add("lalt")
                new_set2.add("ralt")
                return [new_set, new_set2]
            return None
        transformed = True
        while transformed:
            transformed = False
            new_check_sets = []
            for check_set in check_key_sets:
                variants = transform_set_to_all_variants(check_set)
                if variants != None:
                    transformed = True
                    new_check_sets += list(variants)
                else:
                    new_check_sets.append(check_set)
            check_key_sets = new_check_sets
        if key_pressed_set in check_key_sets:
            matching.append(shortcut)
    return matching

virtual_keys_pressed = set()
keys_active_widget_aware = set()
physical_keys_pressed = set()

def internal_update_keystate_keydown(vkey, pkey,
        trigger_shortcuts=True,
        active_widget_aware_of_keydown=True):
    global virtual_keys_pressed, physical_keys_pressed,\
        keys_active_widget_aware
    clean_global_shortcuts()
    virtual_keys_pressed.add(vkey)
    physical_keys_pressed.add(pkey)
    if active_widget_aware_of_keydown:
        keys_active_widget_aware.add(pkey)
    if trigger_shortcuts:
        shortcuts = get_matching_shortcuts(virtual_keys_pressed)
        for shortcut in shortcuts:
            if shortcut[1] != None:
                shortcut[1]()

def internal_update_keystate_keyup(vkey, pkey):
    global virtual_keys_pressed, physical_keys_pressed,\
        virtual_keys_active_widget_aware,\
        physical_keys_active_widget_aware
    widget_key_aware = (vkey in
        keys_active_widget_aware)
    virtual_keys_pressed.discard(vkey)
    physical_keys_pressed.discard(pkey)

    # Return info on whether the active widget was aware of this
    # keypress, and should get an according key up event:
    return widget_key_aware

def get_modifiers():
    """ Get currently pressed modifier keys. """
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

