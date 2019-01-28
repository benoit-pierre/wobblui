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

from wobblui.widget_base cimport WidgetBase
from wobblui.style import AppStyle

cdef class Window(WidgetBase):
    cdef object mouse_position_cache, _renderer, _style
    cdef public object _sdl_window  # accessed by multitouch code
    cdef int _hidden
    cdef public object hiding, shown, closing, destroyed
    cdef public object modal_filter
    cdef public int is_closed
    cdef str _title
    cdef int next_reopen_width, next_reopen_height
    cdef object last_known_dpi_scale, schedule_global_dpi_scale_update

cpdef apply_style_to_all_windows(object style)

cpdef get_focused_window()

cpdef change_dpi_scale_on_all_windows(new_dpi_scale)

cpdef get_window_by_sdl_id(sdl_id)


