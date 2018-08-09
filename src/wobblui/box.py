
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

    def layout(self):
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
                child_space += child.get_natural_width() + item_padding
            else:
                child_space += child.\
                    get_natural_height(max_width=self.width) +\
                    item_padding
        remaining_space = self.height - child_space
        if self.horizontal:
            remaining_space = self.width - child_space
        space_per_item = 0
        if expand_widget_count > 0:
            space_per_item = math.floor(
                remaining_space / expand_widget_count)
        child_id = -1
        cx = 0
        cy = 0
        for child in self._children:
            child_id += 1
            item_padding = round(self.padding * self.dpi_scale)
            if child_id == len(self._children) - 1:
                item_padding = 0
            assigned_w = child.width + item_padding
            assigned_h = child.height + item_padding
            space_for_this_item = space_per_item
            if expand_widget_count <= 1:
                # Make sure to use up all remaining space:
                if horizontal:
                    space_for_this_item = (remaining_space - cx)
                else:
                    space_for_this_item = (remaining_space - cy)
            expand_widget_count -= 1
            if self.expand_info[child_id] and horizontal:
                assigned_w += space_for_this_item
            elif self.expand_info[child_id] and not horizontal:
                assigned_h += space_for_this_item
            child.x = cx
            child.y = cy
            child.width = assigned_w
            child.height = assigned_h
            cx += assigned_w
            cy += assigned_h

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

    def get_natural_height(self, max_width=None):
        if not self.horizontal:
            total_h = 0
            for child in self._children:
                total_h += child.get_natural_height(max_width=max_width)
            return total_h
        elif len(self.children) == 0:
            return self.height
        else:
            max_h = 0
            for child in self._children:
                max_h = max(max_w, child.get_natural_height(
                    max_width=child.width))
            return max_h

    def add(self, item, expand=True):
        super().add(item)
        self.expand_info[len(self._children) - 1] = expand

    def add_spacer(self):
        super().add(BoxSpacer())
        self.expand_info[len(self._children) - 1] = expand

class VBox(Box):
    def __init__(self):
        super().__init__(False)

class HBox(Box):
    def __init__(self):
        super().__init__(True)


