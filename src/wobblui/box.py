
'''
wobblui - Copyright 2018 wobblui team, see AUTHORS.md

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.
'''

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
    def __init__(self, horizontal, box_surrounding_padding=0,
            stretch_children_on_secondary_axis=True):
        super().__init__(is_container=True)
        self.stretch_children_on_secondary_axis =\
            stretch_children_on_secondary_axis
        self.horizontal = (horizontal is True)
        self.expand_info = dict()
        self.shrink_info = dict()
        self.item_padding = 5.0
        self.box_surrounding_padding =\
            max(0, box_surrounding_padding)
        self.bg_color = None

    def set_background_color(self, c):
        if c is None:
            self.bg_color = None
            return
        self.bg_color = Color(c)

    def do_redraw(self):
        if self.bg_color != None:
            draw_rectangle(self.renderer, 0, 0,
                self.width, self.height, color=self.bg_color)
        self.draw_children()

    def on_relayout(self):
        # Adjust items on the non-box axis:
        for item in self._children:
            if self.horizontal:
                iheight = self.height -\
                    round(self.box_surrounding_padding *
                    2 * self.dpi_scale)
                if not self.stretch_children_on_secondary_axis:
                    iheight = min(iheight,
                        item.get_natural_height(item.width))
                item.height = iheight
            else:
                iwidth = self.width -\
                    round(self.box_surrounding_padding *
                    2 * self.dpi_scale)
                if not self.stretch_children_on_secondary_axis:
                    iwidth = min(iwidth,
                        item.get_natural_width(item.width))
                item.width = iwidth

        # Adjust size along box axis:
        expand_widget_count = 0
        shrink_widget_count = 0
        child_space = 0
        child_id = -1
        for child in self._children:
            child_id += 1
            if child.invisible:
                continue
            item_padding = round(self.item_padding * self.dpi_scale)
            if not self.got_visible_child_after_index(child_id):
                item_padding = 0
            if self.expand_info[child_id]:
                expand_widget_count += 1
            if self.shrink_info[child_id]:
                shrink_widget_count += 1
            if self.horizontal:
                child.width = child.get_natural_width()
                child_space += child.width + item_padding
            else:
                child.height = child.\
                    get_natural_height(given_width=child.width)
                child_space += child.height + item_padding
        remaining_space = (self.height - child_space -
            round(self.box_surrounding_padding * self.dpi_scale * 2))
        if self.horizontal:
            remaining_space = (self.width - child_space -
                round(self.box_surrounding_padding * self.dpi_scale * 2))
        expanding = True
        space_per_item = 0
        if expand_widget_count > 0 and remaining_space > 0:
            space_per_item = math.floor(
                remaining_space / expand_widget_count)
        elif shrink_widget_count > 0 and remaining_space < 0:
            expanding = False
            space_per_item = math.ceil(
                remaining_space / shrink_widget_count)
        child_id = -1
        cx = round(self.box_surrounding_padding * self.dpi_scale)
        cy = round(self.box_surrounding_padding * self.dpi_scale)
        for child in self._children:
            child_id += 1
            if child.invisible:
                continue
            assigned_w = max(1, math.ceil(child.width))
            assigned_h = max(1, math.ceil(child.height))
            if expanding and self.expand_info[child_id] and self.horizontal:
                assigned_w += space_per_item
            elif not expanding and self.shrink_info[child_id] and \
                    self.horizontal:
                assigned_w = max(1, assigned_w + space_per_item)
            elif expanding and self.expand_info[child_id] and \
                    not self.horizontal:
                assigned_h += space_per_item
            elif not expanding and self.shrink_info[child_id] and \
                    not self.horizontal:
                assigned_h = max(1, assigned_h + space_per_item)
            if expand_widget_count == 1 and \
                    not self.got_visible_child_after_index(child_id):
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
            item_padding = round(self.item_padding * self.dpi_scale)
            if not self.got_visible_child_after_index(child_id):
                item_padding = 0
            if self.horizontal:
                cx += assigned_w + item_padding
            else:
                cy += assigned_h + item_padding

        # Adjust items again on the non-box axis for horizontal layouts if
        # they are naturally scaled (not stretched), since their new width
        # can change their natural height:
        if self.horizontal and not self.stretch_children_on_secondary_axis:
            for item in self._children:
                iheight = self.height -\
                    round(self.box_surrounding_padding *
                    2 * self.dpi_scale)
                iheight = min(iheight,
                    item.get_natural_height(given_width=item.width))
                item.height = iheight

        # Update placement if not fully stretched on secondary axis:
        if not self.stretch_children_on_secondary_axis:
            for child in self.children:
                if child.invisible:
                    continue
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

        self.needs_redraw = True

    def got_visible_child_after_index(self, index):
        index += 1
        while index < len(self._children):
            if self._children[index].invisible:
                index += 1
                continue
            return True
        return False

    def get_natural_width(self):
        if self.horizontal:
            total_w = 0
            i = 0
            while i < len(self._children):
                child = self._children[i]
                if child.invisible:
                    i += 1
                    continue
                total_w += child.get_natural_width()
                item_padding = round(self.item_padding * self.dpi_scale)
                if not self.got_visible_child_after_index(i):
                    item_padding = 0
                total_w += item_padding
                i += 1
            total_w += round(self.box_surrounding_padding *
                self.dpi_scale * 2)
            return total_w
        elif len(self.children) == 0:
            return 0
        else:
            found_children = False
            max_w = 0
            for child in self._children:
                if child.invisible:
                    continue
                found_children = True
                max_w = max(max_w, child.get_natural_width())
            max_w += round(self.box_surrounding_padding *
                self.dpi_scale * 2)
            if not found_children:
                return 0
            return max_w

    def get_natural_height(self, given_width=None):
        if not self.horizontal:
            total_h = 0
            i = 0
            while i < len(self._children):
                child = self._children[i]
                if child.invisible:
                    i += 1
                    continue
                total_h += child.get_natural_height(given_width=given_width)
                item_padding = round(self.item_padding * self.dpi_scale)
                if not self.got_visible_child_after_index(i):
                    item_padding = 0
                total_h += item_padding
                i += 1
            total_h += round(self.box_surrounding_padding *
                self.dpi_scale * 2)
            return total_h
        elif len(self.children) == 0:
            return 0
        else:
            # Relayout at given width:
            relayout_at = given_width
            if relayout_at == None:
                relayout_at = self.get_natural_width()
            old_width = self.width
            old_needs_redraw = self.needs_redraw
            self.width = relayout_at
            self.on_relayout()

            # See how large everything turned out at this given width:
            found_children = False
            max_h = 0
            for child in self._children:
                if child.invisible:
                    continue
                found_children = True
                max_h = max(max_h, child.get_natural_height(
                    given_width=child.width))
            max_h += round(self.box_surrounding_padding *
                self.dpi_scale * 2)

            # Return to old layout:
            self.width = old_width
            self.on_relayout()
            self.needs_relayout = False
            self.needs_redraw = old_needs_redraw

            if not found_children:
                return (self.box_surrounding_padding *
                    self.dpi_scale * 2)
            return max_h

    def add(self, item, expand=True, shrink=False):
        super().add(item, trigger_resize=False)
        self.expand_info[len(self._children) - 1] = expand
        self.shrink_info[len(self._children) - 1] = shrink
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
    def __init__(self, box_surrounding_padding=0,
            stretch_children_on_secondary_axis=True):
        super().__init__(False,
            box_surrounding_padding=box_surrounding_padding,
            stretch_children_on_secondary_axis=\
                stretch_children_on_secondary_axis)

class HBox(Box):
    def __init__(self, box_surrounding_padding=0,
            stretch_children_on_secondary_axis=True):
        super().__init__(True,
            box_surrounding_padding=box_surrounding_padding,
            stretch_children_on_secondary_axis=\
                stretch_children_on_secondary_axis)

class CenterBox(Widget):
    def __init__(self, padding=0,
            child_minimum_width=0,
            expand_vertically=False,
            expand_horizontally=False):
        super().__init__(is_container=True)
        self.padding = padding
        self.child_minimum_width = child_minimum_width
        self.expand_vertically = expand_vertically
        self.expand_horizontally = expand_horizontally

    def do_redraw(self):
        self.draw_children()

    def get_natural_width(self):
        if len(self._children) == 0:
            return 0
        min_width = round(self.dpi_scale * self.child_minimum_width) 
        return max(min_width,
            self._children[0].get_natural_width()) +\
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
        if self.expand_horizontally:
            nat_width = child.get_natural_width()
            child.width = min(max(1, round(self.width -
                outer_padding * 2)),
                max(self.child_minimum_width, nat_width))
        else:
            child.width = max(1, round(self.width -
                outer_padding * 2))
        if not self.expand_vertically:
            child.height = min(round(self.height -
                outer_padding * 2), child.get_natural_height(
                given_width=child.width))
        else:
            child.height = max(1, self.height -
                self.padding * 2 * self.dpi_scale)
        child.x = math.floor((self.width - child.width) / 2)
        child.y = math.floor((self.height - child.height) / 2)
        child.relayout_if_necessary()


