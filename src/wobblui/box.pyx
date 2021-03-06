#cython: language_level=3

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

from wobblui.color cimport Color
from wobblui.gfx cimport draw_rectangle
from wobblui.image cimport RenderImage
from wobblui.scrollbarwidget cimport ScrollbarDrawingWidget
from wobblui.widget cimport Widget

cdef class BoxSpacer(Widget):
    def __init__(self):
        super().__init__(is_container=False)

    def get_natural_width(self):
        return 0

    def get_natural_height(self, given_width=None):
        return 0

cdef class Box(ScrollbarDrawingWidget):
    def __init__(self,
            horizontal,
            box_surrounding_padding=0,
            default_expand_on_secondary_axis=True,
            item_padding=5.0,
            with_border=False
            ):
        super().__init__(is_container=True)
        self.default_expand_on_secondary_axis =\
            default_expand_on_secondary_axis
        self.horizontal = (horizontal is True)
        self.expand_info = dict()
        self.shrink_info = dict()
        self.item_padding = item_padding
        self.border = 0
        if with_border:
            self.border = 1
        self.box_surrounding_padding =\
            max(0, box_surrounding_padding)
        self.bg_color = None
        self.actual_layout_height = -1
        self.actual_layout_width = -1
        self.scroll_offset_y = 0
        self._background_image = None
        self._background_image_keep_aspect = False

    def set_background_image(self, img, keep_aspect_ratio=True):
        if not isinstance(img, RenderImage):
            img = RenderImage(img)
        self._background_image = img
        self._background_image_keep_aspect = (keep_aspect_ratio is True)
        self.bg_color = None

    def set_background_color(self, c):
        if c is None:
            self.bg_color = None
            return
        self._background_image = None
        self.bg_color = Color(c)

    def do_redraw(self):
        if self.bg_color != None:
            draw_rectangle(self.renderer, 0, 0,
                self.width, self.height, color=self.bg_color)
        elif self._background_image is not None:
            if not self._background_image_keep_aspect:
                self._background_image.draw(self.renderer,
                    0, 0, self.width, self.height)
            else:
                size = self._background_image.render_size
                scale_up_x = (self.width / max(1, size[0]))
                scale_up_y = (self.height / max(1, size[1]))
                scale_up = max(scale_up_x, scale_up_y)
                render_w = (size[0] * scale_up)
                render_offset_x = (self.width - render_w) * 0.5
                render_h = (size[1] * scale_up)
                render_offset_y = (self.height - render_h) * 0.5
                self._background_image.draw(self.renderer,
                    round(render_offset_x), round(render_offset_y),
                    round(render_w), round(render_h))

        max_scroll = (self.actual_layout_height - self.height)
        self.scroll_offset_y = max(0, min(self.scroll_offset_y, max_scroll))
        self._child_mouse_event_shift_y = round(self.scroll_offset_y)
        if max_scroll > 2:
            self.draw_scrollbar(self.actual_layout_height,
                self.height, self.scroll_offset_y)

        # Draw with temporarily applied scroll offset:
        move_y = round(self.scroll_offset_y)
        for child in self.children:
            child.y -= move_y
        try:
            self.draw_children()
        finally:
            for child in self.children:
                child.y += move_y

        # Draw border:
        border_color = Color.black()
        if self.style is not None:
            border_color = Color(self.style.get("widget_text"))
        if self.border > 0:
            border = self.effective_border
            draw_rectangle(
                self.renderer,
                0, 0, border, self.height,
                color=border_color
            )
            draw_rectangle(
                self.renderer,
                self.width - border, 0, border, self.height,
                color=border_color
            )
            draw_rectangle(
                self.renderer,
                0, 0, self.width, border,
                color=border_color
            )
            draw_rectangle(
                self.renderer,
                0, self.height - border, self.width, border,
                color=border_color
            )

    def on_mousewheel(self, mouse_id, x, y):
        self.scroll_offset_y = max(0,
            self.scroll_offset_y -
            y * 50.0 * self.dpi_scale)
        max_scroll = (self.actual_layout_height - self.height)
        self.scroll_offset_y = max(0, min(self.scroll_offset_y, max_scroll))
        self._child_mouse_event_shift_y = round(self.scroll_offset_y)
        self.needs_redraw = True

    def got_exactly_one_flexible_child(self, horizontal):
        """ Check if there is exactly one child that is both shrinkable
            and expandable, and all other children are fixed (not shrinkable,
            and not expandable).

            Returns True if these conditions are met, otherwise Fals.e
        """

        flexible_children_count = 0
        child_id = -1
        for item in self._children:
            child_id += 1
            if child_id in self.expand_info and \
                    ((horizontal and self.expand_info[child_id][0]) or
                    (not horizontal and self.expand_info[child_id][1])):
                if not child_id in self.shrink_info or \
                        not self.shrink_info[child_id]:
                    return False
                flexible_children_count += 1
                if flexible_children_count > 1:
                    return False
            elif child_id in self.shrink_info and \
                    self.shrink_info[child_id]:
                return False
        return (flexible_children_count == 1)

    @property
    def effective_border(self):
        if self.border <= 0.001:
            return 0
        return max(1, round(self.border * self.dpi_scale))

    def on_relayout(self):
        layout_height = 0
        layout_width = 0

        # Adjust items on the non-box axis:
        child_id = -1
        for item in self._children:
            child_id += 1
            if self.horizontal:
                iheight = self.height -\
                    round(self.box_surrounding_padding *
                    self.dpi_scale) * 2 - \
                    self.effective_border * 2
                if not self.expand_info[child_id][1]:
                    iheight = min(iheight,
                        item.get_desired_height(item.width))
                item.height = iheight
            else:
                iwidth = self.width -\
                    round(self.box_surrounding_padding *
                    self.dpi_scale) * 2 - \
                    self.effective_border * 2
                if not self.expand_info[child_id][0]:
                    iwidth = min(iwidth,
                        item.get_desired_width(item.width))
                item.width = iwidth

        # Adjust size along box axis:
        expand_widget_count = 0
        shrink_widget_count = 0
        child_space = 0
        child_id = -1
        for child in self._children:
            child_id += 1
            if child.invisible:  # skip if invisible
                continue

            # Determine padding and count expanding/shrinking children:
            item_padding = round(self.item_padding * self.dpi_scale)
            if not self.got_visible_child_after_index(child_id):
                item_padding = 0
            if self.expand_info[child_id][0 if self.horizontal else 1]:
                expand_widget_count += 1
            if self.shrink_info[child_id]:
                shrink_widget_count += 1

            # Set child's dimensions along main box axis:
            if (not self.got_exactly_one_flexible_child(self.horizontal) or
                    not self.expand_info[child_id][0 if self.horizontal else 1]
                    ):
                # Regular case: add up all children as usual
                if self.horizontal:
                    child.width = child.get_desired_width()
                    child_space += child.width + item_padding
                else:
                    child.height = child.\
                        get_desired_height(given_width=child.width)
                    child_space += child.height + item_padding
            else:
                # SPECIAL CASE / OPTIMIZATION:
                # This is the only flexible child widget, all others
                # are fixed. This means it will be stretched/shrunk, but
                # without need for proportional stretching since it's
                # only this widget stretched/shrunk. (Proportional
                # would require it to have its proper natural size here)
                #   --> we'll stuff it in whatever, non-natural size,
                #       since natural size may take long in rare cases
                if self.horizontal:
                    if child.width <= 0:
                        child.width = 1
                    child_space += child.width + item_padding
                else:
                    if child.height <= 0:
                        child.height = 1
                    child_space += child.height + item_padding
        remaining_space = (self.height - child_space -
            round(self.box_surrounding_padding * self.dpi_scale) * 2 +
            self.effective_border * 2)
        if self.horizontal:
            remaining_space = (self.width - child_space -
                round(self.box_surrounding_padding * self.dpi_scale) * 2 +
                self.effective_border * 2)
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
        cx = round(self.box_surrounding_padding * self.dpi_scale) +\
            self.effective_border
        cy = round(self.box_surrounding_padding * self.dpi_scale) +\
            self.effective_border
        for child in self._children:
            child_id += 1
            if child.invisible:
                continue
            assigned_w = max(1, math.ceil(child.width))
            assigned_h = max(1, math.ceil(child.height))
            if (expanding and
                    self.expand_info[child_id][0 if self.horizontal else 1]
                    and self.horizontal):
                assigned_w += space_per_item
            elif not expanding and self.shrink_info[child_id] and \
                    self.horizontal:
                assigned_w = max(1, assigned_w + space_per_item)
            elif (expanding and
                    self.expand_info[child_id][0 if self.horizontal else 1]
                    and not self.horizontal):
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
                        self.dpi_scale) - self.effective_border)
                else:
                    assigned_h = (self.height - cy -
                        round(self.box_surrounding_padding *
                        self.dpi_scale) - self.effective_border)
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
        if self.horizontal:
            i = -1
            for item in self._children:
                i += 1
                if self.expand_info[i][1 if self.horizontal else 0]:
                    continue
                iheight = self.height -\
                    round(self.box_surrounding_padding *
                    self.dpi_scale) * 2 -\
                    self.effective_border * 2
                iheight = min(iheight,
                    item.get_desired_height(given_width=item.width))
                item.height = iheight

        # Update placement if not fully stretched on secondary axis:
        i = -1
        for child in self.children:
            i += 1
            if child.invisible:
                continue
            if self.expand_info[i][1 if self.horizontal else 0]:
                continue
            if self.horizontal and child.height < (self.height -
                    round(self.box_surrounding_padding *
                          self.dpi_scale) * 2 -
                    self.effective_border * 2):
                child.y += math.floor((self.height - child.height -
                    round(self.box_surrounding_padding *
                          self.dpi_scale) * 2 -
                    self.effective_border * 2) / 2.0)
            elif not self.horizontal and child.width < (self.width -
                    round(self.box_surrounding_padding *
                          self.dpi_scale) * 2 -
                    self.effective_border * 2):
                child.x += math.floor((self.width - child.width -
                    round(self.box_surrounding_padding *
                          self.dpi_scale) * 2 -
                    self.effective_border * 2) / 2.0)

        # Compute layout dimensions:
        for child in self.children:
            if child.invisible:
                continue
            layout_width = max(layout_width, child.x + child.width)
            layout_height = max(layout_height, child.y + child.height)

        self.needs_redraw = True
        self.actual_layout_width = layout_width
        self.actual_layout_height = layout_height

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
                total_w += child.get_desired_width()
                item_padding = round(self.item_padding * self.dpi_scale)
                if not self.got_visible_child_after_index(i):
                    item_padding = 0
                total_w += item_padding
                i += 1
            total_w += round(self.box_surrounding_padding *
                self.dpi_scale) * 2 + self.effective_border * 2
            return total_w
        elif len(self.children) == 0:
            return round(self.box_surrounding_padding *
                self.dpi_scale) * 2 + self.effective_border * 2
        else:
            found_children = False
            max_w = 0
            for child in self._children:
                if child.invisible:
                    continue
                found_children = True
                max_w = max(max_w, child.get_desired_width())
            max_w += round(self.box_surrounding_padding *
                self.dpi_scale) * 2 + self.effective_border * 2
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
                total_h += child.get_desired_height(given_width=given_width)
                item_padding = round(self.item_padding * self.dpi_scale)
                if not self.got_visible_child_after_index(i):
                    item_padding = 0
                total_h += item_padding
                i += 1
            total_h += round(self.box_surrounding_padding *
                self.dpi_scale) * 2 + self.effective_border * 2
            return total_h
        elif len(self.children) == 0:
            return round(self.box_surrounding_padding *
                self.dpi_scale) * 2 + self.effective_border * 2
        else:
            # Relayout at given width:
            relayout_at = given_width
            if relayout_at == None:
                relayout_at = self.get_desired_width()
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
                max_h = max(max_h, child.get_desired_height(
                    given_width=child.width))
            max_h += round(self.box_surrounding_padding *
                self.dpi_scale * 2) + self.effective_border * 2

            # Return to old layout:
            self.width = old_width
            self.on_relayout()
            self.needs_relayout = False
            self.needs_redraw = old_needs_redraw

            if not found_children:
                return round(self.box_surrounding_padding *
                    self.dpi_scale) * 2 + self.effective_border * 2
            return max_h

    def add(self,
            item,
            expand=True,
            shrink=False,
            expand_horizontally=None,
            expand_vertically=None
            ):
        super().add(item, trigger_resize=False)
        if not expand:
            if expand_horizontally is not None or \
                    expand_vertically is not None:
                raise ValueError("cannot specify expand=False " +
                    "but also expand_horizontally or " +
                    "expand_vertically. Please specify " +
                    "only either the expand option, or the " +
                    "expand_horizontally + expand_vertically options!")
            if self.horizontal or \
                    not self.default_expand_on_secondary_axis:
                expand_horizontally = False
            else:
                expand_horizontally = True
            if not self.horizontal or \
                    not self.default_expand_on_secondary_axis:
                expand_vertically = False
            else:
                expand_vertically = True
        else:
            if expand_horizontally is False and \
                    expand_vertically is False:
                raise ValueError("cannot specify expand=True " +
                    "but also both expand_horizontally/expand_vertically " +
                    "set to False. Please specify " +
                    "only either the expand option, or the " +
                    "expand_horizontally + expand_vertically options!")
            if self.horizontal and not self.default_expand_on_secondary_axis:
                expand_horizontally = False
            elif not self.horizontal and \
                    not self.default_expand_on_secondary_axis:
                expand_vertically = False
            if expand_horizontally is not False:
                expand_horizontally = True
            if expand_vertically is not False:
                expand_vertically = True
        self.expand_info[len(self._children) - 1] = (
            expand_horizontally,
            expand_vertically
        )
        self.shrink_info[len(self._children) - 1] = shrink
        if self.horizontal:
            item.size_change(item.get_desired_width(),
                             item.get_desired_height())
        else:
            item.size_change(
                self.width,
                item.get_desired_height(given_width=self.width),
            )

    def add_spacer(self):
        self.add(BoxSpacer(), expand=True, shrink=True)
        assert(len(self._children) > 0)

cdef class VBox(Box):
    def __init__(self, box_surrounding_padding=0,
            default_expand_on_secondary_axis=True,
            item_padding=5.0,
            with_border=False):
        super().__init__(False,
            box_surrounding_padding=box_surrounding_padding,
            default_expand_on_secondary_axis=\
                default_expand_on_secondary_axis,
            item_padding=item_padding,
            with_border=with_border,
        )

cdef class HBox(Box):
    def __init__(self, box_surrounding_padding=0,
            default_expand_on_secondary_axis=True,
            item_padding=5.0,
            with_border=False):
        super().__init__(True,
            box_surrounding_padding=box_surrounding_padding,
            default_expand_on_secondary_axis=\
                default_expand_on_secondary_axis,
            item_padding=item_padding,
            with_border=with_border,
        )

cdef class CenterBox(Widget):
    def __init__(self, content_padding=0,
            child_minimum_width=0,
            child_fixed_width=-1,
            child_fixed_height=-1,
            expand_vertically=False,
            expand_horizontally=False):
        super().__init__(is_container=True)
        self.content_padding = content_padding
        self.child_minimum_width = child_minimum_width
        self.child_fixed_width = child_fixed_width
        self.child_fixed_height = child_fixed_height
        self.expand_vertically = expand_vertically
        self.expand_horizontally = expand_horizontally
        self.bg_color = None

    def set_background_color(self, c):
        if c is None:
            self.bg_color = None
            return
        self.bg_color = Color(c)

    def do_redraw(self):
        if self.bg_color != None:
            x = self.content_padding
            y = self.content_padding
            w = self.width - self.content_padding * 2
            h = self.height - self.content_padding * 2
            if self.child_fixed_width >= 0:
                w = self.child_fixed_width
                x = round(max(0, self.width - self.child_fixed_width) * 0.5)
            if self.child_fixed_height >= 0:
                h = self.child_fixed_height
                y = round(max(0, self.height - self.child_fixed_height) * 0.5)
            draw_rectangle(self.renderer,
                x, y, w, h,
                color=self.bg_color)
        self.draw_children()

    def get_natural_width(self):
        if self.child_fixed_width > 0:
            return (self.content_padding * 2 * self.dpi_scale) + \
                self.child_fixed_width * self.dpi_scale
        if len(self._children) == 0:
            return 0
        min_width = round(self.dpi_scale * self.child_minimum_width) 
        return max(min_width,
            self._children[0].get_desired_width()) +\
            (self.content_padding * 2 * self.dpi_scale)

    def get_natural_height(self, given_width=None):
        if self.child_fixed_height > 0:
            return (self.content_padding * 2 * self.dpi_scale) + \
                self.child_fixed_height * self.dpi_scale
        if len(self._children) == 0:
            return 0
        v = given_width
        if v != None:
            v -= (self.content_padding * 2 * self.dpi_scale)
        return self._children[0].get_desired_height(
            given_width=v) +\
            (self.content_padding * 2 * self.dpi_scale)

    def on_relayout(self):
        if len(self._children) == 0:
            return
        outer_padding = (self.content_padding * self.dpi_scale)
        child = self._children[0]

        if self.child_fixed_width > 0:
            # Completely fixed size for child.
            child.width = min(self.dpi_scale * self.child_fixed_width,
                max(1, round(self.width - outer_padding * 2)))
        else:
            # Give child natural width or expand it fully:
            if not self.expand_horizontally:
                nat_width = child.get_desired_width()
                child.width = min(max(1, round(self.width -
                    outer_padding * 2)),
                    max(self.child_minimum_width * self.dpi_scale,
                    nat_width))
            else:
                child.width = max(1, round(self.width -
                    outer_padding * 2))
        if self.child_fixed_height > 0:
            child.height = min(self.dpi_scale * self.child_fixed_height,
                max(1, round(self.height - outer_padding * 2)))
        else:
            if not self.expand_vertically:
                child.height = min(round(self.height -
                    outer_padding * 2), child.get_desired_height(
                    given_width=child.width))
            else:
                child.height = max(1, self.height -
                    self.content_padding * 2 * self.dpi_scale)
        child.x = math.floor((self.width - child.width) / 2)
        child.y = math.floor((self.height - child.height) / 2)
        child.relayout_if_necessary()


