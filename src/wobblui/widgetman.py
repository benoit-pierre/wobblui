
import copy
import ctypes
import functools
import math
import sdl2 as sdl
import sys
import time
import traceback
import weakref

last_wid = -1
last_add = -1
all_widgets = list()
all_windows = list()

def tab_sort(a, b):
    if a.focus_index is None and b.focus_index != None:
        return 1
    if b.focus_index is None and a.focus_index != None:
        return -1
    if a.focus_index != b.focus_index:
        return (a.focus_index - b.focus_index)
    return (a.added_order - b.added_order)

def add_widget(widget):
    global all_widgets
    all_widgets.append(weakref.ref(widget))

def get_widget_id():
    global last_wid
    last_wid += 1
    return last_wid

def get_add_id():
    global last_add
    last_add += 1
    return last_add


