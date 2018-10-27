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

import ctypes
import queue
import sdl2.sdlttf as sdlttf
import threading

from wobblui.sdlinit import initialize_sdl

cdef int shutdown_in_progress = False
def stop_queue_for_process_shutdown():
    global shutdown_in_progress
    shutdown_in_progress = True

cdef class ThreadJob(object):
    cdef object result, result_waiter

    def __init__(self):
        self.result = None
        self.result_waiter = threading.Event()

    def wait_for_done(self):
        global shutdown_in_progress
        while True:
            if not self.result_waiter.wait(0.2) is True:
                if shutdown_in_progress:
                    raise SystemExit
                continue
            break
        return self.result

cdef class SDLFontSizeJob(ThreadJob):
    cdef object sdl_font
    cdef bytes text

    def __init__(self, object sdl_font, bytes text):
        super().__init__()
        self.sdl_font = sdl_font
        self.text = text

    def execute(self):
        width = ctypes.c_int32()
        height = ctypes.c_int32()
        sdlttf.TTF_SizeUTF8(
            self.sdl_font.font, self.text,
            ctypes.byref(width), ctypes.byref(height))
        self.result = (int(width.value), int(height.value))
        self.result_waiter.set()

cdef class SDLFontCloseJob(ThreadJob):
    cdef object font_ref

    def __init__(self, sdl_ttf_font_ref):
        super().__init__()
        self.font_ref = sdl_ttf_font_ref

    def execute(self):
        sdlttf.TTF_CloseFont(self.font_ref)
        self.result_waiter.set()

def get_sdl_font(str font_path, int px_size):
    font = sdlttf.TTF_OpenFont(
        font_path.encode("utf-8"),
        px_size)
    if font is None:
        error_msg = sdlttf.TTF_GetError()
        raise ValueError("couldn't load TTF " +
            "font: " + str(error_msg))
    return SDLFontWrapper(font, name=font_path, px_size=px_size)

cdef class SDLFontLoadJob(ThreadJob):
    cdef str font_path
    cdef int px_size

    def __init__(self, str font_path, int px_size):
        self.font_path = font_path
        self.px_size = max(1, round(px_size))
        self.result = None
        self.result_waiter = threading.Event()

    def wait_for_done(self):
        self.result_waiter.wait()
        return self.result

    def execute(self):
        try:
            self.result = get_sdl_font(
                self.font_path,
                self.px_size)
        except ValueError:
            pass
        self.result_waiter.set()

job_queue = queue.Queue()
def process_jobs():
    global job_queue
    processed_a_job = False
    while True:
        try:
            result = job_queue.get_nowait()
            processed_a_job = True
        except queue.Empty:
            break
        result.execute()
    return processed_a_job

def is_main_thread():
    return (threading.current_thread() == threading.main_thread())

def get_thread_safe_render_size(sdl_ttf_font, char* text):
    text_bytes = bytes(text)
    size_job = SDLFontSizeJob(sdl_ttf_font, text_bytes)
    if is_main_thread():
        size_job.execute()
        return size_job.result
    else:
        job_queue.put(size_job)
        size_job.wait_for_done()
        return size_job.result

class SDLFontWrapper(object):
    def __init__(self, object sdl_font, name=None, px_size=None):
        self.font = sdl_font
        self.name = name
        self.px_size = px_size

    def __repr__(self):
        return "<SDLFontWrapper name=" + str(self.name) +\
            " px_size=" + str(self.px_size) + ">"

    def __del__(self):
        job_queue.put(SDLFontCloseJob(self.font))

    def __dealloc__(self):
        job_queue.put(SDLFontCloseJob(self.font))

ttf_was_initialized = False
def get_thread_safe_sdl_font(path, px_size):
    global ttf_was_initialized
    if not ttf_was_initialized:
        ttf_was_initialized = True
        initialize_sdl()
        sdlttf.TTF_Init()
    load_job = SDLFontLoadJob(path, round(px_size))
    if is_main_thread():
        load_job.execute()
        return load_job.result
    else:
        job_queue.put(load_job)
        load_job.wait_for_done()
        return load_job.result

