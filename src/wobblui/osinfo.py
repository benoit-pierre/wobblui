
from wobblui.sdlinit import initialize_sdl

cached_is_android = None
def is_android():
    global cached_is_android
    if cached_is_android != None:
        return cached_is_android
    initialize_sdl()
    import sdl2 as sdl
    cached_is_android = (sdl.SDL_GetPlatform().decode(
        "utf-8", "replace").lower() == "android")
    return cached_is_android
 
