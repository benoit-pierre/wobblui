
import math
import sdl2 as sdl

from wobblui.color import Color
from wobblui.gfx import draw_rectangle
from wobblui.widget import Widget

class BoxSpacer(Widget):
    def __init__(self):
        super().__init__(is_container=False)

    def get_natural_width(self):
        return 0

    def get_natural_height(self, given_width=None):
        return 0

class Box(Widget):
    def __init__(self, horizontal, box_surrounding_padding=0):
        super().__init__(is_container=True)
        self.horizontal = (horizontal is True)
        self.expand_info = dict()
        self.item_padding = 5.0
        self.box_surrounding_padding =\
            max(0, box_surrounding_padding)

    def do_redraw(self):
        self.draw_children()

    def on_relayout(self):
        # Adjust items on the non-box axis:
        for item in self._children:
            if self.horizontal:
                item.height = self.height -\
                    round(self.box_surrounding_padding *
                    2 * self.dpi_scale)
            else:
                item.width = self.width -\
                    round(self.box_surrounding_padding *
                    2 * self.dpi_scale)

        # Adjust size along box axis:
        expand_widget_count = 0
        child_space = 0
        child_id = -1
        for child in self._children:
            child_id += 1
            item_padding = round(self.item_padding * self.dpi_scale)
            if child_id == len(self._children) - 1:
                item_padding = 0
            if self.expand_info[child_id]:
                expand_widget_count += 1
            if self.horizontal:
                child.width = child.get_natural_width()
                child_space += child.width + item_padding
            else:
                child.height = child.\
                    get_natural_height(given_width=self.width)
                child_space += child.height + item_padding
        remaining_space = max(0, self.height - child_space -
            round(self.box_surrounding_padding * self.dpi_scale * 2))
        if self.horizontal:
            remaining_space = max(0, self.width - child_space -
                round(self.box_surrounding_padding * self.dpi_scale * 2))
        space_per_item = 0
        if expand_widget_count > 0:
            space_per_item = math.floor(
                remaining_space / expand_widget_count)
        child_id = -1
        cx = round(self.box_surrounding_padding * self.dpi_scale)
        cy = round(self.box_surrounding_padding * self.dpi_scale)
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
                    assigned_w = (self.width - cx -
                        round(self.box_surrounding_padding *
                        self.dpi_scale))
                else:
                    assigned_h = (self.height - cy -
                        round(self.box_surrounding_padding *
                        self.dpi_scale))
            expand_widget_count -= 1
            child.x = cx
            child.y = cy
            if self.horizontal:
                child.width = assigned_w
            else:
                child.height = assigned_h
            if self.horizontal and child.height < (self.height -
                    round(self.box_surrounding_padding *
                        self.dpi_scale * 2)):
                child.y += math.floor((self.height - child.height -
                    round(self.box_surrounding_padding *
                        self.dpi_scale * 2)) / 2.0)
            elif not self.horizontal and child.width < (self.width -
                    round(self.box_surrounding_padding *
                        self.dpi_scale * 2)):
                child.x += math.floor((self.width - child.width -
                    round(self.box_surrounding_padding *
                        self.dpi_scale * 2)) / 2.0)
            item_padding = round(self.item_padding * self.dpi_scale)
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
            i = 0
            while i < len(self._children):
                child = self._children[i]
                total_w += child.get_natural_width()
                item_padding = round(self.item_padding * self.dpi_scale)
                if i == len(self._children) - 1:
                    item_padding = 0
                total_w += item_padding
                i += 1
            total_w += round(self.box_surrounding_padding *
                self.dpi_scale * 2)
            return total_w
        elif len(self.children) == 0:
            return 0
        else:
            max_w = 0
            for child in self._children:
                max_w = max(max_w, child.get_natural_width())
            max_w += round(self.box_surrounding_padding *
                self.dpi_scale * 2)
            return max_w

    def get_natural_height(self, given_width=None):
        if not self.horizontal:
            total_h = 0
            i = 0
            while i < len(self._children):
                child = self._children[i]
                total_h += child.get_natural_height(given_width=given_width)
                item_padding = round(self.item_padding * self.dpi_scale)
                if i == len(self._children) - 1:
                    item_padding = 0
                total_h += item_padding
                i += 1
            total_h += round(self.box_surrounding_padding *
                self.dpi_scale * 2)
            return total_h
        elif len(self.children) == 0:
            return 0
        else:
            max_h = 0
            for child in self._children:
                max_h = max(max_h, child.get_natural_height(
                    given_width=None))  # horizontal box doesn't
                                        # support compression right now
            max_h += round(self.box_surrounding_padding *
                self.dpi_scale * 2)
            return max_h

    def add(self, item, expand=True):
        super().add(item, trigger_resize=False)
        self.expand_info[len(self._children) - 1] = expand
        if self.horizontal:
            item.width = item.get_natural_width()
            item.height = item.get_natural_height()
        else:
            item.width = self.width
            item.height = item.get_natural_height(given_width=self.width)

    def add_spacer(self):
        self.add(BoxSpacer(), expand=True)
        assert(len(self._children) > 0)

class VBox(Box):
    def __init__(self, box_surrounding_padding=0):
        super().__init__(False,
            box_surrounding_padding=box_surrounding_padding)

class HBox(Box):
    def __init__(self, box_surrounding_padding=0):
        super().__init__(True,
            box_surrounding_padding=box_surrounding_padding)

class CenterBox(Widget):
    def __init__(self, padding=0):
        super().__init__(is_container=True)
        self.padding = padding

    def do_redraw(self):
        self.draw_children()

    def get_natural_width(self):
        if len(self._children) == 0:
            return 0
        return self._children[0].get_natural_width() +\
            (self.padding * 2 * self.dpi_scale)

    def get_natural_height(self, given_width=None):
        if len(self._children) == 0:
            return 0
        v = given_width
        if v != None:
            v -= (self.padding * 2 * self.dpi_scale)
        return self._children[0].get_natural_height(
            given_width=v) +\
            (self.padding * 2 * self.dpi_scale)

    def on_relayout(self):
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
        child.x = math.floor((self.width - child.width) / 2)
        child.y = math.floor((self.height - child.height) / 2)



