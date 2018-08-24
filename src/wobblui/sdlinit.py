
import sdl2 as sdl
import sdl2.sdlttf as sdlttf

sdl_init_done = False
def initialize_sdl():
    global sdl_init_done
    if sdl_init_done:
        return
    sdl_init_done = True

    sdl.SDL_SetHintWithPriority(
        b"SDL_HINT_RENDER_SCALE_QUALITY", b"2",
        sdl.SDL_HINT_OVERRIDE)
    subsystems = sdl.SDL_WasInit(sdl.SDL_INIT_EVERYTHING)
    if not (subsystems & sdl.SDL_INIT_VIDEO):
        sdl.SDL_Init(sdl.SDL_INIT_VIDEO|sdl.SDL_INIT_TIMER)


