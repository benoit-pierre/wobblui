
from wobblui.widget import Widget

class Box(Widget):
    def __init__(self, horizontal):
        super().__init__(is_container=True)
        self.horizontal = (horizontal is True)

    def add(self, item, expand=False):
        pass

    def add_spacer(self):
        pass

class VBox(Box):
    def __init__(self):
        super().__init__(False)

class HBox(Box):
    def __init__(self):
        super().__init__(False)


