#cython: language_level=3

'''
wobblui - Copyright 2018-2019 wobblui team, see AUTHORS.md

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

from libc.stdint cimport uintptr_t

from wobblui.uiconf import config
from wobblui.woblog import logdebug, logerror, loginfo, logwarning

cdef int renderer_lock = 0

cdef _internal_set_global_renderer_lock(int locked):
    global renderer_lock
    if locked and not renderer_lock:
        renderer_lock = True
        if config.get("debug_texture_collection_and_render_lock"):
            logdebug("render_lock: GLOBAL ENABLE")
    elif not locked and renderer_lock:
        renderer_lock = False
        if config.get("debug_texture_collection_and_render_lock"):
            logdebug("render_lock: GLOBAL DISABLE")


cpdef can_window_safely_use_its_renderer(window):
    return (not renderer_lock)

cpdef can_renderer_safely_be_used(uintptr_t renderer_addr):
    return (not renderer_lock)
