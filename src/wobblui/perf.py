
import copy
import threading
import time

PERF_DEBUG=True

class Perf(object):
    perf_start_times = dict()
    perf_measurements = dict()
    lock = threading.Lock()

    @classmethod
    def start(cls, name):
        now = time.monotonic()
        cls.lock.acquire()
        if not name in cls.perf_start_times:
            cls.perf_start_times[name] = [now]
        else:
            cls.perf_start_times[name].append(now)
        cls.lock.release()

    @classmethod
    def end(cls, name):
        now = time.monotonic()
        cls.lock.acquire()
        if not name in cls.perf_start_times or \
                len(cls.perf_start_times[name]) == 0:
            cls.lock.release()
            return
        start_time = cls.perf_start_times[name][-1]
        cls.perf_start_times[name] = cls.perf_start_times[name][:-1]
        if not name in cls.perf_measurements:
            cls.perf_measurements[name] = []
        duration = now - start_time
        cls.perf_measurements[name].append((now, duration))
        cls.lock.release()
        if PERF_DEBUG:
            v = str(round(duration * 10000000.0))
            while len(v) < 5:
                v = "0" + v
            v = v[:-4] + "." + v[-4:]
            print("wobblui.perf: " +
                str(name) + " -> " +
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

