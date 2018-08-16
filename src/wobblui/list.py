
import html

from wobblui.color import Color
from wobblui.event import Event
from wobblui.gfx import draw_dashed_line, draw_rectangle
from wobblui.richtext import RichText
from wobblui.widget import Widget

class ListEntry(object):
    def __init__(self, html, style, is_alternating=False):
        self._width = 0
        self._layout_width = 0
        self.html = html
        self.is_alternating = is_alternating
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
            draw_hover=False,
            draw_keyboard_focus=False,
            draw_no_bg=False):
        self.update_size()
        no_bg = draw_no_bg
        c = Color((200, 200, 200))
        if self.style != None:
            if not self.is_alternating:
                c = Color(self.style.get("inner_widget_bg") or
                    not self.style.has("inner_widget_alternating_bg"))
            else:
                c = Color(self.style.get("inner_widget_alternating_bg"))
            if draw_hover:
                no_bg = False
                c = Color(self.style.get("hover_bg"))
            elif draw_selected:
                no_bg = False
                c = Color(self.style.get("selected_bg"))
        if not no_bg:
            draw_rectangle(renderer, x, y,
                self.width, self.height, c)
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
        li.width = self.width
        li.needs_size_update = True
        return li

    def get_natural_width(self):
        text_copy = self.text_obj.copy()
        (w, h) = text_copy.layout(max_width=None)
        return (w + round(10.0 * self.dpi_scale))

    @property
    def width(self):
        self.update_size()
        return self._width

    @width.setter
    def width(self, v):
        if self._max_width != None:
            v = min(self._max_width, v)
        if self._width != v:
            self._width = v
            self.need_size_update = True

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
        if v != None:
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
            mw = min(self.width, mw) - padding * 2
        else:
            mw = self.width
        is_empty = False
        if self.text_obj.text == "":
            is_empty = True
            self.text_obj.text = " "
        (self.text_width, self.text_height) = self.text_obj.layout(
            max_width=mw)
        self._layout_width = round(self.text_width + padding)
        self._height = round(self.text_height + padding_vertical * 2)
        if is_empty:
            self.text_width = 0
            self.text_obj.text = ""

class ListBase(Widget):
    def __init__(self, render_as_menu=False):
        super().__init__(is_container=False, can_get_focus=True)
        self.triggered = Event("triggered", owner=self)
        self.triggered_by_single_click = False
        self._entries = []
        self._selected_index = -1
        self._hover_index = -1
        self.scroll_y_offset = 0
        self.render_as_menu = render_as_menu

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
        elif key == "space" or key == "return":
            if self._selected_index >= 0:
                self.triggered()

    def on_mousewheel(self, mouse_id, x, y):
        self.scroll_y_offset = max(0,
            self.scroll_y_offset -
            round(y * 20.0 * self.dpi_scale))
        self.needs_redraw = True

    def on_mousemove(self, mouse_id, x, y):
        click_index = self.coords_to_entry(x, y)
        if click_index != self._hover_index:
            self._hover_index = click_index
            if self.render_as_menu:
                self.needs_redraw = True

    def on_doubleclick(self, mouse_id, button, x, y):
        if not self.triggered_by_single_click:
            self.triggered()

    def on_click(self, mouse_id, button, x, y):
        if self.triggered_by_single_click and \
                self._selected_index >= 0:
            self.triggered()

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
            # Draw border if a menu:
            border_size = max(1, round(1.0 * self.dpi_scale))
            if not self.render_as_menu:
                border_size = 0
            c = Color.black
            if self.style != None and self.style.has("border"):
                c = Color(self.style.get("border"))
            if border_size > 0:
                draw_rectangle(self.renderer, 0, 0,
                    self.width, self.height, color=c)
               
            # Draw background: 
            c = Color.white
            if self.style != None:
                c = Color(self.style.get("inner_widget_bg"))
                if self.render_as_menu and self.style.has("button_bg"):
                    c = Color(self.style.get("button_bg"))
            draw_rectangle(self.renderer, border_size, border_size,
                self.width - border_size * 2,
                self.height - border_size * 2,
                color=c)

            # Draw items:
            cx = border_size
            cy = border_size
            entry_id = -1
            for entry in self._entries:
                entry_id += 1
                entry.style = self.style
                entry.width = self.width - round(border_size * 2)
                entry.y_offset = cy
                entry.draw(self.renderer,
                    cx, cy - self.scroll_y_offset,
                    draw_selected=(
                    entry_id == self._selected_index and
                    entry_id != self._hover_index),
                    draw_hover=(self.render_as_menu and
                    entry_id == self._hover_index),
                    draw_no_bg=self.render_as_menu)
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

        # Draw scroll bar:
        if max_scroll_down > 0:
            scroll_percent = max(0.0, min(1.0,
                self.scroll_y_offset / float(max_scroll_down)))
            self.scrollbar_height = round(20.0 * self.dpi_scale)
            self.scrollbar_y = round((self.height -
                self.scrollbar_height) * scroll_percent)
            self.scrollbar_width = round(8.0 * self.dpi_scale)
            self.scrollbar_x = self.width - self.scrollbar_width
            c = Color.white
            if self.style != None:
                c = Color(self.style.get("border"))
            draw_rectangle(self.renderer,
                self.scrollbar_x,
                self.scrollbar_y,
                self.scrollbar_width, self.scrollbar_height,
                color=c)
            c = Color.black
            if self.style != None:
                c = Color(self.style.get("selected_bg"))
                if self.style.has("scrollbar_knob_fg"):
                    c = Color(self.style.get("scrollbar_knob_fg"))
            border_width = max(1, round(1 * self.dpi_scale))
            draw_rectangle(self.renderer,
                self.scrollbar_x + 1 * border_width,
                self.scrollbar_y + 1 * border_width,
                self.scrollbar_width - 2 * border_width,
                self.scrollbar_height - 2 * border_width,
                color=c)

    def get_natural_width(self):
        border_size = max(1, round(1.0 * self.dpi_scale))
        if not self.render_as_menu:
            border_size = 0
        w = 0
        entry_copies = []
        for entry in self._entries:
            w = max(w, entry.get_natural_width())
        w = max(w, round(12 * self.dpi_scale)) + border_size * 2
        return w

    def get_natural_height(self, given_width=None):
        border_size = max(1, round(1.0 * self.dpi_scale))
        if not self.render_as_menu:
            border_size = 0
        h = 0
        if given_width != None:
            h = 0
            entry_copies = []
            for entry in self._entries:
                entry_copies.append(entry.copy())
                entry_copies[-1].max_width = given_width
                entry_copies[-1].width = given_width
                h += entry_copies[-1].height
        else:
            for entry in self._entries:
                h += entry.height
        return max(h, round(12 * self.dpi_scale)) + border_size * 2

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
        i = 0
        while i < len(self._entries):
            self._entries[i].is_alternating = \
                (((i + 1) % 0) == 0)
            i += 1

    def add(self, text):
        self.add_html(html.escape(text))

    def add_html(self, html):
        last_was_alternating = True
        if len(self._entries) > 0 and \
                not self._entries[-1].is_alternating:
            last_was_alternating = False
        self._entries.append(ListEntry(html, self.style,
            is_alternating=(not last_was_alternating)))
        
class List(ListBase):
    def __init__(self):
        super().__init__(render_as_menu=False)

