
Getting Started with Wobblui
============================

Installation - System libraries
-------------------------------

**1. Install SDL2 libraries**

To run any wobblui program, you need the following libraries in any place
where Python can find them:

- [SDL2](https://libsdl.org)
- SDL Image
- SDL TTF

Others like SDL GFX are not required.


**Note 1:** on Microsoft Windows, the dlls simply need to be in the `%PATH%`
            once your wobblui program launches.

**Note 2:** development headers **not required.** Wobblui doesn't link any of
            the libraries, it [finds &
            dynamically loads them at runtime](architecture.md#Graphics).

**2. Install C/C++ compiler**

Wobblui requires a [C/C++ compiler](architecture.md#Cython) to install.
On Linux `gcc` is recommended, on Windows you will need
Visual Studio/Build Tools.
For Android, [python-for-android](https://github.com/kivy/python-for-android)
must be set up with the Android SDK (which contains the necessary compiler).


Installation - wobblui
----------------------

With the prerequisites above, get the **stable version of wobblui** like this:
```
pip install --user -U wobblui
```
*(you may need to use `pip3` on Linux systems to ensure Python 3.X is used)*

If you want to have the latest **unstable development version**, use this:
```
pip install https://github.com/wobblui/wobblui/archive/master.zip
```

That's all, you're now ready to use wobblui!
