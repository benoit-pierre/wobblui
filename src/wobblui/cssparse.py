
import html.parser

import wobblui.htmlparse as htmlparse

class CSSAttribute(object):
    def __init__(self, name, value):
        self.name = name.strip()
        self.value = value.strip()
        if self.value.endswith(";"):
            self.value = self.value[:-1]
        if self.value.startswith("'") and self.value.endswith("'"):
            self.value = self.value[1:-1].strip()
        elif self.value.startswith("\"") and self.value.endswith("\""):
            self.value = self.value[1:-1].strip()
        self.value = self.value

    def __repr__(self):
        return "<CSSAttribute " + str(self.name) +\
            ":'" + str(self.value).replace("\\", "\\\\").\
            replace("'", "\\'") + "'>"

    @classmethod
    def parse_from(cls, css_string):
        css_string = css_string.strip()
        if css_string.find(":") <= 0:
            return None
        (left_part, _, right_part) = css_string.partition(":")
        if len(left_part) == 0 or len(right_part) == 0:
            return None
        attribute = CSSAttribute(left_part, right_part)
        if len(attribute.name) == 0 or len(attribute.value) == 0:
            return None
        return attribute

def parse_css_color(color):
    color = color.lower()
    def is_hex(v):
        def char_is_hex(v):
            v = v.lower()
            return (ord(v) >= ord("a") and ord(v) <= ord("f")) or\
                (ord(v) >= ord("0") and ord(v) <= ord("9"))
        if len(v) == 0:
            return False
        i = 0
        while i < len(v):
            if not char_is_hex(v[i]):
                return False
            i += 1
        return True
    if color == "red":
        return "#ff0000"
    elif color == "green":
        return "#00ff00"
    elif color == "blue":
        return "#0000ff"
    elif color == "gray":
        return "#777777"
    elif color == "orange":
        return "#ffee00"
    elif color == "white":
        return "#ffffff"
    elif color == "black":
        return "#000000"
    elif len(color) == 4 and color[0] == "#" and \
            is_hex(color[1:]):
        return "#" + color[1] + color[1] +\
            color[2] + color[2] +\
            color[3] + color[3]
    elif len(color) == 7 and color[0] == "#" and \
            is_hex(color[1:]):
        return color
    return None

def element_text_color(element):
    if type(element) == str:
        parse_result = htmlparse.parse(element)
        if len(parse_result) == 0:
            return None
        element = parse_result[0]
    if element.node_type != "element":
        return None
    for node_attr in element.attributes:
        if node_attr.lower() == "style":
            values = parse_css_fragments(
                element.attributes[node_attr])
            for attr in values:
                if attr.name.lower() == "color":
                    color = parse_css_color(attr.value)
                    if color != None:
                        return color
        if node_attr.lower() == "color":
            color = parse_css_color(element.attributes[node_attr])
            if color != None:
                return color
    return None

def parse_css_fragments(css_string):
    fragments = []
    i = 0
    current_item_start = 0
    bracket_nesting = 0
    backslash_quoted = False
    string_quoting = None
    while i < len(css_string):
        if css_string[i] == ";" and bracket_nesting == 0 and \
                string_quoting == None:
            fragments.append(css_string[
                current_item_start:i + 1])
            current_item_start = i + 1
            backslash_quoted = False
            i += 1
            continue
        elif string_quoting is None and (
                css_string[i] == "(" or css_string[i] == "{"):
            bracket_nesting += 1
        elif string_quoting is None and (
                css_string[i] == ")" or css_string[i] == "}"):
            bracket_nesting -= 1
        elif css_string[i] == "\\":
            backslash_quoted = True
            i += 1
            continue
        elif backslash_quoted:  # stop elif fall-through:
            backslash_quoted = False
        elif css_string[i] == string_quoting:
            string_quoting = None
        elif string_quoting == None and css_string[i] == "'":
            string_quoting = "'"
        elif string_quoting == None and css_string[i] == "\"":
            string_quoting = "\""
        backslash_quoted = False
        i += 1
    fragments.append(css_string[current_item_start:i])
    css_items = []
    for item in fragments:
        item = item.strip()
        attribute = CSSAttribute.parse_from(item)
        if attribute != None:
            css_items.append(attribute)
    return css_items

