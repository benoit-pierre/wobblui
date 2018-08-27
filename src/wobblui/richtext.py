
import copy
import ctypes
import html
import sdl2 as sdl
import string

from wobblui.color import Color
import wobblui.cssparse as cssparse
import wobblui.htmlparse as htmlparse
from wobblui.font.manager import font_manager

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

class RichTextObj(object):
    def __init__(self):
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.italic = False
        self.bold = False
        self.font_family = "Sans Serif"
        self.px_size = 12
        self.draw_scale = 1.0

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

class RichTextFragment(RichTextObj):
    def __init__(self, text, font_family, bold, italic,
            px_size, surrounding_tags=[],
            force_text_color=None):
        super().__init__()
        self.forced_text_color = None
        if force_text_color != None:
            self.forced_text_color = Color(force_text_color)
        self.text = text
        self.font_family = font_family
        self.bold = bold
        self.surrounding_tags = copy.copy(surrounding_tags)
        self.italic = italic
        self.px_size = px_size
        self.align = None
        self.draw_scale = 1.0

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
        t = "<RichTextFragment '" +\
            str(self.text).replace("'", "'\"'\"'") + "'"
        if self.x != None or self.y != None:
            t += " x:" + str(self.x) +\
                " y: " + str(self.y)
        if self.forced_text_color != None:
            t += " color: " + str(self.forced_text_color.html)
        t += " px_size=" + str(self.px_size) + ">"
        return t

    def draw(self, renderer, x, y, color=None, draw_scale=None):
        if color is None:
            color = Color.black
        if draw_scale is None:
            draw_scale = self.draw_scale
        font = self.get_font(draw_scale=draw_scale)
        if self.forced_text_color != None:
            color = self.forced_text_color
        tex = font.get_cached_rendered_sdl_texture(renderer,
            self.text, color=color)
        w = ctypes.c_int32()
        h = ctypes.c_int32()
        sdl.SDL_QueryTexture(tex, None, None,
            ctypes.byref(w), ctypes.byref(h))
        tg = sdl.SDL_Rect()
        tg.x = round(x)
        tg.y = round(y)
        tg.w = w.value
        tg.h = h.value
        sdl.SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255)
        #if self.forced_text_color is None:
        #    sdl.SDL_SetTextureColorMod(tex,
        #        round(color.red), round(color.green),
        #        round(color.blue))
        #else:
        #    sdl.SDL_SetTextureColorMod(tex,
        #        round(self.forced_text_color.red),
        #        round(self.forced_text_color.green),
        #        round(self.forced_text_color.blue))
        sdl.SDL_RenderCopy(renderer,
            tex, None, tg)

    def get_width(self):
        return self.get_width_up_to_length(len(self.text))

    def get_width_up_to_length(self, index):
        text_part = self.text[:index]
        font = font_manager().get_font(self.font_family,
            bold=self.bold, italic=self.italic,
            px_size=self.px_size,
            draw_scale=self.draw_scale)
        (w, h) = font.render_size(text_part)
        return w

    def get_height(self):
        font = font_manager().get_font(self.font_family,
            bold=self.bold, italic=self.italic,
            px_size=self.px_size,
            draw_scale=self.draw_scale)
        (w, h) = font.render_size(self.text)
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
        last_i = -1
        split_before_chars = set([" ", "\n", "\r"])
        split_after_chars = set([",", ".", ":",
            "!", "'", "\"", "-", "=", "?"])
        result = []
        i = 0
        while i < len(self.text):
            c = self.text[i]
            if c in split_after_chars or (i + 1 < len(self.text)
                    and self.text[i + 1] in split_before_chars):
                part = self.text[last_i + 1:i + 1]
                if len(part) > 0:
                    result.append(part)
                    last_i = i
            i += 1
        if last_i + 1 < i:
            part = self.text[last_i + 1:]
            if len(part) > 0:
                result.append(part)
        return result

class RichTextLinebreak(RichTextObj):
    def __init__(self):
        super().__init__()
        self.text = "\n"

    def __repr__(self):
        t = "<RichTextLinebreak x:" + str(self.x) +\
            " y: " + str(self.y) + ">"
        return t

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

class RichText(object):
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
        c = offset - 1
        i = 0
        while i < len(self.fragments):
            fragment = self.fragments[i]
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
        c = offset
        i = 0
        while i < len(self.fragments):
            fragment = self.fragments[i]
            if c < len(fragment.text) or i == len(self.fragments) - 1:
                fragment.text = fragment.text[:c] + text +\
                    fragment.text[c:]
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

    def draw(self, renderer, x, y, color=None, draw_scale=None):
        assert(renderer != None and x != None and y != None)
        for fragment in self.fragments:
            if isinstance(fragment, RichTextLinebreak):
                continue
            assert(fragment != None)
            fragment.draw(renderer, fragment.x + x, fragment.y + y,
                color=color, draw_scale=draw_scale)

    def copy(self):
        new_text = copy.copy(self)
        new_fragments = []
        for fragment in self.fragments:
            new_fragments.append(fragment.copy())
        new_text.fragments = new_fragments
        return new_text

    def layout(self, max_width=None, align_if_none=None):
        self.simplify()
        layouted_elements = []
        layout_line_indexes = []
        current_line_elements = 0
        layout_w = 0
        layout_h = 0
        current_x = 0
        current_y = 0
        max_height_seen_in_line = None
        left_over_fragment = None

        # Helper function to start a new line:
        def add_line_break():
            nonlocal current_x, current_y, \
                current_line_elements,\
                max_height_seen_in_line,\
                layout_w, layout_h
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
            if max_height_seen_in_line != None:
                current_y += max_height_seen_in_line
            else:
                current_y += max(1, font_manager().get_font(
                    self.default_font_family,
                    draw_scale=self.draw_scale,
                    px_size=self.px_size).\
                    render_size(" ")[1])
            layout_h = max(layout_h, current_y)
            max_height_seen_in_line = None
            current_line_elements = 0

        # Helper function to shift elements in a specific line to
        # adapt to different alignments:
        def adjust_line_alignment(start_index, end_index):
            nonlocal current_line_elements, layout_w, layouted_elements
            line_alignment = None
            elements_width = 0
            k = start_index
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
            align_to_width = max_width or layout_w
            layout_w = align_to_width
            shift_space = max(0, align_to_width - elements_width)
            if line_alignment == "center" or line_alignment == "right":
                shift_width = shift_space
                if line_alignment == "center":
                    shift_width = max(round(shift_width / 2.0), 0)
                k = start_index
                while k < end_index:
                    layouted_elements[k].x += shift_width
                    k += 1
                return

        i = 0
        while i < len(self.fragments):
            # Get next element:
            next_element = self.fragments[i]
            if left_over_fragment != None:
                next_element = left_over_fragment
                left_over_fragment = None
            if isinstance(next_element, RichTextLinebreak):
                layouted_elements.append(RichTextLinebreak())
                layouted_elements[-1].x = current_x
                layouted_elements[-1].y = current_y
                layouted_elements[-1].font_family = self.default_font_family
                layouted_elements[-1].px_size = self.px_size
                current_line_elements += 1
                add_line_break()
                i += 1
                continue
            next_element.draw_scale = self.draw_scale

            # Skip empty fragments:
            part_amount = len(next_element.parts)
            if part_amount == 0:
                assert(next_element.text == "")
                i += 1
                continue

            # See how much we can fit into the line:
            partial = False
            letters = None
            next_width = None
            while part_amount > 0:
                letters = len("".join(next_element.parts[:part_amount]))
                next_width = next_element.\
                    get_width_up_to_length(letters)
                if max_width is None or \
                        current_x + next_width <= max_width:
                    break
                partial = True
                if part_amount == 1 and current_line_elements == 0:
                    letters = max(1, len(next_element.parts[0]))
                    next_width = next_element.get_width_up_to_length(
                        letters)
                    while letters > 1 and \
                            current_x + next_width > max_width:
                        letters -= 1
                        next_width = next_element.get_width_up_to_length(
                            letters)
                    break
                part_amount -= 1
            if part_amount == 0:
                add_line_break()
                # Don't increase i, we need to add the element next line.
                continue
            old_max_height_seen_in_line = None
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
                split_before.height = split_before.get_height()
                if max_height_seen_in_line is None:
                    max_height_seen_in_line = split_before.get_height()
                max_height_seen_in_line = max(
                    max_height_seen_in_line, split_before.get_height())
                old_max_height_seen_in_line = max_height_seen_in_line
                current_line_elements += 1
                layout_w = max(layout_w, current_x)
                layouted_elements.append(split_before)
                add_line_break()
                # Don't increase i, will be increased after processing partial
                # element in next loop
            else:
                added = next_element.copy()
                added.x = current_x
                added.y = current_y
                added.width = added.get_width()
                added.height = added.get_height()
                if max_height_seen_in_line is None:
                    max_height_seen_in_line = added.get_height()
                max_height_seen_in_line = max(
                    max_height_seen_in_line, added.get_height())
                old_max_height_seen_in_line = max_height_seen_in_line
                current_x += added.width
                current_line_elements += 1
                layout_w = max(layout_w, current_x)
                layouted_elements.append(added)
                i += 1
            layout_h = max(layout_h, current_y + old_max_height_seen_in_line)
        # Record last line pair if not empty:
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

        # Adjust line elements:
        for (start, end) in layout_line_indexes:
            adjust_line_alignment(start, end)

        # Set final relayouted elements:
        self.fragments = layouted_elements
        return (layout_w, layout_h)
 
    def set_text(self, text):
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
        t = ""
        i = -1
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
        t = ""
        for fragment in self.fragments:
            t += fragment.text
        return t

    def simplify(self):
        simple_fragments = []
        i = 0
        while i < len(self.fragments):
            self.fragments[i].x = None
            self.fragments[i].y = None
            self.fragments[i].width = None
            self.fragments[i].height = None
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
        self.simplify()

def test_process_html(html):
    obj = RichText()
    obj.set_html(html)
    return obj.html


