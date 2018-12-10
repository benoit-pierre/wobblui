#cython: language_level=3

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

cdef class WidgetBase:
    # Base settings:
    cdef public str type
    cdef public int _focusable
    cdef public object focus_index  # integer or None
    cdef public int needs_redraw
    cdef public int id
    cdef public int added_order
    cdef public int no_mouse_events  # disables callbacks AND propagation
    cdef public int continue_infinite_scroll_when_unfocused
    cdef public int fake_mouse_even_with_native_touch_support
    cdef public int has_native_touch_support, takes_text_input
    cdef int _prevent_mouse_event_propagate
    cdef public int needs_relayout
    cdef public int generate_double_click_for_touches 
    cdef public int _x, _y, _width, _height, _max_width, _max_height
    cdef public int _child_mouse_event_shift_x, _child_mouse_event_shift_y
    cdef public int is_container
    cdef public object _children
    cdef object _parent
    cdef int _disabled, _is_focused, _invisible
    cdef object _cursor
    cdef public object extra_focus_check_callback

    # Event processing internal state:
    cdef public int _in_touch_fake_event_processing
    cdef public int last_mouse_move_was_inside,\
        last_mouse_move_was_fake_touch
    cdef public object last_mouse_down_presses
    cdef public object last_mouse_click_with_time
    cdef public int last_touch_was_inside
    cdef public int last_touch_was_pressed
    cdef public int _cached_previous_natural_width
    cdef public int _cached_previous_natural_height
    cdef public double last_touch_event_ts
    cdef public double touch_vel_x, touch_vel_y
    cdef public int last_seen_infinitescroll_touch_x,\
        last_seen_infinitescroll_touch_y, touch_in_progress,\
        have_scheduled_scroll_checker
    cdef public double last_infinite_ts  # for drag-fast-and-let-go scrolling
    cdef public object touch_start_x, touch_start_y  # nullable
    cdef public double touch_max_ever_distance
    cdef public double touch_start_time
    cdef public int last_touch_x, last_touch_y, touch_scrolling
    cdef public int long_click_callback_id, have_long_click_callback
    cdef public int prevent_touch_long_click_due_to_gesture
    cdef public int multitouch_gesture_reported_in_progress
    cdef public double multitouch_two_finger_distance

    # Drawing technical details:
    cdef public object internal_render_target
    cdef public int internal_render_target_width, \
                    internal_render_target_height

    # Event objects:
    cdef public object textinput, parentchanged, multitouchstart,\
        multitouchmove, multitouchend, touchstart, touchmove, touchend,\
        mousemove, mousedown, mouseup, mousewheel, stylechanged,\
        keyup, keydown, click, doubleclick, relayout, moved, resized,\
        focus, unfocus, redraw, post_redraw, multitouchzoom

    # Allow weakrefs to this type:
    cdef object __weakref__
