
import sys

from wobblui.uiconf import config

DEBUG_EVENT=False

class Event(object):
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

    @property
    def disabled(self):
        return self._disabled

    def register(self, func):
        self.funcs.append(func)

    def disable(self):
        self._disabled = True

    def enable(self):
        self._disabled = False

    def clear(self):
        self.funcs = list()

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

    def native_widget_callback(self, *args,
            internal_data=None, only_internal=False):
        if self.on_object != None and \
                hasattr(self.on_object,
                "_internal_on_" + str(self.name)):
            result = getattr(self.on_object,
                "_internal_on_" + str(self.name))(*args,
                internal_data=internal_data)
            if result is True:
                return True
        if self.on_object != None and \
                hasattr(self.on_object, "on_" + str(self.name)) and \
                not only_internal:
            try:
                result = getattr(self.on_object,
                    "on_" + str(self.name))(*args)
            except Exception as e:
                print("ERROR: Exception processing " +
                    "on_" + str(self.name) + " on " + str(self.on_object),
                    file=sys.stderr, flush=True)
                raise e
            if result is True:
                return True
        return False

    def __call__(self, *args, internal_data=None):
        global config
        if config.get("debug_events") is True:
            print("EVENT TRIGGER: " + str(self.name) +
                " ON " + str(self.on_object))
        if self._disabled:
            return True
        if self.special_pre_event_func != None:
            self.special_pre_event_func()
        try:
            if self.widget_must_get_event:
                if self.native_widget_callback(*args,
                        internal_data=internal_data):
                    return False
            for f in self.funcs:
                result = f(*args)
                if result is True:
                    return False
            if not self.widget_must_get_event:
                if self.native_widget_callback(*args,
                        internal_data=internal_data):
                    return False
            return True
        finally:
            if self.special_post_event_func != None:
                self.special_post_event_func()
        return True

class ForceDisabledDummyEvent(Event):
    def __init__(self, name, owner=None):
        super().__init__(name, owner=owner)
        self.disable()    

    def enable(self):
        return

class InternalOnlyDummyEvent(Event):
    def register(self, func):
        raise TypeError("this type of event isn't supported " +
            "by the event owner")

    def __call__(self, *args, internal_data=None):
        global config
        if config.get("debug_events") is True:
            print("EVENT TRIGGER: " + str(self.name) +
                " ON " + str(self.on_object))
        if self._disabled:
            return True
        if self.special_pre_event_func != None:
            self.special_pre_event_func()
        try:
            if self.native_widget_callback(*args,
                    internal_data=internal_data,
                    only_internal=True):
                return False
        finally:
            if self.special_post_event_func != None:
                self.special_post_event_func()
        return True

