#cython: language_level=3

'''
wobblui - Copyright 2018-2019 wobblui team, see AUTHORS.md

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

import sdl2 as sdl

class AppStyle(object):
    def __init__(self):
        self._dpi_scale_base = 1.0
        self._dpi_scale = 1.0
        self.is_android = (sdl.SDL_GetPlatform().decode(
            "utf-8", "replace").lower() == "android")
        #if self.is_android:
        #    self._dpi_scale_base = 1.2
        self.values = dict()

    def __repr__(self):
        return "AppStyle<" + str(self.values) + ">"

    def copy(self):
        copied_style = AppStyle()
        copied_style._dpi_scale = self._dpi_scale
        copied_style.is_android = self.is_android
        for k in self.values:
            copied_style.values[k] = self.values[k]
        return copied_style

    @property
    def dpi_scale(self):
        return self._dpi_scale * self._dpi_scale_base

    @dpi_scale.setter
    def dpi_scale(self, v):
        self._dpi_scale = float(v)

    def has(self, name):
        return (name.upper() in self.values)

    def set(self, name, value):
        name = name.upper()
        if type(value) == int or type(value) == float:
            self.values[name] = value
            return
        if len(value) == 4 and value[0] == "#":
            value = "#" + value[1] + value[1] +\
                value[2] + value[2] +\
                value[3] + value[3]
        self.values[name] = value

    def get(self, name):
        name = name.upper()
        if name in self.values:
            return self.values[name]
        if name.endswith("_BG"):
            if (name.find("SELECTED") >= 0 or \
                        name.find("HOVER") >= 0) and \
                    "SELECTED_BG" in self.values:
                return self.values["SELECTED_BG"]
            if "WIDGET_BG" in self.values:
                return self.values["WIDGET_BG"]
            return "#000000"
        if (name.endswith("_FRONT") or name.endswith("_FONT") or \
                name.endswith("BORDER") or name.endswith("_TEXT")):
            if "WIDGET_TEXT" in self.values:
                return self.values["WIDGET_TEXT"]
            return "#ffffff"
        if name.endswith("_FONT_FAMILY"):
            if "WIDGET_FONT_FAMILY" in self.values:
                return self.values["WIDGET_FONT_FAMILY"]
            return "Tex Gyre Heros"
        if name.endswith("_TEXT_SIZE"):
            if "WIDGET_TEXT_SIZE" in self.values:
                return self.values["WIDGET_TEXT_SIZE"]
            return 13
        return "#aaaaaa"

    def replace_variables(self, t):
        i = t.find("{{")
        while i >= 0:
            if t[i:].startswith("{{") and \
                    i < len(t) - 3 and \
                    ord(t[2]) >= ord("A") and \
                    ord(t[2]) <= ord("Z") and \
                    t[i:].find("}}") > 0:
                var = t[i + 2:i + t[i:].find("}}")]
                t = t[:i] + self.get(var) +\
                    t[i + t[i:].find("}}") + 2:]
            i = t.find("{{", (i + 1))
        return t

    def apply(self, app):
        template_text = None
        with open("style/template.qss", "r", encoding="utf8") as f:
            template_text = f.read()
        template_text = self.replace_variables(template_text)
        app.set_css_style(template_text)

class AppStyleBright(AppStyle):
    def __init__(self):
        super().__init__()
        self.set("window_bg", "#efeeed")
        self.set("button_bg", "#e3e2e2")
        self.set("button_bg_hover", "#dad9d9")
        self.set("button_border", "#e3c2c2")
        self.set("topbar_bg", "#e6e0e3")
        self.set("widget_disabled_bg", "#aaa")
        self.set("inner_widget_bg", "#f0f0f0")
        self.set("inner_widget_alternating_bg", "#efe6e6")
        self.set("inner_widget_bg_hover", "#e0e0e0")
        self.set("inner_widget_alternating_bg_hover", "#cfc6c6")
        self.set("widget_text", "#222121")
        self.set("widget_text_hover", "#424141")
        self.set("widget_text_saturated", "#000")
        self.set("widget_disabled_text", "#777")
        self.set("border", "#222")
        self.set("selected_bg", "#7ae")
        self.set("hover_bg", "#4af")
        self.set("focus_border", "#c7a")
        self.set("selected_text", "#000")
        self.set("scrollbar_knob_fg", "#ee8888")
        self.set("touch_selection_drag_handles", "#ea3")
        self.set("widget_font_family", "Tex Gyre Heros")
        self.set("widget_text_size", 18)
        self.set("topbar_text_size", 23)
 
class AppStyleDark(AppStyle):
    def __init__(self):
        super().__init__()
        self.set("window_bg", "#222")
        self.set("button_bg", "#444")
        self.set("button_bg_hover", "#353535")
        self.set("button_border", "#555")
        self.set("topbar_bg", "#333333")
        self.set("widget_disabled_bg", "#3f3333")
        self.set("inner_widget_bg", "#111")
        self.set("inner_widget_alternating_bg", "#1f1e1e")
        self.set("inner_widget_bg_hover", "#222020")
        self.set("inner_widget_alternating_bg_hover", "#2f2e2e")
        self.set("widget_text", "#e0e0e0")
        self.set("widget_text_hover", "#b0b0b0")
        self.set("widget_text_saturated", "#fff")
        self.set("widget_disabled_text", "#878")
        self.set("border", "#000")
        self.set("selected_bg", "#7ae")
        self.set("hover_bg", "#4af")
        self.set("focus_border", "#a9b")
        self.set("selected_text", "#112")
        self.set("scrollbar_knob_fg", "#cc9099")
        self.set("touch_selection_drag_handles", "#ea3")
        self.set("widget_font_family", "Tex Gyre Heros")
        self.set("widget_text_size", 18)
        self.set("topbar_text_size", 23)
