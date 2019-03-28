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

import copy
import ctypes
import functools
from libc.stdint cimport uint32_t, int64_t
import math
import sys
import time
import traceback
import weakref

last_wid = -1
last_add = -1
_all_widgets = list()
_all_windows = list()


cpdef get_all_widgets():
    return _all_widgets


cpdef get_all_windows():
    return _all_windows


cpdef reduce_memory():
    global _all_widgets
    remove_refs = []
    for wref in _all_widgets:
        w = wref()
        if w is None:
            remove_refs.append(wref)
    for rref in remove_refs:
        _all_widgets.remove(rref)


cpdef int64_t focus_tab_index_sort(a, b):
    if a.focus_index is None and b.focus_index != None:
        return -1
    if b.focus_index is None and a.focus_index != None:
        return 1
    if a.focus_index != b.focus_index:
        return (a.focus_index - b.focus_index)
    return (a.added_order - b.added_order)


cpdef add_widget(widget):
    global _all_widgets
    _all_widgets.append(weakref.ref(widget))


cpdef get_widget_id():
    global last_wid
    last_wid += 1
    return last_wid


cpdef get_add_id():
    global last_add
    last_add += 1
    return last_add


