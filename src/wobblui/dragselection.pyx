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

from wobblui.box import HBox
from wobblui.button import Button
from wobblui.keyboard import get_all_active_text_widgets
from wobblui.osinfo import is_android
from wobblui.uiconf import config
from wobblui.widgetman import all_windows


touch_handles_enabled = False


def draw_drag_selection_handles(window):
    global touch_handles_enabled, all_windows
    if is_android():
        touch_handles_enabled = True
    if config.get("mouse_fakes_touch_events"):
        touch_handles_enabled = True
    if not touch_handles_enabled:
        return

    for win_ref in all_windows:
        win = win_ref()
        if win is None:
            continue
        reposition_hover_menu(win)
    for tw in get_all_active_text_widgets():
        if not hasattr(tw, "parent_window"):
            continue
        if tw.parent_window != window:
            continue
        tw.draw_touch_selection_handles_if_any(
            tw.parent_window.width, tw.parent_window.height
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
        if widget_dist > w.dpi_scale * 30.0:
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


cdef void reposition_hover_menu(window):
    next_to_widget = None
    drag_handle_positions = None
    for tw in get_all_active_text_widgets():
        if not hasattr(tw, "parent_window"):
            continue
        if tw.parent_window != window:
            continue
        p = tw.get_touch_selection_positions()
        if p is None:
            continue
        drag_handle_positions = p
        next_to_widget = tw
        break
    # If we don't have a widget with touch handles, remove menu:
    if next_to_widget is None:
        if window.context_menu is not None:
            window.close_context_menu()
        return
    # Add a menu if we don't have one yet:
    if window.context_menu is None:
        menu = HBox()
        menu.add(Button("Cut"))
        menu.add(Button("Copy"))
        menu.add(Button("Paste"))
        window.open_context_menu(menu, 0, 0, autofocus=False)
    # Re-position menu:
    menu = window.context_menu
    old_x = menu.x
    old_y = menu.y
    selected_rect = (
        round(min(p[0], p[3])),
        round(min(p[1], p[4])),
        max(1, round(max(p[0], p[3])) - round(min(p[0], p[3]))),
        max(1, round(max(p[1] + p[2], p[4] + p[5])) -
            round(min(p[1], p[4]))),
    )
    distance = round(30 * window.dpi_scale)
    new_x = None
    new_y = None
    if selected_rect[0] + selected_rect[2] < window.width / 2 and (
            selected_rect[0] + selected_rect[2] + distance + menu.width <
            window.width):
        # Place to the right of selection rectangle.
        new_x = selected_rect[0] + selected_rect[2] + distance
        if selected_rect[1] > distance * 2 + menu.height:
            # Place above (top-right)
            new_y = selected_rect[1] - distance - menu.height
        else:
            # Place right next to it (horizontal right)
            new_y = selected_rect[1]
    elif menu.width + distance < selected_rect[0]:
        # Place to the left.
        new_x = selected_rect[0] - distance - menu.width
        if selected_rect[1] > distance * 2 + menu.height:
            # Place above (top-left)
            new_y = selected_rect[1] - distance - menu.height
        else:
            # Place left next to it (horizontal left)
            new_y = selected_rect[1]
    else:
        if selected_rect[1] > distance * 2 + menu.height:
            # Place above, as much top-right as is possible:
            new_x = min(window.width - menu.width,
                selected_rect[0] + selected_rect[2] + distance)
            new_y = selected_rect[1] - distance - menu.height
        elif (selected_rect[1] + selected_rect[3] + distance +
              menu.height < window.height):
            # Place below, as much bottom-right as possible:
            new_x = min(window.width - menu.width,
                selected_rect[0] + selected_rect[2] + distance)
            new_y = selected_rect[1] + selected_rect[3] + distance
        else:
            # Place in the center:
            new_x = (selected_rect[0] + selected_rect[2] * 0.5
                - menu.width * 0.5)
            new_y = (selected_rect[1] + selected_rect[3] * 0.5
                - menu.height * 0.5)
    new_x = round(new_x)
    new_y = round(new_y)
    if new_x != menu.x or new_y != menu.y:
        menu.x = new_x
        menu.y = new_y
        window.needs_redraw = True


cdef handle_touch_drag(window, new_x, new_y):
    global touch_handle_last_position, touch_handle_drag_widget, \
        touch_handle_drag_widget_left_side
    if touch_handle_drag_widget is None:
        return
    new_x = round(new_x)
    new_y = round(new_y)
    if new_x == touch_handle_last_position[0] and \
            new_y == touch_handle_last_position[1]:
        return
    new_rel_x = (new_x - touch_handle_drag_widget.abs_x)
    new_rel_y = (new_y - touch_handle_drag_widget.abs_y)
    touch_handle_last_position = (new_x, new_y)
    touch_handle_drag_widget.move_touch_selection_handle(
        touch_handle_drag_widget_left_side,
        new_rel_x, new_rel_y
    )
    touch_handle_drag_widget.update()
    reposition_hover_menu(touch_handle_drag_widget.parent_window)


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
        return True  # still eat up touch end to avoid confusing other code
    handle_touch_drag(window, mx, my)
    touch_handle_drag_active = False
    return True
