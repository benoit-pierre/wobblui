
import math
import sdl2 as sdl

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
        self.topbar_children = []
        self.relayout()

    def get_children(self):
        return self._children + self.topbar_children

    def add_to_top(self, child):
        self.topbar_children.append(child)
        child.internal_override_parent(self)
        self.relayout()
        self.needs_redraw = True

    def do_redraw(self):
        self.relayout()
        c = Color((100, 100, 100))
        if self.style != None:
            c = Color(self.style.get("topbar_bg"))
        sdl.SDL_SetRenderDrawColor(self.renderer,
            255, 255, 255, 255)
        sdl.SDL_RenderClear(self.renderer)
        draw_rectangle(self.renderer, 0, 0,
            self._width, max(round(self.padding * 2),
            self.topbar_height),
            color=c)
        for child in self.topbar_children:
            child.draw(child.x, child.y)

    def relayout(self):
        topbar_height = round((5 + self.padding * 2) * self.dpi_scale)
        current_x = round(self.padding * self.dpi_scale)
        first_child = True
        current_y = round(self.padding * self.dpi_scale)
        for child in self.topbar_children:
            child.x = current_x
            if first_child:
                first_child = False
            else:
                current_x += round(self.child_padding * self.dpi_scale)
            child.x = current_x
            child.y = current_y
            natural_height = child.get_natural_height()
            if child.height < natural_height:
                child.height = natural_height
            topbar_height = max(math.ceil(
                child.height + self.padding * 2 * self.dpi_scale),
                topbar_height)
            current_x += math.ceil(child.width)
        self.topbar_height = topbar_height
        if self._height < topbar_height:
            self._height = topbar_height
            self.needs_redraw = True

