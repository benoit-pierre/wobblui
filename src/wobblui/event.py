
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

import random
import sys

from wobblui.perf import Perf
from wobblui.uiconf import config
from wobblui.woblog import logdebug, logerror, loginfo, logwarning

DEBUG_EVENT=False

class Event(object):
    """ This is a generic event for use by any widgets.

        An event consists of a name, special callback functions
        that may trigger before or after the event, and an
        interface to register any sort of additional user callbacks
        as well as for triggering the event.

        How does it work?
        -----------------
        Create an instance of this class and assign it as a member
        of your widget:

           `self.myevent = Event("myevent", owner=self)`

        (self referring to your widget)

        This will have the following effects:

        1. You can now trigger `yourwidgetinstanced.myevent(args ...)`
           on your widget. This will trigger the event, and issue the
           callbacks. Any amount of positional arguments can be
           passed, as long as the callbacks take the same amount
           of arguments (including the on_myevent callback,
           see below)

        2. If your widget has an `on_myevent` member, it will be called
           as a callback once the event triggers.

        3. Any external user can register additional custom callbacks
           using: `yourwidget.on_myevent.register(my_callback).` All
           user callbacks run in the order they were registered.

           User registered callbacks will run **first** if the option
           `allow_preventing_widget_callback_by_user_callbacks` is
           `True` (the default). If any of these user callbacks returns
           `True` to indicate it handled the event, it will prevent
           the widget's own `on_myevent` callback, which runs **last**,
           and any other follow-up user callbacks from being called.

           If you don't want this behavor, set the option to `False`,
           and the order will **switch**: `on_myevent` will run first,
           and all user callbacks afterwards (and they can no longer
           prevent the widget's own event handling).

        Any errors in any of the callbacks will propagate, and stop
        event processing, apart from `special_post_event_func`: this is
        an optional special callback function to run after all other
        processing that will also run if an error happened before, with
        the error propagating *afterwards*.

        Similarly, `special_pre_event_func` can be provided and will
        in that case be triggered *before* the regular callback
        processing.

        Function signature:
        -------------------
        @param name the event's name
        @param owner the widget owning the event, on which
                     `on_<event's name>` will be called if that
                     member is present
        @param special_pre_event_func special additional callback to
                                      be run each time the event
                                      triggers, before regular processing
        @param special_post_event_func similar to special_pre_event_func,
                                       will run even if an error happened
                                       in regular callback processing,
                                       and cannot be prevented by any
                                       regular callback returning `True`
        @param allow_preventing_widget_callback_by_user_callbacks Control
                                       event order. See text above!
    """
    def __init__(self, name, owner=None,
            special_pre_event_func=None,
            special_post_event_func=None,
            allow_preventing_widget_callback_by_user_callbacks=True):
        self.name = name
        self.widget_must_get_event = \
            (not allow_preventing_widget_callback_by_user_callbacks)
        self.funcs = list()
        self.on_object = owner
        self._disabled = False
        self.special_post_event_func = special_post_event_func
        self.special_pre_event_func = special_pre_event_func

    """ Property whether the event is disabled. Disabled events will
        not do anything when triggered (no error, the trigger is just
        ignored).
    """
    @property
    def disabled(self):
        return self._disabled

    """ Register a custom callback that will be triggered when the
        event runs. Callbacks registered first will be called first.
        If any callback returns `True`, the later callbacks won't
        be called and processing will stop early.
    """
    def register(self, func):
        self.funcs.append(func)

    """ Disable the event. When an event is disabled, any triggering
        will simply be ignored.
    """
    def disable(self):
        self._disabled = True

    """ Re-enable the event. """
    def enable(self):
        self._disabled = False

    """ Clear all callbacks registered for this event. Use
        `unregister` if you want to unregister a specific callback
        instead.
    """
    def clear(self):
        self.funcs = list()

    """ Unregister a specific callback. Use `clear` if you want to
        clear all callbacks instead.
    """
    def unregister(self, func):
        found = False
        new_funcs = []
        for f in self.funcs:
            if f != func:
                new_funcs.append(f)
            else:
                found = True
        self.funcs = new_funcs
        if not found:
            raise ValueError("function was not registered")

    """ This handles the native widget callback `on_<eventname>`.
    """
    def native_widget_callback(self, *args,
            internal_data=None, only_internal=False):
        # Call the special internal callback function provided by a
        # few of the wobblui core widget (not meant to be used by
        # user-defined widgets, it's purely needed by e.g. the mouse
        # events for a more stable way to pass additional absolute
        # mouse coordinates and a bit of a hack)
        if self.on_object != None and \
                hasattr(self.on_object,
                "_internal_on_" + str(self.name)):
            result = getattr(self.on_object,
                "_internal_on_" + str(self.name))(*args,
                internal_data=internal_data)
            if result is True:
                return True
        # Call regular on_<eventname> callback:
        if self.on_object != None and \
                hasattr(self.on_object, "on_" + str(self.name)) and \
                not only_internal:
            try:
                result = getattr(self.on_object,
                    "on_" + str(self.name))(*args)
            except Exception as e:
                logerror("ERROR: Exception processing " +
                    "on_" + str(self.name) + " on " + str(self.on_object))
                raise e
            if result is True:
                return True
        return False


    """ Trigger the event, issuing all the callbacks. The internal
        event data is only for internal use by certain wobblui
        core widgets, and won't be passed to any of the callbacks.

        @param internal_data only used internally by core widgets
        @param user_callbacks_only only used in rare cases where you'd
                                   want to run an event's user callbacks,
                                   but not the core widget callbacks
                                   (needed e.g. by ContainerWithSlidingMenu
                                   due to its close bond to an inner Menu)
    """
    def __call__(self, *args, internal_data=None,
            user_callbacks_only=False):
        global config
        if config.get("debug_events") is True:
            logdebug("EVENT TRIGGER: " + str(self.name) +
                " ON " + str(self.on_object))
        perf_id = None
        if self.name == "redraw":
            perf_id = Perf.start("Event_redraw_" +
                str(self.on_object.__class__.__name__)
                if self.on_object != None else
                "<no_associated_object>")
        try:
            if self._disabled:
                return True
            # Trigger special pre-func if given:
            if self.special_pre_event_func != None and \
                    not user_callbacks_only:
                self.special_pre_event_func(*args,
                    internal_data=internal_data)
            # Regular callbacks:
            try:
                if self.widget_must_get_event and \
                        not user_callbacks_only:
                    # Special configuration where `on_<eventname>`
                    # is set to trigger first:
                    if self.native_widget_callback(*args,
                            internal_data=internal_data):
                        return False
                # Run user callbacks:
                for f in self.funcs:
                    result = f(*args)
                    if result is True:
                        # Callback claims to fully handle event on
                        # its own. Stop processing further callbacks
                        return False
                if not self.widget_must_get_event and \
                        not user_callbacks_only:
                    # Regular configuration where `on_<eventname>`
                    # triggers last (=preventable by user callbacks).
                    if self.native_widget_callback(*args,
                            internal_data=internal_data):
                        return False
                return True
            finally:
                # Run special post event func, even in case of error:
                if self.special_post_event_func != None and \
                        not user_callbacks_only:
                    self.special_post_event_func(*args,
                        internal_data=internal_data)
            return True
        finally:
            # Stop perf measurement.
            if perf_id != None:
                Perf.stop(perf_id)

class ForceDisabledDummyEvent(Event):
    """ This is a special variant that is always disabled. It's meant
        to be used for events that aren't available because the widget
        was instantiated in some configuration where this event makes
        no sense (e.g. widgets without native touch handling will have
        this for touch events).

        Using this event won't break any trigger calls so the widget
        can still support a uniform interface where this event is
        expected, but the user or anyone else will be prevented from
        ever enabling it & actually registering any working callbacks.
    """
    def __init__(self, name, owner=None):
        super().__init__(name, owner=owner)
        self.disable()    

    def enable(self):
        return

class InternalOnlyDummyEvent(Event):
    """ A special event type to indicate that this event is not
        supported by, or made publicly available by the widget,
        and registering to it is considered a user mistake - and
        will accordingly yield an error.

        Use this when a widget is explicitly meant to NOT support
        a given interface, unlike ForceDisabledDummyEvent.
        
        Please note triggering the event and the widget-owned
        callback `on_<eventname>` still work, so such an event
        may still be used internally, while explicitly not made
        available to an external user.
    """

    def register(self, func):
        raise TypeError("this type of event isn't supported " +
            "by the event owner")

    def __call__(self, *args, internal_data=None):
        global config
        if config.get("debug_events") is True:
            logdebug("EVENT TRIGGER: " + str(self.name) +
                " ON " + str(self.on_object))
        if self._disabled:
            return True
        if self.special_pre_event_func != None:
            self.special_pre_event_func(*args,
                internal_data=internal_data)
        try:
            if self.native_widget_callback(*args,
                    internal_data=internal_data,
                    only_internal=True):
                return False
        finally:
            if self.special_post_event_func != None:
                self.special_post_event_func(*args,
                    internal_data=internal_data)
        return True

