
import time
import uuid

class ScheduledEvent(object):
    def __init__(self, func, time):
        self.identifier = str(uuid.uuid4())
        self.func = func
        self.time = float(time)

    def check(self):
        if self.time < time.monotonic():
            return True
        return False

    def __hash__(self):
        return hash(self.identifier)

    def __eq__(self, obj):
        if not hasattr(obj, "func") or \
                not hasattr(obj, "time"):
            return False
        if obj.func == self.func and \
                obj.id == self.id and \
                abs(obj.time - self.time) < 0.0001:
            return True
        return False

    def __call__(self):
        self.func()

scheduled_events = set()

def maximum_sleep_time():
    global scheduled_events
    sleep_time = None
    trigger_events = set()
    for event in scheduled_events:
        until = (event.time - time.monotonic())
        if sleep_time == None:
            sleep_time = until
        sleep_time = min(sleep_time, max(0.1, until))
    return sleep_time

def internal_trigger_check():
    global scheduled_events
    trigger_events = set()
    for event in scheduled_events:
        if event.check():
            trigger_events.add(event)
    for event in trigger_events:
        scheduled_events.discard(event)
        event()

def schedule(func, delay):
    global scheduled_events
    scheduled_events.add(ScheduledEvent(
        func, time.monotonic() + delay))

def schedule_at_absolute_time(func, ts):
    global scheduled_events
    scheduled_events.add(ScheduledEvent(
        func, ts))
 
