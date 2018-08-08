
import copy
import ctypes
import html
import sdl2 as sdl

from wobblui.color import Color
import wobblui.htmlparse as htmlparse
from wobblui.font.manager import font_manager

class RichTextObj(object):
    def __init__(self):
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def __repr__(self):
        t = "<RichTextObj x:" + str(self.x) +\
            " y: " + str(self.y) + ">"
        return t

class RichTextFragment(RichTextObj):
    def __init__(self, text, font_family, bold, italic,
            px_size):
        super().__init__()
        self.text = text
        self.font_family = font_family
        self.bold = bold
        self.italic = italic
        self.px_size = px_size
        self.align = None
        self.draw_scale = 1.0

    def __repr__(self):
        t = "<RichTextFragment '" +\
            str(self.text).replace("'", "'\"'\"'") +\
            "' x:" + str(self.x) +\
            " y: " + str(self.y) + ">"
        return t

    def draw(self, renderer, x, y, color=None, draw_scale=None):
        if color is None:
            color = Color.black
        if draw_scale is None:
            draw_scale = self.draw_scale
        font = font_manager().get_font(self.font_family,
            bold=self.bold, italic=self.italic,
            px_size=round(self.px_size * draw_scale))
        tex = font.render_text_as_sdl_texture(renderer,
            self.text, color=color)
        w = ctypes.c_int32()
        h = ctypes.c_int32()
        sdl.SDL_QueryTexture(tex, None, None,
            ctypes.byref(w), ctypes.byref(h))
        tg = sdl.SDL_Rect()
        tg.x = x
        tg.y = y
        tg.w = w.value
        tg.h = h.value
        sdl.SDL_SetRenderDrawColor(renderer,
            round(color.red), round(color.green),
            round(color.blue), 255)
        sdl.SDL_RenderCopy(renderer,
            tex, None, tg)
        sdl.SDL_DestroyTexture(tex)

    def copy(self):
        return copy.copy(self)

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
                round(obj.px_size * 10.0) != round(self.px_size * 10.0):
            return False
        return True

    @property
    def html(self):
        t = html.escape(self.text)
        if self.bold:
            t = "<b>" + t + "</b>"
        if self.italic:
            t = "<i>" + t + "</i>"
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
                part = self.text[last_i + 1:i]
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
        self.html = "<br/>"

class RichText(RichTextObj):
    def __init__(self, text="", font_family="Tex Gyre Heros",
            px_size=12, draw_scale=1.0):
        super().__init__()
        self.default_font_family = font_family
        self.default_px_size = px_size
        self.draw_scale = 1.0
        self.fragments = []
        if len(text) > 0:
            self.fragments.append(RichTextFragment(
                text, font_family, False, False, px_size))

    def draw(self, renderer, x, y, color=None, draw_scale=None):
        for fragment in self.fragments:
            if isinstance(fragment, RichTextLinebreak):
                continue
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
                    px_size=self.default_px_size).\
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
                current_line_elements += 1
                add_line_break()
                i += 1
                continue
            next_element.draw_scale = self.draw_scale

            # Skip empty fragments:
            part_amount = len(next_element.parts)
            if part_amount == 0:
                assert(next_element.text == "")
                current_line_elements += 1
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
        self.fragments = self.fragments[:1]
        if len(self.fragments) == 0 or \
                not isinstance(self.fragments[0], RichTextFragment):
            self.fragments.append(RichTextFragment(
                text, self.default_font_family, False, False,
                self.default_px_size))
        else:
            self.fragments[0].text = text

    @property
    def html(self):
        t = ""
        for fragment in self.fragments:
            t += fragment.html
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
        new_fragments = []
        in_bold = 0
        in_italic = 0
        line_empty = True
        at_block_start = True
        def add_line_break():
            new_fragments.append(RichTextLinebreak())

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
                    is_int(el_name[1:])):
                return True
            return False

        def visit_item(item):
            nonlocal new_fragments, in_bold, in_italic, \
                line_empty, at_block_start
            if item.node_type == "element" and \
                    item.name.lower() == "b":
                in_bold += 1
            elif item.node_type == "element" and \
                    item.name.lower() == "br":
                if not at_block_start or not line_empty:
                    add_line_break()
                line_empty = True
                at_block_start = False
            elif is_block(item):
                if not line_empty:
                    add_line_break()
                line_empty = True
                at_block_start = True
            elif item.node_type == "text":
                font = self.default_font_family
                bold = (in_bold > 0)
                italic = (in_italic > 0)
                text = item.content
                if at_block_start:
                    while text.startswith("\n") or \
                            text.startswith("\r"):
                        text = text[1:]
                text = text.replace("\n", " ").\
                    replace("\r", " ")
                while text.find("  ") >= 0:
                    text = text.replace("  ", " ")
                if at_block_start and len(text.strip()) == 0:
                    text = ""
                if len(text) > 0:
                    new_fragments.append(RichTextFragment(
                        text, font,
                        bold, italic, self.default_px_size))
                    line_empty = False
                    at_block_start = False
        def leave_item(item):
            nonlocal in_bold, in_italic, line_empty,\
                at_block_start
            if item.node_type == "element" and \
                    item.name.lower() == "b":
                in_bold = max(0, in_bold)
            if is_block(item):
                if not line_empty:
                    add_line_break()
                at_block_start = True
                line_empty = False
        htmlparse.depth_first_walker(html, visit_item,
            visit_out_callback=leave_item)
        self.fragments = new_fragments
        self.simplify()

