
import copy
import threading
import time

from wobblui.uiconf import config

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
            print("wobblui.perf: " +
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

