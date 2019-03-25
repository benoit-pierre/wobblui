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

import code
import contextlib
import io
import sys

from wobblui.box import HBox, VBox
from wobblui.font.manager import font_manager
from wobblui.label import Label
from wobblui.textentry import TextEntry
from wobblui.widget import Widget
from wobblui.woblog import logdebug, logerror, loginfo, logwarning

class DebugTerminal(VBox):
    def __init__(self, exit_callback=None, limit_output_height=200):
        super().__init__()
        self.on_exit_callback = exit_callback
        self.output_max_height = limit_output_height
        self.output_label = None
        self.update_label_style()
        self.output_label.set_text("> Debug Terminal")
        super().add(self.output_label, expand=True, shrink=True)
        self.bar = HBox(box_surrounding_padding=3,
            default_expand_on_secondary_axis=False)
        self.console_entry = TextEntry("")
        def console_keypress(vkey, pkey, modifiers):
            if "ctrl" not in modifiers and vkey == "return":
                text = self.console_entry.text
                self.console_entry.set_text("")

                # Our treatment of extra built-in commands:
                def handle_special_command(cmd):
                    cmd = cmd.strip()
                    if cmd == "exit" or cmd == "quit" or \
                            cmd == "exit()" or cmd == "quit()":
                        self.output_label.set_text("")
                        if self.on_exit_callback is not None:
                            self.on_exit_callback()
                        return True
                    elif cmd == "reset" or cmd == "clear":
                        self.output_label.set_text("")
                        return True
                    elif cmd == "help" or cmd == "?" or \
                            cmd == "help()":
                        # (We block interactive help() since that hangs the
                        # process. Couldn't figure that one out yet)
                        print("This is a Python terminal. Try some Python!")
                        return True
                    return False

                # Process commands:
                if not hasattr(self, "interactive_console"):
                    self.interactive_console = code.InteractiveConsole()
                try:
                    bytesobj = io.BytesIO()
                    enc = "utf-8"
                    try:
                        enc = sys.stdout.encoding
                    except AttributeError:
                        pass
                    f = io.TextIOWrapper(bytesobj, enc)
                    with contextlib.redirect_stdout(f):
                        with contextlib.redirect_stderr(f):
                            if not handle_special_command(text):
                                self.interactive_console.push(text)
                    f.flush()
                    s = bytesobj.getvalue()
                    try:
                        s = s.decode("utf-8", "replace")
                    except AttributeError:
                        pass
                    if len(s.strip()) > 0:
                        if s.endswith("\n"):
                            s = s[:-1]
                        elif s.endswith("\r\n"):
                            s = s[:-2]
                        self.output_label.set_text(
                            self.output_label.get_text() + "\n> " +
                            text + "\n" + s
                            )
                    else:
                        self.output_label.set_text(
                            self.output_label.get_text() + "\n> " +
                            text
                            )
                except Exception as e:
                    logerror("interactive console error: " +
                        str(e))
                return True
        self.console_entry.keydown.register(console_keypress)
        self.bar.add(self.console_entry, expand=True, shrink=True)
        super().add(self.bar, expand=False, shrink=False)
        self.on_stylechanged()

    def update_label_style(self):
        label_px = 20
        if self.output_label is None or \
                self._last_label_px != label_px:
            self._last_label_px = label_px
            try:
                font = font_manager().get_font("Monospace",
                    px_size=label_px
                )
            except ValueError:
                logwarning("DebugTerminal: " +
                    "failed to load monospace font for terminal")
                font = None
            if self.output_label is None:
                self.output_label = Label(font=font)
            if font is not None:
                self.output_label.set_font(font)

    def on_stylechanged(self):
        try:
            super().on_stylechanged()
        except AttributeError:
            pass
        if self.output_max_height is not None and self.output_max_height > 0:
            self.output_label.max_height =\
                (self.output_max_height * self.dpi_scale)
        self.update_label_style()

    def focus(self):
        self.console_entry.focus()
 
    def add(self, *args):
        raise RuntimeError("cannot add children to this")


