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
from wobblui.label import Label
from wobblui.textentry import TextEntry
from wobblui.widget import Widget
from wobblui.woblog import logdebug, logerror, loginfo, logwarning

class DebugTerminal(VBox):
    def __init__(self, exit_callback=None):
        super().__init__()
        self.on_exit_callback = exit_callback
        self.output_label = Label()
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
                        print("wobblui debug terminal. try python commands!")
                        return True
                    return False

                # Process comands:
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

    def focus(self):
        self.console_entry.focus()
 
    def add(self, *args):
        raise RuntimeError("cannot add children to this")


