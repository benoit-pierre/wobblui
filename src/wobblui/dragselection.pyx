#cython: language_level=3

'''
wobblui - Copyright 2018-2019 wobblui team, see AUTHORS.md

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

from wobblui.keyboard import get_all_active_text_widgets
from wobblui.osinfo import is_android
from wobblui.uiconf import config


touch_handles_enabled = False


def draw_drag_selection_handles(window):
    global touch_handles_enabled
    if is_android():
        touch_handles_enabled = True
    if config.get("mouse_fakes_touch_events"):
        touch_handles_enabled = True
    if not touch_handles_enabled:
        return
    for w in get_all_active_text_widgets():
        if not hasattr(w, "parent_window"):
            continue
        if w.parent_window != window:
            continue
        w.draw_touch_selection_handles_if_any(
            w.parent_window.width, w.parent_window.height
        )


touch_handle_drag_active = False
touch_handle_drag_widget = None
touch_handle_drag_widget_left_side = True
touch_handle_last_position = None


def coordinates_to_widget_with_drag_handle(window, mx, my):
    global touch_handles_enabled
    if is_android():
        touch_handles_enabled = True
    if config.get("mouse_fakes_touch_events"):
        touch_handles_enabled = True
    if not touch_handles_enabled:
        return (None, False)
    best_widget = None
    best_widget_dist = None
    best_widget_handle_left = None
    for w in get_all_active_text_widgets():
        if not hasattr(w, "parent_window"):
            continue
        if w.parent_window != window:
            continue
        p = w.get_touch_selection_positions()
        if p is None:
            continue
        assert(len(p) >= 6 and p[0] is not None)
        wx = round(w.abs_x)
        wy = round(w.abs_y)
        dist_left_y = min(abs((p[1] + wy) - my),
            abs((p[1] + wy + p[2]) - my))
        dist_left_x = abs((p[0] + wx) - mx)
        dist_right_y = min(abs((p[4] + wy) - my),
            abs((p[4] + wy + p[5]) - my))
        dist_right_x = abs((p[3] + wx) - mx)
        widget_handle_left = True
        widget_dist = dist_left_x + dist_left_y
        if dist_right_x + dist_right_y < widget_dist:
            widget_dist = dist_right_x + dist_right_y
            widget_handle_left = False
        if widget_dist > w.dpi_scale * 10.0:
            continue
        if best_widget is None or widget_dist < best_widget_dist:
            best_widget = w
            best_widget_dist = widget_dist
            best_widget_handle_left = widget_handle_left
    return (best_widget, best_widget_handle_left)


cdef int touch_handles_take_touch_start(window, mx, my):
    global touch_handle_drag_active, touch_handle_drag_widget, \
        touch_handle_drag_widget_left_side, touch_handle_last_position
    (widget, handle_left_side) = coordinates_to_widget_with_drag_handle(
        window, mx, my
    )
    if widget is None:
        touch_handle_drag_active = False
        return False
    touch_handle_drag_active = True
    touch_handle_drag_widget = widget
    touch_handle_drag_widget_left_side = handle_left_side
    touch_handle_last_position = (round(mx), round(my))
    return True


def handle_touch_drag(window, new_x, new_y):
    global touch_handle_last_position
    new_x = round(new_x)
    new_y = round(new_y)
    if new_x == touch_handle_last_position[0] and \
            new_y == touch_handle_last_position[1]:
        return
    move_x = new_x - touch_handle_last_position[0]
    move_y = new_y - touch_handle_last_position[1]
    touch_handle_last_position = (new_x, new_y)


cdef int touch_handles_take_touch_move(window, mx, my):
    global touch_handle_drag_active, touch_handle_drag_widget
    if not touch_handle_drag_active:
        return False
    if touch_handle_drag_widget is None or \
            not hasattr(touch_handle_drag_widget, "parent_window") or \
            touch_handle_drag_widget.parent_window != window:
        touch_handle_drag_active = False
        return False
    handle_touch_drag(window, mx, my)
    return True


cdef int touch_handles_take_touch_end(window, mx, my):
    global touch_handle_drag_active, touch_handle_drag_widget
    if not touch_handle_drag_active:
        return False
    if touch_handle_drag_widget is None or \
            not hasattr(touch_handle_drag_widget, "parent_window") or \
            touch_handle_drag_widget.parent_window != window:
        touch_handle_drag_active = False
        return False
    handle_touch_drag(window, mx, my)
    touch_handle_drag_active = False
    return True
