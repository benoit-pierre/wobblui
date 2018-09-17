
import sdl2 as sdl

cursors = dict()

last_set_cursor = "normal"
def set_cursor(system_cursor_name):
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

