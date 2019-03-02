
wobblui
=======
*(experimental project)*

**Wobblui** is a versatile & easy-to-use UI framework for Python 3!

**Why wobblui is awesome**:

- *Cross-platform:* Works on Windows, Linux, and
                    [Android](https://github.com/kivy/python-for-android)
- *Easy:* simple API & versatile auto-scaling box layouts
- *Efficient:* 3d accelerated, on-demand redraw/relayout ('lazy') and more!

It also has a consistent look on all platforms and supports styling,
including freeform UI scaling!

This is how easy wobblui is to use:

```
from wobblui import event_loop
from wobblui.label import Label
from wobblui.window import Window

w = Window()
w.add(Label("Hello World! This is a wobblui example!"))

event_loop()
```
**See [the Quickstart Guide for more!](docs/getting_started.md)**


Installation
------------

You'll need `SDL2` and some `SDL2`-related libraries as prerequisite,
**see [the Installation Guide](docs/quickstart.md).**

Afterwards, just install from pip:
```
pip install --user -U wobblui
```
*(make sure to use a Python 3.X pip! Python 2 is NOT supported)*


Documentation
-------------

[Jump into the documentation here!](docs/index.html)


License
-------

Wobblui is open-source under various licenses (due to some included
3rd-party components), but most of it is zlib-licensed.

[See the LICENSE.md document for full details!](LICENSE.md)



