
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

from wobblui.keyboard import get_all_active_text_widgets
from wobblui.osinfo import is_android
from wobblui.uiconf import config

touch_handles_enabled = False

def draw_drag_selection_handles(window):
    global touch_handles_enabled
    if is_android():
        touch_handles_enabled = True
    if config.get("mouse_fakes_touch_events"):
        touch_handles_enabled = True
    if not touch_handles_enabled:
        return
    for w in get_all_active_text_widgets():
        if not hasattr(w, "parent_window"):
            continue
        if w.parent_window != window:
            continue
        w.draw_touch_selection_handles_if_any(
            w.parent_window.width, w.parent_window.height)

