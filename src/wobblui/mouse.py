
'''
wobblui - Copyright 2018 wobblui team, see AUTHORS.md

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.
'''


cursors = dict()

last_set_cursor = "normal"
def set_cursor(system_cursor_name):
    import sdl2 as sdl
    global cursors, last_set_cursor
    if last_set_cursor == system_cursor_name or \
            (last_set_cursor in ["normal", "arrow"] and
            system_cursor_name in ["normal", "arrow"]):
        return
    if system_cursor_name == "normal" or \
            system_cursor_name == "arrow":
        if not "arrow" in cursors:
            cursors["arrow"] = sdl.SDL_CreateSystemCursor(
                sdl.SDL_SYSTEM_CURSOR_ARROW)
        sdl.SDL_SetCursor(cursors["arrow"])
        last_set_cursor = "arrow"
    elif system_cursor_name == "text":
        if not "text" in cursors:
            cursors["text"] = sdl.SDL_CreateSystemCursor(
                sdl.SDL_SYSTEM_CURSOR_IBEAM)
        sdl.SDL_SetCursor(cursors["text"])
        last_set_cursor = "text"
    else:
        raise ValueError("unknown system cursor: " +
            str(system_cursor_name))

cursors_seen_during_mousemove = []
def cursor_seen_during_mousemove(cursor):
    global cursors_seen_during_mousemove
    cursors_seen_during_mousemove.append(cursor)

def reset_cursors_seen_during_mousemove():
    global cursors_seen_during_mousemove
    cursors_seen_during_mousemove[:] = []

