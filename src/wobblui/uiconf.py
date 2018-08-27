
class Conf(object):
    def __init__(self):
        self.data = dict()

    def get(self, value):
        if not value in self.data:
            return self.get_default(value)
        return self.data[value]

    def set(self, key, value):
        self.data[key] = value

    def get_default(self, value):
        if value == "perf_debug":
            return False
        if value == "debug_events":
            return False
        if value == "debug_source_events":
            return False
        if value == "debug_file_dialog":
            return False
        if value == "doubleclick_time":
            return 0.4
        if value == "mouse_wheel_speed_modifier":
            return 1.2
        if value == "touch_longclick_time":
            return 1.1
        if value == "mouse_fakes_touch_events":
            return False

config = Conf()

