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

cpdef draw_rectangle(renderer, int x, int y, int w, int h,
        color=*,
        int filled=*, unfilled_border_thickness=*)

cpdef clear_renderer_gfx(renderer)

cpdef draw_dashed_line(
        object renderer,
        int x1, int y1, int x2, int y2,
        object color=*,
        double dash_length=*,
        double thickness=*)

cpdef draw_line(
    object renderer,
    int x1, int y1, int x2, int y2,
    object color=*,
    double thickness=*)

cpdef draw_font(renderer, text, x, y,
        font_family=*,
        px_size=*, bold=*, italic=*,
        color=*)

cpdef is_font_available(
    font_family,
    bold=*,
    italic=*
    )

cpdef get_draw_font_size(text,
        font_family=*,
        px_size=*, bold=*, italic=*,
        color=*)

cpdef push_render_clip(renderer, _x, _y, _w, _h)

cpdef pop_render_clip(renderer)

