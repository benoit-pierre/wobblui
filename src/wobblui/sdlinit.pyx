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

from wobblui.woblog import logdebug, logerror, loginfo, logwarning


def android_fix_softinput_mode():
    from android.runnable import run_on_ui_thread
    from jnius import autoclass
    @run_on_ui_thread
    def do_it():
        python_activity = \
            autoclass('org.kivy.android.PythonActivity').mActivity
        window = python_activity.getWindow()
        window.setSoftInputMode(16)  # SOFT_INPUT_ADJUST_RESIZE
    do_it()


sdl_init_done = False
cpdef void initialize_sdl():
    global sdl_init_done
    if sdl_init_done:
        return
    sdl_init_done = True

    import sdl2 as sdl

    loginfo("Setting SDL2 settings")
    sdl.SDL_SetHintWithPriority(
        b"SDL_MOUSE_FOCUS_CLICKTHROUGH", b"1",
        sdl.SDL_HINT_OVERRIDE
    )  # For proper multi window focus handling
    sdl.SDL_SetHintWithPriority(
        b"SDL_ANDROID_SEPARATE_MOUSE_AND_TOUCH", b"1",
        sdl.SDL_HINT_OVERRIDE,
    )  # legacy hint, but just to ensure we can support mouse on android
    sdl.SDL_SetHintWithPriority(
        b"SDL_ANDROID_BLOCK_ON_PAUSE", b"0",
        sdl.SDL_HINT_OVERRIDE,
    )
    sdl.SDL_SetHintWithPriority(
        b"SDL_MOUSE_TOUCH_EVENTS", b"0",
        sdl.SDL_HINT_OVERRIDE,
    )  # matches the default, but just to be sure (would cause duplicate
       # taps with woblbui!)
    sdl.SDL_SetHintWithPriority(
        b"SDL_TOUCH_MOUSE_EVENTS", b"1",
        sdl.SDL_HINT_OVERRIDE,
    )  # matches the default, but just to be sure (wobblui heavily relies on
       # SDL_TOUCH_MOUSEID!)
    sdl.SDL_SetHintWithPriority(
        b"SDL_ANDROID_TRAP_BACK_BUTTON", b"1",
        sdl.SDL_HINT_OVERRIDE
    )  # otherwise our app will just quit instead of allowing transitions
       # via escape/back key
    sdl.SDL_SetHintWithPriority(
        b"SDL_TIMER_RESOLUTION", b"0",
        sdl.SDL_HINT_OVERRIDE
    )  # Not really necessary even for games unless you're really adamant
       # about possible micro stutters, and saves battery
    sdl.SDL_SetHintWithPriority(
        b"SDL_RENDER_BATCHING", b"1",
        sdl.SDL_HINT_OVERRIDE
    )  # Should give us better perf
    sdl.SDL_SetHintWithPriority(
        b"SDL_RENDER_SCALE_QUALITY", b"1",
        sdl.SDL_HINT_OVERRIDE
    )
    subsystems = sdl.SDL_WasInit(sdl.SDL_INIT_EVERYTHING)
    if not (subsystems & sdl.SDL_INIT_VIDEO):
        loginfo("Calling SDL_Init")
        sdl.SDL_Init(sdl.SDL_INIT_VIDEO|sdl.SDL_INIT_TIMER|
                     sdl.SDL_INIT_EVENTS|sdl.SDL_INIT_HAPTIC|
                     sdl.SDL_INIT_GAMECONTROLLER)
    else:
        loginfo("NOT calling SDL_Init, already initialized")

    # On android, get the native Java activity and fix the soft input mode:
    if sdl.SDL_GetPlatform().lower() == b"android":
        logdebug("Setting initial SOFT_INPUT_ADJUST_RESIZE")
        android_fix_softinput_mode()


cpdef tuple sdl_version():
    import sdl2 as sdl
    v = sdl.SDL_version()
    sdl.SDL_GetVersion(ctypes.byref(v))
    return (int(v.major), int(v.minor), int(v.patch))
