
Architecture
============

Wobblui is written in Python 3 and
[Cython](https://github.com/cython/cython).
This means large parts compile to native libraries for speed,
such that all core widgets perform adequately even on mobile.

All graphics & event handling is based on
[SDL2](https://libsdl.org/) and all rendering uses the so-called
`SDL Renderer` which supports DirectX, OpenGL, vulkan, and more.

Images are generally loaded up with
[PIL](https://github.com/python-pillow/Pillow), one of the most
wide-spread image libraries for Python, which should hopefully
give you all the interoperability you need.


