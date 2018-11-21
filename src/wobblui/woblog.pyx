#cython: language_level=3

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
import threading
import time

logmutex = threading.Lock()

cdef object log_callback = None
cpdef set_log_callback(callback):
    global log_callback
    log_callback = callback

cdef int log_do_print = True
cpdef set_log_print(int do_print):
    global log_do_print
    log_do_print = (do_print == True)

cdef _dolog(label, msg):
    if log_do_print:
        logmutex.acquire()
        try:
            if label != "error" and label != "warning":
                print("wobblog-" + str(label) + ": " + str(msg))
            else:
                print("wobblog-" + str(label) + ": " + str(msg),
                    file=sys.stderr, flush=True)
        finally:
            logmutex.release()
    if log_callback != None:
        try:
            log_callback(label, msg)
        except Exception as e:
            print("*** ERROR IN LOG CALLBACK: " + str(e),
                file=sys.stderr, flush=True)
            pass

cpdef logdebug(str arg):
    try:
        if _dolog != None:
            _dolog("debug", arg)
    except NameError:
        pass

cpdef logwarning(str arg):
    _dolog("warning", arg)

cpdef loginfo(str arg):
    _dolog("info", arg)

cpdef logerror(str arg):
    _dolog("error", arg)
