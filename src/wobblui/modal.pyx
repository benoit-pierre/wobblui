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

from wobblui.box cimport CenterBox
from wobblui.color cimport Color
from wobblui.gfx import draw_rectangle
from wobblui.osinfo cimport is_android
from wobblui.widget cimport Widget
from wobblui.widgetman cimport get_all_windows
from wobblui.window cimport Window


cdef class ModalBox(CenterBox):
    cdef object current_modal_window_parent

    def __init__(self,
            child,
            content_padding=15,
            child_minimum_width=0,
            child_fixed_width=-1,
            child_fixed_height=-1,
            expand_vertically=False,
            expand_horizontally=False):
        self.current_modal_window_parent = None
        super().__init__(
            content_padding=content_padding,
            child_minimum_width=child_minimum_width,
            child_fixed_width=child_fixed_width,
            child_fixed_height=child_fixed_height,
            expand_vertically=expand_vertically,
            expand_horizontally=expand_horizontally,
        )
        if child is not None:
            self.add(child)

    def do_redraw(self):
        renderer = self.renderer
        if renderer is None:
            return
        if self.content_padding > 0 or True:
            c = Color.white()
            if self.style is not None and \
                    self.style.has("modal_dialog_bg"):
                c = Color(self.style.get("modal_dialog_bg"))
            draw_rectangle(
                renderer,
                0, 0, self.width, self.height,
                color=c, alpha=0.4
            )
        super().do_redraw()

    def adjust_size(self):
        if self.parent_window is not None:
            self.width = self.parent_window.width
            self.height = self.parent_window.height
        self.update()

    def on_parentchanged(self):
        window = self.parent_window
        if window is not self.current_modal_window_parent:
            # Remove modal filter from previous window, if any:
            if self.current_modal_window_parent is not None:
                for w_ref in get_all_windows():
                    w = w_ref()
                    if w is not self.current_modal_window_parent:
                        continue
                    w.modal_filter = None
                    w.resized.unregister(self.adjust_size)
            if window is not None:
                # Add modal filter to new parent window:
                def filter_func(widget):
                    if not widget.has_as_parent(self) and \
                            widget != self:
                        return False
                    return True
                self.current_modal_window_parent = window
                window.resized.register(self.adjust_size)
                window.set_modal_filter(filter_func)
                window.focus_update()


cdef class ModalDialog(Widget):
    def __init__(self, modal_to_window):
        self.window_to_add = modal_to_window
        self.modaldlg_callback_issued = False
        self.modal_dlg_window = None
        self.modal_box = None
        self.unset_filter = False
        return

    def close(self):
        if self.modal_dlg_window is not None:
            self.modal_dlg_window.close()
        else:
            if self.window_to_add is not None:
                if self.modal_box in self.window_to_add.children:
                    self.window_to_add.remove(self.modal_box)
                    self.window_to_add.update()
        if self.parent_window is not None:
            if self in self.parent_window.children:
                if self.unset_filter:
                    self.parent_window.modal_filter = None
                self.parent_window.remove(self)
                self.parent_window.update()
            if self.modal_box in self.window_to_add.children:
                self.parent_window.children.remove(self.modal_box)
                self.parent_window.update()

    def run(self, child, done_callback):
        if self.modal_box is not None:
            raise RuntimeError("dialog was already run()")
        self.modal_box = ModalBox(child)
        if is_android() or True:
            # Initialize in current active window:
            if self.parent_window is not None:
                self.parent_window.add(self.modal_box)
            else:
                self.window_to_add.add(self.modal_box)
        else:
            # Add self to parent to block input:
            def filter_func(widget):
                if widget.has_as_parent(self.window_to_add):
                    return False
                return True
            if self.parent_window is None and self.window_to_add is not None:
                self.window_to_add.add(self)
            self.unset_filter = True
            self.parent_window.set_modal_filter(filter_func)

            # Create window:
            self.modal_dlg_window = Window(
                stay_alive_without_ref=True,
                keep_application_running_while_open=False,
            )
            self.modal_dlg_window.bring_to_front()
            self.modal_dlg_window.style = self.window_to_add.style.copy()
            def window_closed_event():
                if not self.modaldlg_callback_issued:
                    self.modaldlg_callback_issued = True
                    if done_callback is not None:
                        done_callback(None)
            self.modal_dlg_window.closing.register(window_closed_event)
            self.modal_dlg_window.add(self.modal_box)
