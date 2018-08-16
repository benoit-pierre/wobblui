
from wobblui.event import Event
from wobblui.style import AppStyleBright
from wobblui.widget_base import all_widgets, tab_sort, WidgetBase
from wobblui.window import Window

class Widget(WidgetBase):
    def __init__(self, is_container=False, can_get_focus=False):
        super().__init__(is_container=is_container,
            can_get_focus=can_get_focus)
        self.parentwindowresized = Event("parentwindowresized",
            owner=self)

    def update_window(self):
        self.needs_redraw = True

    def get_style(self):
        if self.parent_window == None:
            return AppStyleBright()
        return self.parent_window.style

    @property
    def parent_window(self):
        p = self.parent
        while p:
            if isinstance(p, Window):
                return p
            p = p.parent

    def focus_next(self):
        if not self.focused:
            raise RuntimeError("widget isn't focused")
        self._advance_focus(True)

    def focus_previous(self):
        if not self.focused:
            raise RuntimeError("widget isn't focused")
        self._advance_focus(False)

    def _advance_focus(self, forward):
        sorted_candidates = self.__class__.focus_candidates(self)
        i = 0
        while i < len(sorted_candidates):
            if sorted_candidates[i] == self:
                if forward:
                    if i + 1 < len(sorted_candidates):
                        sorted_candidates[i + 1].focus()
                    else:
                        sorted_candidates[0].focus()
                else:
                    if i > 0:
                        sorted_candidates[i - 1].focus()
                    else:
                        sorted_candidates[len(sorted_candidates) - 1].\
                            focus()
                return
            i += 1

    def get_renderer(self):
        v = super().get_renderer()
        if v is None:
            w = self.parent_window
            if w != None:
                return w.get_renderer()
        return v

    def shares_focus_group(self, widget):
        if isinstance(widget, Window):
            return False
        if isinstance(widget, Widget):
            return (self.parent_window == widget.parent_window)
        return True
