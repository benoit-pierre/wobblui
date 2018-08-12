
class Conf(object):
    def get(self, value):
        if value == "doubleclick_time":
            return 0.4

config = Conf()

