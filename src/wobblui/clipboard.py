
import ctypes
import sdl2 as sdl

def set_clipboard_text(t):
    sdl.SDL_SetClipboardText(t.encode("utf-8", "ignore"))

def get_clipboard_text():
    paste_text_ptr = ctypes.c_char_p()
    old_restype = sdl.SDL_GetClipboardText.restype
    sdl.SDL_GetClipboardText.restype = ctypes.c_void_p
    paste_text_ptr = sdl.SDL_GetClipboardText()
    sdl.SDL_GetClipboardText.restype = old_restype
    if paste_text_ptr == 0:
        return
    paste_text = ctypes.cast(paste_text_ptr, ctypes.c_char_p).\
        value.decode("utf-8", "replace")
    sdl.SDL_free(paste_text_ptr)
    return paste_text
