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
import sdl2 as sdl
import sdl2.sdlttf as sdlttf

sdl_init_done = False
cpdef void initialize_sdl():
    global sdl_init_done
    if sdl_init_done:
        return
    sdl_init_done = True

    sdl.SDL_SetHintWithPriority(b"SDL_HINT_ORIENTATIONS",
        b"LandscapeLeft LandscapeRight Portrait PortraitUpsideDown",
        sdl.SDL_HINT_OVERRIDE)
    sdl.SDL_SetHintWithPriority(b"SDL_HINT_MOUSE_FOCUS_CLICKTHROUGH", b"1",
        sdl.SDL_HINT_OVERRIDE)
    sdl.SDL_SetHintWithPriority(
        b"SDL_HINT_RENDER_SCALE_QUALITY", b"2",
        sdl.SDL_HINT_OVERRIDE)
    subsystems = sdl.SDL_WasInit(sdl.SDL_INIT_EVERYTHING)
    if not (subsystems & sdl.SDL_INIT_VIDEO):
        sdl.SDL_Init(sdl.SDL_INIT_VIDEO|sdl.SDL_INIT_TIMER)

cpdef tuple sdl_version():
    v = sdl.SDL_version()
    sdl.SDL_GetVersion(ctypes.byref(v))
    return (int(v.major), int(v.minor), int(v.patch))
