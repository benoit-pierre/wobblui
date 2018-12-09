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

import copy
import ctypes
import html
import math
import sdl2 as sdl
import string
import sys
import threading
import time

from wobblui.color cimport Color
import wobblui.cssparse as cssparse
cimport wobblui.debug as debug
import nettools.htmlparse as htmlparse
from wobblui.font.manager cimport c_font_manager as font_manager
from wobblui.perf cimport CPerf as Perf
from wobblui.woblog cimport logdebug, logerror, loginfo, logwarning

class TagInfo(object):
    def __init__(self, tag_name, is_block=False):
        self.name = tag_name.lower()
        self.is_block = is_block

    def __eq__(self, other):
        if not isinstance(other, TagInfo) or\
                not hasattr(other, "name") or \
                not hasattr(other, "is_block"):
            return False
        if other.is_block == self.is_block and \
                other.name == self.name:
            return True
        return False

cdef class RichTextObj:
    cdef public int x, y, width, italic, bold, px_size
    cdef public double _draw_scale
    cdef public str font_family

    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = -1
        self.italic = False
        self.bold = False
        self.font_family = "Sans Serif"
        self.px_size = 12
        self._draw_scale = 1.0

    @property
    def draw_scale(self):
        return self._draw_scale

    @draw_scale.setter
    def draw_scale(self, v):
        self.update_to_draw_scale(v)
        self._draw_scale = v

    def update_to_draw_scale(self, v):
        pass

    def compute_height(self):
        raise RuntimeError("abstract function not implemented")

    @property
    def height(self):
        return self.compute_height()

    def copy(self):
        return copy.copy(self)

    def character_index_to_offset(self, c):
        if c == 0:
            (w, h) = self.get_font().render_size(" ")
            w = 0
        else:
            (w, h) = self.get_font().render_size(self.text[:c])
        y = 0
        x = w
        if self.x != None:
            x += self.x
        if self.y != None:
            y += self.y
        return (x, y, h)

    def draw(self, renderer, x, y, color=None, draw_scale=None):
        pass

    def get_font(self, draw_scale=None):
        if draw_scale is None:
            draw_scale = self.draw_scale
        font = font_manager().get_font(self.font_family,
            bold=self.bold, italic=self.italic,
            px_size=self.px_size,
            draw_scale=draw_scale)
        return font

    def __repr__(self):
        t = "<RichTextObj x:" + str(self.x) +\
            " y: " + str(self.y) + ">"
        return t

fragment_draw_rect = None
cdef class RichTextFragment(RichTextObj):
    cdef public object forced_text_color, surrounding_tags, align
    cdef object _cached_parts, _width_cache
    cdef int _cached_height
    cdef str _text

    def __init__(self, text, font_family, int bold, int italic,
            int px_size, surrounding_tags=[],
            str force_text_color=None):
        super().__init__()
        self.forced_text_color = None
        if force_text_color != None:
            self.forced_text_color = Color(force_text_color)
        self._text = text
        self.font_family = font_family
        self.bold = bold
        self.surrounding_tags = copy.copy(surrounding_tags)
        self.italic = italic
        self._cached_parts = None
        self.px_size = px_size
        self.align = None
        self._draw_scale = 1.0
        self._width_cache = dict()
        self._cached_height = -1

    def update_to_draw_scale(self, v):
        if abs(v - self._draw_scale) > 0.001:
            self._cached_height = -1
            self._width_cache = dict()

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, str v):
        self._cached_parts = None
        self._cached_height = -1
        self._width_cache = dict()
        self._text = str(v)

    def has_block_tag(self):
        for tag in self.surrounding_tags:
            if tag.is_block:
                return True
        return False

    def ensure_surrounding_tag(self, tag_name, is_block=False):
        if self.surrounded_in_tag_name(tag_name):
            return
        self.surrounding_tags.append(
            TagInfo(tag_name, is_block=is_block))

    def remove_surrounding_tag(self, tag_name):
        if not self.surrounded_in_tag_name(tag_name):
            return
        new_surrounding_tags = []
        for tag in self.surrounding_tags:
            if tag.name.lower() != tag_name.lower():
                new_surrounding_tags.append(tag)
        self.surrounding_tags = new_surrounding_tags

    def surrounded_in_heading(self):
        def is_digits(v):
            i = 0
            while i < len(v):
                if ord(v[i]) < ord("0") or \
                        ord(v[i]) > ord("9"):
                    return False
                i += 1
            return len(v) > 0
        for tag in self.surrounding_tags:
            if tag.name.lower()[0] == "h" and \
                    is_digits(tag.name[1:]):
                return True
        return False

    def surrounded_in_tag_name(self, tag_name):
        for tag in self.surrounding_tags:
            if tag.name.lower() == tag_name.lower():
                return True
        return False

    def __repr__(self):
        cdef str t = "<RichTextFragment '" +\
            str(self.text).replace("'", "'\"'\"'") + "'"
        if self.x != None or self.y != None:
            t += " x:" + str(self.x) +\
                " y: " + str(self.y)
        if self.forced_text_color != None:
            t += " color: " + str(self.forced_text_color.html)
        t += " draw_scale=" + str(self.draw_scale)
        t += " px_size=" + str(self.px_size) + ">"
        return t

    def draw(self, renderer, x, y, color=None, draw_scale=None):
        global fragment_draw_rect
        if len(self.text.strip()) == 0:
            return
        if fragment_draw_rect is None:
            fragment_draw_rect = sdl.SDL_Rect()
        perf_id = Perf.start("fragment draw part 1")
        if color is None:
            color = Color.black()
        if draw_scale is None:
            draw_scale = self._draw_scale
        font = self.get_font(draw_scale=draw_scale)
        if self.forced_text_color != None:
            color = self.forced_text_color
        Perf.stop(perf_id)
        perf_id = Perf.start("fragment draw part 2")
        tex = font.get_cached_rendered_texture(renderer, self.text)
        Perf.stop(perf_id)
        perf_id = Perf.start("fragment draw part 3")
        sdl.SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255)
        if self.forced_text_color is None:
            tex.set_color(color)
        else:
            tex.set_color(self.forced_text_color)
        tex.draw(round(x), round(y))
        Perf.stop(perf_id)

    def get_width(self):
        cdef int i = self.get_width_up_to_length(len(self.text))
        return i

    def get_width_up_to_length(self, int index):
        index = max(0, min(index, len(self.text)))
        if index in self._width_cache:
            return self._width_cache[index]
        cdef str text_part = self.text[:index]
        font = font_manager().get_font(self.font_family,
            bold=self.bold, italic=self.italic,
            px_size=self.px_size,
            draw_scale=self._draw_scale)
        cdef int w, h
        (w, h) = font.render_size(text_part)
        self._width_cache[index] = w
        return w

    def compute_height(self):
        if self._cached_height >= 0:
            return self._cached_height
        font = font_manager().get_font(self.font_family,
            bold=self.bold, italic=self.italic,
            px_size=self.px_size,
            draw_scale=self._draw_scale)
        cdef int w, h
        (w, h) = font.render_size(self.text)
        self._cached_height = max(0, h)
        return h

    def has_same_formatting_as(self, obj):
        if not isinstance(obj, RichTextFragment):
            return False
        if obj.font_family != self.font_family or \
                obj.bold != self.bold or \
                obj.italic != self.italic or \
                obj.forced_text_color != self.forced_text_color or \
                round(obj.px_size * 10.0) != round(self.px_size * 10.0):
            return False
        return True

    def to_html(self, previous_richtext_obj=None,
            next_richtext_obj=None):
        t = htmlparse.html_escape(self.text)
        if self.bold and not self.surrounded_in_heading():
            self.ensure_surrounding_tag("b")
        else:
            self.remove_surrounding_tag("b")
        if self.italic:
            self.ensure_surrounding_tag("i")
        else:
            self.remove_surrounding_tag("i")

        def previous_obj_forced_color():
            if previous_richtext_obj is None or \
                    not hasattr(previous_richtext_obj,
                    "forced_text_color"):
                return None
            return previous_richtext_obj.forced_text_color
        def next_obj_forced_color():
            if next_richtext_obj is None or \
                    not hasattr(next_richtext_obj,
                    "forced_text_color"):
                return None
            return next_richtext_obj.forced_text_color
        def next_has_tag(tag):
            if next_richtext_obj is None or \
                    not hasattr(next_richtext_obj,
                        "surrounding_tags") or \
                    not tag in next_richtext_obj.\
                        surrounding_tags:
                return False
            return True
        def previous_has_tag(tag):
            if previous_richtext_obj is None or \
                    not hasattr(previous_richtext_obj,
                        "surrounding_tags") or \
                    not tag in previous_richtext_obj.\
                        surrounding_tags:
                return False
            return True

        # Update virtual color <span> nesting:
        if self.forced_text_color != None:
            if previous_richtext_obj == None or \
                    previous_obj_forced_color() != self.forced_text_color:
                t = "<span style='color:" +\
                    Color(self.forced_text_color).html + "'>" + t
            if next_richtext_obj == None or \
                    next_obj_forced_color() != self.forced_text_color:
                t = t + "</span>"

        # Update element nesting:
        serialized_opening_tags = []
        serialized_closing_tags = []
        for tag in self.surrounding_tags:
            if not next_has_tag(tag):
                serialized_closing_tags.append("</" + tag.name + ">")
            if not previous_has_tag(tag):
                serialized_opening_tags.append("<" + tag.name + ">")
        for tag in reversed(serialized_opening_tags):
            t = tag + t
        for tag in reversed(serialized_closing_tags):
            t += tag
        return t

    @property
    def parts(self):
        if self._cached_parts != None:
            return self._cached_parts
        cdef int last_i = -1
        cdef str part, c

        # The characters we want to split at & a search regex for them
        cdef str split_before_chars = " \n\r"
        cdef str split_after_chars = ",.:!'\"-=?/\\"

        # Actually split at the characters given above:
        result = []
        cdef int i = 0
        while i < len(self.text):
            c = self.text[i]
            if c in split_after_chars or (i + 1 < len(self.text)
                    and self.text[i + 1] in split_before_chars):
                # Found a split!
                part = self.text[last_i + 1:i + 1]
                if len(part) > 0:
                    result.append(part)
                    last_i = i
            i += 1
        if last_i + 1 < i:
            part = self.text[last_i + 1:]
            if len(part) > 0:
                result.append(part)
        self._cached_parts = result
        return self._cached_parts

cdef class RichTextLinebreak(RichTextObj):
    cdef public str text

    def __init__(self):
        super().__init__()
        self.text = "\n"

    def __repr__(self):
        t = "<RichTextLinebreak x:" + str(self.x) +\
            " y: " + str(self.y) + ">"
        return t

    def character_index_to_offset(self, c):
        (w, h) = self.get_font().render_size(" ")
        if c == 0:
            return (self.x, self.y, h)
        return (0, self.y + h, h)

    def compute_height(self):
        return 0

    def to_html(self, previous_richtext_obj=None,
            next_richtext_obj=None):
        if hasattr(previous_richtext_obj,
                "has_block_tag") and \
                previous_richtext_obj.has_block_tag():
            # This is a visual line break after a block ->
            # omit.
            return ""
        if hasattr(previous_richtext_obj,
                "has_block_tag") and \
                not previous_richtext_obj.has_block_tag() and\
                hasattr(next_richtext_obj,
                "has_block_tag") and \
                next_richtext_obj.has_block_tag():
            # This is a visual line break after inline/before
            # block element. -> omit
            return ""
        return "<br/>"

cdef class RichText:
    """ MEMBERS ARE IN richtext.pxd """

    def __init__(self, text="", font_family="Tex Gyre Heros",
            px_size=12, draw_scale=1.0):
        super().__init__()
        self.default_font_family = font_family
        self._px_size = px_size
        self.draw_scale = draw_scale
        self.fragments = []
        if len(text) > 0:
            self.fragments.append(RichTextFragment(
                text, font_family, False, False, px_size))

    def __repr__(self):
        t = "<RichText html='"
        if len(self.html) < 40:
            t += self.html
        else:
            t += self.html[:40] + "..."
        t += "'>"
        return t

    def remove_char_before_offset(self, offset):
        self._cached_text = None
        c = offset - 1
        i = 0
        while i < len(self.fragments):
            fragment = self.fragments[i]
            if isinstance(fragment, RichTextLinebreak) and \
                    c == 0:
                self.fragments = self.fragments[:i] +\
                    self.fragments[i + 1:]
                return
            if c < len(fragment.text) or i == len(self.fragments) - 1:
                fragment.text = fragment.text[:c] +\
                    fragment.text[c + 1:]
                return
            c -= len(fragment.text)
            i += 1

    def insert_text_at_offset(self, offset, text):
        if len(self.fragments) == 0:
            self.set_text(text)
            return
        lines = text.replace("\r\n", "\n").\
            replace("\r", "\n").split("\n")
        if len(lines) == 0:
            return
        self._cached_text = None
        c = offset
        i = 0
        while i < len(self.fragments):
            fragment = self.fragments[i]
            if c < len(fragment.text) or i == len(self.fragments) - 1 or \
                    (c == len(fragment.text) and i < len(self.fragments) - 1
                    and isinstance(self.fragments[i + 1], RichTextLinebreak)):
                fragment_ending = ""
                insert_after = i
                k = 0
                if not isinstance(fragment, RichTextLinebreak):
                    # Insert first line directly into this text fragment,
                    # instead of making a separate new one:
                    fragment_ending = fragment.text[c:]
                    fragment.text = fragment.text[:c] + lines[0]
                    if len(lines) == 1:
                        fragment.text += fragment_ending
                    if len(fragment.text) == 0:
                        # Can happen when inserting '\n' at the start
                        # of a fragment (-> c=0, lines = ['', '']).
                        # When that happens: SCRAP fragment
                        self.fragments = self.fragments[:i] +\
                            self.fragments[i + 1:]
                        insert_after -= 1
                    k += 1  # don't reinsert first line later
                else:
                    # It's a linebreak. See where want to insert:
                    if c > 0:
                        # Insert AFTER linebreak.
                        insert_after = i
                    else:
                        # Insert BEFORE linebreak.
                        insert_after = i - 1

                # Insert all the lines:
                while k < len(lines):
                    inserted_line = []
                    if k > 0:
                        inserted_line = [RichTextLinebreak()]
                    if len(lines[k]) > 0 or (k == len(lines) - 1 and
                            len(fragment_ending) > 0):
                        fragment_text = lines[k]
                        if k == len(lines) - 1:
                            fragment_text += fragment_ending
                        font_family = self.default_font_family
                        px_size = self.px_size
                        bold = False
                        italic = False
                        if insert_after >= 0:
                            font_family = \
                                self.fragments[insert_after].font_family
                            pixel_size =\
                                self.fragments[insert_after].px_size
                            bold =\
                                self.fragments[insert_after].bold
                            italic =\
                                self.fragments[insert_after].italic
                        inserted_line += [RichTextFragment(
                            fragment_text, font_family, bold,
                            italic, px_size)]
                    self.fragments = self.fragments[:insert_after + 1] +\
                        inserted_line +\
                        self.fragments[insert_after + 1:]
                    insert_after += 1
                    k += 1
                return
            c -= len(fragment.text)
            i += 1

    @property
    def px_size(self):
        return self._px_size

    @px_size.setter
    def px_size(self, v):
        v = round(v)
        if self._px_size == v:
            return
        self._px_size = v
        self.set_html(self.html)

    def character_count(self):
        return len(self.text)

    def character_index_to_offset(self, c):
        i = 0
        while i < len(self.fragments):
            fragment = self.fragments[i]
            if c < len(fragment.text) or i == len(self.fragments) - 1:
                return fragment.character_index_to_offset(
                    max(0, min(len(fragment.text), c)))
            c -= len(fragment.text)
            i += 1
        obj = RichTextObj()
        obj.font_family = self.default_font_family
        obj.px_size = self.px_size
        obj.draw_scale = self.draw_scale
        (w, h) = obj.get_font().render_size(" ")
        return (0, 0, h)

    def draw(self, renderer, int x, int y, color=None, draw_scale=None):
        assert(renderer != None)
        for fragment in self.fragments:
            if isinstance(fragment, RichTextLinebreak):
                continue
            assert(fragment != None)
            fragment.draw(renderer, fragment.x + x, fragment.y + y,
                color=color, draw_scale=draw_scale)

    def copy(self):
        new_text = copy.copy(self)
        new_text.fragments = [fragment.copy()
            for fragment in self.fragments]
        return new_text

    def layout(self, max_width=None, align_if_none=None,
            bailout_func=None):
        if max_width is not None and max_width < 1:
            max_width = 1
        if max_width is None:
            max_width = -1
        return self._layout_internal(max_width, align_if_none, bailout_func)

    def _layout_internal(self, int max_width, align_if_none,
            bailout_func):
        perf_id = Perf.start("richtext_layout")
        perf_1 = Perf.start("richtext_layout_1")
        self.simplify()
        layouted_elements = []
        layout_line_indexes = []
        cdef int current_line_elements = 0
        cdef int layout_w = 0
        cdef int layout_h = 0
        cdef int current_x = 0
        cdef int current_y = 0
        cdef int max_height_seen_in_line = -1
        left_over_fragment = None

        # Helper function to start a new line:
        def add_line_break():
            nonlocal current_x, current_y, \
                current_line_elements,\
                max_height_seen_in_line,\
                layout_w, layout_h
            cdef int clen, forawrd_start, substract_ending
            if current_line_elements > 0:
                clen = len(layouted_elements)
                assert(clen > 0)
                forward_start = 0
                if isinstance(
                        layouted_elements[clen - current_line_elements],
                        RichTextLinebreak):
                    forward_start = 1
                substract_ending = 0
                if isinstance(layouted_elements[-1], RichTextLinebreak):
                    substract_ending = 1
                layout_line_indexes.append((
                    clen - current_line_elements + forward_start,
                    clen - substract_ending))
            line_alignment = None
            current_x = 0
            if max_height_seen_in_line >= 0:
                current_y += max_height_seen_in_line
            else:
                current_y += max(1, font_manager().get_font(
                    self.default_font_family,
                    draw_scale=self.draw_scale,
                    px_size=self.px_size).\
                    render_size(" ")[1])
            layout_h = max(layout_h, current_y)
            max_height_seen_in_line = -1
            current_line_elements = 0

        # Helper function to shift elements in a specific line to
        # adapt to different alignments:
        def adjust_line_alignment(int start_index, int end_index):
            nonlocal current_line_elements, layout_w, layouted_elements
            line_alignment = None
            cdef int elements_width = 0
            cdef int k = start_index
            while k < end_index:
                if hasattr(layouted_elements[k], "align") and \
                        layouted_elements[k].align != None:
                    line_alignment = layouted_elements[k].align
                elements_width += layouted_elements[k].width
                k += 1
            if line_alignment is None:
                line_alignment = align_if_none
            if line_alignment == "left" or line_alignment == None:
                return
            cdef int align_to_width = (max_width
                                       if max_width >= 0 else layout_w)
            layout_w = align_to_width
            cdef int shift_space = max(0, align_to_width - elements_width)
            if line_alignment == "center" or line_alignment == "right":
                shift_width = shift_space
                if line_alignment == "center":
                    shift_width = max(round(shift_width / 2.0), 0)
                k = start_index
                while k < end_index:
                    layouted_elements[k].x += shift_width
                    k += 1
                return

        Perf.stop(perf_1)
        perf_1 = Perf.start("fragment loop")

        # Variables for outer fragment loop:
        cdef int fragment_count = len(self.fragments)
        cdef int prev_i = -1
        cdef double stuck_warning_start_time = time.monotonic()
        cdef int i = 0

        # Variables for inner fitting loop:
        cdef int partial = False
        cdef int letters = -1
        cdef int max_part_amount
        cdef int previously_downwards = True
        cdef int jump_amount
        cdef int next_width = -1
        cdef int part_amount
        cdef int max_letters
        cdef int last_successful_part_amount = -1

        while i < fragment_count:
            # See if we're supposed to bail out early:
            if bailout_func != None:
                if bailout_func(layout_w, layout_h) is True:
                    # Add remaining fragments unlayouted and bail out:
                    if left_over_fragment != None:
                        layouted_elements.append(left_over_fragment)
                    while i < fragment_count:
                        layouted_elements.append(self.fragments[i])
                        i += 1
                    break
            
            # Warning if we've been stuck here for a long time:
            if stuck_warning_start_time + 30.0 < time.monotonic():
                logwarning("This is the layouting loop of wobblui. I'm " +
                    "doing this for a long time already. Am I stuck???")
                logwarning("Elements layouted so far: " +
                    str(layouted_elements))
                logwarning("Loop progress: " + str(i) + "/" +
                    str(fragment_count))
                logwarning("Layouting for width: " + str(max_width))
                logwarning("Caller backtrace: " + debug.get_backtrace())
                stuck_warning_start_time = time.monotonic()
            # Get next element:
            perf_10 = Perf.start("before fitting loop")
            next_element = self.fragments[i]
            if left_over_fragment != None:
                next_element = left_over_fragment
                left_over_fragment = None
            else:
                if i <= prev_i:
                    raise RuntimeError("no partial element but " +
                        "haven't increased the index either - " +
                        "layouting stuck???")
                prev_i = i
            if isinstance(next_element, RichTextLinebreak):
                layouted_elements.append(RichTextLinebreak())
                layouted_elements[-1].x = current_x
                layouted_elements[-1].y = current_y
                layouted_elements[-1].font_family = self.default_font_family
                layouted_elements[-1].px_size = self.px_size
                current_line_elements += 1
                add_line_break()
                i += 1
                Perf.stop(perf_10)
                continue
            next_element.draw_scale = self.draw_scale

            # Skip empty fragments:
            part_amount = len(next_element.parts)
            if part_amount == 0:
                assert(next_element.text == "")
                i += 1
                Perf.stop(perf_10)
                continue

            # See how much we can fit into the line with binary search:
            partial = False
            letters = -1
            Perf.stop(perf_10)
            perf_2 = Perf.start("fitting loop")
            max_part_amount = part_amount
            if last_successful_part_amount >= 0 and \
                    last_successful_part_amount < max_part_amount / 3.0:
                # This is extraordinarily short. Don't search full area to
                # start with, but try a shorter range:
                part_amount = max(1, round(last_successful_part_amount * 2))
            previously_downwards = True
            # Force jump amount >= 2 such that the first loop can't
            # immediately exit. Boundary enforcements will prevent jumping
            # outside of valid range anyway:
            jump_amount = -max(2, round(part_amount / 2.0))
            next_width = -1
            while True:
                part_amount = max(1, min(max_part_amount,
                    part_amount + jump_amount))
                letters = len("".join(
                    next_element.parts[:part_amount]))
                next_width = next_element.\
                    get_width_up_to_length(letters)

                # If it fits, continue binary search upwards:
                if max_width < 0 or \
                        current_x + next_width <= max_width:
                    if (part_amount >= max_part_amount or (
                            previously_downwards and
                            abs(jump_amount) <= 1)):
                        # Already at upper edge. We're done!
                        partial = (part_amount < max_part_amount)
                        break
                    previously_downwards = False
                    jump_amount = max(1, abs(round(jump_amount / 2.0)))
                    continue

                # If it doesn't fit, continue binary search downwards:
                if part_amount <= 1:
                    # Already at bottom. We're done:
                    partial = True
                    part_amount = 0  # indicate nothing fits for later code
                    if current_line_elements == 0:
                        # Have to break up into individual letters:
                        part_amount = 1  # partial word (more than zero)
                        max_letters = max(1,
                            len(next_element.parts[0]))
                        letters = max_letters
                        jump_letters = -max(2, round(max_letters / 2))
                        while True:
                            letters = max(1, min(max_letters,
                                letters + jump_letters))
                            next_width = next_element.get_width_up_to_length(
                                letters)
                            if current_x + next_width < max_width:
                                if letters == max_letters:
                                    break
                                jump_letters = max(1, abs(
                                    round(jump_letters / 2.0)))
                                continue
                            else:
                                if letters <= 1:
                                    break
                                if jump_letters <= 2 and \
                                        next_element.get_width_up_to_length(
                                        letters - 1) + current_x < max_width:
                                    letters -= 1
                                    break
                                jump_letters = -max(1, abs(
                                    round(jump_letters / 2.0)))
                    break
                previously_downwards = True
                jump_amount = -max(1, abs(round(jump_amount / 2.0)))
            Perf.stop(perf_2)
            last_successful_part_amount = part_amount
            perf_9 = Perf.start("after fitting loop")
            if part_amount == 0:
                if len(layouted_elements) > 0 and\
                        isinstance(layouted_elements[-1],
                        RichTextLinebreak):
                    raise RuntimeError("fitted no elements after " +
                        "a line break - layouting bug???")
                add_line_break()
                # Don't increase i, we need to add the element next line.
                prev_i = i - 1  # avoid no progress alert
                Perf.stop(perf_9)
                continue
            old_max_height_seen_in_line = -1
            if partial and letters < len(next_element.text):
                assert(letters > 0)
                split_before = next_element.copy()
                left_over_fragment = next_element.copy()
                split_before.text = split_before.text[:letters]
                left_over_fragment.text = left_over_fragment.text[letters:]
                split_before.x = current_x
                split_before.y = current_y
                split_before.width = next_width
                layout_w = max(layout_w, current_x + next_width)
                if max_height_seen_in_line < 0:
                    max_height_seen_in_line = max(0, split_before.height)
                max_height_seen_in_line = max(
                    max_height_seen_in_line, split_before.height)
                old_max_height_seen_in_line = max_height_seen_in_line
                current_line_elements += 1
                layout_w = max(layout_w, current_x)
                layouted_elements.append(split_before)
                add_line_break()
                # Don't increase i, will be increased after processing partial
                # element in next loop
            else:
                added = next_element
                added.x = current_x
                added.y = current_y
                added.width = added.get_width()
                if max_height_seen_in_line < 0:
                    max_height_seen_in_line = added.height
                max_height_seen_in_line = max(
                    max_height_seen_in_line, added.height)
                old_max_height_seen_in_line = max_height_seen_in_line
                current_x += added.width
                current_line_elements += 1
                layout_w = max(layout_w, current_x)
                layouted_elements.append(added)
                i += 1
            layout_h = max(layout_h, current_y + old_max_height_seen_in_line)
            Perf.stop(perf_9)
        Perf.stop(perf_1)
        perf_1 = Perf.start("ending")

        # Record start/end indexes of last line if not empty:
        if current_line_elements > 0:
            clen = len(layouted_elements)
            assert(clen >= current_line_elements)
            forward_start = 0
            if isinstance(
                    layouted_elements[clen - current_line_elements],
                    RichTextLinebreak):
                forward_start = 1
            layout_line_indexes.append((
                clen - current_line_elements + forward_start, clen))

        # If layout ends in linebreak, add height of another default
        # style line to the end:
        if len(layouted_elements) > 0 and \
                isinstance(layouted_elements[-1], RichTextLinebreak):
            dummy_fragment = RichTextFragment(
                " ", self.default_font_family, False, False,
                self.px_size)
            layout_h += dummy_fragment.height

        # Adjust line elements:
        for (start, end) in layout_line_indexes:
            adjust_line_alignment(start, end)

        # Set final relayouted elements:
        self.fragments = layouted_elements
        Perf.stop(perf_1)
        Perf.stop(perf_id)
        return (layout_w, layout_h)
 
    def set_text(self, str text):
        self._cached_text = text
        parts = text.replace("\r\n", "\n").\
            replace("\r", "\n").split("\n")
        self.fragments = self.fragments[:1]
        if len(self.fragments) == 0 or \
                not isinstance(self.fragments[0], RichTextFragment):
            self.fragments = []
            self.fragments.append(RichTextFragment(
                parts[0], self.default_font_family, False, False,
                self.px_size))
        else:
            self.fragments[0].text = parts[0]
        i = 1
        while i < len(parts):
            self.fragments.append(RichTextLinebreak())
            self.fragments[-1].font_family = self.default_font_family
            self.fragments[-1].px_size = self.px_size
            self.fragments.append(RichTextFragment(
                parts[i], self.default_font_family, False, False,
                self.px_size))
            i += 1

    @property
    def html(self):
        cdef str t = ""
        cdef int i = -1
        for fragment in self.fragments:
            i += 1
            prev_fragment = None
            next_fragment = None
            if i > 0:
                prev_fragment = self.fragments[i - 1]
            if i < len(self.fragments) - 1:
                next_fragment = self.fragments[i + 1]
            t += fragment.to_html(prev_fragment, next_fragment)
        return t

    @property
    def text(self):
        if self._cached_text != None:
            return self._cached_text
        cdef str t = ""
        for fragment in self.fragments:
            t += fragment.text
        self._cached_text = t
        return t

    def simplify(self):
        simple_fragments = []
        cdef int i = 0
        while i < len(self.fragments):
            self.fragments[i].x = 0
            self.fragments[i].y = 0
            self.fragments[i].width = -1
            if i == 0 or not isinstance(simple_fragments[-1],
                    RichTextFragment) or \
                    not simple_fragments[-1].has_same_formatting_as(
                    self.fragments[i]):
                simple_fragments.append(self.fragments[i])
            else:
                simple_fragments[-1].text += self.fragments[i].text
            i += 1
        self.fragments = simple_fragments

    def set_html(self, html):
        state = {
            "fragments": [],
            "in_small": 0,
            "in_bold": 0,
            "in_italic": 0,
            "in_headings": [],
            "line_empty_or_not_inline": True,
            "after_explicit_linebreak": False,
            "at_block_start": True,
            "text_color_nesting": [],
            "at_block_end": False,
        }
        def add_line_break():
            state["fragments"].append(RichTextLinebreak())
            state["fragments"][-1].font_family = self.default_font_family
            state["fragments"][-1].px_size = self.px_size

        def is_int(v):
            try:
                converted = int(v)
                return True
            except (TypeError, ValueError):
                return False
        def is_block(el):
            if el.node_type != "element":
                return False
            if el.name.lower() in set([
                    "br", "div", "p",
                    "table"]) or (
                    el.name.lower()[:1] == "h" and
                    is_int(el.name[1:])):
                return True
            return False

        def last_fragment_is_line_break():
            if len(state["fragments"]) > 0 and \
                    isinstance(state["fragments"][-1], RichTextLinebreak):
                return True
            return False

        def visit_item(item):
            text_color = cssparse.element_text_color(item)
            effective_color = text_color
            if text_color != None:
                state["text_color_nesting"].append(text_color)
            elif len(state["text_color_nesting"]) > 0:
                effective_color = state["text_color_nesting"][-1]

            if is_block(item) and item.name.lower() != "br":
                # If this is after a non-empty inline item,
                # do line break:
                if not state["line_empty_or_not_inline"] \
                        and not state["at_block_end"]:
                    add_line_break()
                state["after_explicit_linebreak"] = False
                state["line_empty_or_not_inline"] = True
                state["at_block_start"] = True
                state["at_block_end"] = False
            if item.node_type == "element" and \
                    item.name.lower() == "b":
                state["in_bold"] += 1
            elif item.node_type == "element" and \
                    item.name.lower() == "i":
                state["in_italic"] += 1
            elif item.node_type == "element" and \
                    item.name.lower() == "small":
                state["in_small"] += 1
            elif item.node_type == "element" and \
                    len(item.name) > 1 and \
                    item.name.lower()[0] == "h" and \
                    is_int(item.name[1:]):
                state["in_headings"].append(item.name.lower())
            elif item.node_type == "element" and \
                    item.name.lower() == "br":
                add_line_break()
                state["after_explicit_linebreak"] = True
                state["line_empty_or_not_inline"] = True
            elif item.node_type == "text":
                state["font"] = self.default_font_family
                state["bold"] = (state["in_bold"] > 0)
                state["italic"] = (state["in_italic"] > 0)
                state["in_small"] = (state["in_small"] > 0)
                text = item.content
                if state["at_block_start"] or \
                        state["after_explicit_linebreak"]:
                    while text.startswith("\n") or \
                            text.startswith("\r"):
                        text = text[1:]
                text = text.replace("\n", " ").\
                    replace("\r", " ")
                while text.find("  ") >= 0:
                    text = text.replace("  ", " ")
                if (state["at_block_start"] or
                        state["after_explicit_linebreak"]) \
                        and len(text.strip(string.whitespace)) == 0:
                    text = ""
                if len(text) > 0:
                    fac = 1.0
                    surrounding_tags = []
                    if len(state["in_headings"]) > 0:
                        for heading in state["in_headings"]:
                            surrounding_tags.append(
                                TagInfo(heading,
                                    is_block=True))
                            if heading == "h1":
                                fac *= 2.5
                            elif heading == "h2":
                                fac *= 2.0
                            elif heading == "h3":
                                fac *= 1.5
                            elif heading == "h4":
                                fac *= 1.2
                    if state["in_small"] > 0:
                        fac = 0.75
                        surrounding_tags.append(TagInfo("small",
                            is_block=False))
                    state["fragments"].append(RichTextFragment(
                        text, state["font"],
                        state["bold"] or len(state["in_headings"]) > 0,
                        state["italic"], self.px_size * fac,
                        surrounding_tags=surrounding_tags,
                        force_text_color=effective_color))
                    state["after_explicit_linebreak"] = False
                    state["line_empty_or_not_inline"] = False
                    state["at_block_start"] = False
                    state["at_block_end"] = False

        def leave_item(item):
            text_color = cssparse.element_text_color(item)
            if text_color != None:
                assert(len(state["text_color_nesting"]) > 0)
                state["text_color_nesting"] =\
                    state["text_color_nesting"][:-1]

            if item.node_type == "element" and \
                    item.name.lower() == "b":
                state["in_bold"] = max(0, state["in_bold"] - 1)
            elif item.node_type == "element" and \
                    item.name.lower() == "i":
                state["in_italic"] = max(0, state["in_italic"] - 1)
            elif item.node_type == "element" and \
                    item.name.lower() == "small":
                state["in_small"] = max(0, state["in_small"] - 1)
            elif item.node_type == "element" and \
                    len(item.name) > 1 and \
                    item.name.lower()[0] == "h" and \
                    is_int(item.name[1:]):
                state["in_headings"] = state["in_headings"][:-1]
            if is_block(item) and item.name.lower() != "br":
                if not state["line_empty_or_not_inline"]:
                    add_line_break()
                state["at_block_end"] = True
                state["at_block_start"] = False
                state["after_explicit_linebreak"] = False
                state["at_block_start"] = True
                state["line_empty_or_not_inline"] = False
            elif not state["line_empty_or_not_inline"]:
                # Something inline happened, no longer at block start:
                state["at_block_start"] = False
                state["at_block_end"] = False
        htmlparse.depth_first_walker(html, visit_item,
            visit_out_callback=leave_item)
        self.fragments = state["fragments"]
        self._cached_text = None
        self.simplify()

def test_process_html(html):
    obj = RichText()
    obj.set_html(html)
    return obj.html


