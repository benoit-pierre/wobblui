
from wobblui.event import Event
from wobblui.list import ListBase

class Menu(ListBase):
    def __init__(self):
        super().__init__(render_as_menu=True)
        self.callback_funcs = []
        self.triggered_by_single_click = True

    def on_triggered(self):
        item_id = self.selected_index
        if item_id >= 0:
            f = None
            if item_id < len(self.callback_funcs):
                if self.callback_funcs[item_id] != None:
                    f = self.callback_funcs[item_id]
            if self.focused:
                self.focus_next()
            if f != None:
                f()

    def add(self, text, func_callback=None):
        super().add(text)
        self.callback_funcs.append(func_callback)

    def on_keydown(self, virtual_key, physical_key, modifiers):
        if virtual_key == "escape":
            self.focus_next()
            return True
        return super().on_keydown(virtual_key, physical_key, modifiers)
