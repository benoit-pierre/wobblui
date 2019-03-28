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

import functools
import html
import os
import platform
import time

from wobblui.box cimport HBox, VBox
from wobblui.button import Button, ImageButton
from wobblui.color cimport Color
from wobblui.gfx cimport draw_rectangle
from wobblui.image cimport stock_image
from wobblui.label import Label
from wobblui.list import List
from wobblui.modal cimport ModalDialog
from wobblui.osinfo cimport is_android
from wobblui.textentry import TextEntry
from wobblui.timer import schedule
from wobblui.topbar import Topbar
from wobblui.uiconf import config
from wobblui.widget cimport Widget
from wobblui.window cimport Window
from wobblui.woblog cimport logdebug, logerror, loginfo, logwarning

CHOSEN_NOTHING=-1

class _FileOrDirChooserDialogContents(Widget):
    def __init__(self,
            choose_dir=False,
            confirm_text=None,
            title=None,
            can_choose_nothing=False,
            cancel_text="Cancel",
            choose_nonexisting=False,
            start_directory=None,
            file_filter="*",
            done_callback=None):
        if confirm_text == None:
            if choose_dir:
                confirm_text = "Choose Folder"
            else:
                confirm_text = "Choose File"
        self.debug = (config.get("debug_file_dialog") is True)
        if self.debug:
            logdebug("wobblui.filedialog " + str(id(self)) + ": " +
                "dialog initializing " +
                "with start_directory=" + str(start_directory))
        self.choose_dir = choose_dir
        self.show_hidden = False
        self.done_callback = done_callback
        super().__init__(is_container=True,
            can_get_focus=False)
        self.start_directory = start_directory
        self.listing_data = None
        self.listing_path = None
        self.file_filter = file_filter
        vbox = VBox()
        nav_hbox = HBox()
        self.location_label = Label("")
        nav_hbox.add(self.location_label, expand=True,
            shrink=True)
        self.up_button = Button("To Parent")
        self.up_button.set_image(stock_image("outandup"),
            scale_to_width=25.0)
        def go_up():
            self.current_path = os.path.normpath(os.path.abspath(
                os.path.join(self.current_path, "..")))
            self.refresh()
        self.up_button.triggered.register(go_up)
        nav_hbox.add(self.up_button, expand=False)
        vbox.add(nav_hbox, expand=False)
        self.contents_list = List(fixed_one_line_entries=True)
        self.contents_list.triggered.register(self.select_item)
        vbox.add(self.contents_list, shrink=True)
        
        # Add new file entry if choosing new file:
        if not choose_dir and choose_nonexisting:
            create_row = HBox()
            create_label = Label("...or create new file:")
            create_row.add(create_label, expand=False)
            self.create_entry = TextEntry()
            self.create_entry.set_text("Enter New Filename")
            def focus_entry():
                self.create_entry.select_all()
                self.contents_list.selected_index = -1
                def select_all():
                    if self.create_entry.text == \
                            "Enter New Filename":
                        # No typing yet
                        self.create_entry.select_all()
                schedule(select_all, 0.1)
            self.create_entry.focus.register(focus_entry)
            create_row.add(self.create_entry, expand=True)
            vbox.add(create_row, expand=False)

        # Add bottom button row:
        buttons_row = HBox()
        self.cancel_button = Button(cancel_text)
        self.cancel_button.triggered.register(self.abort_dialog)
        self.okay_button = Button(confirm_text)
        self.okay_button.triggered.register(self.select_item)
        if can_choose_nothing:
            self.no_target = Button("Clear Old Choice")
            buttons_row.add(self.no_target, expand=False)
            self.no_target.triggered.register(
                lambda: self.select_item(no_target=True))
            if not choose_nonexisting:
                create_row.add_spacer()
        buttons_row.add_spacer()
        buttons_row.add(self.cancel_button, expand=False)
        buttons_row.add(self.okay_button, expand=False)
        vbox.add(buttons_row, expand=False)
        super().add(vbox)

    def can_access_dir(self, path):
        try:
            if not os.path.exists(path):
                return False
            contents = os.listdir(path)
            return True
        except (OSError, PermissionError):
            return False

    def abort_dialog(self):
        self.done_callback(None)

    def select_item(self, no_target=False):
        if no_target:
            self.done_callback(CHOSEN_NOTHING)
            return
        item_index = self.contents_list.selected_index
        if self.listing_data is None or \
                self.listing_data == "error" or \
                item_index < 0 or \
                item_index >= len(self.listing_data):
            if not self.choose_dir and \
                    hasattr(self, "create_entry") and \
                    len(self.create_entry.text.strip()) > 0 and \
                    self.create_entry.text.strip().lower() != \
                    "Enter New Filename".lower():
                result = os.path.normpath(os.path.abspath(
                    os.path.join(self.current_path,
                    self.create_entry.text.strip())))
                ending = None
                if self.file_filter.startswith("*.") and\
                        len(self.file_filter) > 2:
                    ending = self.file_filter[1:]
                if not result.endswith(ending):
                    result += ending
                self.done_callback(result)
            return
        info = self.listing_data[item_index]
        if info[1]:
            self.current_path = os.path.normpath(os.path.abspath(
                os.path.join(self.current_path,
                info[0].replace(os.path.sep, ""))))
            self.refresh()
            return
        elif not self.choose_dir:
            result = os.path.normpath(os.path.abspath(
                os.path.join(self.current_path,
                info[0].replace(os.path.sep, ""))))
            self.done_callback(result)

    def on_parentchanged(self):
        if self.parent_window is None:
            return
        if self.debug:
            logdebug("wobblui.filedialog " + str(id(self)) +
                ": initializing")
        def filter_func(widget):
            if not widget.has_as_parent(self) and \
                    widget != self:
                return False
            return True
        start_directory = self.start_directory
        if start_directory == None:
            start_directory = self.suggest_start_dir()
        self.current_path = start_directory
        if self.debug:
            logdebug("wobblui.filedialog " + str(id(self)) + ": " +
                "dialog start path is now: " +
                str(self.current_path))
        self.refresh()
        self.contents_list.focus()

    def add(self, *args):
        raise TypeError("cannot add widgets to file dialog")

    def refresh(self):
        if self.debug:
            logdebug("wobblui.filedialog " + str(id(self)) + ": " +
                "refreshing dialog with path: " +
                str(self.current_path))
        try:
            new_listing_data = [[f, None] for f in \
                os.listdir(self.current_path)]
            for item in new_listing_data:
                try:
                    item[1] = os.path.isdir(os.path.join(
                        self.current_path, item[0]))
                except (OSError, PermissionError) as e:
                    if self.debug:
                        logdebug("wobblui.filedialog " +
                            str(id(self)) + ": " +
                            "error getting isdir for '" +
                            str(item) + "': " + str(e))
            if self.debug:
                logdebug("wobblui.filedialog " + str(id(self)) + ": " +
                    "listing obtained is: " +
                    str(new_listing_data))
        except (OSError, PermissionError) as e:
            if self.debug:
                logdebug("wobblui.filedialog " + str(id(self)) + ": " +
                    "failed to obtain listing: " +
                    str(e))
            new_listing_data = "error"
        if self.listing_path != self.current_path and \
                new_listing_data != self.listing_data:
            if self.debug:
                logdebug("wobblui.filedialog " + str(id(self)) + ": " +
                    "rebuilding list contents")
            self.contents_list.clear()
            self.listing_path = self.current_path
            self.listing_data = new_listing_data
            if self.listing_data == "error":
                self.contents_list.add_html("<b>Failed to access " +
                    "folder contents.</b>")
            elif len(self.listing_data) == 0:
                self.contents_list.add_html("<i>(Empty)</i>")
            else:
                def sort_items(a, b):
                    if a[1] == True and b[1] != True:
                        return -1
                    elif a[1] != True and b[1] == True:
                        return 1
                    if (a[0].lower() > b[0].lower()):
                        return 1
                    return -1
                self.listing_data = sorted(
                    self.listing_data, key=\
                    functools.cmp_to_key(sort_items))
                if not self.show_hidden:
                    self.listing_data = [entry for entry in \
                        self.listing_data if not entry[0].startswith(".")]
                if self.choose_dir:
                    self.listing_data = [entry for entry in \
                        self.listing_data if entry[1]]
                if self.file_filter != "*":
                    filters = self.file_filter.replace(" ", ",").split(",")
                    filters = [f.strip() for f in filters if\
                        len(f.strip()) > 0]
                    def is_filtered(name):
                        for filefilter in filters:
                            if filefilter.startswith("*"):
                                if name.lower().endswith(filefilter[1:]):
                                    return False
                        return True
                    self.listing_data = [entry for entry in \
                        self.listing_data if not is_filtered(
                        entry[0].lower()) or entry[1]]
                for item in self.listing_data:
                    t = item[0]
                    if len(t) > 50:
                        t = t[:50] + "..."
                    side_text = None
                    if item[1]:
                        side_text = "(Folder)"
                    self.contents_list.add(t, side_text=side_text)
            self.location_label.set_html("<b>At:</b> " +
                html.escape(os.path.normpath(os.path.abspath(
                    self.current_path))))
            self.needs_redraw = True
            self.needs_relayout = True

    def on_relayout(self):
        inner_padding = max(2, round(5.0 * self.dpi_scale))
        child = self._children[0]
        child.x = inner_padding
        child.y = inner_padding
        child.width = max(1, round(self.width - inner_padding * 2))
        child.height = max(1, round(self.height - inner_padding * 2))

    def on_redraw(self):
        border_c = Color.black()
        if self.style != None:
            border_c = Color(self.style.get("window_bg"))
        draw_rectangle(self.renderer, 0, 0,
                       self.width, self.height, color=border_c)
        self.draw_children()

    def suggest_start_dir(self):
        d = os.path.abspath(os.path.expanduser("~"))
        if not is_android() and os.path.exists(d):
            return d
        elif platform.system().lower() == "windows":
            return "C:\\"
        elif is_android() and not self.can_access_dir("/sdcard/") and \
                self.can_access_dir("/storage/emulated/0/"):
            return "/storage/emluated/0/"
        elif is_android() and not self.can_access_dir("/sdcard/") and \
                self.can_access_dir(d):
            return d
        elif is_android():
            return "/sdcard/"
        elif os.path.exists("/home"):
            return "/home"
        else:
            return "/"

    def get_natural_width(self):
        return round(600 * self.dpi_scale)

    def get_natural_height(self, given_width=None):
        return round(800 * self.dpi_scale)


cdef class FileOrDirChooserDialog(ModalDialog):
    cdef dict file_browser_args
    cdef int callback_issued

    def __init__(self, window, **kwargs):
        super().__init__(window)
        self.file_browser_args = dict(kwargs)
        self.callback_issued = False

    def run(self, done_callback):
        # Initialize in current active window:
        def file_browser_done(result):
            try:
                self.close()
            finally:
                if not self.callback_issued:
                    self.callback_issued = True
                    if done_callback is not None:
                        done_callback(result)
        self.file_browser_args["done_callback"] = file_browser_done
        child = _FileOrDirChooserDialogContents(**self.file_browser_args)
        super().run(child, done_callback)


class FileChooserDialog(FileOrDirChooserDialog):
    def __init__(self,
            window,
            confirm_text=None,
            title=None,
            can_choose_nothing=False,
            choose_nonexisting=False,
            start_directory=None,
            file_filter="*"
            ):
        super().__init__(window, choose_dir=False,
            confirm_text=confirm_text,
            choose_nonexisting=choose_nonexisting,
            start_directory=start_directory,
            title=title,
            can_choose_nothing=can_choose_nothing,
            file_filter=file_filter
            )


class DirectoryChooserDialog(FileOrDirChooserDialog):
    def __init__(self,
            window,
            confirm_text="Select",
            start_directory=None
            ):
        super().__init__(window, choose_dir=False,
            confirm_text=confirm_text,
            choose_nonexisting=False,
            can_choose_nothing=False,
            start_directory=start_directory
            )
