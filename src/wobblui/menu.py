
from wobblui.event import Event
from wobblui.list import ListBase

class Menu(ListBase):
    def __init__(self):
        super().__init__(render_as_menu=True)

    def on_keydown(self, virtual_key, physical_key, modifiers):
        if virtual_key == "escape":
            self.focus_next()
            return True
        return super().on_keydown(virtual_key, physical_key, modifiers)
