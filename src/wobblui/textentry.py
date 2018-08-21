

import sdl2 as sdl

from wobblui.clipboard import set_clipboard_text,\
    get_clipboard_text
from wobblui.color import Color
from wobblui.gfx import draw_rectangle
from wobblui.richtext import RichText
from wobblui.widget import Widget

class TextEntry(Widget):
    def __init__(self, text="", color=None):
        super().__init__(can_get_focus=True,
            takes_text_input=True)
        self.type = "textentry"
        self.html = ""
        self.text = ""
        self.padding_base_size = 5.0
        self.cursor_offset = 0
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
        self.default_width = w * 2
        self.text_obj.set_html(self.html)
        self.needs_relayout = True

    def set_text(self, v):
        self.text = (v.replace("\r\n", "\n").\
            replace("\r", "\n").partition("\n")[0])
        self.html = html.escape(text)
        self.text_obj.set_text(self.text)
        self.cursor_offset = min(len(self.text),
            self.cursor_offset)
        self.needs_relayout = True
        self.needs_redraw = True

    def set_html(self, v):
        self.html = v
        self.text_obj.set_html(v)
        self.cursor_offset = min(len(self.text),
            self.cursor_offset)
        self.text = self.text_obj.text
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
            return Color.black
        return Color(self.style.get("widget_text"))

    def update_window(self):
        super().update_window()
        self.needs_redraw = True

    def on_textinput(self, text, modifiers):
        if "ctrl" in modifiers:
            return
        text = text.replace("\r\n", "\n").replace("\r", "\n").\
            partition("\n")[0]
        if len(text) == 0:
            return
        if self.selection_length != 0:
            self.del_selection()
        self.text_obj.insert_text_at_offset(
            self.cursor_offset, text)
        self.cursor_offset += len(text)
        self.text = self.text_obj.text
        self.html = self.text_obj.html
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

    def on_keydown(self, virtual_key, physical_key, modifiers):
        if "ctrl" in modifiers:
            if virtual_key == "c" or virtual_key == "x":
                if self.selection_length > 0:
                    set_clipboard_text(
                        self.text[self.cursor_offset:
                            self.cursor_offset + self.selection_length])
                elif self.selection_length < 0:
                    set_clipboard_text(
                        self.text[
                            self.cursor_offset + self.selection_length:
                            self.cursor_offset])
                if virtual_key == "x" and self.selection_length != 0:
                    self.del_selection()
            elif virtual_key == "a":
                self.select_all()
            elif virtual_key == "v":
                self.del_selection()
                self.text_obj.insert_text_at_offset(
                    self.cursor_offset, get_clipboard_text())
                self.text = self.text_obj.text
                self.html = self.text_obj.html
                self.needs_relayout = True
                self.needs_redraw = True
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
            self.needs_redraw = True
        elif virtual_key == "right" or virtual_key == "down":
            self.cursor_offset = min(len(self.text),
                self.cursor_offset + 1)
            self.selection_length = 0
            self.needs_redraw = True

    def do_redraw(self):
        border_size = max(1, round(1.0 * self.dpi_scale))
        # Draw basic bg:
        c = Color.white
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
                x1 + self.padding, y1 + self.padding,
                max(1, x2 - x1),
                max(1, max(h1, h2)),
                color=c)

        # Draw text:
        for fragment in self.text_obj.fragments:
            fragment.draw(self.renderer,
                fragment.x + self.padding,
                fragment.y + self.padding,
                color=self.color)

        # Redraw padding area (in case text is clipped
        # outside of the widget size)
        c = Color.white
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
            x + self.padding,
            y + self.padding, max(1, round(1.0 * self.dpi_scale)),
            max(5, h), color=self.color)

        # Draw border:
        c = Color.black
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
        (w, self._layout_height) = self.text_obj.layout(max_width=None)

    def get_natural_width(self):
        if len(self.text_obj.text) == 0:
            return 0
        return self.default_width + self.padding * 2

    def get_natural_height(self, given_width=None):
        if len(self.text_obj.text) > 0:
            (w, h) = self.text_obj.layout(max_width=None)
        else:
            copy_obj = self.text_obj.copy()
            copy_obj.set_text(" ")
            (w, h) = copy_obj.layout(max_width=None)
        return h + self.padding * 2

