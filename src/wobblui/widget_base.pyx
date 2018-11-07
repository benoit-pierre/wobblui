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

import copy
import ctypes
import functools
import math
import random
import sdl2 as sdl
import sys
import time
import traceback
import weakref

from wobblui.color import Color
from wobblui.event import Event, ForceDisabledDummyEvent,\
    InternalOnlyDummyEvent
from wobblui.gfx import draw_dashed_line, draw_rectangle
from wobblui.mouse import cursor_seen_during_mousemove
from wobblui.keyboard import enable_text_events
from wobblui.perf cimport CPerf as Perf
from wobblui.texture import RenderTarget
from wobblui.timer import schedule
from wobblui.uiconf import config
from wobblui.widgetman import add_widget, all_widgets, \
    get_widget_id, get_add_id, tab_sort
from wobblui.woblog import logdebug, logerror, loginfo, logwarning

cdef class WidgetBase:
    # MEMBERS SEE WidgetBase.pxd FILE !!!

    def __init__(self, int is_container=False,
            int can_get_focus=False,
            int takes_text_input=False,
            int has_native_touch_support=False,
            int fake_mouse_even_with_native_touch_support=False,
            int generate_double_click_for_touches=False):
        self.type = "unknown"
        self._focusable = can_get_focus
        self.needs_redraw = True
        self._invisible = False

        self.id = get_widget_id()
        self.added_order = get_add_id()

        self.continue_infinite_scroll_when_unfocused = False
        self.fake_mouse_even_with_native_touch_support =\
            fake_mouse_even_with_native_touch_support
        self._in_touch_fake_event_processing = False
        self.needs_relayout = True
        self.last_mouse_move_was_inside = False
        self.last_mouse_down_presses = set()
        self.last_mouse_click_with_time = dict()  # for double clicks
        self.last_touch_was_inside = False
        self.last_touch_was_pressed = False
        self.generate_double_click_for_touches =\
            generate_double_click_for_touches
        self._x = 0
        self._y = 0
        self._width = 64
        self._height = 64
        self._max_width = -1
        self._max_height = -1
        self.is_container = is_container
        self._children = []
        self._parent = None
        self._disabled = False
        self.internal_render_target = None
        self.internal_render_target_width = -1
        self.internal_render_target_height = -1

        def start_redraw(internal_data=None):
            if self.renderer is None:
                return
            assert(self.renderer != None)
            if self.needs_relayout:
                self.relayout()
            renderer = self.renderer
            assert(renderer != None)
            dpi_scale = self.style.dpi_scale
            tex_x = max(1, math.ceil(self.width + 1.0))
            tex_y = max(1, math.ceil(self.height + 1.0))
            if self.internal_render_target is None or \
                    self.internal_render_target_width != tex_x or \
                    self.internal_render_target_height != tex_y:
                if renderer is None or \
                        tex_x <= 0 or tex_y <= 0:
                    if renderer is None:
                        self.needs_redraw = True
                    return
                if self.internal_render_target != None:
                    if config.get("debug_texture_references"):
                        logdebug("WidgetBase.<closure>.start_redraw: " +
                            "DUMPED self.internal_render_target")
                    self.internal_render_target = None 
                self.internal_render_target = RenderTarget(
                    renderer, tex_x, tex_y)
                if config.get("debug_texture_references"):
                        logdebug("WidgetBase.<closure>.start_redraw: " +
                            "NEW self.internal_render_target")
                self.internal_render_target_width = tex_x
                self.internal_render_target_height = tex_y
            self.internal_render_target.set_as_rendertarget()
        def end_redraw(internal_data=None):
            if self.renderer is None or \
                    self.internal_render_target is None:
                return
            if hasattr(self, "do_redraw"):
                self.do_redraw()
            self.internal_render_target.unset_as_rendertarget()
            self.needs_redraw = False
            self.post_redraw()
        self.redraw = Event("redraw", owner=self,
            special_post_event_func=end_redraw,
            special_pre_event_func=start_redraw)
        self.post_redraw = Event("post_redraw", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False)
        self.focus_index = None
        self._is_focused = False

        # Note: textinput event can't be a dummy event even if
        # widget doesn't take text input, because Window instnaces
        # need this event to be working even not marked as widgets
        # taking text input (which would cause them to prompt the
        # virtual keyboard on Android/iOS merely by existing).
        # Therefore, the event must always work, but the window
        # won't actually dispatch it to any widget if it's not
        # marked with .takes_text_input = True
        self.textinput = Event("textinput", owner=self)
        if not can_get_focus or not takes_text_input:
            self.takes_text_input = False
        else:
            self.takes_text_input = True

        self.parentchanged = Event("parentchanged", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False)
        def touchstart_pre(int x, int y, internal_data=None):
            self._pre_mouse_event_handling("touchstart",
                [x, y], internal_data=internal_data)
        def touchmove_pre(int x, int y, internal_data=None):
            self._pre_mouse_event_handling("touchmove",
                [x, y], internal_data=internal_data)
        def touchend_pre(int x, int y, internal_data=None):
            self._pre_mouse_event_handling("touchend",
                [x, y], internal_data=internal_data)
        if has_native_touch_support:
            self.has_native_touch_support = True
            self.multitouchstart = Event("multitouchstart", owner=self,
                parameter_transform_func=\
                    self.mouse_event_param_adjustment)
            self.multitouchmove = Event("multitouchmove", owner=self,
                parameter_transform_func=\
                    self.mouse_event_param_adjustment)
            self.multitouchend = Event("multitouchend", owner=self,
                parameter_transform_func=\
                    self.mouse_event_param_adjustment)
            self.touchstart = Event("touchstart", owner=self,
                special_pre_event_func=touchstart_pre,
                parameter_transform_func=\
                    self.mouse_event_param_adjustment)
            self.touchmove = Event("touchmove", owner=self,
                special_pre_event_func=touchmove_pre,
                parameter_transform_func=\
                    self.mouse_event_param_adjustment)
            self.touchend = Event("touchend", owner=self,
                special_pre_event_func=touchend_pre,
                parameter_transform_func=\
                    self.mouse_event_param_adjustment)
        else:
            self.multitouchstart = InternalOnlyDummyEvent(
                "multitouchstart", owner=self,
                parameter_transform_func=\
                    self.mouse_event_param_adjustment
                )
            self.multitouchmove = InternalOnlyDummyEvent(
                "multitouchmove", owner=self,
                parameter_transform_func=\
                    self.mouse_event_param_adjustment)
            self.multitouchend = InternalOnlyDummyEvent(
                "multitouchend", owner=self,
                parameter_transform_func=\
                    self.mouse_event_param_adjustment)
            self.touchstart = InternalOnlyDummyEvent(
                "touchstart", owner=self,
                special_pre_event_func=touchstart_pre,
                parameter_transform_func=\
                    self.mouse_event_param_adjustment)
            self.touchmove = InternalOnlyDummyEvent(
                "touchmove", owner=self,
                special_pre_event_func=touchmove_pre,
                parameter_transform_func=\
                    self.mouse_event_param_adjustment)
            self.touchend = InternalOnlyDummyEvent(
                "touchend", owner=self,
                special_pre_event_func=touchend_pre,
                parameter_transform_func=\
                    self.mouse_event_param_adjustment)
            self.has_native_touch_support = False
        def mousemove_pre(int mouse_id, int x, int y, internal_data=None):
            self._pre_mouse_event_handling("mousemove",
                [mouse_id, x, y], internal_data=internal_data)
        self.mousemove = Event("mousemove", owner=self,
            special_pre_event_func=mousemove_pre,
            parameter_transform_func=\
                    self.mouse_event_param_adjustment)
        def mousedown_pre(int mouse_id, int button_id, int x, int y,
                internal_data=None):
            self._pre_mouse_event_handling("mousedown",
                [mouse_id, button_id, x, y], internal_data=internal_data)
        self.mousedown = Event("mousedown", owner=self,
            special_pre_event_func=mousedown_pre,
            parameter_transform_func=\
                self.mouse_event_param_adjustment)
        def mousewheel_pre(int mouse_id, int x, int y, internal_data=None):
            self._pre_mouse_event_handling("mousewheel",
                [mouse_id, x, y], internal_data=internal_data)
        self.mousewheel = Event("mousewheel", owner=self,
            special_pre_event_func=mousewheel_pre,
            parameter_transform_func=\
                self.mouse_event_param_adjustment)
        self.stylechanged = Event("stylechanged", owner=self)
        self.keyup = Event("keyup", owner=self)
        self.keydown = Event("keydown", owner=self)
        self.click = Event("click", owner=self)
        self.multitouchzoom = Event("multitouchzoom", owner=self)
        self.doubleclick = Event("doubleclick", owner=self)
        def mouseup_pre(mouse_id, button_id, x, y, internal_data=None):
            self._pre_mouse_event_handling("mouseup",
                [mouse_id, button_id, x, y], internal_data=internal_data)
        self.mouseup = Event("mouseup", owner=self,
            special_pre_event_func=mouseup_pre)
        def layouting_done(internal_data=None):
            self.needs_relayout = False
            self._internal_post_relayout(internal_data=internal_data)
        self.relayout = Event("relayout", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False,
            special_post_event_func=layouting_done)
        self.moved = Event("moved", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False)
        self.resized = Event("resized", owner=self,
            allow_preventing_widget_callback_by_user_callbacks=False)
        self.focus = Event("focus", owner=self,
                allow_preventing_widget_callback_by_user_callbacks=False)
        if can_get_focus:
            self.unfocus = Event("unfocus", owner=self,
                allow_preventing_widget_callback_by_user_callbacks=False)
        else:
            self.unfocus = ForceDisabledDummyEvent("unfocus", owner=self)
        add_widget(self)

    @property
    def cursor(self):
        if not hasattr(self, "_cursor") or \
                self._cursor is None:
            self._cursor = self.get_default_cursor() or "normal"
        return self._cursor

    def mouse_event_param_adjustment(self, event_name, owner,
            *args, internal_data=None):
        args = list(args)
        if self._in_touch_fake_event_processing:
            # The touch event itself already translated coordinates.
            # --> Nothing to do
            return args + [internal_data]
        if self.mouse_event_shift_x == 0 and self.mouse_event_shift_y == 0:
            # Nothing to shift.
            return args + [internal_data]

        # Do actual shift:

        # If internal data has absolute mouse pos, shift it as well:
        if internal_data != None and len(internal_data) == 2:
            internal_data = (
                internal_data[0] + self.mouse_event_shift_x,
                internal_data[1] + self.mouse_event_shift_y)

        # Shift regular event parameters:
        if event_name == "mousedown" or event_name == "mouseup" or \
                event_name == "click" or event_name == "doubleclick":
            # args: (mouse_id, button, x, y),
            # internal data: (abs_x, abs_y)
            return [args[0], args[1],
                args[1] + self.mouse_event_shift_x,
                args[2] + self.mouse_event_shift_y] + [internal_data]
        if event_name == "mousemove":
            # args: (mouse_id, x, y)
            return [args[0],
                args[1] + self.mouse_event_shift_x,
                args[2] + self.mouse_event_shift_y] + [internal_data]
        if event_name == "mousewheel":
            # args: (mouse_id, wx, wy)
            return args + [internal_data]
        if event_name == "touchstart" or event_name == "touchmove" or \
                event_name == "touchend":
            # args: (x, y)
            return [args[0] + self.mouse_event_shift_x,
                args[1] + self.mouse_event_shift_y] + [internal_data]
        if event_name == "multitouchstart" or \
                event_name == "multitouchmove":
            # args: (finger coordinates list)
            new_coordinates = []
            for (x, y) in args[0]:
                new_coordinates.append((
                    x + self.mouse_event_shift_x,
                    y + self.mouse_event_shift_y))
            return (new_coordinates, internal_data)
        if event_name == "multitouchend":
            # no args, nothing to translate.
            return [internal_data]
        raise RuntimeError("unknown parameter translation event")

    @cursor.setter
    def cursor(self, v):
        self._cursor = str(v)

    def get_default_cursor(self):
        return "normal"

    def set_invisible(self, int v):
        self.invisible = v

    @property
    def invisible(self):
        return self._invisible

    def is_mouse_event_actually_touch(self):
        return self._in_touch_fake_event_processing

    @invisible.setter
    def invisible(self, int v):
        v = (v is True)
        if self._invisible != v:
            self._invisible = v
            if self.focused:
                if hasattr(self, "focus_next"):
                    self.focus_next()
                if self.focused:
                    self.unfocus()
            self.needs_relayout = True
            if self.parent != None:
                self.parent.needs_relayout = True
            self.update()
            def update_children(obj):
                for child in obj.children:
                    if child.focused:
                        update_children(child)
                        if self._invisible:
                            child.unfocus()
                        else:
                            child.update()
            update_children(self)

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, int v):
        v = (v is True)
        if self._disabled != v:
            self._disabled = v
            if self.focused:
                if hasattr(self, "focus_next"):
                    self.focus_next()
                if self.focused:
                    self.unfocus()
            self.update()

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, int v):
        if self._x != v:
            self._x = v
            self.moved()

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, int v):
        if self._y != v:
            self._y = v
            self.moved()

    def _internal_post_relayout(self, internal_data=None):
        # Our own relayouting is done. See if our size changed:
        cdef int current_natural_width = self.get_natural_width()
        cdef int current_natural_height = self.get_natural_height(
            given_width=current_natural_width)
        if self._cached_previous_natural_width != \
                current_natural_width and \
                self._cached_previous_natural_height !=\
                current_natural_height:
            # Parent needs relayout.
            if self.parent != None:
                self.parent.needs_relayout = True
        self._cached_previous_natural_width = current_natural_width
        self._cached_previous_natural_height = current_natural_height
        self.needs_relayout = False  # just to enforce this in any case.

    def _internal_on_relayout(self, internal_data=None):
        # Prepare relayouting. If it's obvious that the parent
        # needs a change, already schedule this:
        self.needs_relayout = False
        need_parent_relayout = True
        cdef int current_natural_width = self.get_natural_width()
        cdef int current_natural_height = self.get_natural_height(
            given_width=current_natural_width)
        if self._cached_previous_natural_width == \
                current_natural_width and \
                self._cached_previous_natural_height ==\
                current_natural_height:
            need_parent_relayout = False
        self._cached_previous_natural_width = current_natural_width
        self._cached_previous_natural_height = current_natural_height
        if self.parent != None and need_parent_relayout:
            self.parent.needs_relayout = True
            self.parent.needs_redraw = True

    def _internal_on_multitouchstart(self, object finger_coordinates,
            internal_data=None):
        self.prevent_touch_long_click_due_to_gesture = True
        self.multitouch_two_finger_distance = 0.0
        if len(finger_coordinates) == 2:
            dist = math.sqrt(math.pow(
                finger_coordinates[0][0] - finger_coordinates[1][0], 2) +
                math.pow(
                finger_coordinates[0][1] - finger_coordinates[1][1], 2))
            self.multitouch_two_finger_distance = max(0.05,
                dist)
        self.have_long_click_callback = False
        self.long_click_callback_id += 1

    def _internal_on_multitouchmove(self, object finger_coordinates,
            internal_data=None):
        if len(finger_coordinates) == 2:
            dist = max(0.05, math.sqrt(math.pow(
                finger_coordinates[0][0] - finger_coordinates[1][0], 2) +
                math.pow(
                finger_coordinates[0][1] - finger_coordinates[1][1], 2)))
            if self.multitouch_two_finger_distance == 0.0:
                # Start zoom handling:
                self.multitouch_two_finger_distance = max(0.05, dist)
            else:
                dist_change = (dist - self.multitouch_two_finger_distance)
                self.multitouch_two_finger_distance = dist
                self.multitouchzoom(dist_change)

    def _internal_on_multitouchend(self, internal_data=None):
        self.prevent_touch_long_click_due_to_gesture = False
        self.multitouch_two_finger_distance = 0.0

    def _internal_on_touchstart(self, int x, int y, internal_data=None):
        self._post_mouse_event_handling("touchstart",
            [x, y],
            internal_data=internal_data)

    def _internal_on_touchmove(self, int x, int y, internal_data=None):
        self._post_mouse_event_handling("touchmove",
            [x, y],
            internal_data=internal_data)

    def _internal_on_touchend(self, int x, int y, internal_data=None):
        self._post_mouse_event_handling("touchend",
            [x, y],
            internal_data=internal_data)

    def _internal_on_mousedown(self, int mouse_id, int button, int x, int y,
            internal_data=None):
        self._post_mouse_event_handling("mousedown",
            [mouse_id, button, x, y],
            internal_data=internal_data)

    def _internal_on_mouseup(self, int mouse_id, int button, int x, int y,
            internal_data=None):
        self._post_mouse_event_handling("mouseup",
            [mouse_id, button, x, y],
            internal_data=internal_data)

    def _internal_on_mousemove(self, int mouse_id, int x, int y,
            internal_data=None):
        self._post_mouse_event_handling("mousemove", [mouse_id, x, y],
            internal_data=internal_data)

    def _internal_on_mousewheel(self, int mouse_id, double x, double y,
            internal_data=None):
        self._post_mouse_event_handling("mousewheel",
            [mouse_id, float(x), float(y)],
            internal_data=internal_data)

    @property
    def abs_x(self):
        x = self.x
        p = self.parent
        while p != None:
            x += p.x
            p = p.parent
        return x

    @property
    def abs_y(self):
        y = self.y
        p = self.parent
        while p != None:
            y += p.y
            p = p.parent
        return y

    def stop_infinite_scroll(self):
        self.touch_vel_x = 0
        self.touch_vel_y = 0

    def schedule_infinite_scroll_check(self, int x, int y, stop_event=False):
        # If this widget wants to handle its own touch without faked
        # mouse events, abort (since this is for faking a mouse wheel):
        if self.has_native_touch_support and \
                not self.fake_mouse_even_with_native_touch_support:
            return
        now = time.monotonic()

        # Track how this touch drag is going:
        if self.last_touch_event_ts != 0:
            old_ts = self.last_touch_event_ts
        else:
            old_ts = now
            self.last_seen_infinitescroll_touch_x = x
            self.last_seen_infinitescroll_touch_y = y
        self.last_touch_event_ts = max(1, now)
        self.touch_in_progress = (not stop_event)
        if not stop_event:
            duration = max(0.001, now - old_ts)
            self.touch_vel_x = \
                max(-90 * self.dpi_scale,
                min(90 * self.dpi_scale,
                (x - float(self.last_seen_infinitescroll_touch_x))
                    * 0.02 / duration))
            self.touch_vel_y = \
                max(-90 * self.dpi_scale,
                min(90 * self.dpi_scale,
                (y - float(self.last_seen_infinitescroll_touch_y))
                    * 0.02 / duration))
        if stop_event and abs(self.touch_vel_x) < 5.0 * self.dpi_scale \
                and abs(self.touch_vel_y) < 5.0 * self.dpi_scale:
            self.touch_vel_x = 0
            self.touch_vel_y = 0
        self.last_seen_infinitescroll_touch_x = x
        self.last_seen_infinitescroll_touch_y = y

        # Schedule checker to see if user keeps finger still:
        if self.have_scheduled_scroll_checker:
            return
        self.have_scheduled_scroll_checker = True
        self_ref = weakref.ref(self)
        def do_it():
            self_value = self_ref()
            if self_value is None:
                return
            t = self_value.scheduled_infinite_scroll_checker()
            if t != None:
                schedule(do_it, t)
            else:
                self_value.have_scheduled_scroll_checker = False
        schedule(do_it, 0.1)

    def scheduled_infinite_scroll_checker(self):
        now = time.monotonic()

        # Stop if finger rests or we're no longer focused:
        if (self.touch_in_progress and (self.last_touch_event_ts
                + 0.2 < now)) or (not self.focused
                and not self.continue_infinite_scroll_when_unfocused):
            self.touch_vel_x = 0
            self.touch_vel_y = 0
            self.last_infinite_ts = 0

        # See if we should continue moving infinitely:
        continue_moving = abs(self.touch_vel_x) > 2.0 * self.dpi_scale or \
            abs(self.touch_vel_y) > 2.0 * self.dpi_scale
        faked_event = False
        if not self.touch_in_progress and continue_moving:
            faked_event = True
            if self.last_infinite_ts == 0:
                self.last_infinite_ts = max(0.1, now)
            duration = min(1.0, now - self.last_infinite_ts)
            i = 0
            while i < 5:
                self.touch_vel_x *= min(0.999, 1.0 - duration * 0.1)
                self.touch_vel_y *= min(0.999, 1.0 - duration * 0.1)
                i += 1
            self.last_infinite_ts = now
            effective_vel_x = self.touch_vel_x * duration
            effective_vel_y = self.touch_vel_y * duration
            self.last_seen_infinitescroll_touch_x += effective_vel_x
            self.last_seen_infinitescroll_touch_y += effective_vel_y
            scalar = 0.3
            self._prevent_mouse_event_propagate = True
            try:
                self.mousewheel(0,
                    effective_vel_x * scalar,
                    effective_vel_y * scalar,
                    internal_data=[
                    self.last_seen_infinitescroll_touch_x + self.abs_x,
                    self.last_seen_infinitescroll_touch_y + self.abs_y])
            finally:
                self._prevent_mouse_event_propagate = False
        else:
            self.last_infinite_ts = 0
        if self.touch_in_progress or continue_moving:
            if faked_event:
                return 0.01  # keep high rate to scroll smoothly
            else:
                return 0.1
        return None

    def _post_mouse_event_handling(self, str event_name,
            event_args, internal_data=None):
        return self._pre_or_post_mouse_event_handling(event_name,
            event_args, internal_data=None, is_post=True)

    def _pre_mouse_event_handling(self, str event_name,
            event_args, internal_data=None):
        return self._pre_or_post_mouse_event_handling(event_name,
            event_args, internal_data=None, is_post=False)

    def draw_selection_drag_handle(self, double _x, double _y, line_height):
        cdef int x = round(_x)
        cdef int y = round(_y)
        c = Color.black
        if self.style != None and self.style.has(
                "touch_selection_drag_handles"):
            c = Color(self.style.get("touch_selection_drag_handles"))
        elif self.style != None and self.style.has("scrollbar_knob_fg"):
            c = Color(self.style.get("scrollbar_knob_fg"))
        line_thickness = max(1, round(1.0 * self.dpi_scale))
        line_offset_x = math.floor(line_thickness / 0.5)
        draw_rectangle(self.renderer, x + line_offset_x, y,
            line_thickness, line_height, color=c)
        square_size = max(3, round(5.0 * self.dpi_scale))
        square_offset_x = x - -max(1, round(square_size / 2.0))
        square_offset_y = y - square_size
        draw_rectangle(self.renderer, square_offset_x,
            square_offset_y, square_size, square_size, color=c)

    def return_long_click_test_closure(self, callback_id):
        self_ref = weakref.ref(self)
        def test_long_click():
            self_value = self_ref()
            if self_value is None:
                return
            if self_value.long_click_callback_id != callback_id:
                # A newer callback was already started.
                return
            self_value.have_long_click_callback = False
            fake_clicks_for_event = \
                ((not self_value.has_native_touch_support or
                self_value.fake_mouse_even_with_native_touch_support) and \
                self_value.last_touch_x != None and
                self_value.last_touch_y != None)
            # Emulate a right-click if necessary:
            if fake_clicks_for_event and \
                    not self_value.touch_scrolling:
                self_value.stop_infinite_scroll()
                self_value.consider_mouse_click_focus(
                    self_value.last_touch_x, self_value.last_touch_y)
                self_value._prevent_mouse_event_propagate = True
                old_value = self_value._in_touch_fake_event_processing
                try:
                    self_value._in_touch_fake_event_processing = True
                    self_value.mousedown(0, 2,
                        self_value.last_touch_x - self_value.abs_x,
                        self_value.last_touch_y - self_value.abs_y,
                        internal_data=[
                            self_value.last_touch_x,
                            self_value.last_touch_y])
                    self_value.click(0, 2,
                        self_value.last_touch_x - self_value.abs_x,
                        self_value.last_touch_y - self_value.abs_y,
                        internal_data=[
                            self_value.last_touch_x,
                            self_value.last_touch_y])
                    self_value.mouseup(0, 2,
                        self_value.last_touch_x - self_value.abs_x,
                        self_value.last_touch_y - self_value.abs_y,
                        internal_data=[
                            self_value.last_touch_x,
                            self_value.last_touch_y])
                finally:
                    self_value._in_touch_fake_event_processing = old_value
                    self_value._prevent_mouse_event_propagate = False
        return test_long_click 

    def consider_mouse_click_focus(self, int hit_check_x, int hit_check_y):
        event_descends_into_child = False
        for child in self.children:
            rel_x = hit_check_x - self.abs_x
            rel_y = hit_check_y - self.abs_y
            if rel_x >= child.x and rel_y >= child.y and \
                    rel_x <= child.x + child.width and \
                    rel_y <= child.y + child.height and \
                    child.focusable and \
                    not child.effectively_inactive:
                event_descends_into_child = True
                break
        if not event_descends_into_child:
            if self.focusable and not self.focused:
                self.focus()
            else:
                p = self.parent
                while p != None and not p.focusable:
                    p = p.parent
                if p != None and not p.focused:
                    p.focus()

    def _pre_or_post_mouse_event_handling(self, str event_name,
            event_args, internal_data=None, int is_post=False):
        # If we arrived here, the internal event wasn't prevented from
        # firing / propagate. Inform all children that are inside the
        # mouse bounds and propagate the event:

        cdef str r = str(random.random()).replace(".", "")
        cdef str chain_id = "_pre_or_post_mouse_event_handling" + r +\
            str(self)
        Perf.chain(chain_id)

        now = time.monotonic()
        if self.no_mouse_events == True:
            Perf.stop(chain_id)
            return

        # First, extract relevant event parameters:
        cdef int wx = 0
        cdef int wy = 0
        cdef int x = 0
        cdef int y = 0
        cdef int mouse_id = -1
        try:
            mouse_id = event_args[0]
        except OverflowError as e:
            logerror("got invalid mouse id which overflows: " +
                str(mouse_id) + " - is this a touch handling issue??")
            raise e
        if event_name == "mousedown" or event_name == "mouseup":
            x = event_args[2]
            y = event_args[3]
        elif event_name == "mousemove":
            x = event_args[1]
            y = event_args[2]
        elif event_name == "mousewheel":
            wx = event_args[1]
            wy = event_args[2]
            if (not hasattr(self, "parent_window") or
                    self.parent_window == None) and \
                    not hasattr(self, "get_mouse_pos"):
                # Wheel with no parent window. bail out, that's useless
                return
            if internal_data != None:
                # Mouse pos is provided in internal data:
                x = internal_data[0]
                y = internal_data[1]
            else:
                if hasattr(self, "get_mouse_pos"):
                    (x, y) = self.get_mouse_pos(event_args[0])
                else:
                    (x, y) = self.parent_window.get_mouse_pos(event_args[0])
        elif event_name.startswith("touch"):
            mouse_id = -1
            x = event_args[0]
            y = event_args[1]
        elif event_name.startswith("multitouch"):
            x = event_args[1]
            y = event_args[2]
        if internal_data != None:
            # Get absolute event coordinates if possible,
            # to be independent of shifting around parents:
            x = internal_data[0]
            y = internal_data[1]
        else:
            x += self.abs_x
            y += self.abs_y

        # Process starting point, hit point and overall
        # movement for touch gestures:
        cdef object touch_hitpoint_check_x = x  # type: can be None!
        cdef object touch_hitpoint_check_y = y
        cdef int treat_as_touch_start = False

        # Update cursor:
        if not is_post and event_name == "mousemove" and \
                x >= self.abs_x and y >= self.abs_y and \
                x < self.abs_x + self.width and \
                y < self.abs_y + self.height:
            cursor_seen_during_mousemove(self.cursor)

        # Obtain touch start and diff info:
        orig_touch_start_x = self.touch_start_x
        orig_touch_start_y = self.touch_start_y
        cdef int diff_x = 0
        cdef int diff_y = 0
        if event_name == "touchstart" or \
                (event_name.startswith("touch") and \
                self.touch_start_x is None):
            orig_touch_start_x = x
            orig_touch_start_y = y
            treat_as_touch_start = True
        elif event_name.startswith("touch"):
            diff_x = (x - self.last_touch_x)
            diff_y = (y - self.last_touch_y)
        if event_name == "touchstart" or event_name == "touchmove":
            if self.touch_start_x != None:
                touch_hitpoint_check_x = self.touch_start_x
                touch_hitpoint_check_y = self.touch_start_y

        Perf.chain(chain_id, "preparations_done")

        # *** BASIC TOUCH STATE UPDATE, ONLY ON PRE-CALLBACK ***
        if not is_post:
            # Update touch start and last touch point:
            if event_name == "touchstart" or \
                    (event_name.startswith("touch") and \
                    self.touch_start_x is None):
                self.touch_max_ever_distance = 0.0
                self.touch_start_time = now
                self.touch_start_x = x
                self.touch_scrolling = False
                self.touch_start_y = y
                self.last_touch_x = x
                self.last_touch_y = y
                
                # Schedule test for long-press click:
                if not self.prevent_touch_long_click_due_to_gesture:
                    self.long_click_callback_id += 1
                    curr_id = self.long_click_callback_id
                    self_ref = weakref.ref(self)
                    self.have_long_click_callback = True
                    schedule(self.return_long_click_test_closure(curr_id),
                        config.get("touch_longclick_time"))
            elif event_name.startswith("touch"):
                self.last_touch_x = x
                self.last_touch_y = y
            # Update touch info during move & end events:
            if event_name == "touchmove" or \
                    event_name == "touchend":
                self.touch_max_ever_distance = max(
                    self.touch_max_ever_distance, float(
                    math.sqrt(math.pow(
                    x - self.touch_start_x, 2) +
                    math.pow(y - self.touch_start_y, 2))))
                # Make sure moving too far stops long clicks:
                if self.touch_max_ever_distance > 7 * self.dpi_scale \
                        and self.have_long_click_callback:
                    # Finger moved too far, no longer long press click:
                    self.have_long_click_callback = False
                    self.long_click_callback_id += 1
                if event_name == "touchend":
                    # Stop long click detection:
                    if self.have_long_click_callback:
                        self.long_click_callback_id += 1
                        self.have_long_click_callback = False
                    # Reset touch start:
                    self.touch_start_x = None
                    self.touch_start_y = None
            # Update infinite scroll emulation:
            if event_name.startswith("touch"):
                self.schedule_infinite_scroll_check(x, y,
                    stop_event=(event_name == "touchend"))

        Perf.chain(chain_id, "touchstate_update_done")

        # See what we want to use for the hit check for propagation:
        # (This needs to happen both in pre and post handler!!)
        cdef int hit_check_x = x
        cdef int hit_check_y = y
        if event_name.startswith("touch"):
            if touch_hitpoint_check_x != None:
                hit_check_x = touch_hitpoint_check_x
                hit_check_y = touch_hitpoint_check_y

        # *** FAKE MOUSE TOUCH EVENTS (only in pre handler) ***
        if not is_post:
            # Regular mouse down focus:
            if event_name == "mousedown":
                self.consider_mouse_click_focus(hit_check_x, hit_check_y)            

            # If our own widget doesn't handle touch, fire the
            # fake clicks here:
            touch_fake_clicked = False
            fake_clicks_for_event = \
                ((not self.has_native_touch_support or
                self.fake_mouse_even_with_native_touch_support)
                and event_name == "touchend" and
                orig_touch_start_x != None and
                orig_touch_start_y != None)
            if fake_clicks_for_event and \
                    self.touch_max_ever_distance <\
                    40.0 * self.dpi_scale and \
                    not self.touch_scrolling and \
                    self.touch_start_time + config.get(
                    "touch_shortclick_time") > now and \
                    not self.effectively_inactive:
                # Emulate a mouse click, but make sure it's not
                # propagated to children (since they would, if
                # necessary, emulate their own mouse clicks as well
                # from the already propagating touch event):
                self.stop_infinite_scroll()
                self._prevent_mouse_event_propagate = True
                touch_fake_clicked = True
                self.consider_mouse_click_focus(hit_check_x,
                    hit_check_y)
                old_value = self._in_touch_fake_event_processing
                try:
                    self._in_touch_fake_event_processing = True
                    self.mousedown(0, 1,
                        orig_touch_start_x - self.abs_x,
                        orig_touch_start_y - self.abs_y,
                        internal_data=[
                            orig_touch_start_x,
                            orig_touch_start_y])
                    if not self.generate_double_click_for_touches:
                        self.click(0, 1,
                            orig_touch_start_x - self.abs_x,
                            orig_touch_start_y - self.abs_y,
                            internal_data=[
                                orig_touch_start_x,
                                orig_touch_start_y])
                    else:
                        self.doubleclick(0, 1,
                            orig_touch_start_x - self.abs_x,
                            orig_touch_start_y - self.abs_y,
                            internal_data=[
                                orig_touch_start_x,
                                orig_touch_start_y])
                    self.mouseup(0, 1,
                        orig_touch_start_x - self.abs_x,
                        orig_touch_start_y - self.abs_y,
                        internal_data=[
                            orig_touch_start_x,
                            orig_touch_start_y])
                finally:
                    self._in_touch_fake_event_processing = old_value
                    self._prevent_mouse_event_propagate = False 

            # If our own widget doesn't handle touch, do the
            # fake scrolling here:
            fake_scrolling_for_event =\
                ((not self.has_native_touch_support or
                self.fake_mouse_even_with_native_touch_support)
                and
                (event_name == "touchmove" or
                event_name == "touchend") and
                orig_touch_start_x != None and
                orig_touch_start_y != None)
            if fake_scrolling_for_event and \
                    (abs(diff_x) >= 0.1 or abs(diff_y) >= 0.1) and (
                    self.touch_scrolling or
                    self.touch_max_ever_distance >
                    40.0 * self.dpi_scale or \
                    (self.touch_max_ever_distance >
                    20.0 * self.dpi_scale and \
                    self.touch_start_time + 0.7 > now)):
                self.touch_scrolling = True
                self.consider_mouse_click_focus(hit_check_x,
                    hit_check_y)
                scalar = 0.019
                self._prevent_mouse_event_propagate = True
                old_value = self._in_touch_fake_event_processing
                try:
                    self._in_touch_fake_event_processing = True
                    self.mousewheel(0,
                        diff_x * scalar, diff_y * scalar,
                        internal_data=[
                        orig_touch_start_x, orig_touch_start_y])
                finally:
                    self._in_touch_fake_event_processing = False
                    self._prevent_mouse_event_propagate = False

        Perf.chain(chain_id, "fakemouse_events_done")

        # *** EVENT PROPAGATION, ONLY POST-CALLBACK HANDLING ***
        if not is_post:
            Perf.stop(chain_id)
            return

        # Pass on event to child widgets:
        if self._prevent_mouse_event_propagate == True:
            Perf.stop(chain_id)
            return
        cdef object child_list = copy.copy(self.children)
        cdef int check_widget_overlap = False
        if hasattr(self, "get_children_in_strict_mouse_event_order"):
            child_list = copy.copy(
                self.get_children_in_strict_mouse_event_order())
            check_widget_overlap = True
        cdef int force_no_more_matches = False
        cdef int rel_x = x - self.abs_x
        cdef int rel_y = y - self.abs_y
        cdef int hit_check_rx = hit_check_x - self.abs_x
        cdef int hit_check_ry = hit_check_y - self.abs_y
        Perf.chain(chain_id, "propagate_start")
        for child in child_list:
            if child.parent != self or (child.type != "window" and
                    child.parent_window is None):
                # Either invalid child, or was already removed during
                # processing of a previous child.
                continue
            if not force_no_more_matches and \
                    hit_check_rx >= child.x and \
                    hit_check_ry >= child.y and \
                    hit_check_rx < child.x + child.width and \
                    hit_check_ry < child.y + child.height and \
                    not child.effectively_invisible and \
                    (not child.effectively_inactive or\
                    (event_name != "mousedown" and
                    event_name != "touchstart" and
                    event_name != "multitouchstart")):
                # If we're in strict ordered mouse event mode, this
                # widget will be treated as obscuring the next ones:
                if check_widget_overlap:
                    force_no_more_matches = True

                # --- Touch events ---
                if event_name == "touchmove":
                    child.last_touch_was_inside = True
                    if not child.touchmove(
                            rel_x - child.x, rel_y - child.y,
                            internal_data=internal_data):
                        return True
                    continue
                elif event_name == "touchstart":
                    child.last_touch_was_pressed = True
                    if not child.touchstart(
                            rel_x - child.x, rel_y - child.y,
                            internal_data=internal_data):
                        return True
                    continue
                elif event_name == "touchend":
                    child.last_touch_was_inside = False
                    child.last_touch_was_pressed = False
                    if not child.touchend(
                            rel_x - child.x, rel_y - child.y,
                            internal_data=internal_data):
                        return True
                    continue

                # --- Only mouse events from here ---
                # Track some side effects, to make sure e.g. mouse move
                # events get followed up by one last outside-of-widget
                # event when mouse leaves, or that mouse down changes
                # the keyboard focus, or double-click:
                if event_name == "mousemove":
                    child.last_mouse_move_was_inside = True
                elif event_name == "mousedown":
                    child.last_mouse_down_presses.add((event_args[0],
                        event_args[1]))
                elif event_name == "mouseup" and \
                        (event_args[0], event_args[1]) in \
                        child.last_mouse_down_presses:
                    child.last_mouse_down_presses.discard(
                        (event_args[0], event_args[1]))

                    # See if this is a double-click:
                    t = now - 10.0
                    if (event_args[0], event_args[1]) in \
                            child.last_mouse_click_with_time:
                        t = child.last_mouse_click_with_time[
                            (event_args[0], event_args[1])]
                    if t > now - config.get("doubleclick_time"):
                        # It's a double click!
                        del(child.last_mouse_click_with_time[
                            (event_args[0], event_args[1])])
                        child.doubleclick(mouse_id, event_args[1],
                            rel_x - child.x,
                            rel_y - child.y)
                    else:
                        # Just a normal click.
                        child.last_mouse_click_with_time[
                            (event_args[0], event_args[1])] = \
                            now
                        child.click(mouse_id, event_args[1],
                            rel_x - child.x,
                            rel_y - child.y,
                            internal_data=internal_data)
                # Trigger actual event on the child widget:
                if event_name == "mousemove":
                    if not child.mousemove(mouse_id,
                            rel_x - child.x, rel_y - child.y,
                            internal_data=internal_data):
                        Perf.chain(chain_id, "propagate_end")
                        Perf.stop(chain_id)
                        return True
                elif event_name == "mousewheel":
                    if not child.mousewheel(mouse_id, float(wx),
                            float(wy),
                            internal_data=internal_data):
                        Perf.chain(chain_id, "propagate_end")
                        Perf.stop(chain_id)
                        return True
                else:
                    if not getattr(child, event_name)(mouse_id,
                            event_args[1],
                            rel_x - child.x, rel_y - child.y,
                            internal_data=internal_data):
                        Perf.chain(chain_id, "propagate_end")
                        Perf.stop(chain_id)
                        return True
            else:
                if event_name.startswith("touch") and \
                        child.last_touch_was_inside:
                    child.last_touch_was_inside = False
                    if child.last_touch_was_pressed:
                        if force_no_more_matches:
                            child.touchmove(-5, -5)
                        else:
                            child.touchmove(
                                rel_x - child.x, rel_y - child.y,
                                internal_data=internal_data)
                if event_name.startswith("mouse") and \
                        child.last_mouse_move_was_inside:
                    child.last_mouse_move_was_inside = False
                    if force_no_more_matches:
                        # Need to use true outside fake coordinates
                        # to remove focus etc
                        child.mousemove(mouse_id, -5, -5)
                    else:
                        child.mousemove(mouse_id,
                            rel_x - child.x, rel_y - child.y,
                            internal_data=internal_data)
                if event_name == "mouseup" and \
                        (event_args[0], event_args[1]) in \
                        child.last_mouse_down_presses:
                    child.last_mouse_down_presses.discard(
                        (event_args[0], event_args[1]))
                    child.mouseup(mouse_id, event_args[1],
                        rel_x - child.x, rel_y - child.y,
                        internal_data=internal_data)
                elif event_name == "touchend" and \
                        child.last_touch_was_pressed:
                    child.last_touch_was_pressed = False
                    child.touchend(
                        rel_x - child.x, rel_y - child.y,
                        internal_data=internal_data)
        # Done!
        Perf.chain(chain_id, "propagate_end")
        Perf.stop(chain_id)

    def renderer_update(self):
        if self.internal_render_target != None:
            if config.get("debug_texture_references"):
                logdebug("WidgetBase.renderer_update: " +
                    "DUMPED self.internal_render_target")
            self.internal_render_target = None
        for child in self.children:
            child.renderer_update()

    @property
    def style(self):
        return self.get_style()

    @style.setter
    def style(self, v):
        if not hasattr(self, "style"):
            raise RuntimeError("this item doesn't support " +
                "setting a style")

    def get_style(self):
        return None

    def recursive_needs_redraw(self):
        self.needs_redraw = True
        for child in self.children:
            child.recursive_needs_redraw()

    @property
    def dpi_scale(self):
        cdef double window_scaler = 1.0
        if hasattr(self, "parent_window") and \
                self.parent_window != None:
            window_scaler = self.parent_window.get_window_dpi()
        s = self.style
        if s != None:
            return s.dpi_scale * window_scaler
        return 1.0 * window_scaler

    def get_natural_width(self):
        return 64

    def get_natural_height(self, given_width=None):
        return 64

    def draw_children(self):
        for child in self.children:
            child.redraw_if_necessary()
            sdl.SDL_SetRenderDrawColor(self.renderer,
                255, 255, 255, 255)
            child.draw(child.x, child.y)

    def draw(self, int x, int y):
        if self.invisible:
            return
        self.redraw_if_necessary()
        if self.internal_render_target is None:
            if self._width < 0 or self._height < 0 or \
                    self.renderer is None:
                return
            self.redraw()
            if self.internal_render_target is None:
                return
        assert(x != None and y != None)
        self.internal_render_target.draw(x, y)

    def relayout_if_necessary(self):
        cdef int changed = False
        for child in self.children:
            if child.relayout_if_necessary():
                changed = True
        if self.needs_relayout:
            changed = True
            self.relayout()
        return changed

    def redraw_if_necessary(self):
        for child in self.children:
            if child.redraw_if_necessary():
                self.needs_redraw = True
        if self.needs_redraw:
            self.needs_redraw = False
            self.redraw()
            return True
        return (self.needs_redraw is True)

    def do_redraw(self):
        pass

    def set_max_width(self, w):
        if w != None:
            w = max(0, int(w))
        else:
            w = -1
        if self._max_width == w:
            return
        self._max_width = w 
        self.resized()

    def set_max_height(self, w):
        if w != None:
            w = max(0, int(w))
        else:
            w = -1
        if self._max_height == w:
            return
        self._max_height = w
        self.resized()

    @property
    def width(self):
        if self._max_width >= 0:
            return min(self._max_width, self._width)
        return self._width

    @property
    def height(self):
        if self._max_height >= 0:
            return min(self._max_height, self._height)
        return self._height

    @width.setter
    def width(self, int v):
        if self._width != v:
            self.size_change(v, self.height)

    @height.setter
    def height(self, int h):
        if self._height != h:
            self.size_change(self.width, h)

    @staticmethod
    def focus_candidates(group_widget):
        global all_widgets
        assert(group_widget != None)
        group_widgets = group_widget
        if type(group_widgets) != list:
            group_widgets = [group_widgets]
        candidates = []
        for w_ref in all_widgets:
            w = w_ref()
            if w is None or not w.focusable:
                continue
            is_in_group = False
            for group_widget in group_widgets:
                if w.shares_focus_group(group_widget) and \
                        group_widget.shares_focus_group(w):
                    is_in_group = True
                    break
            if not is_in_group:
                continue
            assert(w != None)
            candidates.append(w)
        for group_widget in group_widgets:
            if not group_widget in candidates and \
                    group_widget.focusable:
                candidates.append(group_widget)
        sorted_candidates = sorted(candidates,
            key=functools.cmp_to_key(tab_sort))
        return sorted_candidates

    def size_change(self, int w, int h):
        self._width = w
        self._height = h
        self.needs_relayout = True
        self.needs_redraw = True
        self.resized()

    @staticmethod
    def get_focused_widget(group_widget):
        global all_widgets
        for w_ref in all_widgets:
            w = w_ref()
            if w is None or not w.focused or \
                    not w.shares_focus_group(group_widget) or \
                    not group_widget.shares_focus_group(w):
                continue
            return w
        return None

    @staticmethod
    def get_focused_widget_by_window(window):
        global all_widgets
        for w_ref in all_widgets:
            w = w_ref()
            if w is None or not w.focused \
                    or not w.focusable \
                    or not hasattr(w, "parent_window") \
                    or w.parent_window != window:
                continue
            return w

    def _internal_on_stylechanged(self, internal_data=None):
        self.needs_redraw = True
        self.needs_relayout = True

    @property
    def effectively_invisible(self):
        if self.invisible:
            return True
        p = self.parent
        while p != None:
            if p.invisible:
                return True
            p = p.parent
        return False

    @property
    def effectively_inactive(self):
        if self.type != "window" and \
                hasattr(self, "parent_window") and \
                self.parent_window is None:
            return True
        if self.type != "window" and \
                hasattr(self, "parent_window") and \
                self.parent_window != None and \
                self.parent_window.modal_filter != None and \
                self.parent_window.modal_filter(self) is False:
            return True
        if self.disabled or self.invisible:
            return True
        p = self.parent
        while p != None:
            if p.disabled or p.invisible:
                return True
            p = p.parent
        return False

    def has_as_parent(self, other_widget):
        p = self.parent
        while p != None and p != other_widget:
            p = p.parent
        return (p == other_widget)

    @property
    def focusable(self):
        return (self._focusable and not self.effectively_inactive)

    @property
    def focused(self):
        return self._is_focused

    def shares_focus_group(self, widget):
        return True

    def _internal_on_unfocus(self, internal_data=None):
        if not self.focused:
            raise RuntimeError("not focused")
        self._is_focused = False
        self.needs_redraw = True

    def update(self):
        self.needs_relayout = True
        self.needs_redraw = True

    def focus_next(self):
        raise RuntimeError("not implemented for this " +
            "type of widget")

    def focus_previous(self):
        raise RuntimeError("not implemented for this " +
            "type of widget")

    def on_focus(self):
        if self.focused:
            return
        def unfocus_focused():
            global all_widgets
            for w_ref in all_widgets:
                w = w_ref()
                if w is None or w is self or \
                        not w.shares_focus_group(self):
                    continue
                if w.focused:
                    w.unfocus()
        if self.disabled or self.invisible:
            return True  # prevent focus entirely
        if not self.focusable:
            # See if a child can be focused:
            def try_children_focus(w):
                tab_index_sorted = sorted(w.children,
                    key=functools.cmp_to_key(tab_sort))
                for child in tab_index_sorted:
                    if child.disabled:
                        continue
                    if not child.focusable:
                        if try_children_focus(child):
                            return True
                    else:
                        child.focus()
                        return True
                return False
            if not try_children_focus(self):
                return True  # prevent focus
        else:
            do_event = False
            if not self.focused:
                try:
                    unfocus_focused()
                finally:
                    self._is_focused = True
                    self.needs_redraw = True
                    if self.takes_text_input:
                        enable_text_events(self)

    def set_focus_index(self, index):
        self.focus_index = index

    def get_renderer(self):
        return None

    def draw_keyboard_focus(self, x, y, width, height):
        perf_id = Perf.start("draw_keyboard_focus")
        focus_border_thickness = 1.0
        c = Color.red
        if c != None:
            c = Color(self.style.get("focus_border"))
        draw_dashed_line(self.renderer,
            x + 0.5 * focus_border_thickness * self.dpi_scale,
            y,
            x + 0.5 * focus_border_thickness * self.dpi_scale,
            y + height,
            dash_length=(7.0 * self.dpi_scale),
            thickness=(focus_border_thickness * self.dpi_scale),
            color=c)
        draw_dashed_line(self.renderer,
            x + width - 0.5 * focus_border_thickness * self.dpi_scale,
            y,
            x + width - 0.5 * focus_border_thickness * self.dpi_scale,
            y + height,
            dash_length=(7.0 * self.dpi_scale),
            thickness=(focus_border_thickness * self.dpi_scale),
            color=c)
        draw_dashed_line(self.renderer,
            x,
            y + 0.5 * focus_border_thickness * self.dpi_scale,
            x + width,
            y + 0.5 * focus_border_thickness * self.dpi_scale,
            dash_length=(7.0 * self.dpi_scale),
            thickness=(focus_border_thickness * self.dpi_scale),
            color=c)
        draw_dashed_line(self.renderer,
            x,
            y + height - 0.5 * focus_border_thickness * self.dpi_scale,
            x + width,
            y + height - 0.5 * focus_border_thickness * self.dpi_scale,
            dash_length=(7.0 * self.dpi_scale),
            thickness=(focus_border_thickness * self.dpi_scale),
            color=c)
        Perf.stop(perf_id)

    @property
    def renderer(self):
        return self.get_renderer()

    def remove(self, item, error_if_not_present=True):
        if not self.is_container:
            raise RuntimeError("this widget is " +
                "not a container, can't remove children")
        if not item in self._children:
            if error_if_not_present:
                raise ValueError("child is not contained: " +
                    str(item))
            return
        if item.parent == self:
            item.internal_override_parent(None)
        self._children.remove(item)

    def add(self, item, trigger_resize=True):
        if not self.is_container:
            raise RuntimeError("this widget is " +
                "not a container, can't add children")
        # Check that this nesting is valid:
        if item == self:
            raise ValueError("cannot add widget to itself")
        item_p = item.parent
        while item_p != None:
            if item_p == self:
                raise ValueError("cannot add widget here, " +
                    "this results in a cycle")
            item_p = item_p.parent

        # Remove item from previous parent if any:
        if item.parent != None:
            item.parent.remove(item, error_if_not_present=False)
        self._children.append(item)
        self.needs_relayout = True
        item.internal_override_parent(self)
        self.needs_redraw = True
        item.relayout()
        if trigger_resize:
            self.resized()

    def internal_override_parent(self, parent):
        old_renderer = self.get_renderer()
        if self._parent == parent:
            return
        prev_style = self.get_style()
        prev_dpi = self.dpi_scale
        old_parent = self._parent
        self._parent = parent
        self.needs_redraw = True
        self.parentchanged()
        if prev_style != self.get_style() or \
                abs(prev_dpi - self.dpi_scale) > 0.01:
            def recursive_style_event(item):
                item.stylechanged()
                for child in item.children:
                    recursive_style_event(child)
            recursive_style_event(self)
        if self.get_renderer() != old_renderer:
            if config.get("debug_texture_references"):
                logdebug("WidgetBase.internal_override_parent: " +
                    "recursive renderer_update() call")
            def recursive_update_event(item):
                item.renderer_update()
                for child in item.children:
                    recursive_update_event(child)
            recursive_update_event(self)

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return copy.copy(self.get_children())

    def get_children(self):
        return self._children


