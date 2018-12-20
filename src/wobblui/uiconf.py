
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
        if value == "capture_debug":
            return False
        if value == "software_renderer":
            return True
        if value == "recreate_renderer_when_in_background":
            return False
        if value == "perf_debug":
            return False
        if value == "debug_core_event_loop":
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
        if value == "touch_shortclick_time":
            return 0.2
        if value == "touch_longclick_time":
            return 1.1
        if value == "mouse_fakes_touch_events":
            return False
        if value == "debug_texture_references":
            return False

config = Conf()

