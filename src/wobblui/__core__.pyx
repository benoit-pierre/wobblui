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

import ctypes
import math
import sdl2 as sdl
import sys
import threading
import time
import traceback

from wobblui.keyboard import internal_update_text_events,\
    get_active_text_widget, get_modifiers, \
    internal_update_keystate_keydown, \
    internal_update_keystate_keyup, \
    clean_global_shortcuts
from wobblui.mouse import cursors_seen_during_mousemove,\
    reset_cursors_seen_during_mousemove, set_cursor
from wobblui.osinfo import is_android
from wobblui.perf cimport CPerf as Perf
import wobblui.font.sdlfont as sdlfont
from wobblui.timer import internal_trigger_check,\
    maximum_sleep_time
from wobblui.uiconf import config
from wobblui.widgetman import all_widgets
from wobblui.window import all_windows, get_focused_window,\
    get_window_by_sdl_id
from wobblui.woblog import logdebug, logerror, loginfo, logwarning

cdef long long sdl_touch_mouseid = 4294967295
if hasattr(sdl, "SDL_TOUCH_MOUSEID"):
    sdl_touch_mouseid = sdl.SDL_TOUCH_MOUSEID

cdef int MULTITOUCH_DEBUG = 1

def redraw_windows(int layout_only=False):
    for w_ref in all_windows:
        w = w_ref()
        if w is None or w.hidden:
            continue
        try:
            relayout_perf = Perf.start("redraw_windows_relayout")
            w.update_to_real_sdlw_size()
            w.do_scheduled_dpi_scale_update()
            i = 0
            while i < 20:
                if not w.relayout_if_necessary():
                    break
                i += 1
            if i == 20:
                logwarning("WARNING: a widget appears to be causing a " +
                    "relayout() loop !!! affected window: " +
                    str(w) + ", all widgets that need relayouting: " +
                    str([widget for widget in [
                        wi_ref() for wi_ref in all_widgets] if \
                        widget != None and widget.needs_relayout and \
                        ((hasattr(widget, "parent_window") and
                        widget.parent_window) == w or widget == w)]))
            Perf.stop(relayout_perf, expected_max_duration=0.010)
            if not layout_only:
                w.redraw_if_necessary()
        except Exception as e:
            logerror("*** ERROR HANDLING WINDOW ***")
            logerror(str(traceback.format_exc()))

def sdl_vkey_map(int key):
    if key >= sdl.SDLK_0 and key <= sdl.SDLK_9:
        return chr(ord("0") + (key - sdl.SDLK_0))
    if key >= sdl.SDLK_a and key <= sdl.SDLK_z:
        return chr(ord("a") + (key - sdl.SDLK_a))
    if key == sdl.SDLK_KP_TAB or key == sdl.SDLK_TAB:
        return "tab"
    if key == sdl.SDLK_LALT:
        return "lalt"
    if key == sdl.SDLK_RALT:
        return "ralt"
    if key == sdl.SDLK_LCTRL:
        return "lctrl"
    if key == sdl.SDLK_RCTRL:
        return "rctrl"
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
    if key == sdl.SDLK_AC_BACK:
        return "back"
    return str("scancode-" + str(key))

def sdl_key_map(int key):
    if key >= sdl.SDL_SCANCODE_0 and key <= sdl.SDL_SCANCODE_9:
        return chr(ord("0") + (key - sdl.SDL_SCANCODE_0))
    if key >= sdl.SDL_SCANCODE_A and key <= sdl.SDL_SCANCODE_Z:
        return chr(ord("a") + (key - sdl.SDL_SCANCODE_A))
    if key == sdl.SDL_SCANCODE_KP_TAB or key == sdl.SDL_SCANCODE_TAB:
        return "tab"
    if key == sdl.SDL_SCANCODE_AC_BACK:
        return "back"
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

stuck_thread = None
last_alive_time = None
def stuck_check():
    global last_alive_time
    while True:
        time.sleep(5)
        if last_alive_time != None and \
                last_alive_time + 60.0 < time.monotonic():
            logwarning("Application appears stuck, UI processing " +
                "not called for >60 seconds!")
            logwarning("Backtraces of all threads will follow.")
            for th in threading.enumerate():
                logwarning(str(th))
                logwarning(str("\n".join(
                    traceback.format_stack(sys._current_frames()[th.ident]))))
            # Make sure we don't fire this again right away:
            last_alive_time = time.monotonic()

def event_loop(app_cleanup_callback=None):
    global stuck_thread, last_alive_time
    if stuck_thread is None:
        stuck_thread = threading.Thread(target=stuck_check, daemon=True)
        stuck_thread.start()
    last_alive_time = time.monotonic()
    cdef int had_jobs
    cdef int event_loop_ms = 10
    try:
        font_no_sleep_counter = 0
        while True:
            last_alive_time = time.monotonic()
            max_sleep = maximum_sleep_time()
            sleep_amount = event_loop_ms * 0.001
            had_jobs = False
            if max_sleep != None:
                had_jobs = sdlfont.process_jobs()
                sleep_amount = max(0, min(sleep_amount, max_sleep))
                if had_jobs:
                    font_no_sleep_counter = 10
                    sleep_amount = 0
                    event_loop_ms = min(10, event_loop_ms)
            if font_no_sleep_counter > 0:
                font_no_sleep_counter -= 1
                sleep_amount = 0
            if sleep_amount > 0.0005:
                time.sleep(sleep_amount)
            result = do_event_processing(ui_active=True)
            if result == "appquit":
                if app_cleanup_callback != None:
                    app_cleanup_callback()
                # Get __del__ processed on as many things as possible
                # to allow them to wrap up things cleanly:
                import gc; gc.collect()
                time.sleep(0.05)
                gc.collect()
                time.sleep(0.05)
                sys.exit(0)
                return
            if result is True:
                # Had events. Remain responsive!
                if event_loop_ms > 10:
                    event_loop_ms = 10
            else:
                # No events. Take some time
                max_sleep = maximum_sleep_time()
                if event_loop_ms < 500:
                    event_loop_ms = min(
                        event_loop_ms + 1,
                        500)
    except (SystemExit, KeyboardInterrupt) as e:
        loginfo("APP SHUTDOWN INITIATED. CLEANING UP...")
        sdlfont.stop_queue_for_process_shutdown()
        if app_cleanup_callback != None:
            app_cleanup_callback()

        # Get __del__ processed on as many things as possible
        # to allow them to wrap up things cleanly:
        import gc; gc.collect()
        time.sleep(0.05)
        gc.collect()
        time.sleep(0.05)
        raise e

def sdl_event_name(event):
    cdef int ev_no = event.type
    if ev_no == sdl.SDL_MOUSEBUTTONDOWN:
        return "mousebuttondown"
    elif ev_no == sdl.SDL_MOUSEBUTTONUP:
        return "mousebuttonup"
    elif ev_no == sdl.SDL_MOUSEMOTION:
        return "mousemotion"
    elif ev_no == sdl.SDL_MOUSEWHEEL:
        return "mousewheel"
    elif ev_no == sdl.SDL_KEYDOWN:
        return "keydown-" + str(sdl_vkey_map(event.key.keysym.sym))
    elif ev_no == sdl.SDL_KEYUP:
        return "keyup-" + str(sdl_vkey_map(event.key.keysym.sym))
    elif ev_no == sdl.SDL_TEXTINPUT:
        return "textinput"
    elif ev_no == sdl.SDL_WINDOWEVENT:
        if event.window.event == sdl.SDL_WINDOWEVENT_FOCUS_GAINED:
            return "windowfocusgained"
        elif event.window.event == sdl.SDL_WINDOWEVENT_RESIZED:
            return "windowresized"
        elif event.window.event == sdl.SDL_WINDOWEVENT_CLOSE:
            return "windowclose"
        elif event.window.event == sdl.SDL_WINDOWEVENT_HIDDEN:
            return "windowhidden"
        elif event.window.event == sdl.SDL_WINDOWEVENT_MINIMIZED:
            return "windowminimized"
        elif event.window.event == sdl.SDL_WINDOWEVENT_RESTORED:
            return "windowrestored"
        elif event.window.event == sdl.SDL_WINDOWEVENT_EXPOSED:
            return "windowexposed"
        elif event.window.event == sdl.SDL_WINDOWEVENT_MAXIMIZED:
            return "windowmaximized"
        elif hasattr(sdl, "SDL_WINDOWEVENT_TAKE_FOCUS") and \
                event.window.event == sdl.SDL_WINDOWEVENT_TAKE_FOCUS:
            return "windowtakefocus"
        else:
            return "windowunknownevent-" +\
                str(event.window.event)
    return "unknown-" + str(ev_no)

def debug_describe_event(event):
    cdef str t = sdl_event_name(event)
    if event.type == sdl.SDL_MOUSEBUTTONDOWN or \
            event.type == sdl.SDL_MOUSEBUTTONUP:
        t += "(which:" + str(event.button.which) +\
            ",button:" + str(event.button.button) +\
            ",x:" + str(event.motion.x) +\
            ",y:" + str(event.motion.y) +")"
    elif event.type == sdl.SDL_MOUSEMOTION:
        t += "(which:" + str(event.motion.which) +\
            ",x:" + str(event.motion.x) +\
            ",y:" + str(event.motion.y) + ")"
    elif event.type == sdl.SDL_MOUSEWHEEL:
        t += "(which:" + str(event.wheel.which) +\
            ",x:" + str(event.wheel.x) +\
            ",y:" + str(event.wheel.y) + ")"
    return t

def do_event_processing_if_on_main_thread(ui_active=True):
    if threading.current_thread() != threading.main_thread():
        return
    do_event_processing(ui_active=ui_active)

_last_clean_shortcuts_ts = None
def do_event_processing(int ui_active=True):
    global _last_clean_shortcuts_ts, last_alive_time
    if threading.current_thread() != threading.main_thread():
        raise RuntimeError("UI events can't be processed " +
            "from another thread")
    last_alive_time = time.monotonic()
    if _last_clean_shortcuts_ts is None:
        _last_clean_shortcuts_ts = time.monotonic()
    if _last_clean_shortcuts_ts + 1.0 < time.monotonic():
        clean_global_shortcuts()
    events = []
    while True:
        ev = sdl.SDL_Event()
        result = sdl.SDL_PollEvent(ctypes.byref(ev))
        if result == 1:
            events.append(ev)
            continue
        break
    update_multitouch()
    if len(events) == 0:
        internal_trigger_check(idle=True)
        internal_update_text_events()
        redraw_windows()
        return False
    for event in events:
        if config.get("debug_source_events") is True:
            logdebug("wobblui.__init__.py: DEBUG: sdl event: " +
                debug_describe_event(event))
        if not ui_active:
            # Skip this event unless it is essential.
            if (event.type != sdl.SDL_QUIT and
                    (event.type != sdl.SDL_WINDOWEVENT or
                    (event.window.event !=
                        sdl.SDL_WINDOWEVENT_FOCUS_GAINED and
                        event.window.event !=
                        sdl.SDL_WINDOWEVENT_FOCUS_LOST and
                        event.window.event !=
                        sdl.SDL_WINDOWEVENT_RESIZED and
                        event.window.event !=
                        sdl.SDL_WINDOWEVENT_CLOSE and
                        event.window.event !=
                        sdl.SDL_WINDOWEVENT_HIDDEN and
                        event.window.event !=
                        sdl.SDL_WINDOWEVENT_MINIMIZED and
                        event.window.event !=
                        sdl.SDL_WINDOWEVENT_RESTORED and
                        event.window.event !=
                        sdl.SDL_WINDOWEVENT_EXPOSED and
                        event.window.event !=
                        sdl.SDL_WINDOWEVENT_MAXIMIZED)) and
                    event.type != sdl.SDL_APP_DIDENTERBACKGROUND and
                    event.type != sdl.SDL_APP_WILLENTERBACKGROUND and
                    event.type != sdl.SDL_APP_DIDENTERFOREGROUND and
                    event.type != sdl.SDL_APP_WILLENTERFOREGROUND and
                    event.type != sdl.SDL_MOUSEMOTION
                    ):
                # Update keystate while avoiding global shortcuts:
                if event.type == sdl.SDL_KEYDOWN or \
                        event.type == sdl.SDL_KEYUP:
                    _process_key_event(event, trigger_shortcuts=False,
                        force_no_widget_can_receive_new_input=True)

                # Update touch state:
                if (event.type == sdl.SDL_MOUSEBUTTONUP
                        or event.type == sdl.SDL_MOUSEBUTTONDOWN):
                    _process_mouse_click_event(event,
                        force_no_widget_can_receive_new_input=True)
        try:
            perf_id = Perf.start("sdlevent_" + str(
                debug_describe_event(event)) + "_processing")
            if _handle_event(event) is False and ui_active:
                # App termination.
                Perf.stop(perf_id)
                return "appquit"
            Perf.stop(perf_id, expected_max_duration=0.020)
        except Exception as e:
            logerror("*** ERROR IN EVENT HANDLER ***")
            logerror(str(traceback.format_exc()))
    redraw_windows(layout_only=True)
    internal_trigger_check(idle=False)
    internal_update_text_events()
    redraw_windows()
    sdlfont.process_jobs()
    return True

def _process_mouse_click_event(event,
        force_no_widget_can_receive_new_input=False):
    global capture_enabled, touch_pressed, \
        mouse_ids_button_ids_pressed,\
        multitouch_gesutre_active
    _debug_mouse_fakes_touch = (
        config.get("mouse_fakes_touch_events") is True)

    Perf.chain("mouseevent")

    if event.type != sdl.SDL_MOUSEBUTTONDOWN and \
            event.type != sdl.SDL_MOUSEBUTTONUP:
        raise TypeError("invalid event type")

    # A few preparations:
    w = get_window_by_sdl_id(event.button.windowID)
    if w is None or w.is_closed:
        return
    if w.hidden:
        w.set_hidden(False)
    capture_enabled = (len(mouse_ids_button_ids_pressed) > 0 or
        touch_pressed)

    is_touch = False
    if event.button.which == sdl_touch_mouseid or\
            _debug_mouse_fakes_touch:
        is_touch = True
        if not multitouch_gesture_active:
            # Update single finger pos for use in multi touch gesture
            # if there is ever an additional finger placed on device:
            last_single_finger_xpos = int(event.button.x)
            last_single_finger_ypos = int(event.button.y)
            last_single_finger_sdl_windowid =\
                event.button.windowID

    # Swap button 2 and 3, since SDL maps them unintuitively
    # (SDL: middle 2, right 3 - ours: middle 3, right 2)
    if event.button.button == 2:
        event.button.button = 3
    elif event.button.button == 3:
        event.button.button = 2

    # Actually send off event:
    if event.type == sdl.SDL_MOUSEBUTTONDOWN:
        if force_no_widget_can_receive_new_input:
            return
        if event.button.which == sdl_touch_mouseid or \
                _debug_mouse_fakes_touch:
            if multitouch_gesture_active:
                return
            touch_pressed = True
            Perf.chain("mouseevent", "callback_prep")
            w.touchstart(
                int(event.button.x), int(event.button.y))
        else:
            mouse_ids_button_ids_pressed.add(
                (int(event.button.which),
                int(event.button.button)))
            Perf.chain("mouseevent", "callback_prep")
            w.mousedown(int(event.button.which),
                int(event.button.button),
                int(event.button.x), int(event.button.y),
                internal_data=[int(event.button.x),
                int(event.button.y)])
            Perf.chain('mouseevent', "callback")
        if not capture_enabled:
            if config.get("capture_debug"):
                logdebug("wobblui.py: debug: mouse capture engage")
            sdl.SDL_CaptureMouse(sdl.SDL_TRUE)
    else:
        if event.button.which == sdl_touch_mouseid or \
                _debug_mouse_fakes_touch:
            if force_no_widget_can_receive_new_input and \
                    not touch_pressed:
                # This was an ignored gesture. Don't do anything.
                return
            touch_pressed = False
            if multitouch_gesture_active:
                return
            Perf.chain("mouseevent", "callback_prep")
            w.touchend(
                int(event.button.x), int(event.button.y),
                internal_data=[int(event.button.x),
                int(event.button.y)])
            Perf.chain("mouseevent", "callback")
        else:
            if force_no_widget_can_receive_new_input and \
                    not (int(event.button.which),
                    int(event.button.button)) in \
                    mouse_ids_button_ids_pressed:
                # This click was ignored from the start. Ignore.
                return
            Perf.chain("mouseevent", "callback_prep")
            w.mouseup(int(event.button.which),
                int(event.button.button),
                int(event.button.x), int(event.button.y),
                internal_data=[int(event.button.x),
                int(event.button.y)])
            Perf.chain("mouseevent", "callback")
            mouse_ids_button_ids_pressed.discard(
                (int(event.button.which),
                int(event.button.button)))
        if capture_enabled and \
                (len(mouse_ids_button_ids_pressed) == 0 and
                not touch_pressed):
            if config.get("capture_debug"):
                logdebug("wobblui.py: debug: mouse capture release")
            sdl.SDL_CaptureMouse(sdl.SDL_FALSE)
    Perf.stop("mouseevent")

def _process_key_event(event,
        int trigger_shortcuts=True,
        int force_no_widget_can_receive_new_input=False):
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
    if event.type == sdl.SDL_KEYDOWN:
        internal_update_keystate_keydown(virtual_key,
            physical_key, trigger_shortcuts=trigger_shortcuts,
            active_widget_aware_of_keydown=(
                not force_no_widget_can_receive_new_input))
        if not force_no_widget_can_receive_new_input:
            w.keydown(virtual_key, physical_key, modifiers)
            if virtual_key.lower() == "return":
                w.textinput("\n", get_modifiers())
    else:
        widget_is_aware = internal_update_keystate_keyup(
            virtual_key, physical_key)
        if widget_is_aware:
            w.keyup(virtual_key, physical_key, modifiers)

def loading_screen_fix():
    if sdl.SDL_GetPlatform().decode(
            "utf-8", "replace").lower() == "android":
        # Hide python-for-android loading screen:
        try:
            from jnius import autoclass
        except ImportError:
            return
        autoclass('org.kivy.android.PythonActivity').\
            mActivity.removeLoadingScreen()


# Used to identify the "main" finger in multitouch used to continue sending
# the single finger touchstart/touchend event (to e.g. scroll while zooming)
last_single_finger_xpos = None
last_single_finger_ypos = None
last_single_finger_sdl_windowid = None
multitouch_gesture_active = False
active_touch_device = None

def finger_coordinates_to_window_coordinates(
        touch_device_id, finger_x, finger_y):
    # THIS ASSIGNMENT IS WRONG.
    # Due to an apparent SDL API design fault, there seems to be no
    # way to get this. Once there is one, this code will be updated.
    screen_for_touch_device = 0
    screen_mode = sdl.SDL_DisplayMode()
    result = sdl.SDL_GetCurrentDisplayMode(screen_for_touch_device,
        ctypes.byref(screen_mode))
    if result != 0:
        raise RuntimeError("unexpected failure to get current display mode")
    screen_touch_x = round(float(finger_x) * float(screen_mode.w))
    screen_touch_y = round(float(finger_y) * float(screen_mode.h))
    for w_ref in all_windows:
        w = w_ref()
        if w is None or not hasattr(w, "_sdl_window") or \
                w._sdl_window is None:
            continue
        if w.screen_index != screen_for_touch_device:
            continue
        (win_x, win_y) = w.get_screen_offset()
        if screen_touch_x >= win_x and \
                screen_touch_x < win_x + w.width and \
                screen_touch_y >= win_y and \
                screen_touch_y < win_y + w.height:
            return (w, round(screen_touch_x - win_x),
                round(screen_touch_y - win_y))
    return (None, -1, -1)

def update_multitouch():
    global touch_pressed
    global last_single_finger_xpos, last_single_finger_ypos,\
        last_single_finger_sdl_windowid
    global multitouch_gesture_active, active_touch_device
    if active_touch_device is None:
        multitouch_gesture_active = False
        return
    cdef int finger_amount = sdl.SDL_GetNumTouchFingers(
        active_touch_device)
    if finger_amount <= 1:
        # This is handled by regular single touch code. Stop multitouch.
        if multitouch_gesture_active and \
                last_single_finger_xpos != None and \
                finger_amount == 0:
            # Multitouch gesture still active, and we faked single touch so
            # far -> send end event
            if touch_pressed:
                event = sdl.SDL_Event()
                event.type = sdl.SDL_MOUSEBUTTONUP
                event.button.which = sdl_touch_mouseid
                event.button.button = 0
                event.button.x = last_single_finger_xpos
                event.button.y = last_single_finger_ypos
                event.button.windowID = last_single_finger_sdl_windowid
                _process_mouse_click_event(event)
                touch_pressed = False
            for w_ref in all_widgets:
                w = w_ref()
                if w != None:
                    if w.multitouch_gesture_reported_in_progress:
                        w.multitouch_gesture_reported_in_progress = False
                        w.multitouchend()
        # End multigesture:
        multitouch_gesture_active = False
        return
    if MULTITOUCH_DEBUG:
        logdebug("MULTITOUCH WITH FINGERS: " + str(finger_amount))
    multitouch_gesture_active = True

    # Find main finger of multitouch gesture:
    cdef int main_finger_id = -1
    cdef int main_finger_x = 0
    cdef int main_finger_y = 0
    cdef int main_finger_sdlwindowID = -1
    cdef double main_finger_dist = 0.0
    cdef object finger_positions = list()
    cdef int i = 0
    while i < finger_amount:
        finger_obj = sdl.SDL_GetTouchFinger(active_touch_device, i)
        (win, fx, fy) = finger_coordinates_to_window_coordinates(
            active_touch_device,
            float(finger_obj.contents.x),
            float(finger_obj.contents.y))
        if last_single_finger_sdl_windowid != None and \
                last_single_finger_sdl_windowid != win.sdl_window_id and \
                main_finger_id >= 0:
            i += 1
            continue
        last_single_finger_sdl_windowid = win.sdl_window_id

        finger_positions.append((int(fx), int(fy)))
        finger_dist = math.sqrt(math.pow(fx -
            last_single_finger_xpos) +
            math.pow(fy - last_single_finger_ypos))
        if finger_dist < main_finger_dist or main_finger_id < 0:
            main_finger_id = i
            main_finger_dist = finger_dist
            main_finger_x = fx
            main_finger_y = fy
        i += 1
    if MULTITOUCH_DEBUG:
        logdebug("MAIN FINGER ID: " + str(main_finger_id) +
            ", FINGER POSITIONS: " + str(finger_positions) +
            ", WINDOW: " + str(last_single_finger_sdl_windowid))

    # Report touch press if not done yet:
    if not touch_pressed:
        touch_pressed = True
        event = sdl.SDL_Event()
        event.type = sdl.SDL_MOUSEBUTTONDOWN
        event.button.windowID = last_single_finger_sdl_windowid
        event.button.which = sdl_touch_mouseid
        event.button.button = 0
        event.button.x = main_finger_x
        event.button.y = main_finger_y
        _process_mouse_click_event(event)

    # Report movement if single finger moved:
    if last_single_finger_xpos != None and \
            abs(last_single_finger_xpos - main_finger_x) >= 1 or \
            abs(last_single_finger_ypos - main_finger_y) >= 1:
        last_single_finger_xpos = main_finger_x
        last_single_finger_ypos = main_finger_y
        event = sdl.SDL_Event()
        event.type = sdl.SDL_MOUSEMOTION
        event.button.windowID = last_single_finger_sdl_windowid
        event.motion.which = sdl_touch_mouseid
        event.motion.x = last_single_finger_xpos
        event.motion.y = last_single_finger_ypos
        _process_mouse_click_event(event)

    # Get the display where the multitouch event is happening on:
    touch_event_screen_index = \
        get_window_by_sdl_id(last_single_finger_sdl_windowid)

    # Report multitouch gesture to all widgets in affected window:
    for w_ref in all_widgets:
        w = w_ref()
        if w == None or w.screen_index != touch_event_screen_index:
            continue
        if not w.multitouch_gesture_reported_in_progress:
            w.multitouch_gesture_reported_in_progress = True
            w.multitouchstart(finger_positions)
        w.multitouchmove(finger_positions)

annoying_sdl_hack_spacebar_outstanding = False
touch_pressed = False
mouse_ids_button_ids_pressed = set()
def _handle_event(event):
    global mouse_ids_button_ids_pressed, touch_pressed,\
        annoying_sdl_hack_spacebar_outstanding
    global last_single_finger_xpos,\
        last_single_finger_ypos, multitouch_gesture_active,\
        last_single_finger_sdl_windowid
    global active_touch_device
    cdef int x, y
    cdef str text
    cdef int _debug_mouse_fakes_touch = (
        config.get("mouse_fakes_touch_events") is True)
    if event.type == sdl.SDL_QUIT:
        window = get_focused_window()
        if window != None and window.focused:
            window.unfocus()
        for w_ref in all_windows:
            w = w_ref()
            if w is None or w.is_closed:
                continue
            w.destroyed()
        return
    elif event.type == sdl.SDL_MOUSEBUTTONDOWN or \
            event.type == sdl.SDL_MOUSEBUTTONUP:
        update_multitouch()
        if multitouch_gesture_active and \
                event.button.which == sdl_touch_mouseid:
            # Don't handle this, multitouch update will do so.
            return
        _process_mouse_click_event(event)
    elif event.type == sdl.SDL_MOUSEWHEEL:
        if event.wheel.which == sdl_touch_mouseid or \
                _debug_mouse_fakes_touch:
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
            float(x) * config.get("mouse_wheel_speed_modifier"),
            float(y) * config.get("mouse_wheel_speed_modifier"))
    elif event.type == sdl.SDL_FINGERDOWN or\
            event.type == sdl.SDL_FINGERMOTION or \
            event.type == sdl.SDL_FINGERUP:
        active_touch_device = event.tfinger.touchId
        update_multitouch()
    elif event.type == sdl.SDL_MOUSEMOTION:
        w = get_window_by_sdl_id(event.motion.windowID)
        if w is None or w.is_closed:
            return
        if w.hidden:
            w.set_hidden(False)
        if event.motion.which == sdl_touch_mouseid or \
                _debug_mouse_fakes_touch:
            if touch_pressed:
                if multitouch_gesture_active and \
                        event.button.which == sdl_touch_mouseid:
                    # Don't handle this, multitouch update will do so.
                    return
                w.touchmove(float(event.motion.x),
                    float(event.motion.y),
                    internal_data=[float(event.motion.x),
                        float(event.motion.y)])
        else:
            reset_cursors_seen_during_mousemove()
            w.mousemove(int(event.motion.which),
                float(event.motion.x), float(event.motion.y),
                internal_data=[float(event.motion.x),
                    float(event.motion.y)])
            special_cursor = False
            for cursor_seen in cursors_seen_during_mousemove:
                if cursor_seen not in ["arrow", "normal"]:
                    set_cursor(cursor_seen)
                    special_cursor = True
                    break
            if not special_cursor:
                set_cursor("normal")
    elif event.type == sdl.SDL_TEXTINPUT:
        text = event.text.text.decode("utf-8", "replace")
        widget = get_active_text_widget()
        if text.find(" ") >= 0:
            annoying_sdl_hack_spacebar_outstanding = False
        elif annoying_sdl_hack_spacebar_outstanding and \
                widget != None:
            annoying_sdl_hack_spacebar_outstanding = False
            widget.textinput(" ", get_modifiers())
        if widget != None and text != "\n" and text != "\r\n":
            widget.textinput(text, get_modifiers())
    elif event.type == sdl.SDL_KEYDOWN or \
            event.type == sdl.SDL_KEYUP:
        if event.type == sdl.SDL_KEYDOWN and is_android():
            # SDL has a stupid bug, so work around it:
            if sdl_vkey_map(event.key.keysym.sym) == "space" and \
                    get_active_text_widget() != None:
                annoying_sdl_hack_spacebar_outstanding = True
        elif event.type == sdl.SDL_KEYUP and is_android():
            if annoying_sdl_hack_spacebar_outstanding and \
                    sdl_vkey_map(event.key.keysym.sym) == "space":
                annoying_sdl_hack_spacebar_outstanding = False
                widget = get_active_text_widget()
                if widget != None:
                    widget.textinput(" ", get_modifiers())
        _process_key_event(event, trigger_shortcuts=True)
    elif event.type == sdl.SDL_WINDOWEVENT:
        if event.window.event == \
                sdl.SDL_WINDOWEVENT_FOCUS_GAINED:
            loading_screen_fix()
            w = get_window_by_sdl_id(event.window.windowID)
            if w != None and not w.focused and not w.is_closed:
                w.focus()
                w.redraw()
                internal_update_text_events()
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
                internal_update_text_events()
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
            loading_screen_fix()
            w = get_window_by_sdl_id(event.window.windowID)
            if w != None and w.hidden and not w.is_closed:
                w.set_hidden(False)
    elif (event.type == sdl.SDL_APP_DIDENTERBACKGROUND):
        logdebug("APP BACKGROUND EVENT.")
        if sdl.SDL_GetPlatform().decode("utf-8", "replace").\
                lower() == "android":
            dump_renderers = config.get(
                "recreate_renderer_when_in_background")
            if dump_renderers:
                logdebug("ANDROID IN BACKGROUND. DUMP ALL WINDOW RENDERERS.")
                for w_ref in all_windows:
                    w = w_ref()
                    if w != None:
                        if w.focused:
                            w.unfocus()
                        w.handle_sdlw_close()
            else:
                logdebug("ANDROIND IN BACKGROUND. KEEPING RENDERERS AS " +
                    "PER CONFIG OPTION. (not recommended)")
    elif (event.type == sdl.SDL_APP_WILLENTERFOREGROUND):
        logdebug("APP RESUME EVENT")
        for w_ref in all_windows:
            w = w_ref()
            if w != None and not w.is_closed:
                w.internal_app_reopen()
    elif (event.type == sdl.SDL_APP_DIDENTERFOREGROUND):
        loading_screen_fix()
    return True

