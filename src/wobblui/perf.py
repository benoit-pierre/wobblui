
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
import threading
import time

from wobblui.uiconf import config
from wobblui.woblog import logdebug, logerror, loginfo, logwarning

class Perf(object):
    perf_start_times = dict()
    perf_measurements = dict()
    perf_id = 0
    lock = threading.Lock()

    @classmethod
    def start(cls, name):
        now = time.monotonic()
        cls.lock.acquire()
        cls.perf_id += 1
        perf_id = cls.perf_id
        cls.perf_start_times[perf_id] = (now, name)
        cls.lock.release()
        return perf_id

    @classmethod
    def stop(cls, perf_id):
        global config
        now = time.monotonic()
        cls.lock.acquire()
        if not perf_id in cls.perf_start_times:
            raise ValueError("invalid perf id")
        start_time = cls.perf_start_times[perf_id][0]
        perf_name = cls.perf_start_times[perf_id][1]
        duration = now - start_time
        if not perf_name in cls.perf_measurements:
            cls.perf_measurements[perf_name] = list()
        cls.perf_measurements[perf_name].append((now, duration))
        if len(cls.perf_measurements[perf_name]) > 40:
            cls.perf_measurements[perf_name] = \
                cls.perf_measurements[perf_name][20:]
        cls.lock.release()
        if config.get("perf_debug"):
            v = str(round(duration * 10000000.0))
            while len(v) < 5:
                v = "0" + v
            v = v[:-4] + "." + v[-4:]
            logdebug("perf: " +
                str(perf_name) + " -> " +
                v + "ms")

    @staticmethod
    def values(cls, name, startswith=False):
        cls.lock.acquire()
        measurements = dict()
        for pname in cls.perf_measurements:
            if pname == name or (startswith and
                    pname.startswith(name)):
                measurements[pname] = copy.copy(
                    cls.perf_measurements[pname])
        cls.lock.release()
        return measurements

