
import html

from wobblui.color import Color
from wobblui.gfx import draw_dashed_line, draw_rectangle
from wobblui.richtext import RichText
from wobblui.widget import Widget

class ListEntry(object):
    def __init__(self, html, style):
        self.html = html
        self._style = style
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
            if draw_selected:
                c = Color(self.style.get("selected_bg"))
        if width is None:
            width = self.width
        draw_rectangle(renderer, x, y,
            width, self.height, c)
        c = Color((0, 0, 0))
        if self.style != None:
            c = Color(self.style.get("widget_text"))
            if draw_selected:
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
        super().__init__(is_container=False)
        self._entries = []
        self._selected_index = -1
        self._hover_index = -1

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

    def on_mousemove(self, mouse_id, x, y):
        pass

    def do_redraw(self):
        c = Color.white
        if self.style != None:
            c = Color(self.style.get("inner_widget_bg"))
        draw_rectangle(self.renderer, 0, 0,
            self.width, self.height, c) 
        cx = 0
        cy = 0
        entry_id = -1
        for entry in self._entries:
            entry_id += 1
            entry.style = self.style
            if entry.width > self.width and (entry.max_width is None
                    or entry.max_width != self.width):
                entry.max_width = self.width
            elif entry.width < self.width and (entry.max_width != self.width):
                entry.max_width = self.width
            if entry_id == 1 or True:
                entry.draw(self.renderer, cx, cy, draw_selected=(
                    entry_id == self._selected_index and
                    entry_id != self._hover_index),
                    width=self.width,
                    draw_hover=(entry_id == self._hover_index))
            cy += round(entry.height)

        # Draw keyboard focus line if we have the focus:
        if self.focused or True:
            focus_border_thickness = 1.0
            c = Color.red
            if c != None:
                c = Color(self.style.get("focus_border"))
            draw_dashed_line(self.renderer,
                0.5 * focus_border_thickness * self.dpi_scale,
                0,
                0.5 * focus_border_thickness * self.dpi_scale,
                self.height,
                dash_length=(7.0 * self.dpi_scale),
                thickness=(focus_border_thickness * self.dpi_scale),
                color=c)
            draw_dashed_line(self.renderer,
                self.width - 0.5 * focus_border_thickness * self.dpi_scale,
                0,
                self.width - 0.5 * focus_border_thickness * self.dpi_scale,
                self.height,
                dash_length=(7.0 * self.dpi_scale),
                thickness=(focus_border_thickness * self.dpi_scale),
                color=c)
            draw_dashed_line(self.renderer,
                0,
                0.5 * focus_border_thickness * self.dpi_scale,
                self.width,
                0.5 * focus_border_thickness * self.dpi_scale,
                dash_length=(7.0 * self.dpi_scale),
                thickness=(focus_border_thickness * self.dpi_scale),
                color=c)
            draw_dashed_line(self.renderer,
                0,
                self.height - 0.5 * focus_border_thickness * self.dpi_scale,
                self.width,
                self.height - 0.5 * focus_border_thickness * self.dpi_scale,
                dash_length=(7.0 * self.dpi_scale),
                thickness=(focus_border_thickness * self.dpi_scale),
                color=c)

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


