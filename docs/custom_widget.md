
Implementing Custom Widgets
===========================

To implement a custom widget, write a custom class derived from
`wobblui.widget.Widget` for your widgets.
(Don't forget to call `super().__init__` in your `__init__`
function, if you decide to implement one)

As soon as an `on_redraw()` is implemented accessing `self.width`
and `self.height` for the canvas (use `wobblui.gfx` functions for
drawing), your widget will already display and work in layouts
correctly! Just `.add()` your widget to any layout container
and it should work fine.

To handle any mouse input, implement/override the according
event functions like `on_mousedown`, `on_mousemove`, ... on
your widget class.

To handle any keyboard input, you need to implement an
`__init__` function that passes `can_get_focus=True` to
`super().__init__` to enable keyboard focus for your widget.
As soon as that is done, just implement `on_keydown` to
get key events when your widget is in focus.

To make your widget resize to any desired default size,
implement `get_natural_width()` and `get_natural_height()`.
However, you need to follow the layout rules in the section
`Layout Rules` below, or things will break!

Layout Rules
------------

Any custom widget must follow these rules to not cause feedback loops or
other grave layouting problems:

**1. Stable natural size**

The `get_natural_width()` and `get_natural_height()` function must be stable
in between any two non-`redraw` and non-`relayout` events (only a click,
timer event or similar may cause a change in natural size). Most importantly,
the `relayout()` event being triggered multiple times with no other events
other than `redraw()` in between must not result in a different natural size.

**2. Lowest natural height with no width restriction**

A call to `get_natural_height(given_width=None)` must return an equal or
smaller value than `get_natural_height(given_width=v)` with `v` being
any other non-negative number.



