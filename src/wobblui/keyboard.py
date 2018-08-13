
import sdl2 as sdl

def get_modifiers():
    result = set()
    sdl_modstate = sdl.SDL_GetModState()
    if ((sdl_modstate & sdl.KMOD_LSHIFT) != 0 or
            (sdl_modstate & sdl.KMOD_RSHIFT) != 0):
        result.add("shift")
    if ((sdl_modstate & sdl.KMOD_LCTRL) != 0 or
            (sdl_modstate & sdl.KMOD_RCTRL) != 0):
        result.add("ctrl")
    if ((sdl_modstate & sdl.KMOD_LALT) != 0 or
            (sdl_modstate & sdl.KMOD_RALT) != 0):
        result.add("alt")
    return result

