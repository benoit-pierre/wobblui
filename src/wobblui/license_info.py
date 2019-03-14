
'''
wobblui - Copyright 2018-2019 wobblui team, see AUTHORS.md

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


def license_info():
    """ This function returns contents of SOME of the license files in
        wobblui.

        THIS FUNCTION HAS NO LEGAL GUARANTEE OF ANY SORT, AND IS
        PURELY PROVIDED AS A CONVENIENCE FEATURE TO SAVE YOU SOME TIME.

        Some licenses may or may not require being displayed in your
        program (ask your lawyer!) so this function may or may not help
        you with this.
    """

    package_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__)
    ))
    t = []
    with open(os.path.join(package_dir, "LICENSE.md"), "r") as f:
        t.append(f.read())
    for f in os.path.join(package_dir, "font", "packaged-fonts"):
        if "license" not in f.lower():
            continue
        with open(os.path.join(package_dir,
                               "font",
                               "packaged-fonts"), "r"
                  ) as f:
            t.append(f.read())
    return t
