#cython: language_level=3

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

import os
import sys
import traceback

from wobblui import event_loop
from wobblui.box import VBox
from wobblui.image import ImageWidget, RenderImage
from wobblui.label import Label
from wobblui.window import Window

def launch_viewer(fpath, delete_source=False):
    # Disable stdout:
    f = open(os.devnull, 'w')
    sys.stdout = f
    
    # Load image into UI:
    w = Window(title="Image " + str(fpath))
    b = VBox()
    w.add(b)
    b.add(Label("Image loaded from " + str(fpath)), expand=False)
    try:
        ri = RenderImage(fpath)
        b.add(ImageWidget(ri))
    except Exception as e:
        b.add(Label("Failed to load image: " + str(
            traceback.format_exception_only(type(e), e)
        )))
    if delete_source is True:
        os.remove(fpath)
    event_loop()
