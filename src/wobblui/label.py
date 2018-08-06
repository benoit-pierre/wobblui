
from wobblui.color import Color
from wobblui.richtext import RichText
from wobblui.widget import Widget

class Label(Widget):
    def __init__(self, text=""):
        super().__init__()
        font_family = self.style.get("widget_font_family")
        px_size = self.style.get("widget_text_size") 
        self.text_obj = RichText(font_family=font_family,
            px_size=px_size)
        self.text_obj.set_text(text)
        self.color = Color.black
        self._current_align = "left"
        self._layout_max_width = None

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
        self.update_layout

    def do_redraw(self):
        for fragment in self.text_obj.fragments:
            fragment.draw(self.renderer,
                fragment.x, fragment.y,
                color=self.color,
                draw_scale=self.style.dpi_scale)

    def _internal_on_resized(self):
        old_w = self._width
        if self._max_width != self._layout_max_width:
            self.update_layout()
            self._width = max(old_w, self._width)

    def update_layout(self):
        self.text_obj.layout(max_width=self._max_width,
            align_if_none=self._current_align)
        (self._width, self._height) = self.text_obj.layout()

    @property
    def text(self):
        return self.text_obj.text

    @text.setter
    def text(self, t):
        self.text_obj.set_text(t)
        self.update_layout()

    @property
    def html(self):
        return self.text_obj.html

    @text.setter
    def html(self, t):
        self.text_obj.set_html(t)
        self.update_layout()

