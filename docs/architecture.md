
Architecture
============

This section has some overview information about how wobblui
works internally.


Cython
------

Wobblui is written in Python 3 and
[Cython](https://github.com/cython/cython).
This means large parts compile to native libraries for speed,
such that all core widgets perform adequately even on mobile.

As a result, wobblui cannot be installed without a *C/C++ compiler*
being present. On Microsoft Windows, this means Visual Studio, or
respectively the C/C++ Build Tools, are required.
*(This is not necessary for your application later if you package
  it in some baked binary format like with PyInstaller or a wheel)*


Graphics
--------

All graphics & event handling is based on
[SDL2](https://libsdl.org/) and all rendering uses the so-called
`SDL Renderer` which supports DirectX, OpenGL, vulkan, and more.

SDL2 is loaded **dynamically** at runtime, which means wobblui can
even be installed without it present! You also only need the actual
libraries, *no development headers.* Wobblui achieves this by combining
its use of Cython for performance with the use of `ctypes` for flexibility.


Image handling
--------------

Images are generally loaded up with
[PIL](https://github.com/python-pillow/Pillow), one of the most
wide-spread image libraries for Python, which should hopefully
give you all the interoperability you need.


