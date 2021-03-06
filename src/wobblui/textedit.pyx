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

import html

from wobblui.clipboard import set_clipboard_text,\
    get_clipboard_text
from wobblui.color cimport Color
from wobblui.gfx cimport draw_rectangle
from wobblui.richtext cimport RichText
from wobblui.widget cimport Widget


cdef class TextEditBase(Widget):
    cdef int minimum_lines_height, _layout_width, _layout_height
    cdef public int selection_length, cursor_offset, multiline
    cdef str html, _text, hide_with_character
    cdef int draw_touch_handles_without_selection
    cdef object _user_set_color, text_object
    cdef int scroll_x_offset, scroll_y_offset

    def __init__(self, text="", color=None, hide_with_character=None,
            is_multiline=False, minimum_lines_height=1):
        super().__init__(can_get_focus=True,
            takes_text_input=True)
        self.minimum_lines_height = minimum_lines_height
        self.hide_with_character = hide_with_character
        self.type = "textentry"
        self.html = ""
        self.scroll_x_offset = 0
        self.scroll_y_offset = 0
        self.text_object = None
        self._text = ""
        self._layout_width = 0
        self._layout_height = 0
        self.multiline = is_multiline
        self.padding_base_size = 5.0
        self.cursor_offset = 0
        self.draw_touch_handles_without_selection = False
        self.selection_length = 0
        self.update_with_style()
        if text.find("<") >= 0 and (text.find("/>") > 0 or
                text.find("/ >") > 0 or
                (text.find("</") > 0 and text.find(">") > 0)):
            self.set_html(text)    
        else:
            self.set_text(text)
        self._user_set_color = color

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, v):
        self._text = v

    def can_cutcopy(self):
        return (self.hide_with_character is None)

    @property
    def padding(self):
        return max(1, round(self.padding_base_size *
            self.dpi_scale))

    def on_stylechanged(self):
        self.update_with_style()

    def update_with_style(self):
        font_family = self.style.get("widget_font_family")
        px_size = self.style.get("widget_text_size") 
        self._layout_height = 0
        self.text_obj = RichText(font_family=font_family,
            px_size=px_size,
            draw_scale=self.dpi_scale)
        self.text_obj.set_text("This is a test text")
        (w, h) = self.text_obj.layout()
        self._layout_width = 0
        self.default_width = w * 2
        self.text_obj.set_html(self.html)
        self.needs_relayout = True

    def get_text_height(self):
        if self.needs_relayout:
            self.relayout()
        return self._layout_height

    def get_text_width(self):
        if self.needs_relayout:
            self.relayout()
        return self._layout_width

    def get_default_cursor(self):
        return "text"

    def set_text(self, v):
        self.text = v.replace("\r\n", "\n").\
            replace("\r", "\n")

        # Cut off text after one line:
        if not self.multiline:
            self.text = self.text.partition("\n")[0]
        self.html = html.escape(self.text).replace("\n", "<br/>")

        # Set text to internal layouting object:
        if self.hide_with_character is None:
            self.text_obj.set_text(self.text)
        else:
            self.text_obj.set_text(
                self.hide_with_character * len(self.text))
        self.cursor_offset = min(len(self.text),
            self.cursor_offset)
        self.needs_relayout = True
        self.needs_redraw = True

    def set_html(self, v):
        self.html = v
        if self.hide_with_character is None:
            self.text_obj.set_html(v)
        else:
            self.text_obj.set_html(v)
            chars = len(self.text_obj.text)
            self.text_obj.set_text(
                self.hide_with_character * chars)
        self.text = self.text_obj.text

        # Enforce one-line contents afterwards if required:
        # (if we don't need to do that, HTML formatting will
        # be kept as a small bonus. wouldn't be easy to keep if
        # we did this beforehand)
        if not self.multiline:
            one_line_text = self.text.partition("\n")[0]
            if one_line_text != self.text:
                if self.hide_with_character is None:
                    self.text_obj.set_text(
                        self.hide_with_characters *
                        len(one_line_text))
                else:
                    self.text_obj.set_text(one_line_text)
                self.text = one_line_text

        # Limit cursor to text length:
        self.cursor_offset = min(len(self.text),
            self.cursor_offset)
        self.needs_relayout = True
        self.needs_redraw = True

    def in_topbar(self):
        p = self.parent
        while p != None:
            if p.type == "topbar":
                return True
            p = p.parent
        return False

    @property
    def color(self):
        if self._user_set_color != None:
            return self._user_set_color
        if self.style is None:
            return Color.black()
        return Color(self.style.get("widget_text"))

    def update_window(self):
        super().update_window()
        self.needs_redraw = True

    def mouse_offset_to_cursor_offset(self, int x, int y):
        cdef int is_last_line, first_of_line, c, x1, x2, h
        x += self.scroll_x_offset
        y += self.scroll_y_offset
        first_of_line = True
        c = 0
        while c < len(self.text):
            # Get coordinates around this character:
            (x1, y1, h) = self.text_obj.character_index_to_offset(c)
            (x2, y2, h) = self.text_obj.character_index_to_offset(c + 1)
            x1 = round(x1)
            x2 = round(x2)
            if x1 == x2:
                x2 += 1  # make sure to differentiate them
            is_last_line = False
            if y1 + h * 1.2 < y:
                # Skip if we're in some above, irrelevant line...
                if y1 + h * 1.1 >= self.padding + self.get_text_height():
                    # ... unless this is the last line.
                    is_last_line = True
                else:
                    c += 1
                    continue

            # See if this is the beginning of the line:
            first_of_line = False
            if c <= 0:
                first_of_line = True
            elif self.text[c - 1] == "\n":
                first_of_line = True

            # See if this is the end of the line:
            last_of_line = False
            if c == len(self.text) - 1:
                last_of_line = True
            elif self.text[c + 1] == "\n":
                last_of_line = True

            # Special handling for line breaks:
            if self.text[c] == "\n":
                if (c == 0 or
                        self.text[c - 1] == "\n"):
                    # Only character in line. Place cursor here.
                    return c
                # Skip handling to the next regular character.
                c += 1
                continue

            # See if we want to place cursor before or after character:
            x1 += self.padding
            x2 += self.padding
            if (y >= y1 and y <= y1 + h) or is_last_line:
                if x >= x1 and x <= x2:
                    if abs(x1 - x) < abs(x2 - x):
                        # Left-side of letter
                        return c
                    else:
                        # Right side of letter
                        return c + 1
                if x < x1 and first_of_line:
                    return c
                if x > x2 and last_of_line:
                    return c + 1
            c += 1
        return 0

    def end_mouse_drag(self, x, y):
        self.process_mouse_drag(x, y)
        self._mouse_dragging = False

    def start_mouse_drag(self, x, y):
        if not hasattr(self, "_mouse_dragging") or \
                not self._mouse_dragging:
            self._mouse_dragging = True
            self._mouse_drag_x = x
            self._mouse_drag_y = y
            self._known_mouse_pos = -1
        self.process_mouse_drag(x, y)

    def process_mouse_drag(self, x, y):
        if not hasattr(self, "_mouse_dragging") or \
                not self._mouse_dragging:
            return
        start_pos = self.mouse_offset_to_cursor_offset(
            self._mouse_drag_x, self._mouse_drag_y
        )
        end_pos = self.mouse_offset_to_cursor_offset(x, y)
        if self._known_mouse_pos == end_pos:
            return
        self._known_mouse_pos = end_pos
        if self.cursor_offset != end_pos:
            self.cursor_offset = end_pos
            self.needs_redraw = True
        if self.selection_length != (start_pos - end_pos):
            self.selection_length = (start_pos - end_pos)
            self.needs_redraw = True

    def on_mouseup(self, mouse_id, button, x, y):
        self.end_mouse_drag(x, y)

    def on_mousemove(self, mouse_id, x, y):
        self.process_mouse_drag(x, y)

    def on_textinput(self, text, modifiers):
        if "ctrl" in modifiers:
            return
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if not self.multiline:
            text = text.partition("\n")[0]
        if len(text) == 0:
            return
        if self.selection_length != 0:
            self.del_selection()
        self.insert_at(self.cursor_offset, text)
        self.scroll_to_cursor()
        self.draw_touch_handles_without_selection = False

    def scroll_to_cursor(self):
        cdef int x, y, h
        if self.cursor_offset is None or \
                self.cursor_offset < 0:
            return
        (x, y, h) = self.text_obj.character_index_to_offset(
            max(0, self.cursor_offset or 0)
        )
        reference_lower_point = y + max(0, round(h) - 2)
        if x >= self.width - self.padding * 2 + self.scroll_x_offset:
            excess_x = (x - (
                self.width - self.padding * 2 + self.scroll_x_offset
            )) + 1
            self.scroll_x_offset += round(excess_x)
        if reference_lower_point >= (self.height - self.padding * 2 +
                                     self.scroll_y_offset):
            excess_y = (
                reference_lower_point -
                (self.height - self.padding * 2 + self.scroll_y_offset)
            ) + 1
            self.scroll_y_offset += round(excess_y)
        if x <= self.scroll_x_offset:
            underrun_x = (self.scroll_x_offset - x) + 1
            self.scroll_x_offset -= round(underrun_x)
        if y < self.scroll_y_offset:
            underrun_y = (self.scroll_y_offset - y)
            self.scroll_y_offset -= round(underrun_y)

    def insert_at(self, pos, text):
        text = text.replace("\r\n", "\n").\
            replace("\r", "\n")
        if not self.multiline:
            text = text.partition("\n")[0]
        if self.hide_with_character:
            self.text_obj.set_text(self.text)
        self.text_obj.insert_text_at_offset(
            pos, text)
        self.cursor_offset += len(text)
        self.text = self.text_obj.text
        self.html = self.text_obj.html
        if self.hide_with_character != None:
            self.text_obj.set_text(
                self.hide_with_character * len(self.text))
        self.needs_relayout = True
        self.needs_redraw = True

    def del_range(self, start, end):
        i = min(end, len(self.text))
        while i > start:
            self.text_obj.remove_char_before_offset(i)
            i -= 1
        self.needs_relayout = True
        self.needs_redraw = True
        self.text = self.text_obj.text
        self.html = self.text_obj.html

    def del_selection(self):
        start = self.cursor_offset
        end = start + self.selection_length
        if end < start:
            start = self.cursor_offset + self.selection_length
            end = self.cursor_offset
        self.del_range(start, end)
        self.selection_length = 0
        self.cursor_offset = start

    def select_all(self):
        self.cursor_offset = 0
        self.selection_length = len(self.text)
        self.needs_redraw = True

    def do_copy(self):
        if self.selection_length > 0:
            set_clipboard_text(
                self.text[self.cursor_offset:
                    self.cursor_offset + self.selection_length])
        elif self.selection_length < 0:
            set_clipboard_text(
                self.text[
                    self.cursor_offset + self.selection_length:
                    self.cursor_offset])

    def do_cut(self):
        self.do_copy()
        self.del_selection()

    def do_paste(self):
        insert_text = get_clipboard_text()
        if len(insert_text) == 0:
            return
        self.del_selection()
        self.insert_at(
            self.cursor_offset, insert_text)

    def on_keydown(self, virtual_key, physical_key, modifiers):
        if "ctrl" in modifiers:
            if virtual_key == "c":
                self.do_copy()
            elif virtual_key == "x":
                self.do_cut()
            elif virtual_key == "a":
                self.select_all()
            elif virtual_key == "v":
                self.do_paste()
        elif "shift" in modifiers:
            if virtual_key == "left" or virtual_key == "up":
                self.cursor_offset = max(0, self.cursor_offset - 1)
                self.selection_length += 1
                self.needs_redraw = True
            elif virtual_key == "right" or virtual_key == "down":
                self.cursor_offset = min(len(self.text),
                    self.cursor_offset + 1)
                self.selection_length -= 1
                self.needs_redraw = True
        elif virtual_key == "backspace":
            if self.cursor_offset > 0 or self.selection_length > 0:
                if self.selection_length == 0:
                    self.text_obj.remove_char_before_offset(
                        self.cursor_offset)
                    self.cursor_offset = max(0,
                        self.cursor_offset - 1)
                else:
                    self.del_selection()
                self.text = self.text_obj.text
                self.html = self.text_obj.html
                self.needs_relayout = True
                self.needs_redraw = True
                return
            self.cursor_offset = max(0, self.cursor_offset - 1) 
            self.needs_redraw = True
        elif virtual_key == "left" or virtual_key == "up":
            self.cursor_offset = max(0, self.cursor_offset - 1)
            self.selection_length = 0
            self.draw_touch_handles_without_selection = False
            self.scroll_to_cursor()
            self.needs_redraw = True
        elif virtual_key == "right" or virtual_key == "down":
            self.cursor_offset = min(len(self.text),
                self.cursor_offset + 1)
            self.selection_length = 0
            self.draw_touch_handles_without_selection = False
            self.scroll_to_cursor()
            self.needs_redraw = True

    def on_mousedown(self, mouse_id, button, mx, my):
        if button == 2:
            self.update()
            self.move_cursor_to_mouse(mx, my)
            if not self.is_mouse_event_actually_touch():
                # Regular desktop mode right-click:
                raise RuntimeError("not implemented")
            else:
                # This is actually a touch long press:
                if mx < self.padding + self.get_text_width():
                    # This is on the text, so select full word:
                    self.select_full_word_at_cursor()
                else:
                    # This is "past" the text, so do paste selection
                    # marker without selecting word:
                    self.move_cursor_to_mouse(mx, my)
                    self.selection_length = 0
                    self.draw_touch_handles_without_selection = True
            return
        elif button == 1:
            self.move_cursor_to_mouse(mx, my)
            self.selection_length = 0
            self.start_mouse_drag(mx, my)
            self.update()

    def on_doubleclick(self, mouse_id, button, x, y):
        self.move_cursor_to_mouse(x, y)
        self.select_full_word_at_cursor()

    def move_cursor_to_mouse(self, mx, my):
        self.cursor_offset = max(0, min(
            len(self.text),
            self.mouse_offset_to_cursor_offset(mx, my)
        ))

    def select_full_word_at_cursor(self):
        word_start = max(0, self.cursor_offset)
        word_end = max(0, self.cursor_offset)
        word_seps = set([" ", "\n", "\t", ",", ":",
            ";"])
        while word_start > 0 and \
                self.text[word_start - 1] not in word_seps:
            word_start -= 1
        while word_end < len(self.text) and \
                self.text[word_end] not in word_seps:
            word_end += 1
        self.cursor_offset = word_start
        self.selection_length = (word_end - word_start)
        self.update()

    def current_touch_handle_height(self, first_one):
        positions = self.get_touch_selection_positions()
        if positions is None:
            return 0.0
        if first_one:
            return positions[2]
        else:
            return positions[5]

    def move_touch_selection_handle(self,
            first_one, target_x, target_y
            ):
        if self.selection_length <= 0:
            return None
        offset_y = round(self.current_touch_handle_height(first_one) * 0.5)
        if first_one:
            new_pos = self.mouse_offset_to_cursor_offset(
                target_x, target_y + offset_y
            )
            if new_pos >= 0:
                move_diff = (new_pos - self.cursor_offset)
                self.cursor_offset += move_diff
                self.selection_length =\
                    self.selection_length - move_diff
        else:
            new_pos = self.mouse_offset_to_cursor_offset(
                target_x, target_y + offset_y
            )
            if new_pos >= 0:
                move_diff = (new_pos - (self.cursor_offset
                    + self.selection_length))
                self.selection_length += move_diff
        if self.selection_length == 0:
            self.selection_length = 1

    def get_touch_selection_positions(self):
        if self.selection_length <= 0 and \
                not self.draw_touch_handles_without_selection:
            return None
        (x1, y1, h1) = self.text_obj.character_index_to_offset(
            max(0, self.cursor_offset or 0))
        (x2, y2, h2) = self.text_obj.character_index_to_offset(
            max(0, self.cursor_offset or 0) +
            self.selection_length)
        return (
            self.padding + x1,
            self.padding + y1, h1,
            self.padding + x2,
            self.padding + y2, h2
            )

    def do_redraw(self):
        border_size = max(1, round(1.0 * self.dpi_scale))
        # Draw basic bg:
        c = Color.white()
        if self.style != None:
            c = Color(self.style.get("inner_widget_bg"))
        draw_rectangle(self.renderer,
            0, 0, self.width, self.height, color=c)

        # Make sure text draws at correct size (important for
        # selection rectangle size calculation right below)
        self.text_obj.draw_scale = self.dpi_scale
        for fragment in self.text_obj.fragments:
            fragment.draw_scale = self.dpi_scale

        # Draw text selection if any:
        if self.selection_length != 0:
            if self.selection_length > 0:
                # Selection forward:
                (x1, y1, h1) = self.text_obj.character_index_to_offset(
                    max(0, self.cursor_offset or 0))
                (x2, y2, h2) = self.text_obj.character_index_to_offset(
                    max(0, self.cursor_offset or 0) +
                    self.selection_length)
            else:
                # Selection backwards:
                (x1, y1, h1) = self.text_obj.character_index_to_offset(
                    max(0, self.cursor_offset or 0) +
                    self.selection_length)
                (x2, y2, h2) = self.text_obj.character_index_to_offset(
                    max(0, self.cursor_offset or 0))
            c = Color("#aaf")
            if self.style != None and self.style.has("selected_bg"):
                c = Color(self.style.get("selected_bg"))
            draw_rectangle(self.renderer,
                x1 + self.padding - self.scroll_x_offset,
                y1 + self.padding - self.scroll_y_offset,
                max(1, x2 - x1),
                max(1, max(h1, h2)),
                color=c)

        # Draw text:
        for fragment in self.text_obj.fragments:
            fragment.draw(self.renderer,
                fragment.x + self.padding - self.scroll_x_offset,
                fragment.y + self.padding - self.scroll_y_offset,
                color=self.color)

        # Redraw padding area (in case text is clipped
        # outside of the widget size)
        c = Color.white()
        if self.style != None:
            c = Color(self.style.get("inner_widget_bg"))
        draw_rectangle(self.renderer,
            border_size, border_size,
            self.width, self.height, color=c,
            filled=False, unfilled_border_thickness=self.padding)

        # Draw cursor:
        (x, y, h) = self.text_obj.character_index_to_offset(
            max(0, self.cursor_offset or 0))
        draw_rectangle(self.renderer,
            x + self.padding - self.scroll_x_offset,
            y + self.padding - self.scroll_y_offset,
            max(1, round(1.0 * self.dpi_scale)),
            max(5, h), color=self.color)

        # Draw border:
        c = Color.black()
        if self.style != None:
            c = Color(self.style.get("border"))
        draw_rectangle(self.renderer,
            0, 0, self.width, self.height, color=c,
            filled=False, unfilled_border_thickness=border_size)

        # Draw keyboard focus:
        if self.focused:
            focus_padding = round(0.0 * self.dpi_scale)
            self.draw_keyboard_focus(
                focus_padding, focus_padding,
                self.width - focus_padding * 2,
                self.height - focus_padding * 2)

    def on_relayout(self):
        self.text_obj.draw_scale = self.dpi_scale
        self.text_obj.px_size = int(self.style.get("widget_text_size"))
        if self.style.has("topbar_text_size") and self.in_topbar():
            self.text_obj.px_size = \
                int(self.style.get("topbar_text_size"))
        (self._layout_width, self._layout_height) = \
            self.text_obj.layout(max_width=None)

    def get_natural_width(self):
        return self.default_width + self.padding * 2

    def get_natural_height(self, given_width=None):
        copy_obj = self.text_obj.copy()
        copy_obj.set_text(" ")
        (_, min_height) = copy_obj.layout(max_width=None)
        min_height *= max(1, round(self.minimum_lines_height))
        (w, h) = (0, min_height)
        if len(self.text_obj.text) > 0:
            (w, h) = self.text_obj.layout(max_width=None)
        return max(h, min_height) + self.padding * 2


cdef class TextEdit(TextEditBase):
    def __init__(self, text="", color=None, hide_with_character=None,
            minimum_lines_height=3):
        super().__init__(
            text=text, color=color,
            hide_with_character=hide_with_character,
            is_multiline=True,
            minimum_lines_height=minimum_lines_height)
