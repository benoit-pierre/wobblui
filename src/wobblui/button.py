
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

import html
import math
import os
import PIL.Image
import sdl2 as sdl

from wobblui.color import Color
from wobblui.event import ForceDisabledDummyEvent, Event
from wobblui.gfx import draw_rectangle, pop_render_clip, push_render_clip
from wobblui.image import RenderImage, stock_image
from wobblui.richtext import RichText
from wobblui.texture import Texture
from wobblui.uiconf import config
from wobblui.widget import Widget
from wobblui.woblog import logdebug, logerror, loginfo, logwarning

class Button(Widget):
    def __init__(self,
            text="",
            with_surrounding_frame=True,
            clickable=True,
            image_placement="left",
            text_scale=1.0,
            override_bg_color=None,
            override_text_color=None
            ):
        super().__init__(is_container=False,
            can_get_focus=clickable)
        if clickable:
            self.triggered = Event("triggered", owner=self)
        else:
            self.triggered = ForceDisabledDummyEvent(
                "triggered", owner=self)
        self.with_surrounding_frame = (with_surrounding_frame is True)
        self._image_draw_scaledown = 1.0
        self.image_placement = image_placement
        self._image_color = Color.white()
        self.override_bg_color = None
        if override_bg_color != None:
            self.override_bg_color = Color(override_bg_color)
        self.override_text_color = None
        if override_text_color != None:
            self.override_text_color = Color(override_text_color)
        self.contained_image = None
        self.contained_image_scale = 1.0
        self.contained_richtext_obj = None
        self.contained_image_pil = None
        self.known_font_family = None
        self.text_layout_width = None
        self.text_scale = text_scale
        self._html = ""
        self.extra_image_render_func = None
        self.border = 5.0
        if with_surrounding_frame:
            self.border = 15.0
        if len(text) > 0:
            self.set_text(text)

    @property
    def font_family(self):
        ff = self.style.get("widget_font_family")
        if ff is None or len(ff.strip()) == 0:
            return "TeX Gyre Heros"
        return ff

    @property
    def html(self):
        return self._html

    def __del__(self):
        if hasattr(super(), "__del__"):
            super().__del__()

    def renderer_update(self):
        super().renderer_update()

    def internal_set_extra_image_render(self, func):
        """ Allows setting an extra function that runs right
            before the actual image renders. It will be passed
            the 4 parameters: x, y, w, h - corresponding to
            the draw rectangle of the image that is rendered on
            top right after. Can be used for a surrounding
            shape. """
        self.extra_image_render_func = func

    def on_keydown(self, key, physical_key, modifiers):
        if key == "return" or key == "space":
            self.triggered()

    def on_click(self, mouse_id, button, x, y):
        self.triggered()

    @property
    def border_size(self):
        return round(self.border * self.dpi_scale)

    def set_image(self, pil_image_or_path, scale=None,
            scale_to_width=None):
        if scale != None and scale_to_width != None:
            raise ValueError("cannot specify both scale factor " +
                "and scale to width measure")
        if scale is None and scale_to_width is None:
            scale = 1.0
        if not hasattr(pil_image_or_path, "save"):
            pil_image_or_path = PIL.Image.open(pil_image_or_path)
        if scale_to_width != None:
            scale = scale_to_width / float(pil_image_or_path.size[0])
        self.contained_image_pil = pil_image_or_path
        assert(scale != None)
        self.contained_image_scale = scale
        self.contained_image = RenderImage(self.contained_image_pil)

    def set_image_color(self, color):
        self.image_color = Color(color)
        self.update()

    @html.setter
    def html(self, v):
        self.set_html(v)

    def set_html(self, html):
        if self.html == html:
            return
        self.needs_redraw = True
        self.needs_relayout = True
        self._html = html
        self.update_font_object()

    def on_stylechanged(self):
        self.update_font_object()

    def update_font_object(self):
        font_family = self.font_family
        px_size = round(self.style.get("widget_text_size") *
            self.text_scale)
        if self.contained_richtext_obj is None or \
                self.known_font_family != font_family:
            self.contained_richtext_obj = RichText(
                font_family=font_family,
                px_size=px_size,
                draw_scale=self.dpi_scale)
            self.known_font_family = font_family
        else:
            self.contained_richtext_obj.px_size = px_size
            self.contained_richtext_obj.draw_scale = self.dpi_scale
        self.contained_richtext_obj.set_html(self.html)
        (self.text_layout_width,
            self.text_layout_height) = \
            self.contained_richtext_obj.layout()
        self.needs_relayout = True

    def set_text(self, text):
        self.set_html(html.escape(text))

    @property
    def image_color(self):
        return self._image_color

    @image_color.setter
    def image_color(self, v):
        if v.value_red != self._image_color.value_red or \
                v.value_green != self._image_color.value_green or \
                v.value_blue != self._image_color.value_blue:
            self._image_color = v
            self.update_texture_color()

    def update_texture_color(self):
        if self.contained_image is not None:
            self.contained_image.set_color(self.image_color)

    def do_redraw(self):
        if self.renderer is None:
            return
        self.update_texture_color()
        if self.with_surrounding_frame:
            c = Color.white()
            if self.style is not None:
                c = Color(self.style.get("button_bg"))
            if self.override_bg_color != None:
                c = self.override_bg_color
            fill_border = round(self.border_size * 0.3)
            draw_rectangle(self.renderer, fill_border, fill_border,
                self.width - fill_border * 2,
                self.height - fill_border * 2,
                color=c)
            border_color = None
            if self.style is not None and \
                    self.style.has("button_border"):
                border_color = Color(self.style.get("button_border"))
            if border_color is not None:
                draw_rectangle(self.renderer,
                    fill_border, self.height - max(1, fill_border) * 2,
                    self.width - fill_border * 2,
                    max(1, fill_border),
                    color=border_color)
                draw_rectangle(self.renderer,
                    self.width - max(1, fill_border) * 2,
                    fill_border,
                    max(1, fill_border),
                    self.height - fill_border * 2,
                    color=border_color)
        offset_x = round(self.border_size)
        full_available_size = round(self.width - (offset_x * 2))
        if full_available_size < 0:
            return
        used_up_size = (self.text_layout_width or 0)
        if self.contained_image_pil is not None:
            used_up_size += math.ceil(
                self.contained_image_pil.size[0] *
                self.contained_image_scale * self.dpi_scale) +\
                round(self.border_size * 0.7)
        extra_size = max(0, full_available_size - used_up_size)
        offset_x += max(0, math.floor(extra_size / 2.0))
        if self.contained_image is not None:
            x = offset_x
            y = round(self.border_size)
            w_full_float = (self.contained_image_pil.size[0] *
                self.contained_image_scale *
                self.dpi_scale * 1.0)
            h_full_float = (self.contained_image_pil.size[1] *
                self.contained_image_scale *
                self.dpi_scale * 1.0)
            w_full = math.ceil(w_full_float)
            h_full = math.ceil(h_full_float)
            w = math.ceil(w_full_float * self._image_draw_scaledown)
            h = math.ceil(h_full_float * self._image_draw_scaledown)
            if self.extra_image_render_func != None:
                self.extra_image_render_func(x, y, w_full, h_full)
            x += round((w_full - w) * 0.5)
            y += round((h_full - h) * 0.5)
            self.contained_image.draw(
                self.renderer,
                x, y,
                w=w, h=h)
            offset_x += w + round(self.border_size * 0.7)
        if self.contained_richtext_obj != None:
            c = Color.white()
            if self.style != None:
                c = Color(self.style.get("widget_text"))
                if self.disabled and self.style.has("widget_disabled_text"):
                    c = Color(self.style.get("widget_disabled_text"))
            if self.override_text_color != None:
                c = self.override_text_color
            sdl.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
            if self.with_surrounding_frame:
                push_render_clip(self.renderer,
                    fill_border, fill_border,
                    self.width - fill_border * 2,
                    self.height - fill_border * 2)
            try:
                self.contained_richtext_obj.draw(
                    self.renderer, offset_x,
                    round(self.height / 2.0 - self.text_layout_height / 2.0),
                    color=c, draw_scale=self.dpi_scale)
            finally:
                if self.with_surrounding_frame:
                    pop_render_clip(self.renderer)
        if self.focused:
            focus_padding = round(2.0 * self.dpi_scale)
            self.draw_keyboard_focus(
                focus_padding, focus_padding,
                self.width - focus_padding * 2,
                self.height - focus_padding * 2)

    def get_natural_height(self, given_width=None):
        my_h = round(self.border_size * 2)
        if self.contained_image != None:
            my_h = max(my_h,
                round(self.contained_image_pil.size[1] *\
                self.contained_image_scale * self.dpi_scale +
                self.border_size * 2))
        if self.contained_richtext_obj != None:
            my_h = max(my_h, self.text_layout_height +
                round(self.border_size * 2))
        return my_h

    def get_natural_width(self):
        my_w = round(self.border_size * 2)
        if self.contained_image != None:
            my_w += round(self.contained_image_pil.size[0] *\
                self.contained_image_scale * self.dpi_scale)
        if self.contained_image != None and \
                self.contained_richtext_obj != None:
            # Add in-between spacing:
            my_w += round(self.border_size * 0.7)
        if self.contained_richtext_obj != None:
            my_w += round(self.text_layout_width)
        return my_w

class ImageButton(Button):
    def __init__(self, image, scale_to_width=33,
            clickable=True):
        super().__init__(with_surrounding_frame=False,
            clickable=clickable)
        self.original_image = image
        self.set_image(image, scale_to_width=scale_to_width)
        color = Color.black()
        if self.style != None:
            color = self.style.get("widget_text")
            if self.style.has("saturated_widget_text"):
                color = Color(self.style.get("saturated_widget_text"))
            if self.disabled and style.has("widget_disabled_text"):
                color = Color(self.style.get("widget_disabled_text"))
        assert(isinstance(color, Color))
        self.set_image_color(color)

    def __repr__(self):
        orig_img = "none"
        if hasattr(self, "original_image"):
            orig_img = str(self.original_image)
        return "<wobblui.ImageButton original_image='" +\
            orig_img.replace("'", "'\"'\"'") + "'>"

    def do_redraw(self):
        color = Color(self.style.get("widget_text"))
        if self.style.has("saturated_widget_text"):
            color = Color(self.style.get("saturated_widget_text"))
        if self.disabled and self.style.has("widget_disabled_text"):
            color = Color(self.style.get("widget_disabled_text"))
        self.image_color = color
        super().do_redraw()

class HamburgerButton(ImageButton):
    def __init__(self, override_color=None):
        super().__init__(stock_image("sandwich"))

class CircleImageButton(Button):
    def __init__(self, image_path, scale=None, scale_to_width=None,
            inner_image_scale=1.0,
            circle_color=None):
        super().__init__(with_surrounding_frame=False, clickable=True)
        self.image_path = image_path
        self.circle_pil = None
        self.circle_img = None
        color = Color.white()
        self.set_image(image_path, scale=scale,
            scale_to_width=scale_to_width)
        self.set_image_color(color)
        self._image_draw_scaledown = inner_image_scale
        self.internal_set_extra_image_render(self.render_circle)
        self.circle_color = Color((0, 150, 250))
        if circle_color is not None:
            self.circle_color = Color(circle_color)

    def __del__(self):
        self.dump_textures()
        super().__del__()

    def renderer_update(self):
        super().renderer_update()
        self.dump_textures()

    def dump_textures(self):
        if hasattr(super(), "dump_textures"):
            super().dump_textures()

    def render_circle(self, x, y, w, h):
        if self.circle_pil is None:
            self.circle_pil = PIL.Image.open(stock_image("circlebutton"))
        if self.circle_img is None:
            self.circle_img = RenderImage(self.circle_pil)
            self.circle_img.set_color(self.circle_color)
        if self.renderer is None:
            return
        self.circle_img.draw(self.renderer, x, y, w=w, h=h)

