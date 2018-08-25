
class Conf(object):
    def get(self, value):
        if value == "doubleclick_time":
            return 0.4
        if value == "mouse_wheel_speed_modifier":
            return 1.2
        if value == "touch_longclick_time":
            return 1.1

config = Conf()

