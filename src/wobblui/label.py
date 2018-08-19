
import sdl2 as sdl

from wobblui.color import Color
from wobblui.richtext import RichText
from wobblui.widget import Widget

class Label(Widget):
    def __init__(self, text="", color=None):
        super().__init__()
        self.type = "label"
        font_family = self.style.get("widget_font_family")
        px_size = self.style.get("widget_text_size") 
        self._layout_height = 0
        self.text_obj = RichText(font_family=font_family,
            px_size=px_size,
            draw_scale=self.dpi_scale)
        self._current_align = "left"
        if text.find("<") >= 0 and (text.find("/>") > 0 or
                text.find("/ >") > 0 or
                (text.find("</") > 0 and text.find(">") > 0)):
            self.html = text
        else:
            self.text = text
        self._user_set_color = color
        self._layout_max_width = None

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
        self.needs_relayout = True
        for fragment in self.text_obj.fragments:
            fragment.draw(self.renderer,
                fragment.x, fragment.y,
                color=self.color,
                draw_scale=self.dpi_scale)

    def _internal_on_resized(self, internal_data=None):
        old_w = self._width
        if self._max_width != self._layout_max_width:
            self.needs_relayout = True
            self._width = max(old_w, self._width)

    def on_relayout(self):
        self.text_obj.draw_scale = self.dpi_scale
        self.text_obj.px_size = int(self.style.get("widget_text_size"))
        if self.style.has("topbar_text_size") and self.in_topbar():
            self.text_obj.px_size = \
                int(self.style.get("topbar_text_size"))
        self.text_obj.layout(max_width=self._max_width,
            align_if_none=self._current_align)
        layout_width = self.width
        if self._max_width != None and self._max_width < layout_width:
            layout_width = self._max_width
        (self._width, self._layout_height) = self.text_obj.layout(
            max_width=layout_width)
        self._height = self._layout_height

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

    @text.setter
    def html(self, t):
        self.text_obj.set_html(t)
        self.needs_relayout = True
        self.needs_redraw = True

