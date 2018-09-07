
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

class BaseColors(type):
    @property
    def white(self):
        return Color("#fff")

    @property
    def black(self):
        return Color("#000")

    @property
    def red(self):
        return Color("#f00")

    @property
    def green(self):
        return Color("#0f0")

    @property
    def blue(self):
        return Color("#00f")

    @property
    def yellow(self):
        return Color("#fe0")

    @property
    def orange(self):
        return Color("#f70")

    @property
    def gray(self):
        return Color("#444")

class Color(object, metaclass=BaseColors):
    def __init__(self, from_value=None):
        self.red = 255
        self.green = 255
        self.blue = 255
        if isinstance(from_value, str):
            if from_value.startswith("#"):
                if len(from_value) == 4:
                    self.red = int(from_value[1:2] +
                        from_value[1:2], 16)
                    self.green = int(from_value[2:3] +
                        from_value[2:3], 16)
                    self.blue = int(from_value[3:4] +
                        from_value[3:4], 16)
                elif len(from_value) == 7:
                    self.red = int(from_value[1:3], 16)
                    self.green = int(from_value[3:5], 16)
                    self.blue = int(from_value[5:7], 16)
                else:
                    raise ValueError("unrecognized color " +
                        "value: " + str(from_value))
            else:
                raise ValueError("unrecognized color " +
                    "value: " + str(from_value))
        elif isinstance(from_value, tuple) and len(from_value) == 3:
            self.red = max(0, min(255, round(from_value[0])))
            self.green = max(0, min(255, round(from_value[1])))
            self.blue = max(0, min(255, round(from_value[2])))
        elif isinstance(from_value, Color):
            self.red = max(0, min(255, round(from_value.red)))
            self.green = max(0, min(255, round(from_value.green)))
            self.blue = max(0, min(255, round(from_value.blue)))
        else:
            raise ValueError("unrecognized color " +
                "value: " + str(from_value))

    def __repr__(self):
        return "<Color " + str((
            self.red, self.green, self.blue)) + ">"

    @property
    def brightness(self):
        return max(0.0, min(1.0, (max(0, min(255, self.red)) +
            max(0, min(255, self.blue)) +
            max(0, min(255, self.green))) / (255.0 * 3.0)))

    @property
    def html(self):
        def tohex(v):
            t = "{:x}".format(max(0, min(255, int(v))))
            while len(t) < 2:
                t = "0" + t
            return t
        return "#" + tohex(self.red) +\
            tohex(self.green) +\
            tohex(self.blue)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return other.red == self.red and \
            other.green == self.green and \
            other.blue == self.blue 

