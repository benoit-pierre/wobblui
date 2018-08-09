
class AppStyle(object):
    def __init__(self):
        self.dpi_scale = 1.0

    def set(self, name, value):
        if not hasattr(self, "values"):
            self.values = dict()

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
        self.set("widget_bg", "#ccc")
        self.set("window_bg", "#efeeed")
        self.set("button_bg", "#bbb")
        self.set("widget_disabled_bg", "#aaa")
        self.set("inner_widget_bg", "#ddd")
        self.set("widget_text", "#111")
        self.set("widget_disabled_text", "#444")
        self.set("border", "#222")
        self.set("selected_bg", "#ea3")
        self.set("hover_bg", "#f81")
        self.set("focus_border", "#f50")
        self.set("selected_text", "#000")
        self.set("widget_font_family", "Tex Gyre Heros")
        self.set("widget_text_size", 13)
    
class AppStyleDark(AppStyle):
    def __init__(self):
        super().__init__()
        self.set("widget_bg", "#333")
        self.set("window_bg", "#222")
        self.set("button_bg", "#444")
        self.set("toolbar_bg", "#666")
        self.set("widget_disabled_bg", "#333")
        self.set("inner_widget_bg", "#111")
        self.set("widget_text", "#ccc")
        self.set("widget_disabled_text", "#888")
        self.set("border", "#000")
        self.set("selected_bg", "#ea3")
        self.set("hover_bg", "#f81")
        self.set("focus_border", "#f50")
        self.set("selected_text", "#500")
        self.set("widget_font_family", "Tex Gyre Heros")
        self.set("widget_text_size", 13)

