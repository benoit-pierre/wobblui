
import math
import sdl2 as sdl

from wobblui.color import Color
from wobblui.gfx import draw_rectangle
from wobblui.widget import Widget

class BoxSpacer(Widget):
    def __init__(self):
        super().__init__(is_container=False)

class Box(Widget):
    def __init__(self, horizontal):
        super().__init__(is_container=True)
        self.horizontal = (horizontal is True)
        self.expand_info = dict()
        self.padding = 5.0
        self.layout()

    def do_redraw(self):
        self.draw_children()

    def _internal_on_moved(self, internal_data=None):
        self.layout()

    def layout(self):
        # Adjust items on the non-box axis:
        for item in self._children:
            if self.horizontal:
                nat_height = item.get_natural_height(given_width=\
                    item.width)
                if nat_height < self.height:
                    item.height = nat_height
                else:
                    item.height = self.height
            else:
                nat_width = item.get_natural_width()
                if nat_width < self.width:
                    item.width = nat_width
                else:
                    item.width = self.width

        # Adjust size along box axis:
        expand_widget_count = 0
        child_space = 0
        child_id = -1
        for child in self._children:
            child_id += 1
            item_padding = round(self.padding * self.dpi_scale)
            if child_id == len(self._children) - 1:
                item_padding = 0
            if self.expand_info[child_id]:
                expand_widget_count += 1
            if self.horizontal:
                child.width = child.get_natural_width()
                child.height = min(child.get_natural_height(
                    given_width=child.width),
                    self.height)
                child_space += child.width + item_padding
            else:
                child.width = min(self.width, child.get_natural_width())
                child.height = child.\
                    get_natural_height(given_width=self.width)
                child_space += child.height + item_padding
        remaining_space = max(0, self.height - child_space)
        if self.horizontal:
            remaining_space = max(0, self.width - child_space)
        space_per_item = 0
        if expand_widget_count > 0:
            space_per_item = math.floor(
                remaining_space / expand_widget_count)
        child_id = -1
        cx = 0
        cy = 0
        for child in self._children:
            child_id += 1
            assigned_w = max(1, math.ceil(child.width))
            assigned_h = max(1, math.ceil(child.height))
            if self.expand_info[child_id] and self.horizontal:
                assigned_w += space_per_item
            elif self.expand_info[child_id] and not self.horizontal:
                assigned_h += space_per_item
            if expand_widget_count <= 1 and \
                    child_id == len(self._children) - 1:
                # Make sure to use up all remaining space:
                if self.horizontal:
                    assigned_w = (self.width + self.x - cx)
                else:
                    assigned_h = (self.height + self.y - cy)
            expand_widget_count -= 1
            child.x = cx
            child.y = cy
            child.width = assigned_w
            child.height = assigned_h
            if self.horizontal and child.height < self.height:
                child.y += math.floor((self.height - child.height) / 2.0)
            elif not self.horizontal and child.width < self.width:
                child.x += math.floor((self.width - child.width) / 2.0)
            item_padding = round(self.padding * self.dpi_scale)
            if child_id == len(self._children) - 1:
                item_padding = 0
            if self.horizontal:
                cx += assigned_w + item_padding
            else:
                cy += assigned_h + item_padding
        self.needs_redraw = True

    def get_natural_width(self):
        if self.horizontal:
            total_w = 0
            for child in self._children:
                total_w += child.get_natural_width()
            return total_w
        elif len(self.children) == 0:
            return self.width
        else:
            max_w = 0
            for child in self._children:
                max_w = max(max_w, child.get_natural_width())
            return max_w

    def get_natural_height(self, given_width=None):
        if not self.horizontal:
            total_h = 0
            for child in self._children:
                total_h += child.get_natural_height(given_width=given_width)
            return total_h
        elif len(self.children) == 0:
            return self.height
        else:
            max_h = 0
            for child in self._children:
                max_h = max(max_h, child.get_natural_height(
                    given_width=child.width))
            return max_h

    def _internal_on_resized(self, internal_data=None):
        self.layout()

    def add(self, item, expand=True):
        super().add(item, trigger_resize=False)
        self.expand_info[len(self._children) - 1] = expand
        if self.horizontal:
            item.width = item.get_natural_width()
            item.height = item.get_natural_height()
        else:
            item.width = self.width
            item.height = item.get_natural_height(given_width=self.width)
        self.layout()

    def add_spacer(self):
        self.add(BoxSpacer(), expand=True)
        assert(len(self._children) > 0)

class VBox(Box):
    def __init__(self):
        super().__init__(False)

class HBox(Box):
    def __init__(self):
        super().__init__(True)

class CenterBox(Widget):
    def __init__(self, padding=0):
        super().__init__(is_container=True)
        self.padding = padding

    def do_redraw(self):
        self.draw_children()
 
    def relayout(self):
        if len(self._children) == 0:
            return
        outer_padding = (self.padding * self.dpi_scale)
        child = self._children[0]
        nat_width = child.get_natural_width()
        child.width = min(round(self.width -
            outer_padding * 2), nat_width)
        child.height = min(round(self.height -
            outer_padding * 2), child.get_natural_height(
            given_width=child.width))
        child.x = math.floor((self.width - child.width) / 2) + self.x
        child.y = math.floor((self.height - child.height) / 2) + self.y

    def _internal_on_resized(self, internal_data=None):
        self.relayout()

    def _internal_on_moved(self, internal_data=None):
        self.relayout()

    def add(self, item):
        super().add(item)
        self.relayout()



