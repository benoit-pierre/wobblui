
import copy
import html
import math
import sdl2 as sdl

from wobblui.color import Color
from wobblui.event import Event
from wobblui.gfx import draw_dashed_line, draw_rectangle
from wobblui.perf import Perf
from wobblui.richtext import RichText
from wobblui.scrollbarwidget import ScrollbarDrawingWidget
from wobblui.widget import Widget

class ListEntry(object):
    def __init__(self, html, style,
            px_size_scaler=1.0,
            extra_html_as_subtitle=None,
            extra_html_as_subtitle_scale=0.7,
            extra_html_at_right=None,
            extra_html_at_right_scale=0.8, is_alternating=False,
            with_visible_bg=False):
        self.with_visible_bg = with_visible_bg
        self._cached_natural_width = None
        self._cached_render_tex = None
        self._width = 0
        self._style = style
        self._html = html
        self.extra_html_at_right = extra_html_at_right
        self.extra_html_at_right_scale = extra_html_at_right_scale
        self.extra_html_as_subtitle = extra_html_as_subtitle
        self.extra_html_as_subtitle_scale =\
            extra_html_as_subtitle_scale
        self.disabled = False
        self.is_alternating = is_alternating
        self._style = style
        self.px_size_scaler = px_size_scaler
        self.update_text_objects()

    def __del__(self):
        self.clear_texture()

    def update_text_objects(self):
        if self._cached_render_tex != None:
            sdl.SDL_DestroyTexture(self._cached_render_tex)
            self._cached_render_tex = None
        dpi_scale = 1.0
        px_size = 12 * self.px_size_scaler
        font_family = "Tex Gyre Heros"
        if self.style != None:
            px_size = round(self.style.get("widget_text_size") *
                self.px_size_scaler)
            dpi_scale = self.style.dpi_scale
            font_family = self.style.get("widget_font_family")

        # Main text:
        self.text_obj = RichText(font_family=font_family,
            px_size=round(px_size),
            draw_scale=dpi_scale)
        self.text_obj.set_html(self._html)
        self._text = self.text_obj.text

        # Extra text at the right:
        self.extra_html_at_right_x = 0
        self.extra_html_at_right_y = 0
        self.extra_html_at_right_w = 0
        self.extra_html_at_right_h = 0
        self.extra_html_at_right_obj = None
        self.extra_html_at_right_padding = 0
        if self.extra_html_at_right != None:
            self.extra_html_at_right_padding = 35.0
            self.extra_html_at_right_obj = RichText(
                font_family=font_family,
                px_size=round(self.extra_html_at_right_scale *
                    px_size),
                draw_scale=dpi_scale)
            self.extra_html_at_right_obj.set_html(
                self.extra_html_at_right)

        # Subtitle text:
        self.subtitle_x = 0
        self.subtitle_y = 0
        self.subtitle_w = 0
        self.subtitle_h = 0
        self.extra_html_as_subtitle_obj = None
        self.extra_html_as_subtitle_padding = 0.0
        if self.extra_html_as_subtitle != None:
            self.extra_html_as_subtitle_padding = 5.0
            self.extra_html_as_subtitle_obj = RichText(
                font_family=font_family,
                px_size=round(self.extra_html_as_subtitle_scale *
                    px_size),
                draw_scale=dpi_scale)
            self.extra_html_as_subtitle_obj.\
                set_html(self.extra_html_as_subtitle)

        self._max_width = None
        self.need_size_update = True
        self.dpi_scale = dpi_scale

    @property
    def text(self):
        return self._text

    @property
    def html(self):
        return self._html

    def __repr__(self):
        return "<ListEntry text='" +\
            str(self.text).replace("'", "'\"'\"'") + "'>"

    def clear_texture(self):
        if self._cached_render_tex != None:
            sdl.SDL_DestroyTexture(self._cached_render_tex)
            self._cached_render_tex = None

    def draw(self, renderer, x, y, draw_selected=False,
            draw_hover=False,
            draw_keyboard_focus=False):
        self.update_size()
        if draw_selected or draw_hover or \
                draw_keyboard_focus:
            self.do_actual_draw(renderer, x, y,
                draw_selected=draw_selected,
                draw_hover=draw_hover,
                draw_keyboard_focus=draw_keyboard_focus)
            return

        tex = self._cached_render_tex
        if tex is None:
            old_t = sdl.SDL_GetRenderTarget(renderer)
            self._cached_render_tex = sdl.SDL_CreateTexture(
                renderer, sdl.SDL_PIXELFORMAT_ARGB8888,
                sdl.SDL_TEXTUREACCESS_TARGET, round(self.width),
                round(self.height))
            sdl.SDL_SetTextureBlendMode(self._cached_render_tex,
                sdl.SDL_BLENDMODE_BLEND)
            sdl.SDL_SetRenderTarget(renderer, self._cached_render_tex)
            sdl.SDL_SetRenderDrawColor(renderer, 0, 0, 0, 0)
            sdl.SDL_RenderClear(renderer)
            sdl.SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255)
            self.do_actual_draw(renderer, 0, 0,
                draw_selected=draw_selected,
                draw_hover=draw_hover,
                draw_keyboard_focus=draw_keyboard_focus)
            sdl.SDL_RenderPresent(renderer)
            sdl.SDL_SetRenderTarget(renderer, old_t)
            sdl.SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255)
            tex = self._cached_render_tex
        r = sdl.SDL_Rect()
        r.x = round(x)
        r.y = round(y)
        r.w = round(self.width)
        r.h = round(self.height)
        sdl.SDL_RenderCopy(renderer, tex, None, r)

    def do_actual_draw(self, renderer, x, y, draw_selected=False,
            draw_hover=False,
            draw_keyboard_focus=False):
        no_bg = (not self.with_visible_bg)
        c = Color((200, 200, 200))
        if self.style != None:
            if not draw_hover and not draw_selected:
                if not self.is_alternating:
                    c = Color(self.style.get("inner_widget_bg") or
                        not self.style.has("inner_widget_alternating_bg"))
                else:
                    c = Color(self.style.get("inner_widget_alternating_bg"))
            if draw_hover:
                no_bg = False
                c = Color(self.style.get("hover_bg"))
            elif draw_selected:
                no_bg = False
                c = Color(self.style.get("selected_bg"))
        if not no_bg:
            draw_rectangle(renderer, x, y,
                self.width, self.height, c)
        c = Color((0, 0, 0))
        if self.style != None:
            c = Color(self.style.get("widget_text"))
            if draw_hover or draw_selected:
                c = Color(self.style.get("selected_text"))
            if self.disabled and self.style.has("widget_disabled_text"):
                c = Color(self.style.get("widget_disabled_text"))
        perf_id = Perf.start("ListItem.draw -> text_objs draw")
        self.text_obj.draw(renderer,
            round(5.0 * self.dpi_scale) + x,
            round(self.vertical_padding * self.dpi_scale) + y,
            color=c)
        if self.extra_html_as_subtitle_obj != None:
            self.extra_html_as_subtitle_obj.draw(renderer,
                round(5.0 * self.dpi_scale) +\
                self.subtitle_x + x,
                round(self.vertical_padding * self.dpi_scale) +\
                self.subtitle_y +  y,
                color=c)
        if self.extra_html_at_right_obj != None:
            self.extra_html_at_right_obj.draw(renderer,
                round(5.0 * self.dpi_scale) +\
                self.extra_html_at_right_x + x,
                round(self.vertical_padding * self.dpi_scale) +\
                max(0, self.extra_html_at_right_y) + y,
                color=c)
        Perf.stop(perf_id)

    def copy(self):
        old_self_tex = self._cached_render_tex
        self._cached_render_tex = None
        li = copy.copy(self)
        self._cached_render_tex = old_self_tex
        li.update_text_objects()
        return li

    def get_natural_width(self):
        if self._cached_natural_width != None:
            return self._cached_natural_width
        text_copy = self.text_obj.copy()
        (w, h) = text_copy.layout(max_width=None)
        if self.extra_html_at_right_obj != None:
            w += max(1, round(self.extra_html_at_right_padding * self.dpi_scale))
            (w2, h2) = self.extra_html_at_right_obj.layout(max_width=None)
            w += w2
        self._cached_natural_width = (w + round(10.0 * self.dpi_scale))
        return self._cached_natural_width

    @property
    def width(self):
        self.update_size()
        return self._width

    @width.setter
    def width(self, v):
        if self._max_width != None:
            v = min(self._max_width, v)
        if self._width != v:
            self._width = v
            self.need_size_update = True

    @property
    def height(self):
        self.update_size()
        return self._height

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, v):
        if self._style != v:
            self._cached_natural_width = None
            self.need_size_update = True
            self._style = v
            self.update_text_objects()

    @property
    def max_width(self):
        return self._max_width

    @max_width.setter
    def max_width(self, v):
        if v != None:
            v = int(round(v))
        if self._max_width != v:
            self._max_width = v
            self.need_size_update = True

    @property
    def vertical_padding(self):
        return 10.0

    def update_size(self):
        if not self.need_size_update:
            return
        self.need_size_update = False
        if self._cached_render_tex != None:
            sdl.SDL_DestroyTexture(self._cached_render_tex)
            self._cached_render_tex = None
        padding = max(0, round(5.0 * self.dpi_scale))
        padding_vertical = max(0,
            round(self.vertical_padding * self.dpi_scale))
        mw = self.max_width
        if mw != None:
            mw = min(self.width, mw) - padding * 2
        else:
            mw = max(1, self.width - padding * 2)
        is_empty = False
        if self.text_obj.text == "":
            is_empty = True
            self.text_obj.set_text(" ")
        subtitle_w = 0
        subtitle_h = 0
        self.subtitle_x = 0
        self.subtitle_y = 0
        self.subtitle_w = 0
        self.subtilte_h = 0
        if self.extra_html_as_subtitle_obj != None:
            (subtitle_w, subtitle_h) = self.extra_html_as_subtitle_obj.\
                layout(max_width=mw)
            self.subtitle_h = subtitle_h
            self.subtitle_w = subtitle_w
        self.extra_html_at_right_x = 0
        self.extra_html_at_right_y = 0
        if self.extra_html_at_right_obj != None:
            (natural_w, natural_h) = self.text_obj.layout(
                max_width=None)
            (natural_w2, natural_h2) = self.\
                extra_html_at_right_obj.layout(
                max_width=None)
            missing_space = max(0, math.ceil((natural_w +
                self.extra_html_at_right_padding *
                self.dpi_scale + natural_w2) - mw))
            if mw < (natural_w * 0.5 +
                    self.extra_html_at_right_padding * self.dpi_scale +
                    natural_w2 * 0.5) and mw <= natural_w * 1.2 and \
                    missing_space > 5.0 * self.dpi_scale:
                # Put the extra HTML part below
                (self.text_width, self.text_height) = \
                    self.text_obj.layout(max_width=mw)
                self.subtitle_y = self.text_height +\
                    math.ceil(self.extra_html_as_subtitle_padding *
                        self.dpi_scale)
                self.extra_html_at_right_x = 0
                self.extra_html_at_right_y = self.text_height +\
                    math.ceil(self.extra_html_as_subtitle_padding * 2.0 *
                    self.dpi_scale) +\
                    self.subtitle_h
                (self.extra_html_at_right_w, self.extra_html_at_right_h) =\
                    self.extra_html_at_right_obj.layout(max_width=mw)
                self._height = round(self.extra_html_at_right_y +
                    self.extra_html_at_right_h + padding_vertical * 2)
            else:
                # Put extra HTML part to the right
                right_side_fac = (float(natural_w2) / float(natural_w +
                    natural_w2))
                left_side_fac = (float(natural_w) / float(natural_w +
                    natural_w2))
                left_side_w = round(natural_w -
                    missing_space * left_side_fac)
                right_side_w = round(natural_w2 -
                    missing_space * right_side_fac)
                self.text_width = left_side_w
                (ignore_w, self.text_height) = self.text_obj.layout(
                    max_width=left_side_w)
                self.subtitle_y = self.text_height +\
                    math.ceil(self.extra_html_as_subtitle_padding *
                        self.dpi_scale)
                self.extra_html_at_right_y = 0
                self.extra_html_at_right_x = self.text_width +\
                    self.extra_html_as_subtitle_padding
                (self.extra_html_at_right_w, self.extra_html_at_right_h) =\
                    self.extra_html_at_right_obj.\
                        layout(max_width=right_side_w)
                self.extra_html_at_right_y = max(0,
                    round((self.text_height -
                    self.extra_html_at_right_h) / 2.0))
                self.extra_html_at_right_x = mw -\
                    self.extra_html_at_right_w - round(padding * 2)
                self._height = round(max(self.subtitle_y +
                    self.subtitle_h,
                    self.extra_html_at_right_y +
                    self.extra_html_at_right_h) + padding_vertical * 2)
        else:
            (self.text_width, self.text_height) = self.text_obj.layout(
                max_width=mw)
            self._height = round(self.text_height + padding_vertical * 2)
            self.subtitle_y = self.text_height +\
                math.ceil(self.extra_html_as_subtitle_padding *
                    self.dpi_scale)
            if self.extra_html_as_subtitle_obj != None:
                self._height = round(self.subtitle_y +
                    self.subtitle_h) + padding_vertical * 2
        if is_empty:
            self.text_width = 0
            self.text_obj.set_text("")

class ListBase(ScrollbarDrawingWidget):
    def __init__(self, render_as_menu=False,
            fixed_one_line_entries=False,
            triggered_by_single_click=False):
        super().__init__(is_container=False, can_get_focus=True,
            generate_double_click_for_touches=(
            not triggered_by_single_click))
        self.triggered = Event("triggered", owner=self)
        self.triggered_by_single_click =\
            triggered_by_single_click
        self._entries = []
        self._selected_index = -1
        self._hover_index = -1
        self.scroll_y_offset = 0
        self.usual_entry_height = None
        self.render_as_menu = render_as_menu
        self.fixed_one_line_entries = fixed_one_line_entries
        self.update_style_info()

    def _internal_on_unfocus(self, internal_data=None):
        super()._internal_on_unfocus(
            internal_data=internal_data)
        self._hover_index = -1

    def renderer_update(self):
        super().renderer_update()
        for entry in self._entries:
            entry.clear_texture()

    def on_stylechanged(self):
        self.update_style_info()

    def update_style_info(self):
        entry = ListEntry("", self.style)
        self.usual_entry_height = entry.height
        del(entry)

    def set_disabled(self, entry_index, state):
        new_state = (state is True)
        if self._entries[entry_index].disabled == state:
            return
        self._entries[entry_index].disabled = state
        if self._selected_index == entry_index:
            self._selected_index = -1
        if self._hover_index == entry_index:
            self._selected_index = -1
        self.needs_redraw = True

    def clear(self):
        self._entries = []
        self._selected_index = -1
        self._hover_index = -1
        self.scroll_y_offset = 0
        self.needs_redraw = True
        self.needs_relayout = True

    @property
    def hover_index(self):
        return self._hover_index

    @hover_index.setter
    def hover_index(self, v):
        if self._hover_index != v:
            self._hover_index = v
            self.needs_redraw = True

    @property
    def selected_index(self):
        return self._selected_index

    @selected_index.setter
    def selected_index(self, v):
        if self._selected_index != v:
            self._selected_index = v
            self.needs_redraw = True

    def on_keydown(self, key, physical_key, modifiers):
        if key == "down":
            self._selected_index += 1
            if self._selected_index >= len(self._entries):
                self._selected_index = len(self._entries) - 1
                if len(self._entries) == 0:
                    self._selected_index = -1
            # Make sure we haven't selected a disabled entry:
            if len(self._entries) > 0:
                while self._selected_index < len(self._entries) and \
                        self._entries[self._selected_index].disabled:
                    self._selected_index += 1
                while self.selected_index >= 0 and \
                        (self._selected_index >= len(self._entries) or
                        self._entries[self._selected_index].disabled):
                    self._selected_index -= 1
                if self._selected_index < 0:
                    # No non-disabled entries.
                    self._selected_index = -1

            self.scroll_y_offset = max(
                self._entries[self._selected_index].y_offset +
                self._entries[self._selected_index].height -
                self.height,
                self.scroll_y_offset)
            self.needs_redraw = True
        elif key == "up":
            self._selected_index -= 1
            if self._selected_index < 0:
                self._selected_index = 0
                if len(self._entries) == 0:
                    self._selected_index = -1
            # Make sure we haven't selected a disabled entry:
            if len(self._entries) > 0:
                while self._selected_index >= 0 and \
                        self._entries[self._selected_index].disabled:
                    self._selected_index -= 1
                while self.selected_index < len(self._entries) and \
                        (self._selected_index < 0 or
                        self._entries[self._selected_index].disabled):
                    self._selected_index += 1
                if self._selected_index >= len(self._entries):
                    # No non-disabled entries.
                    self._selected_index = -1
            self.scroll_y_offset = min(
                self._entries[self._selected_index].y_offset,
                self.scroll_y_offset)
            self.needs_redraw = True
        elif key == "space" or key == "return":
            if self._selected_index >= 0:
                self.triggered()

    def on_mousewheel(self, mouse_id, x, y):
        self.scroll_y_offset = max(0,
            self.scroll_y_offset -
            y * 50.0 * self.dpi_scale)
        self.needs_redraw = True

    def on_mousemove(self, mouse_id, x, y):
        self.set_selection_by_mouse_pos(x, y) 

    def set_selection_by_mouse_pos(self, x, y):
        click_index = self.coords_to_entry(x, y)
        if click_index != self._hover_index:
            if click_index >= 0 and \
                    self._entries[click_index].disabled:
                return  # it's a disabled entry, ignore
            self._hover_index = click_index
            if self.render_as_menu:
                self.needs_redraw = True

    def on_doubleclick(self, mouse_id, button, x, y):
        self.set_selection_by_mouse_pos(x, y)
        if not self.triggered_by_single_click and \
                self._hover_index >= 0:
            self._selected_index = self._hover_index
            self.triggered()

    def on_click(self, mouse_id, button, x, y):
        if button != 1 and self.triggered_by_single_click:
            # This is supposed to be an instant-click list.
            # Since this click doesn't do anything for that,
            # also ignore it for selection:
            return
        self.set_selection_by_mouse_pos(x, y)
        if self.triggered_by_single_click and \
                self._hover_index >= 0 and button == 1:
            self._selected_index = self._hover_index
            self.triggered()

    def on_mousedown(self, mouse_id, button, x, y):
        click_index = self.coords_to_entry(x, y)
        if click_index >= 0 and \
                click_index != self._selected_index:
            self._selected_index = click_index
            self.needs_redraw = True

    def coords_to_entry(self, x, y):
        if x < 0 or x >= self.width:
            return -1
        if y < 0 or y >= self.height:
            return -1

        if self.fixed_one_line_entries:
            offset = y + round(self.scroll_y_offset)
            match = math.floor(offset / float(self.usual_entry_height))
            return max(-1, min(match, len(self._entries) - 1))

        entry_id = -1
        for entry in self._entries:
            entry_id += 1
            if entry.y_offset < y + round(self.scroll_y_offset) and \
                    entry.y_offset + entry.height >\
                    y + round(self.scroll_y_offset):
                return entry_id
        return -1

    def on_relayout(self):
        # Update the entry positions:
        border_size = max(1, round(1.0 * self.dpi_scale))
        if not self.render_as_menu:
            border_size = 0
        cy = 0
        for entry in self._entries:
            entry.style = self.style
            entry.width = self.width - round(border_size * 2)
            entry.y_offset = cy
            if not self.fixed_one_line_entries:
                cy += round(entry.height)
            else:
                cy += self.usual_entry_height

    def on_redraw(self):
        perf_id = Perf.start("list_innerdraw")
        content_height = 0
        max_scroll_down = 0

        #Perf.start("sectiona")

        # Get height of content:
        if not self.fixed_one_line_entries:
            for entry in self._entries:
                content_height += round(entry.height)
        else:
            content_height = round(len(self._entries) *\
                self.usual_entry_height) 

        # Make sure scroll down offset is in a valid range:
        max_scroll_down = max(0, content_height - self.height)
        self.scroll_y_offset = max(0, min(self.scroll_y_offset,
            max_scroll_down))

        # Draw border if a menu:
        border_size = max(1, round(1.0 * self.dpi_scale))
        if not self.render_as_menu:
            border_size = 0
        c = Color.black
        if self.style != None and self.style.has("border"):
            c = Color(self.style.get("border"))
        if border_size > 0:
            draw_rectangle(self.renderer, 0, 0,
                self.width, self.height, color=c)
               
        # Draw background: 
        c = Color.white
        if self.style != None:
            c = Color(self.style.get("inner_widget_bg"))
            if self.render_as_menu and self.style.has("button_bg"):
                c = Color(self.style.get("button_bg"))
        draw_rectangle(self.renderer, border_size, border_size,
            self.width - border_size * 2,
            self.height - border_size * 2,
            color=c)

        # Draw items:
        skip_start_items = 0
        if self.fixed_one_line_entries:
            skip_start_items = math.floor(
                round(self.scroll_y_offset) /
                self.usual_entry_height)
        cx = border_size
        cy = border_size
        entry_id = -1 + skip_start_items
        for entry in self._entries[skip_start_items:]:
            entry_id += 1
            entry.draw(self.renderer,
                cx,
                cy + entry.y_offset - round(self.scroll_y_offset),
                draw_selected=(
                entry_id == self._selected_index and
                (entry_id != self._hover_index or
                not self.render_as_menu)),
                draw_hover=(self.render_as_menu and
                entry_id == self._hover_index))
            if self.fixed_one_line_entries and \
                    entry.y_offset > self.height +\
                    self.scroll_y_offset:
                break

        # Draw keyboard focus line if we have the focus:
        if self.focused:
            self.draw_keyboard_focus(0, 0, self.width, self.height)

        # Draw scroll bar:
        self.draw_scrollbar(content_height, self.height,
            self.scroll_y_offset)
        Perf.stop(perf_id)

    def get_natural_width(self):
        border_size = max(1, round(1.0 * self.dpi_scale))
        if not self.render_as_menu:
            border_size = 0
        w = 0
        entry_copies = []
        for entry in self._entries:
            w = max(w, entry.get_natural_width())
        w = max(w, round(12 * self.dpi_scale)) + border_size * 2
        return w

    def get_natural_height(self, given_width=None):
        border_size = max(1, round(1.0 * self.dpi_scale))
        if not self.render_as_menu:
            border_size = 0
        if self.fixed_one_line_entries:
            return max(12 * self.dpi_scale,
                round(self.usual_entry_height *\
                len(self._entries))) + border_size * 2
        h = 0
        if given_width != None:
            h = 0
            entry_width = given_width - round(border_size * 2)
            entry_copies = []
            for entry in self._entries:
                entry_copies.append(entry.copy())
                entry_copies[-1].max_width = entry_width
                entry_copies[-1].width = entry_width
                h += entry_copies[-1].height
        else:
            for entry in self._entries:
                h += entry.height
        return max(h, round(12 * self.dpi_scale)) + border_size * 2

    @property
    def entries(self):
        l = []
        for entry in self._entries:
            l.append(entry.text_obj.html)
        return l

    def insert(self, index, text):
        self.insert_html(index, html.escape(text))

    def insert_html(self, index, text):
        self._entries.insert(index, ListEntry(html, self.style,
            with_visible_bg=(not self.render_as_menu)))
        i = 0
        while i < len(self._entries):
            self._entries[i].is_alternating = \
                (((i + 1) % 0) == 0)
            i += 1

    def add(self, text, side_text=None, subtitle=None):
        if side_text != None:
            side_text = html.escape(side_text)
        if subtitle != None:
            subtitle = html.escape(subtitle)
        self.add_html(html.escape(text), side_html=side_text,
            subtitle_html=subtitle)

    def add_html(self, html, side_html=None, subtitle_html=None):
        if subtitle_html != None and self.fixed_one_line_entries:
            raise ValueError("cannot use subtitle when list is " +
                "forced to simple one-line entries")
        last_was_alternating = True
        if len(self._entries) > 0 and \
                not self._entries[-1].is_alternating:
            last_was_alternating = False
        self._entries.append(ListEntry(html, self.style,
            is_alternating=(not last_was_alternating),
            extra_html_at_right=side_html,
            extra_html_as_subtitle=subtitle_html,
            with_visible_bg=(not self.render_as_menu)))
        
class List(ListBase):
    def __init__(self, fixed_one_line_entries=False,
            triggered_by_single_click=False):
        super().__init__(render_as_menu=False,
            fixed_one_line_entries=fixed_one_line_entries,
            triggered_by_single_click=triggered_by_single_click)

