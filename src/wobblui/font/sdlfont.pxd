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

cpdef void stop_queue_for_process_shutdown()

cpdef int process_jobs()

cpdef int is_main_thread()

cdef class SDLFontWrapper:
    """ MEMBERS ARE IN font/sdlfont.pxd """

    cdef public object font
    cdef public str name
    cdef public int px_size

cpdef tuple get_thread_safe_render_size(sdl_ttf_font, char* text)

cpdef SDLFontWrapper get_thread_safe_sdl_font(path, px_size)
