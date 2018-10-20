
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
from wobblui.gfx import draw_rectangle
from wobblui.image import image_to_sdl_surface, stock_image
from wobblui.richtext import RichText
from wobblui.texture import Texture
from wobblui.uiconf import config
from wobblui.widget import Widget
from wobblui.woblog import logdebug, logerror, loginfo, logwarning

class Button(Widget):
    def __init__(self, text="", with_border=True, clickable=True,
            image_placement="left", text_scale=1.0):
        super().__init__(is_container=False,
            can_get_focus=clickable)
        if clickable:
            self.triggered = Event("triggered", owner=self)
        else:
            self.triggered = ForceDisabledDummyEvent(
                "triggered", owner=self)
        self.with_border = (with_border is True)
        self.image_placement = image_placement
        self._image_color = Color.white
        self.contained_image = None
        self.contained_image_scale = 1.0
        self.contained_richtext_obj = None
        self.contained_image_srf = None
        self.contained_image_texture = None
        self.text_layout_width = None
        self.text_scale = text_scale
        self._html = ""
        self.extra_image_render_func = None
        self.border = 5.0
        if with_border:
            self.border = 15.0
        if len(text) > 0:
            self.set_text(text)

    @property
    def html(self):
        return self._html

    def __del__(self):
        if hasattr(super(), "__del__"):
            super().__del__()
        if hasattr(self, "contained_image_srf") and \
                self.contained_image_srf != None:
            sdl.SDL_FreeSurface(self.contained_image_srf)
        if hasattr(self, "contained_image_texture") and \
                self.contained_image_texture != None:
            if config.get("debug_texture_references"):
                logdebug("Button: " +
                    "DUMPED self.contained_image_texture")
            self.contained_image_texture = None

    def renderer_update(self):
        super().renderer_update()
        if self.contained_image_texture != None:
            if config.get("debug_texture_references"):
                logdebug("Button: " +
                    "DUMPED self.contained_image_texture")
            self.contained_image_texture = None

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
        self.contained_image = pil_image_or_path
        assert(scale != None)
        self.contained_image_scale = scale
        if self.contained_image_srf != None:
            sdl.SDL_FreeSurface(self.contained_image_srf)
            self.contained_image_srf = None
        if self.contained_image_texture != None:
            if config.get("debug_texture_references"):
                logdebug("Button: " +
                    "DUMPED self.contained_image_texture")
            self.contained_image_texture = None
        self.contained_image_srf = image_to_sdl_surface(pil_image_or_path)

    def set_image_color(self, color):
        self.image_color = color
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
        font_family = self.style.get("widget_font_family")
        px_size = round(self.style.get("widget_text_size") *
            self.text_scale)
        if self.contained_richtext_obj is None:
            self.contained_richtext_obj = RichText(
                font_family=font_family,
                px_size=px_size,
                draw_scale=self.dpi_scale)
        else:
            self.contained_richtext_obj.px_size = px_size
            self.contained_richtext_obj.draw_scale = self.dpi_scale
        self.contained_richtext_obj.set_html(self.html)
        (self.text_layout_width,
            self.text_layout_height) = \
            self.contained_richtext_obj.layout()

    def set_text(self, text):
        self.set_html(html.escape(text))

    @property
    def image_color(self):
        return self._image_color

    @image_color.setter
    def image_color(self, v):
        if v.red != self._image_color.red or \
                v.green != self._image_color.green or \
                v.blue != self._image_color.blue:
            self._image_color = v
            self.update_texture_color()

    def update_texture_color(self):
        if self.contained_image_texture != None:
            sdl.SDL_SetTextureColorMod(
                self.contained_image_texture._texture,
                self.image_color.red, self.image_color.green,
                self.image_color.blue)

    def do_redraw(self):
        if self.renderer is None:
            return
        if self.with_border:
            c = Color.white
            if self.style != None:
                c = Color(self.style.get("button_bg"))
            fill_border = round(self.border_size * 0.3)
            draw_rectangle(self.renderer, fill_border, fill_border,
                self.width - fill_border * 2,
                self.height - fill_border * 2,
                color=c)
        offset_x = round(self.border_size)
        full_available_size = round(self.width - (offset_x * 2))
        if full_available_size < 0:
            return
        used_up_size = (self.text_layout_width or 0)
        if self.contained_image != None:
            used_up_size += math.ceil(self.contained_image.size[0] *
                self.contained_image_scale * self.dpi_scale) +\
                round(self.border_size * 0.7)
        extra_size = max(0, full_available_size - used_up_size)
        offset_x += max(0, math.floor(extra_size / 2.0))
        if self.contained_image != None:
            if self.contained_image_texture is None:
                self.contained_image_texture =\
                    Texture.new_from_sdl_surface(self.renderer,
                        self.contained_image_srf)
                self.update_texture_color()
            x = offset_x
            y = round(self.border_size)
            w = math.ceil(self.contained_image.size[0] *
                self.contained_image_scale * self.dpi_scale * 1.0)
            h = math.ceil(self.contained_image.size[1] *
                self.contained_image_scale * self.dpi_scale * 1.0)
            if self.extra_image_render_func != None:
                self.extra_image_render_func(x, y, w, h)
            self.contained_image_texture.draw(
                x, y,
                w=w, h=h)
            offset_x += w + round(self.border_size * 0.7)
        if self.contained_richtext_obj != None:
            c = Color.white
            if self.style != None:
                c = Color(self.style.get("widget_text"))
                if self.disabled and self.style.has("widget_disabled_text"):
                    c = Color(self.style.get("widget_disabled_text"))
            sdl.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
            self.contained_richtext_obj.draw(
                self.renderer, offset_x,
                round(self.height / 2.0 - self.text_layout_height / 2.0),
                color=c, draw_scale=self.dpi_scale)
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
                round(self.contained_image.size[1] *\
                self.contained_image_scale * self.dpi_scale +
                self.border_size * 2))
        if self.contained_richtext_obj != None:
            my_h = max(my_h, self.text_layout_height +
                round(self.border_size * 2))
        return my_h

    def get_natural_width(self):
        my_w = round(self.border_size * 2)
        if self.contained_image != None:
            my_w += round(self.contained_image.size[0] *\
                self.contained_image_scale * self.dpi_scale)
        if self.contained_image != None and \
                self.contained_richtext_obj != None:
            # Add in-between spacing:
            my_w += round(self.border_size * 0.7)
        if self.contained_richtext_obj != None:
            my_w += round(self.text_layout_width)
        return my_w

class ImageButton(Button):
    def __init__(self, image, scale_to_width=30,
            clickable=True):
        super().__init__(with_border=False,
            clickable=clickable)
        self.original_image = image
        self.set_image(image, scale_to_width=scale_to_width)
        color = Color.black
        if self.style != None:
            color = self.style.get("widget_text")
            if self.style.has("saturated_widget_text"):
                color = Color(self.style.get("saturated_widget_text"))
            if self.disabled and style.has("widget_disabled_text"):
                color = Color(self.style.get("widget_disabled_text"))
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

class HoverCircleImageButton(Button):
    def __init__(self, image_path, scale=None, scale_to_width=None):
        super().__init__(with_border=False, clickable=True)
        self.image_path = image_path
        self.circle_srf = None
        self.circle_tex = None
        self.circle_img = None
        color = Color.white
        self.set_image(image_path, scale=scale,
            scale_to_width=scale_to_width)
        self.set_image_color(color)
        self.internal_set_extra_image_render(self.render_circle)
        self.circle_r = 0
        self.circle_g = 150
        self.circle_b = 250

    def __del__(self):
        if hasattr(self, "circle_srf") and self.circle_srf != None:
            sdl.SDL_FreeSurface(self.circle_srf)
            self.circle_srf = None
        self.dump_textures()
        super().__del__()

    def renderer_update(self):
        super().renderer_update()
        self.dump_textures()

    def dump_textures(self):
        if hasattr(self, "circle_tex") and self.circle_tex != None:
            if config.get("debug_texture_references"):
                logdebug("HoverCircleImageButtonButton: " +
                    "DUMPED self.circle_tex")
            self.circle_tex = None

    def render_circle(self, x, y, w, h):
        if self.circle_img is None:
            self.circle_img = PIL.Image.open(stock_image("hovercircle"))
        if self.circle_srf is None:
            self.circle_srf = image_to_sdl_surface(self.circle_img)
        if self.circle_tex is None:
            self.circle_tex = Texture.new_from_sdl_surface(
                self.renderer, self.circle_srf)
            sdl.SDL_SetTextureColorMod(self.circle_tex._texture,
                self.circle_r, self.circle_g, self.circle_b)
        self.circle_tex.draw(x, y, w=w, h=h)

