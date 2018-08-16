
import html
import math
import os
import PIL.Image
import sdl2 as sdl

from wobblui.color import Color
from wobblui.event import DummyEvent, Event
from wobblui.gfx import draw_rectangle
from wobblui.image import image_to_sdl_surface, stock_image
from wobblui.richtext import RichText
from wobblui.widget import Widget

class Button(Widget):
    def __init__(self, text="", with_border=True, clickable=True,
            image_placement="left"):
        super().__init__(is_container=False,
            can_get_focus=clickable)
        if clickable:
            self.triggered = Event("triggered", owner=self)
        else:
            self.triggered = DummyEvent("triggered", owner=self)
        self.with_border = (with_border is True)
        self.image_placement = image_placement
        self.image_color = Color.white
        self.contained_image = None
        self.contained_image_scale = 1.0
        self.contained_richtext_obj = None
        self.text_layout_width = None
        self.extra_image_render_func = None
        self.border = 5.0
        if with_border:
            self.border = 15.0
        if len(text) > 0:
            self.set_text(text)

    def internal_set_extra_image_render(self, func):
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
        self.contained_image_srf = image_to_sdl_surface(pil_image_or_path)

    def set_image_color(self, color):
        self.image_color = color
        self.update()

    def set_html(self, html):
        font_family = self.style.get("widget_font_family")
        px_size = self.style.get("widget_text_size")
        self.contained_richtext_obj = RichText(
            font_family=font_family,
            px_size=px_size,
            draw_scale=self.dpi_scale)
        self.contained_richtext_obj.set_html(html)
        (self.text_layout_width,
            self.text_layout_height) = \
            self.contained_richtext_obj.layout()

    def set_text(self, text):
        self.set_html(html.escape(text))

    def __del__(self):
        if hasattr(self, "contained_image_srf"):
            if self.contained_image_srf != None:
                sdl.SDL_FreeSurface(self.contained_image_srf)
            self.contained_image_srf = None

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
            tex = sdl.SDL_CreateTextureFromSurface(self.renderer,
                self.contained_image_srf)
            tg = sdl.SDL_Rect()
            tg.x = offset_x
            tg.y = round(self.border_size)
            tg.w = math.ceil(self.contained_image.size[0] *
                self.contained_image_scale * self.dpi_scale * 1.0)
            tg.h = math.ceil(self.contained_image.size[1] *
                self.contained_image_scale * self.dpi_scale * 1.0)
            if self.extra_image_render_func != None:
                self.extra_image_render_func(tg.x, tg.y, tg.w, tg.h)
            sdl.SDL_SetTextureColorMod(tex,
                self.image_color.red, self.image_color.green,
                self.image_color.blue)
            sdl.SDL_RenderCopy(self.renderer, tex, None, tg)
            sdl.SDL_DestroyTexture(tex)
            offset_x += tg.w + round(self.border_size * 0.7)
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
        return "<wobblui.ImageButton original_image='" +\
            str(self.original_image).replace("'", "'\"'\"'") + "'>"

    def do_redraw(self):
        color = Color(self.style.get("widget_text"))
        if self.style.has("saturated_widget_text"):
            color = Color(self.style.get("saturated_widget_text"))
        self.image_color = color
        super().do_redraw()

class HamburgerButton(ImageButton):
    def __init__(self, override_color=None):
        super().__init__(stock_image("sandwich"))

class HoverCircleImageButton(Button):
    def __init__(self, image_path, scale=None, scale_to_width=None):
        super().__init__(with_border=False, clickable=True)
        self.image_path = image_path
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
        super().__del__()

    def render_circle(self, x, y, w, h):
        if not hasattr(self, "circle_img") or self.circle_img is None:
            self.circle_img = PIL.Image.open(stock_image("hovercircle"))
        if not hasattr(self, "circle_srf") or self.circle_srf is None:
            self.circle_srf = image_to_sdl_surface(self.circle_img)

        tex = sdl.SDL_CreateTextureFromSurface(self.renderer,
            self.circle_srf)
        tg = sdl.SDL_Rect()
        tg.x = x
        tg.y = y
        tg.w = w
        tg.h = h
        sdl.SDL_SetTextureColorMod(tex,
            self.circle_r, self.circle_g, self.circle_b)
        sdl.SDL_RenderCopy(self.renderer, tex, None, tg)
        sdl.SDL_DestroyTexture(tex)

class ImageWithLabel(Button):
    def __init__(self, image_path, scale=None, scale_to_width=None,
            color_with_text_color=False):
        super().__init__(with_border=False, clickable=False,
            image_placement="left")
        self.original_image = image_path
        color = Color.white
        if color_with_text_color:
            color = Color(self.style.get("widget_text"))
            if self.style.has("saturated_widget_text"):
                color = Color(self.style.get("saturated_widget_text"))
        self.color_with_text_color = color_with_text_color
        self.set_image(image_path, scale=scale,
            scale_to_width=scale_to_width)
        self.set_image_color(color)

    def do_redraw(self):
        if self.color_with_text_color:
            color = Color(self.style.get("widget_text"))
            if self.style.has("saturated_widget_text"):
                color = Color(self.style.get("saturated_widget_text"))
            self.image_color = color
        super().do_redraw()

class LoadingLabel(ImageWithLabel):
    def __init__(self, html):
        super().__init__(stock_image("hourglass"), scale_to_width=100,
            color_with_text_color=True)
        self.set_html(html)

