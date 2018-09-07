
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

import sys
import time
import traceback
import uuid

from wobblui.woblog import logdebug, logerror, loginfo, logwarning

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
        try:
            self.func()
        except Exception as e:
            logerror("*** ERROR IN SCHEDULED TIMER FUNCTION ***")
            logerror(str(traceback.format_exc()))

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
    for event in trigger_events:
        event()

def schedule(func, delay):
    global scheduled_events
    scheduled_events.add(ScheduledEvent(
        func, time.monotonic() + delay))

def schedule_at_absolute_time(func, ts):
    global scheduled_events
    scheduled_events.add(ScheduledEvent(
        func, ts))
 
