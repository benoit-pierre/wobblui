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

import ctypes
import math
import os
import platform
import weakref

from wobblui.color cimport Color
from wobblui.dragselection import draw_drag_selection_handles
from wobblui.event cimport Event
import wobblui.font.manager
from wobblui.gfx cimport clear_renderer_gfx, draw_rectangle
from wobblui.osinfo import is_android
from wobblui.sdlinit cimport initialize_sdl
from wobblui.style import AppStyle, AppStyleBright, AppStyleDark
cimport wobblui.texture
from wobblui.uiconf import config
from wobblui.widget_base cimport WidgetBase
from wobblui.widgetman import get_all_widgets, get_all_windows
from wobblui.woblog cimport logdebug, logerror, loginfo, logwarning

cpdef get_focused_window():
    for w_ref in get_all_windows():
        w = w_ref()
        if w is None or not w.focused:
            continue
        return w
    return None

cpdef apply_style_to_all_windows(object style):
    style = style.copy()
    new_w_refs = []
    for w_ref in get_all_windows():
        w = w_ref()
        if w is None:
            continue
        new_w_refs.append(w_ref)
        w.style = style
    get_all_windows()[:] = new_w_refs
    trigger_global_style_changed()

cpdef change_dpi_scale_on_all_windows(new_dpi_scale):
    logdebug("manual DPI change triggered on all windows by " +
        "app. new scale is: " + str(new_dpi_scale) + ". " +
        "firing stylechanged() on all widgets...")
    styles_seen = dict()
    new_w_refs = []
    for w_ref in get_all_windows():
        w = w_ref()
        if w is None:
            continue
        new_w_refs.append(w_ref)
        if not w.style in styles_seen:
            w.style.dpi_scale = new_dpi_scale
            styles_seen[w.style] = w.style.copy()
        # Assign new copy of the style, to make sure the window and all
        # widgets realize it changed:
        w.style = styles_seen[w.style]
    get_all_windows()[:] = new_w_refs
    trigger_global_style_changed()

cpdef get_window_by_sdl_id(sdl_id):
    result = None
    seen = set()
    new_refs = []
    for w_ref in get_all_windows():
        w = w_ref()
        if w is None or w.sdl_window_id != int(sdl_id):
            if w != None:
                if str(id(w)) in seen:
                    logerror("Duplicate window in all_windows list: " +
                        str(w))
                seen.add(str(id(w)))
                new_refs.append(w_ref)
            continue
        result = w
        if str(id(w)) in seen:
            logerror("Duplicate window in all_windows list: " +
                str(w))
        seen.add(str(id(w)))
        new_refs.append(w_ref)
    get_all_windows()[:] = new_refs
    return result

cpdef trigger_global_style_changed():
    new_refs = []
    collected_widgets = []
    for w_ref in get_all_widgets():
        w = w_ref()
        if w is None:
            continue
        collected_widgets.append(w)
        new_refs.append(w_ref)
    get_all_widgets()[:] = new_refs
    for w in collected_widgets:
        w.stylechanged()

keep_alive_window_refs = []

cdef class Window(WidgetBase):
    def __init__(self,
            title="Untitled",
            width=640, height=480,
            style=None,
            fullscreen=False,
            stay_alive_without_ref=False,
            keep_application_running_while_open=True,
            ):
        self._renderer = None
        self.type = "window"
        initialize_sdl()
        if style is None:
            style = AppStyleBright()
        self.mouse_position_cache = dict()
        self._sdl_window = None
        self._style = style
        super().__init__(is_container=True, can_get_focus=True)
        self._hidden = False
        self._width = width
        self._height = height
        self._fullscreen = fullscreen
        self.keep_application_running = keep_application_running_while_open
        self.hiding = Event("hiding", owner=self)
        self.shown = Event("shown", owner=self)
        self.closing = Event("closing", owner=self)
        self.destroyed = Event("destroyed", owner=self)
        self.modal_filter = None
        self.is_closed = False
        self._title = title
        self.next_reopen_width = width
        self.next_reopen_height = height
        self.internal_app_reopen()
        
        # Now that SDL window is open, we can access screen geometry:
        if self._sdl_window != None:
            import sdl2 as sdl
            scale = self.screen_based_scale()
            # Correct our initial size if not on android:
            if abs(scale - 1.0) > 0.1 and not is_android():
                logdebug("DPI-scaling new window by " + str(scale) + "x")
                self._width = round(width * scale)
                self._height = round(height * scale)
                sdl.SDL_SetWindowSize(self._sdl_window,
                    self._width, self._height)

        self.last_known_dpi_scale = None
        self.schedule_global_dpi_scale_update = False
        get_all_windows().append(weakref.ref(self))
        if stay_alive_without_ref:
            keep_alive_window_refs.append(self)

    @property
    def fullscreen(self):
        if is_android():
            return (os.environ.get(
                    "P4A_IS_WINDOWED", "false"
            ).lower().strip() in {"0", "false", "no", "off"})
        return self._fullscreen

    def screen_based_scale(self):
        scale = 1.0
        (sw, sh) = self.containing_screen_dimensions()
        if (sw + sh) > ((1920 * 1080) * 0.9):
            # About 1080p / 2K:
            scale = max(scale, 1.5)
        elif (sw + sh) > ((2500 + 1500) * 0.9):
            # Between 2K and 3K:
            scale = max(scale, 1.7)
        elif (sw + sh) > ((3840 + 2160) * 0.9):
            # About 4K
            scale = max(scale, 2.0)
        return scale

    def get_window_dpi(self):
        guessed_scale = 1.0

        # --- SCREEN SIZE BASED GUESSING ---
        guessed_scale = max(guessed_scale, self.screen_based_scale())

        # --- WINDOW SIZE BASED GUESSING ---

        if not is_android():
            # If window is really large, just scale up nevertheless:
            if guessed_scale < 1.5 and self.width > 2000 and \
                    self.height > 1100:
                guessed_scale = max(guessed_scale, 1.5)
            if guessed_scale < 1.5 and self.width > 3000 and \
                    self.height > 1800:
                guessed_scale = max(guessed_scale, 2.0)
        else:
            if guessed_scale < 1.5 and (self.width +
                    self.height) > (1300 + 1000):
                guessed_scale = max(guessed_scale, 1.5)
            if guessed_scale < 1.8 and (self.width + self.height) >\
                    (1800 + 1000):
                guessed_scale = max(guessed_scale, 1.8)

        # On android, always scale up some more:
        if is_android():
            guessed_scale *= 1.4

        # If this changed anything, inform everything after we bailed
        # out of this function back into the global main loop:
        if self.last_known_dpi_scale != guessed_scale:
            logdebug("window.py: scheduling global style update " +
                "because of DPI change " +
                str(self.last_known_dpi_scale) +
                " -> " + str(guessed_scale) +
                " in window: " + str(self))
            self.last_known_dpi_scale = guessed_scale
            self.schedule_global_dpi_scale_update = True

        return guessed_scale   
 
    def do_scheduled_dpi_scale_update(self):
        if not self.schedule_global_dpi_scale_update:
            return
        self.schedule_global_dpi_scale_update = False
        logdebug("window.py: processing global style update, " +
            "firing stylechanged() on all widgets")
        # Update window layout and style of all widgets
        self.needs_relayout = True
        trigger_global_style_changed()

    def clear(self):
        old_renderer = self._renderer
        self._renderer = None
        for child in self.children:
            child.renderer_update()
            if child.parent == self:
                child.internal_override_parent(None)
        self._children = []
        self._context_menu = None
        assert(len(self.children) == 0)
        self._renderer = old_renderer
        self.update()

    def on_renderer_to_be_destroyed(self):
        """ Called when a renderer will be destroyed. This will
            clear out all textures to avoid a crash. """

        if self._renderer is None:
            return

        logdebug("Window: renderer loss on " + str(self) +
            " (renderer address: " +
            str(ctypes.addressof(self._renderer.contents))
            + ")")
        wobblui.texture.mark_textures_invalid(self._renderer)
        wobblui.font.manager.Font.clear_global_cache_textures()
        old_renderer = self._renderer
        self._renderer = None
        def recursive_renderer_update(item):
            item.renderer_update()
            for child in item.children:
                recursive_renderer_update(child)
        for child in self.children:
            recursive_renderer_update(child)
        clear_renderer_gfx(old_renderer)
        self._renderer = old_renderer
        if self.internal_render_target != None:
            if config.get("debug_texture_references"):
                logdebug("Window.on_renderer_to_be_destroyed: " +
                    "DUMPED self.internal_render_target")
            self.internal_render_target._force_unload()
            self.internal_render_target = None
        logdebug("Renderer loss processed.")

    def ensure_renderer(self):
        import sdl2 as sdl
        if self._sdl_window is None or not self._sdl_window:
            return
        if self._renderer is None:
            if config.get("software_renderer"):
                self._renderer = \
                    sdl.SDL_CreateRenderer(self._sdl_window, -1,
                        sdl.SDL_RENDERER_SOFTWARE)
            else:
                self._renderer = \
                    sdl.SDL_CreateRenderer(self._sdl_window, -1,
                        sdl.SDL_RENDERER_ACCELERATED)
            if self._renderer != None and not self._renderer:
                # Renderer is a null pointer. Void it again.
                self._renderer = None
                # We need to wait until we get focused and get another
                # chance to set a proper renderer.
                return False
            logdebug("Window: created renderer with address " +
                str(ctypes.addressof(self._renderer.contents)) +
                " for " + str(self))
            self.needs_redraw = True
        return (self._renderer is not None)

    @property
    def context_menu(self):
        return self._context_menu

    def close_context_menu(self):
        self.context_menu.internal_override_parent(None)
        self._context_menu = None
        self.needs_redraw = True

    def open_context_menu(self, menu, xpos, ypos, autofocus=True):
        self._context_menu = menu
        menu.internal_override_parent(self)
        self.needs_redraw = True
        self.context_menu.width = self.context_menu.get_desired_width()
        self.context_menu.height = self.context_menu.get_desired_height(
            given_width=self.context_menu.width
        )
        self.context_menu.needs_redraw = True
        def close_menu():
            self.close_context_menu()
        if autofocus:
            self.context_menu.focus()
            try:
                self.context_menu.unfocus.register(close_menu)
            except AttributeError:
                pass
        try:
            self.context_menu.triggered.register(close_menu)
        except AttributeError:
            pass
        self.context_menu.x = xpos
        self.context_menu.y = ypos

    def internal_app_reopen(self):
        import sdl2 as sdl
        if self.is_closed:
            return
        unhide = False
        if self._sdl_window is None:
            if platform.system().lower() == "windows":
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            wwidth = self.next_reopen_width
            wheight = self.next_reopen_height
            fullscreen_flag = 0
            if self.fullscreen:
                # Make sure window size is not too large to cause error
                # (since it's ignored when fullscreen but can still cause
                # an error when too large according to SDL2 docs)
                wwidth = 100
                wheight = 100
                if is_android():
                    fullscreen_flag = sdl.SDL_WINDOW_FULLSCREEN
                else:
                    fullscreen_flag = sdl.SDL_WINDOW_FULLSCREEN_DESKTOP
            self._sdl_window = sdl.SDL_CreateWindow(
                self._title.encode("utf-8", "replace"),
                sdl.SDL_WINDOWPOS_CENTERED, sdl.SDL_WINDOWPOS_CENTERED,
                wwidth, wheight,
                sdl.SDL_WINDOW_SHOWN | sdl.SDL_WINDOW_RESIZABLE |
                sdl.SDL_WINDOW_ALLOW_HIGHDPI | fullscreen_flag
            )
            unhide = True
            if self._renderer != None:
                self.on_renderer_to_be_destroyed()
                sdl.SDL_DestroyRenderer(self._renderer)
                self._renderer = None
        if not self.ensure_renderer():
            # Ooops. well, nothing we can do.
            # (Can happen e.g. when on android and in background)
            return
        self.update_to_real_sdlw_size()
        for child in self.children:
            child.renderer_update()
        if unhide:
            self.set_hidden(False)
        self.redraw_if_necessary()

    def __dealloc__(self):
        try:
            if self._sdl_window is not None:
                self.close()
        finally:
            try:
                super().__dealloc__()
            except AttributeError:
                pass

    def close(self):
        global keep_alive_window_refs
        if self in keep_alive_window_refs:
            keep_alive_window_refs.remove(self)
        if self._sdl_window is None:
            return
        self.is_closed = True
        try:
            self.handle_sdlw_close(forced=True)
        finally:
            self._sdl_window = None

    def handle_sdlw_close(self, forced=False):
        import sdl2 as sdl
        if self._sdl_window is None:
            return
        self.next_reopen_width = self._width
        self.next_reopen_height = self._height

        close_window = False
        if sdl.SDL_GetPlatform().decode("utf-8",
                "replace").lower() != "android":
            if self.closing() or forced:
                logdebug("Window: regular close on " + str(self))
                close_window = True
            else:
                logdebug("Window: REJECTED close on " + str(self))
                return 
            self.set_hidden(True)
        else:
            logdebug("Window: android window hide on " + str(self))
            if self.focused:
                self.unfocus()
            self.set_hidden(True)

        if close_window or sdl.SDL_GetPlatform().decode("utf-8",
                "replace").lower() == "android":
            if self._renderer != None:
                self.on_renderer_to_be_destroyed()
                sdl.SDL_DestroyRenderer(self._renderer)
                self._renderer = None
                for child in self.children:
                    if close_window:
                        if child.parent == self:
                            child.internal_override_parent(None)
            self._renderer = None
            if close_window:
                if self._sdl_window != None:
                    sdl.SDL_DestroyWindow(self._sdl_window)
                self._sdl_window = None
                self.is_closed = True
                self._children = []
                self.destroyed()
            else:
                # Keep it around to be reopened.
                logdebug("Window: renderer dumped, waiting for resume")
                return

    def get_mouse_pos(self, mouse_id):
        if not mouse_id in self.mouse_position_cache:
            return (0, 0)
        return self.mouse_position_cache[mouse_id]

    def _internal_on_mousemove(self, mouse_id, x, y, internal_data=None):
        super()._internal_on_mousemove(mouse_id, x, y,
            internal_data=internal_data)
        self.mouse_position_cache[mouse_id] = (x, y)

    def _internal_on_keydown(self, key, physical_key, modifiers,
            internal_data=None):
        focused_widget = WidgetBase.get_focused_widget_by_window(self)
        if focused_widget is None or \
                focused_widget.keydown(key, physical_key, modifiers):
            # Event was not stopped in user handler. Process focus:
            if key == "tab" and focused_widget != None:
                if not "shift" in modifiers and \
                        hasattr(focused_widget, "focus_next"):
                    focused_widget.focus_next()
                    
                elif "shift" in modifiers and \
                        hasattr(focused_widget, "focus_previous"):
                    focused_widget.focus_previous()
                focused_widget.needs_redraw = True
                new_focused_widget = \
                    WidgetBase.get_focused_widget_by_window(self)
                new_focused_widget.needs_redraw = True

    def _internal_on_textinput(self, text, modifiers, internal_data=None):
        focused_widget = WidgetBase.get_focused_widget_by_window(self)
        if focused_widget != None and focused_widget.takes_text_input:
            focused_widget.textinput(text, modifiers)

    def focus_first_item(self):
        focused_widget = WidgetBase.get_focused_widget_by_window(self)
        if focused_widget != None:
            focused_widget.unfocus()
        self.focus_update()

    def focus_update(self):
        if len(self.children) > 0 and \
                WidgetBase.get_focused_widget_by_window(self) is None:
            sorted_candidates = self.__class__.focus_candidates(
                self.children)
            if len(sorted_candidates) > 0:
                sorted_candidates[0].focus()

    def _internal_on_focus(self, internal_data=None):
        self.focus_update()

    def get_screen_offset(self):
        if not hasattr(self, "_sdl_window") or self._sdl_window is None:
            if hasattr(self, "_last_sdl_coordinates_x"):
                return (self._last_sdl_coordinates_x,
                    self._last_sdl_coordinates_y)
            return (0, 0)
        import sdl2 as sdl
        x = ctypes.c_int32()
        y = ctypes.c_int32()
        sdl.SDL_GetWindowPosition(self._sdl_window,
            ctypes.byref(x), ctypes.byref(y))
        factor = self.get_sdl_incorrect_scaling_correction_factor()
        x = round(float(x.value) * factor)
        y = round(float(y.value) * factor)
        self._last_sdl_coordinates_x = x
        self._last_sdl_coordinates_y = y
        return (x, y) 

    def containing_screen_dimensions(self):
        if self._sdl_window is None:
            return (0, 0)
        import sdl2 as sdl
        screen_mode = sdl.SDL_DisplayMode()
        result = sdl.SDL_GetCurrentDisplayMode(self.screen_index,
            ctypes.byref(screen_mode))
        if result != 0:
            raise RuntimeError("unexpected failure to get " +
                "current display mode")
        return (int(screen_mode.w), int(screen_mode.h))

    @property
    def screen_index(self):
        if self._sdl_window is None:
            return 0
        import sdl2 as sdl
        return sdl.SDL_GetWindowDisplayIndex(self._sdl_window)

    def get_sdl_incorrect_scaling_correction_factor(self):
        """ Because the SDL window API appears to be occasionally stupid
            and return coordinates not in actual pixels, this function
            returns the factor internally used to correct this.

            Please note .width/.height and .get_screen_offset() already use
            this internally to correct things, so you don't need to bother
            to do this manually.
        """
        import sdl2 as sdl

        w = ctypes.c_int32()
        h = ctypes.c_int32()
        sdl.SDL_GetWindowSize(self._sdl_window, ctypes.byref(w),
            ctypes.byref(h))
        if self._renderer != None:
            w2 = ctypes.c_int32()
            h2 = ctypes.c_int32()
            if sdl.SDL_GetRendererOutputSize(self._renderer,
                    ctypes.byref(w2), ctypes.byref(h2)) != 0:
                raise RuntimeError("unexpected failure to " +
                    "get renderer size")
            self._sdl_last_wrong_scaling_factor = max(
                float(w2.value) / float(w.value),
                float(h2.value) / float(h.value))
        elif hasattr(self, "_sdl_last_wrong_scaling_factor"):
            return self._sdl_last_wrong_scaling_factor
        else:
            return 1.0  # likely wrong, but nothing we can do
        return self._sdl_last_wrong_scaling_factor

    def update_to_real_sdlw_size(self):
        if self._sdl_window is None:
            return
        import sdl2 as sdl
        w = ctypes.c_int32()
        h = ctypes.c_int32()
        sdl.SDL_GetWindowSize(self._sdl_window, ctypes.byref(w),
            ctypes.byref(h))
        if self._renderer is not None:
            w2 = ctypes.c_int32()
            h2 = ctypes.c_int32()
            if sdl.SDL_GetRendererOutputSize(self._renderer,
                    ctypes.byref(w2), ctypes.byref(h2)) != 0:
                # If we can't get the renderer size, we're probably
                # in the background. This can happen on Android when
                # tabbing out of the app right as it tries to launch
                pass
            else:
                w = w2
                h = h2
        if self._width != w.value or self._height != h.value:
            self._width = w.value
            self._height = h.value
            self.resized()
            self.needs_redraw = True
            self.needs_relayout = True

    def set_modal_filter(self, func):
        if self.modal_filter != None and func != None:
            raise RuntimeError("cannot set modal filter, " +
                "already one set")
        self.modal_filter = func
        focused_widget = WidgetBase.get_focused_widget_by_window(self)
        if focused_widget != None and not focused_widget.focusable:
            focused_widget.unfocus()
            self.focus_update()

    def get_style(self):
        return self._style

    def set_style(self, style):
        self._style = style.copy()
        self.needs_relayout = True
        self.recursive_needs_redraw()
        self.redraw()

    @property
    def sdl_window_id(self):
        if self._sdl_window is None:
            return None
        import sdl2 as sdl
        return int(sdl.SDL_GetWindowID(self._sdl_window))

    @property
    def hidden(self):
        return (self._hidden or self.is_closed)

    def set_hidden(self, new_status):
        new_status = (new_status is True)
        if new_status != self._hidden:
            self._hidden = new_status
            if self.focused and self.hidden:
                self.unfocus()
            if self.hidden:
                self.hiding()
            else:
                self.shown()

    def add(self, *args, **kwargs):
        return_value = super().add(*args, **kwargs)
        if len(self._children) > 0:
            self.focus_update()
        return return_value

    def do_redraw(self):
        if not self.ensure_renderer():
            return

        # Work around potential SDL bug / race condition
        # (flickering window background)
        c = Color.white
        if self.style != None:
            c = Color(self.style.get("window_bg"))
        draw_rectangle(self.renderer, 0, 0,
            self.width, self.height, color=c)

        self.draw_children()
        draw_drag_selection_handles(self)

    def _internal_on_resized(self, internal_data=None):
        self.needs_relayout = True
        for w_ref in get_all_widgets():
            w = w_ref()
            if w is None or not hasattr(w, "parent_window") or \
                    w.parent_window != self:
                continue
            if hasattr(w, "parentwindowresized"):
                w.parentwindowresized()
        for child in self._children:
            child.needs_relayout = True

    def on_relayout(self):
        changed = False
        if len(self._children) > 0:
            # Make first child fill out the window:
            self._children[0].x = 0
            self._children[0].y = 0
            if self.width != self._children[0].width:
                self._children[0].width = self.width
                changed = True
            if self.height != self._children[0].height:
                self._children[0].height = self.height
                changed = True

            # Let the others float about, but shrink them to
            # window size:
            for child in self._children[1:]:
                child.x = max(0, min(math.floor(self.width) - 1,
                    child.x))
                child.y = max(0, min(math.floor(self.height) - 1,
                    child.y))
                intended_w = min(child.width,
                    max(1, math.floor(self.width) - child.x))
                if child.width != intended_w:
                    changed = True
                    child.width = intended_w
                intended_h = min(child.height,
                    max(1, math.floor(self.height) - child.y))
                if child.height != intended_h:
                    changed = True
                    child.height = intended_h
        if changed:
            self.needs_redraw = True

    def get_children_in_strict_mouse_event_order(self):
        r = list(reversed(self.get_children()))
        return r

    def get_children(self):
        r = list(self._children)
        if self.context_menu is not None:
            r += [self.context_menu]
        return list(r)

    def _internal_on_post_redraw(self, internal_data=None):
        import sdl2 as sdl
        if self.renderer is None:
            return
        elif self.needs_redraw:
            raise RuntimeError("still needing redraw in post " +
                "redraw, this may lead to an infinite loop")
        # Work around double/triple buffering issues by drawing repeatedly:
        i = 0
        while i < 3:
            sdl.SDL_SetRenderTarget(self.renderer, None)
            c = Color.white
            if self.style != None:
                c = Color(self.style.get("window_bg"))
            sdl.SDL_SetRenderDrawColor(self.renderer,
                c.value_red,
                c.value_blue, c.value_green, 255)
            sdl.SDL_RenderClear(self.renderer)

            # Work around potential SDL bug / race condition:
            # (Flickering texture contents of window)
            draw_rectangle(self.renderer, 0, 0,
                self.width, self.height, color=c)
            if self.internal_render_target != None:
                self.draw(0, 0)
            sdl.SDL_RenderPresent(self.renderer)
            i += 1

    def get_renderer(self):
        return self._renderer

    def shares_focus_group(self, other_obj):
        if not isinstance(other_obj, Window):
            return False
        return True
