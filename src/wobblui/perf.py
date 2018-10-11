
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
        return cls._start_do(name, type="normal")

    @classmethod
    def _start_do(cls, name, type="normal", chain_step_name=None):
        now = time.monotonic()
        cls.lock.acquire()
        if type == "normal":
            cls.perf_id += 1
            perf_id = cls.perf_id
        else:
            perf_id = "chain_" + name
        if type == "normal":
            cls.perf_start_times[perf_id] = (type, name, now)
        elif type == "chain":
            if not perf_id in cls.perf_start_times or \
                    chain_step_name is None:
                cls.perf_start_times[perf_id] =\
                    (type, name, [])
            cls.perf_start_times[perf_id][2].append(
                (chain_step_name, now))
        else:
            raise RuntimeError("unknown perf type: " + str(type))
        cls.lock.release()
        return perf_id

    @classmethod
    def chain(cls, chain_name, step_name=None):
        return cls._start_do(chain_name,
            type="chain", chain_step_name=step_name)

    @classmethod
    def stop(cls, perf_id, debug=None, expected_max_duration=None,
            do_print=False):
        global config
        now = time.monotonic()
        cls.lock.acquire()
        if not perf_id in cls.perf_start_times:
            if "chain_" + perf_id in cls.perf_start_times:
                perf_id = "chain_" + perf_id
            else:
                raise ValueError("invalid perf id")
        is_chain = False
        if cls.perf_start_times[perf_id][0] == "normal":
            start_time = cls.perf_start_times[perf_id][2]
        elif cls.perf_start_times[perf_id][0] == "chain":
            is_chain = True
            start_time = cls.perf_start_times[perf_id][2][0][1]
        else:
            raise RuntimeError("unexpected perf type")
        perf_name = cls.perf_start_times[perf_id][1]
        duration = now - start_time
        if not perf_name in cls.perf_measurements:
            cls.perf_measurements[perf_name] = list()
        cls.perf_measurements[perf_name].append((now, duration))
        if len(cls.perf_measurements[perf_name]) > 40:
            cls.perf_measurements[perf_name] = \
                cls.perf_measurements[perf_name][20:]
        cls.lock.release()
        if config.get("perf_debug") or do_print:
            note = "" 
            if expected_max_duration != None:
                if (duration < expected_max_duration):
                    return
                note = "[SLOW]"
            v = str(round(duration * 1000000.0) / 1000.0)
            if not is_chain:
                logdebug("perf: " +
                    str(perf_name) + note + " -> " +
                    v + "ms" + ("" if (debug is None
                    or len(str(debug)) == 0) else "  " + str(debug))
                    )
            else:
                t = "perf[CHAIN]: " +\
                    str(perf_name) + note + " -> "
                i = 1
                while i < len(cls.perf_start_times[perf_id][2]):
                    time_diff = (cls.perf_start_times[perf_id][2][i][1] -
                        cls.perf_start_times[perf_id][2][i - 1][1])
                    step_name = cls.perf_start_times[perf_id][2][i][0]
                    t += str(step_name) + ":" +\
                        str(round(time_diff * 1000000.0) / 1000.0) + "ms "
                    i += 1
                t += "total:" + v + "ms" + ("" if (debug is None
                    or len(str(debug)) == 0) else "  " + str(debug))
                logdebug(t)

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

