
import html
import math
import os
import PIL.Image
import sdl2 as sdl

from wobblui.color import Color
from wobblui.image import image_to_sdl_surface
from wobblui.widget import Widget

class Button(Widget):
    def __init__(self, with_border=True, clickable=True,
            image_placement="left"):
        super().__init__(is_container=False,
            can_get_focus=clickable)
        self.image_placment = image_placement
        self.image_color = Color.white
        self.contained_image = None
        self.contained_image_scale = 1.0
        self.contained_richtext_obj = None
        self.text_layout_width = None
        self.border = 5.0

    @property
    def border_size(self):
        return round(self.border * self.dpi_scale)

    def set_image(self, pil_image_or_path, scale=1.0):
        if not hasattr(pil_image_or_path, "save"):
            pil_image_or_path = PIL.Image.open(pil_image_or_path)
        self.contained_image = pil_image_or_path
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
            self.text_layout_height) = self.text_obj.layout()

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
        offset_x = round(self.border_size)
        full_available_size = round(self.width - (offset_x * 2))
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
                self.contained_image_scale * self.dpi_scale)
            tg.h = math.ceil(self.contained_image.size[1] *
                self.contained_image_scale * self.dpi_scale)
            sdl.SDL_SetRenderDrawColor(self.renderer,
                self.image_color.red, self.image_color.green,
                self.image_color.blue, 255)
            sdl.SDL_RenderCopy(self.renderer, tex, None, tg)
            sdl.SDL_DestroyTexture(tex)
            offset_x += tg.w + round(self.border_size * 0.7)
        if self.contained_richtext_obj != None:
            c = Color.white
            if self.style != None:
                c = Color(self.style.get("widget_text"))
            sdl.SDL_SetRenderDrawColor(self.renderer, 255, 255, 255, 255)
            self.contained_rich_text_obj.draw(
                self.renderer, offset_x, 0,
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

class HamburgerButton(Button):
    def __init__(self, override_color=None):
        super().__init__(with_border=False)
        self.set_image(os.path.join(os.path.dirname(__file__),
            "img", "sandwich.png"), scale=0.3)
        color = Color.black
        if self.style != None:
            color = self.style.get("widget_text")
        self.set_image_color(color)

    def internal_override_parent(self, parent):
        super().internal_override_parent(parent)
        color = Color(self.style.get("widget_text"))
        self.set_image_color(color)

class ImageWithLabelBelow(Button):
    def __init__(self, image_path, image_scale=1.0,
            color_with_text_color=False):
        super().__init__(with_border=False, clickable=False,
            image_placement="top")
        color = Color.white
        if color_with_text_color:
            color = Color(self.style.get("widget_text"))
        self.color_with_text_color = color_with_text_color
        self.set_image(image_path, scale=image_scale)
        self.set_image_color(color)

    def internal_override_parent(self, parent):
        super().internal_override_parent(parent)
        if self.color_with_text_color:
            color = Color(self.style.get("widget_text"))
            self.set_image_color(color)

class LoadingLabel(ImageWithLabelBelow):
    def __init__(self, text):
        super().__init__(
            os.path.join(os.path.dirname(__file__),
            "img", "hourglass.png"), image_scale=0.5)

