
import functools
import html
import os
import platform

from wobblui.box import HBox, VBox
from wobblui.button import Button, ImageButton
from wobblui.color import Color
from wobblui.gfx import draw_rectangle
from wobblui.image import stock_image
from wobblui.label import Label
from wobblui.list import List
from wobblui.topbar import Topbar
from wobblui.uiconf import config
from wobblui.widget import Widget

class FileOrDirChooserDialog(Widget):
    def __init__(self, window, choose_dir=False, confirm_text="Open",
            cancel_text="Cancel",
            choose_nonexisting=False, outer_padding=15.0,
            start_directory=None, file_filter="*"):
        self.debug = (config.get("debug_file_dialog") is True)
        if self.debug:
            print("wobblui.filedialog " + str(id(self)) + ": " +
                "dialog initializing " +
                "with start_directory=" + str(start_directory))
        self.choose_dir = choose_dir
        self.window_to_add = window
        self.show_hidden = False
        self.active = False
        super().__init__(is_container=True,
            can_get_focus=False)
        self.outer_padding = outer_padding
        self.start_directory = start_directory
        self.listing_data = None
        self.file_filter = file_filter
        topbar = Topbar()
        topbar.add_to_top(Label("Choose a " +
            ("File:" if not choose_dir else "Folder:")))
        vbox = VBox()
        nav_hbox = HBox()
        self.location_label = Label("")
        nav_hbox.add(self.location_label, expand=True,
            shrink=True)
        self.up_button = Button("To Parent Folder...")
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
        buttons_row = HBox()
        self.cancel_button = Button(cancel_text)
        self.cancel_button.triggered.register(self.abort_dialog)
        self.okay_button = Button(confirm_text)
        self.okay_button.triggered.register(self.select_item)
        buttons_row.add_spacer()
        buttons_row.add(self.cancel_button, expand=False)
        buttons_row.add(self.okay_button, expand=False)
        vbox.add(buttons_row, expand=False)
        topbar.add(vbox)
        super().add(topbar)

    def stop_run(self):
        self.active = False
        self.window_to_add.resized.unregister(self.update)
        self.window_to_add.remove(self)
        self.window_to_add.modal_filter = None
        self.window_to_add.focus_update()
        if self.start_directory != None:
            current_path = self.start_directory
        else:
            current_path = self.suggest_start_dir()

    def abort_dialog(self):
        self.stop_run()
        self.run_callback(None)

    def select_item(self):
        item_index = self.contents_list.selected_index
        if self.listing_data is None or \
                self.list_data == "error" or \
                item_index < 0 or \
                item_index >= len(self.listing_data):
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
            self.stop_run()
            self.run_callback(result)

    def run(self, done_callback):
        if self.debug:
            print("wobblui.filedialog " + str(id(self)) +
                ": run() called")
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
            print("wobblui.filedialog " + str(id(self)) + ": " +
                "dialog start path is now: " +
                str(self.current_path))
        self.window_to_add.add(self)
        self.active = True
        self.width = self.parent_window.width
        self.height = self.parent_window.height
        self.x = 0
        self.y = 0
        self.run_callback = done_callback
        self.window_to_add.set_modal_filter(filter_func)
        self.window_to_add.resized.register(self.update)
        self.refresh()
        self.contents_list.focus()

    def add(self, *args):
        raise TypeError("cannot add widgets to file dialog")

    def refresh(self):
        if self.debug:
            print("wobblui.filedialog " + str(id(self)) + ": " +
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
                        print("wobblui.filedialog " +
                            str(id(self)) + ": " +
                            "error getting isdir for '" +
                            str(f) + "': " + str(e))
            if self.debug:
                print("wobblui.filedialog " + str(id(self)) + ": " +
                    "listing obtained is: " +
                    str(new_listing_data))
        except (OSError, PermissionError) as e:
            if self.debug:
                print("wobblui.filedialog " + str(id(self)) + ": " +
                    "failed to obtain listing: " +
                    str(e))
            new_listing_data = "error"
        if new_listing_data != self.listing_data:
            if self.debug:
                print("wobblui.filedialog " + str(id(self)) + ": " +
                    "rebuilding list contents")
            self.contents_list.clear()
            self.listing_data = new_listing_data
            if self.listing_data == "error":
                self.contents_list.add_html("<b>Failed to access " +
                    "this folder.</b>")
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
                    if self.file_filter.startswith("*"):
                        self.listing_data = [entry for entry in \
                            self.listing_data if entry[0].lower().endswith(
                            self.file_filter[1:]) or entry[1]]
                for item in self.listing_data:
                    t = item[0]
                    if len(t) > 50:
                        t = t[:50] + "..."
                    side_text = None
                    if item[1]:
                        side_text = "(Folder)"
                    self.contents_list.add(t, side_text=side_text)
            self.location_label.set_html("<b>Location:</b> " +
                html.escape(os.path.normpath(os.path.abspath(
                    self.current_path))))
            self.needs_redraw = True
            self.needs_relayout = True

    def on_relayout(self):
        if self.active:
            self.x = 0
            self.y = 0
            self.width = self.parent_window.width
            self.height = self.parent_window.height
        outer_padding = max(0, round(self.outer_padding * self.dpi_scale))
        inner_padding = max(2, round(3.0 * self.dpi_scale))
        total_padding = outer_padding + inner_padding
        child = self._children[0]
        child.x = total_padding
        child.y = total_padding
        child.width = max(1, round(self.width - total_padding * 2))
        child.height = max(1, round(self.height - total_padding * 2))

    def on_redraw(self):
        outer_padding = max(0, round(self.outer_padding * self.dpi_scale))
        border_c = Color.black
        bg_c = Color.white
        if self.style != None:
            border_c = Color(self.style.get("border"))
            bg_c = Color(self.style.get("window_bg"))
        outer_border_width = max(1, round(1.0 * self.dpi_scale))
        draw_rectangle(self.renderer, outer_padding, outer_padding,
            self.width - outer_padding * 2,
            self.height - outer_padding * 2, color=border_c)
        draw_rectangle(self.renderer,
            outer_border_width + outer_padding,
            outer_border_width + outer_padding,
            self.width - outer_border_width * 2 - outer_padding * 2,
            self.height - outer_border_width * 2 - outer_padding * 2,
            color=bg_c)
        self.draw_children()

    def suggest_start_dir(self):
        d = os.path.abspath(os.path.expanduser("~"))
        if os.path.exists(d):
            return d
        elif platform.system().lower() == "windows":
            return "C:\\"
        elif os.path.exists("/home"):
            return "/home"
        elif os.path.exists("/sdcard"): # android
            return "/sdcard"
        else:
            return "/"

    def get_natural_width(self):
        return round(200 * self.dpi_scale)

    def get_natural_height(self, given_width=None):
        return round(600 * self.dpi_scale)

class FileChooserDialog(FileOrDirChooserDialog):
    def __init__(self, window, confirm_text="Open",
            choose_nonexisting=False, outer_padding=15.0,
            start_directory=None,
            file_filter="*"):
        super().__init__(window, choose_dir=False,
            confirm_text=confirm_text,
            choose_nonexisting=choose_nonexisting,
            outer_padding=outer_padding,
            start_directory=start_directory,
            file_filter=file_filter)

class DirectoryChooserDialog(FileOrDirChooserDialog):
    def __init__(self, window, confirm_text="Select",
            outer_padding=15.0, start_directory=None):
        super().__init__(window, choose_dir=False,
            confirm_text=confirm_text,
            choose_nonexisting=False,
            outer_padding=outer_padding,
            start_directory=start_directory)


