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

from wobblui.scrollbarwidget cimport ScrollbarDrawingWidget

cdef class ListEntry:
    cdef public int with_visible_bg
    cdef public int _max_width
    cdef public object _cached_natural_width
    cdef public object _cached_render_tex
    cdef int _width
    cdef public object _style
    cdef str _html, _text
    cdef public object override_dpi_scale
    cdef public object extra_html_at_right
    cdef public double extra_html_at_right_scale
    cdef int extra_html_at_right_x
    cdef int extra_html_at_right_y
    cdef int extra_html_at_right_w
    cdef int extra_html_at_right_h
    cdef object extra_html_at_right_obj
    cdef double extra_html_at_right_padding
    cdef public object extra_html_as_subtitle
    cdef public double extra_html_as_subtitle_scale
    cdef int subtitle_x
    cdef int subtitle_y
    cdef int subtitle_w
    cdef int subtitle_h
    cdef int textoffset_x, textoffset_y
    cdef int iconoffset_x, iconoffset_y
    cdef object extra_html_as_subtitle_obj
    cdef double extra_html_as_subtitle_padding
    cdef public int disabled
    cdef public int is_alternating
    cdef public double px_size_scaler
    cdef public object text_obj
    cdef public int need_size_update
    cdef public int _height
    cdef public double effective_dpi_scale
    cdef public object y_offset  # can be None
    cdef public int text_width, text_height

    # Side icon:
    cdef public object side_icon
    cdef public int side_icon_or_space_width, side_icon_height
    cdef public int side_icon_or_space_left
    cdef public int side_icon_with_text_color

cdef class ListBase(ScrollbarDrawingWidget):
    cdef public object triggered
    cdef list _entries
    cdef int _selected_index, _hover_index
    cdef int scroll_y_offset
    cdef object usual_entry_height, last_known_effective_dpi_scale
    cdef public int render_as_menu, fixed_one_line_entries
    cdef object cached_natural_width
    cdef int triggered_by_single_click

cdef class List(ListBase):
    pass

