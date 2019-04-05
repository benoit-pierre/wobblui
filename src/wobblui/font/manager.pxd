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
cdef class FontManager:
    cdef int next_limit_cache_counter
    cdef public int cache_size
    cdef public object font_by_sizedpistyle_cache,\
        font_by_sizedpistyle_cache_times,\
        font_metrics_by_styledpi_cache,\
        load_debug_info_shown,\
        missing_fonts,\
        avg_letter_width_cache,\
        mutex

cdef FontManager c_font_manager()
