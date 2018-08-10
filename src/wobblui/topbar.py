
import math
import sdl2 as sdl

from wobblui.box import HBox
from wobblui.color import Color
from wobblui.gfx import draw_rectangle
from wobblui.widget import Widget

class Topbar(Widget):
    def __init__(self, padding=None):
        super().__init__(is_container=True)
        self.padding = 15
        if padding != None:
            self.padding = max(0, round(padding))
        self.child_padding = 8
        if self.padding <= 0:
            self.child_padding = 0
        self.topbar_height = 0
        self.topbar_box = HBox()
        self.relayout()

    def _internal_on_moved(self, internal_data=None):
        self.relayout()

    def get_children(self):
        return self._children + self.topbar_box.children

    def add_to_top(self, child, expand=True):
        self.topbar_box.add(child, expand=expand)
        child.internal_override_parent(self)
        self.topbar_box.height = self.topbar_box.get_natural_height()
        self.relayout()
        self.needs_redraw = True

    @property
    def border_size(self):
        return max(1, round(
            2.0 * self.dpi_scale))

    def do_redraw(self):
        self.relayout()
        c = Color((100, 100, 100))
        if self.style != None:
            c = Color(self.style.get("topbar_bg"))
        sdl.SDL_SetRenderDrawColor(self.renderer,
            255, 255, 255, 255)
        sdl.SDL_RenderClear(self.renderer)

        # Draw topbar background:
        topbar_actual_height = max(round(self.padding * 2),
            self.topbar_height)
        draw_rectangle(self.renderer, 0, 0,
            self._width, topbar_actual_height,
            color=c)

        # Draw topbar items:
        for child in self.topbar_box.children:
            child.draw(child.x, child.y)

        # Draw border:
        c = Color((100, 100, 100))
        if self.style != None:
            c = Color(self.style.get("border"))
        draw_rectangle(self.renderer, 0, topbar_actual_height,
            self._width, self.border_size,
            color=c)

        # Draw background of below-topbar area:
        c = Color((255, 255, 255))
        if self.style != None:
            c = Color(self.style.get("window_bg"))
        draw_rectangle(self.renderer,
            0, self.topbar_height + self.border_size,
            self._width,
            self._height - topbar_actual_height - self.border_size,
            color=c)

        # Draw below-topbar items:
        for child in self._children:
            child.draw(child.x, child.y)

    def relayout(self):
        topbar_height = round((5 + self.padding * 2) * self.dpi_scale)
        current_x = round(self.padding * self.dpi_scale)
        first_child = True
        current_y = round(self.padding * self.dpi_scale)
        self.topbar_box.x = current_x
        self.topbar_box.y = current_y
        self.topbar_box.width = self.width - round(
            self.padding * self.dpi_scale * 2.0)
        self.topbar_box.height = self.topbar_box.get_natural_height(
            given_width=self.topbar_box.width)
        topbar_height = round(self.topbar_box.height + (
            self.padding * 2) * self.dpi_scale)
        for child in self._children:
            child.x = 0
            child.y = topbar_height + self.border_size
            child.width = self.width
            child.height = self.height - child.y
        self.topbar_height = topbar_height
        if self._height < topbar_height:
            self._height = topbar_height
            self.needs_redraw = True

