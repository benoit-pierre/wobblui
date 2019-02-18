
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

def set_clipboard_text(t):
    import sdl2 as sdl
    sdl.SDL_SetClipboardText(t.encode("utf-8", "ignore"))

def get_clipboard_text():
    import sdl2 as sdl
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
