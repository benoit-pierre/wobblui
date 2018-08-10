
import html

from wobblui.color import Color
from wobblui.gfx import draw_dashed_line, draw_rectangle
from wobblui.richtext import RichText
from wobblui.widget import Widget

class ListEntry(object):
    def __init__(self, html, style):
        self.html = html
        self._style = style
        self.y_offset = 0
        font_family = "Tex Gyre Heros"
        if style != None:
            font_family = style.get("widget_font_family")
        px_size = 12
        if style != None:
            px_size = style.get("widget_text_size")
        self.text_obj = RichText(font_family=font_family,
            px_size=px_size,
            draw_scale=style.dpi_scale)
        self.text_obj.set_html(html)
        self.text = self.text_obj.text
        self._max_width = None
        self.need_size_update = True
        self.dpi_scale = 1.0
        if style != None:
            self.dpi_scale = style.dpi_scale

    def draw(self, renderer, x, y, draw_selected=False,
            draw_hover=False, width=None,
            draw_keyboard_focus=False):
        c = Color((200, 200, 200))
        if self.style != None:
            c = Color(self.style.get("inner_widget_bg"))
            if draw_hover:
                c = Color(self.style.get("hover_bg"))
            elif draw_selected:
                c = Color(self.style.get("selected_bg"))
        if width is None:
            width = self.width
        draw_rectangle(renderer, x, y,
            width, self.height, c)
        c = Color((0, 0, 0))
        if self.style != None:
            c = Color(self.style.get("widget_text"))
            if draw_hover or draw_selected:
                c = Color(self.style.get("selected_text"))
        self.text_obj.draw(renderer,
            round(5.0 * self.dpi_scale) + x,
            round(self.vertical_padding * self.dpi_scale) + y,
            color=c)

    def copy(self):
        li = ListEntry(self.html, self.style)
        li.max_width = self.max_width
        return li

    @property
    def width(self):
        self.update_size()
        return self._width

    @property
    def height(self):
        self.update_size()
        return self._height

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, v):
        if self._style != v:
            self.need_size_update = True
            self._style = v

    @property
    def max_width(self):
        return self._max_width

    @max_width.setter
    def max_width(self, v):
        v = int(round(v))
        if self._max_width != v:
            self._max_width = v
            self.need_size_update = True

    @property
    def vertical_padding(self):
        return 10.0

    def update_size(self):
        if not self.need_size_update:
            return
        self.need_size_update = False
        padding = max(0, round(5.0 * self.dpi_scale))
        padding_vertical = max(0,
            round(self.vertical_padding * self.dpi_scale))
        mw = self.max_width
        if mw != None:
            mw -= padding * 2
        is_empty = False
        if self.text_obj.text == "":
            is_empty = True
            self.text_obj.text = " "
        (self.text_width, self.text_height) = self.text_obj.layout(
            max_width=mw)
        self._width = round(self.text_width + padding)
        if self.max_width != None and self.max_width < self._width:
            self._width = self.max_width
        self._height = round(self.text_height + padding_vertical * 2)
        if is_empty:
            self.text_width = 0
            self.text_obj.text = ""

class List(Widget):
    def __init__(self):
        super().__init__(is_container=False, can_get_focus=True)
        self._entries = []
        self._selected_index = -1
        self.scroll_y_offset = 0

    @property
    def hover_index(self):
        return self._hover_index

    @hover_index.setter
    def hover_index(self, v):
        if self._hover_index != v:
            self._hover_index = v
            self.needs_redraw = True

    @property
    def selected_index(self):
        return self._selected_index

    @selected_index.setter
    def selected_index(self, v):
        if self._selected_index != v:
            self._selected_index = v
            self.needs_redraw = True

    def on_keydown(self, key, physical_key, modifiers):
        if key == "down":
            self._selected_index += 1
            if self._selected_index >= len(self._entries):
                self._selected_index = len(self._entries) - 1
            self.scroll_y_offset = max(
                self._entries[self._selected_index].y_offset +
                self._entries[self._selected_index].height -
                self.height,
                self.scroll_y_offset)
            self.needs_redraw = True
        elif key == "up":
            self._selected_index -= 1
            if self._selected_index < 0:
                self._selected_index = 0
            self.scroll_y_offset = min(
                self._entries[self._selected_index].y_offset,
                self.scroll_y_offset)
            self.needs_redraw = True

    def on_mousewheel(self, mouse_id, x, y):
        self.scroll_y_offset = max(0,
            self.scroll_y_offset -
            round(y * 60.0 * self.dpi_scale))
        self.needs_redraw = True

    def on_mousemove(self, mouse_id, x, y):
        pass

    def on_mousedown(self, mouse_id, button, x, y):
        click_index = self.coords_to_entry(x, y)
        if click_index >= 0 and \
                click_index != self._selected_index:
            self._selected_index = click_index
            self.needs_redraw = True

    def coords_to_entry(self, x, y):
        if x < 0 or x >= self.width:
            return -1
        if y < 0 or y >= self.height:
            return -1

        entry_id = -1
        for entry in self._entries:
            entry_id += 1
            if entry.y_offset < y + self.scroll_y_offset and \
                    entry.y_offset + entry.height >\
                    y + self.scroll_y_offset:
                return entry_id
        return -1

    def do_redraw(self):
        content_height = 0
        max_scroll_down = 0
        while True:
            # Draw background:
            c = Color.white
            if self.style != None:
                c = Color(self.style.get("inner_widget_bg"))
            draw_rectangle(self.renderer, 0, 0,
                self.width, self.height, c)

            # Draw items:
            cx = 0
            cy = 0
            entry_id = -1
            for entry in self._entries:
                entry_id += 1
                entry.style = self.style
                if entry.width > self.width and (entry.max_width is None
                        or entry.max_width != self.width):
                    entry.max_width = self.width
                elif entry.width < self.width and \
                        (entry.max_width != self.width):
                    entry.max_width = self.width
                entry.y_offset = cy
                entry.draw(self.renderer, cx, cy - self.scroll_y_offset,
                    draw_selected=(
                    entry_id == self._selected_index),
                    width=self.width,
                    draw_hover=False)
                cy += round(entry.height)
                content_height = max(content_height, cy)

            # Make sure scroll down offset is not too far:
            max_scroll_down = max(0, content_height - self.height)
            if max_scroll_down < self.scroll_y_offset != 0:
                # Oops, scrolled down too far. Fix it and redraw:
                self.scroll_y_offset = max_scroll_down
                continue
            break

        # Draw keyboard focus line if we have the focus:
        if self.focused:
            self.draw_keyboard_focus(0, 0, self.width, self.height)

    def get_natural_width(self):
        w = 0
        entry_copies = []
        for entry in self._entries:
            entry_copies.append(entry.copy())
            entry_copies[-1].max_width = None
            w = max(w, entry_copies[-1].width)
        return max(w, round(12 * self.dpi_scale))

    def get_natural_height(self, given_width=None):
        h = 0
        if given_width != None:
            h = 0
            entry_copies = []
            for entry in self._entries:
                entry_copies.append(entry.copy())
                entry_copies[-1].max_width = given_width
                h += entry_copies[-1].height
        else:
            for entry in self._entries:
                h += entry.height
        return max(h, round(12 * self.dpi_scale))

    @property
    def entries(self):
        l = []
        for entry in self._entries:
            l.append(entry.text_obj.html)
        return l

    def insert(self, index, text):
        self.insert_html(index, html.escape(text))

    def insert_html(self, index, text):
        self._entries.insert(index, ListEntry(html, self.style))

    def add(self, text):
        self.add_html(html.escape(text))

    def add_html(self, html):
        self._entries.append(ListEntry(html, self.style))


