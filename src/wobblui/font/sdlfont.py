
import ctypes
import queue
import sdl2.sdlttf as sdlttf
import threading

from wobblui.cache import KeyValueCache
from wobblui.sdlinit import initialize_sdl

class SDLFontSizeJob(object):
    def __init__(self, sdl_font, text):
        self.sdl_font = sdl_font
        self.text = text
        self.result = None
        self.result_waiter = threading.Event()

    def wait_for_done(self):
        self.result_waiter.wait()
        return self.result

    def execute(self):
        width = ctypes.c_int32()
        height = ctypes.c_int32()
        sdlttf.TTF_SizeUTF8(
            self.sdl_font.font, self.text,
            ctypes.byref(width), ctypes.byref(height))
        self.result = (int(width.value), int(height.value))
        self.result_waiter.set()

class SDLFontCloseJob(object):
    def __init__(self, sdl_font):
        self.sdl_font = sdl_font
        self.result_waiter = threading.Event()

    def wait_for_done(self):
        self.result_waiter.wait()
        return

    def execute(self):
        sdlttf.TTF_CloseFont(self.sdl_font.font)
        self.result_waiter.set()

def get_sdl_font(font_path, px_size):
    font = sdlttf.TTF_OpenFont(
        font_path.encode("utf-8"),
        px_size)
    if font is None:
        error_msg = sdlttf.TTF_GetError()
        raise ValueError("couldn't load TTF " +
            "font: " + str(error_msg))
    return SDLFontWrapper(font)

class SDLFontLoadJob(object):
    def __init__(self, font_path, px_size):
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

def get_thread_safe_render_size(sdl_ttf_font, text):
    size_job = SDLFontSizeJob(sdl_ttf_font, text)
    if is_main_thread():
        size_job.execute()
        return size_job.result
    else:
        job_queue.put(size_job)
        size_job.wait_for_done()
        return size_job.result

class SDLFontWrapper(object):
    def __init__(self, sdl_font):
        self.font = sdl_font

    def __del__(self):
        job_queue.put(SDLFontCloseJob(self))

ttf_was_initialized = False
def get_thread_safe_sdl_font(path, px_size):
    global ttf_was_initialized
    if not ttf_was_initialized:
        ttf_was_initialized = True
        initialize_sdl()
        sdlttf.TTF_Init()
    load_job = SDLFontLoadJob(path, px_size)
    if is_main_thread():
        load_job.execute()
        return load_job.result
    else:
        job_queue.put(load_job)
        job_queue.wait_for_done()
        return job_queue.result

