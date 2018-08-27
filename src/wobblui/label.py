
import sdl2 as sdl

from wobblui.color import Color
from wobblui.richtext import RichText
from wobblui.scrollbarwidget import ScrollbarDrawingWidget
from wobblui.widget import Widget

class Label(ScrollbarDrawingWidget):
    def __init__(self, text="", color=None,
            text_scale=1.0):
        super().__init__()
        self.type = "label"
        self.text_scale = text_scale
        font_family = self.style.get("widget_font_family")
        self.px_size = self.get_intended_text_size()
        self._layout_height = 0
        self.scroll_y_offset = 0
        self.text_obj = RichText(font_family=font_family,
            px_size=self.px_size,
            draw_scale=self.dpi_scale)
        self._current_align = "left"
        if text.find("<") >= 0 and (text.find("/>") > 0 or
                text.find("/ >") > 0 or
                (text.find("</") > 0 and text.find(">") > 0)):
            self.html = text
        else:
            self.text = text
        self._user_set_color = color

    def get_intended_text_size(self):
        if self.style == None:
            return 12
        px_size = round(self.style.get("widget_text_size") *\
            self.text_scale)
        if self.style.has("topbar_text_size") and self.in_topbar():
            px_size = \
                round(self.style.get("topbar_text_size") *\
                self.text_scale)
        return px_size

    def set_text(self, v):
        self.text = v

    def set_html(self, v):
        self.html = v

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

    def set_alignment(self, alignment):
        if not alignment in ["left", "center", "right", "justified"]:
            raise ValueError("unknown alignment specified: '" +
                str(alignment) + "'")
        if self._current_align == alignment:
            return
        self._current_align = alignment
        self.needs_relayout = True

    def do_redraw(self):
        # Calculate content height:
        content_height = self._layout_height

        # Limit scrolling to reasonable area:
        max_scroll_down = max(0, content_height - self.height)
        self.scroll_y_offset = max(0, min(max_scroll_down,
            self.scroll_y_offset))

        # Draw label text:
        for fragment in self.text_obj.fragments:
            fragment.draw(self.renderer,
                fragment.x, fragment.y - self.scroll_y_offset,
                color=self.color,
                draw_scale=self.dpi_scale)

        # Draw scrollbar:
        self.draw_scrollbar(content_height, self.height,
            self.scroll_y_offset)

    def on_mousewheel(self, mouse_id, x, y):
        self.scroll_y_offset = max(0,
            self.scroll_y_offset -
            y * 50.0 * self.dpi_scale)
        self.needs_redraw = True

    def on_relayout(self):
        new_px_size = self.get_intended_text_size()
        if new_px_size != self.px_size:
            # Font size update!
            self.px_size = new_px_size
            self.text_obj.px_size = self.px_size
        self.text_obj.draw_scale = self.dpi_scale
        if self.style.has("topbar_text_size") and self.in_topbar():
            self.text_obj.px_size = \
                int(self.style.get("topbar_text_size"))
        layout_width = self.width
        if self._max_width != None and self._max_width < layout_width:
            layout_width = self._max_width
        (self._width, self._layout_height) = self.text_obj.layout(
            max_width=layout_width, align_if_none=self._current_align)

    def get_natural_width(self):
        if len(self.text_obj.text) == 0:
            return 0
        text_obj_copy = self.text_obj.copy()
        text_obj_copy.draw_scale = self.dpi_scale
        (w, h) = text_obj_copy.layout()
        return w

    def get_natural_height(self, given_width=None):
        if len(self.text_obj.text) == 0:
            return 0
        text_obj_copy = self.text_obj.copy()
        text_obj_copy.draw_scale = self.dpi_scale
        (w, h) = text_obj_copy.layout(max_width=given_width)
        return h

    @property
    def text(self):
        return self.text_obj.text

    @text.setter
    def text(self, t):
        self.text_obj.set_text(t)
        self.needs_relayout = True
        self.needs_redraw = True

    @property
    def html(self):
        return self.text_obj.html

    @html.setter
    def html(self, t):
        self.text_obj.set_html(t)
        self.needs_relayout = True
        self.needs_redraw = True

