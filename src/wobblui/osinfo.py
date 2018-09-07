
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

from wobblui.sdlinit import initialize_sdl

cached_is_android = None
def is_android():
    global cached_is_android
    if cached_is_android != None:
        return cached_is_android
    initialize_sdl()
    import sdl2 as sdl
    cached_is_android = (sdl.SDL_GetPlatform().decode(
        "utf-8", "replace").lower() == "android")
    return cached_is_android
 
