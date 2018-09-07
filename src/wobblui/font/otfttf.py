
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

'''
Parts of this code are based on modified code from fonttools.
The original licensing of this code / fonttools is as follows:

MIT License

Copyright (c) 2017 Just van Rossum

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''

from __future__ import print_function, division, absolute_import
import sys
import argparse

from wobblui.woblog import logdebug, logerror, loginfo, logwarning

# default approximation error, measured in UPEM
MAX_ERR = 1.0
# default 'post' table format
POST_FORMAT = 2.0
# assuming the input contours' direction is correctly set (counter-clockwise),
# we just flip it to clockwise
REVERSE_DIRECTION = True


def glyphs_to_quadratic(
        glyphs, max_err=MAX_ERR, reverse_direction=REVERSE_DIRECTION):
    try:
        from cu2qu.pens import Cu2QuPen
        from fontTools.pens.ttGlyphPen import TTGlyphPen
    except ImportError:
        raise ValueError("cannot convert glyphs due to missing libs")
    quadGlyphs = {}
    for gname in glyphs.keys():
        glyph = glyphs[gname]
        ttPen = TTGlyphPen(glyphs)
        cu2quPen = Cu2QuPen(ttPen, max_err,
                            reverse_direction=reverse_direction)
        glyph.draw(cu2quPen)
        quadGlyphs[gname] = ttPen.glyph()
    return quadGlyphs


def otf_to_ttf_do(ttFont, post_format=POST_FORMAT, **kwargs):
    if ttFont.sfntVersion != "OTTO":
        raise NotImplementedError("cannot convert this font format")

    try:
        from fontTools.ttLib import TTFont, newTable
        from cu2qu.pens import Cu2QuPen
        from fontTools.pens.ttGlyphPen import TTGlyphPen
        from fontTools.ttx import makeOutputFileName
    except ImportError:
        logwarning("wobblui.font.otftottf.py: " +
            "warning: OTF font conversion aborted due to " +
            "missing fontTools and cu2qu dependencies")
        raise ValueError("cannot convert OTF fonts without " +
            "the fontTools and cu2qu libraries")

    assert "CFF " in ttFont

    glyphOrder = ttFont.getGlyphOrder()

    ttFont["loca"] = newTable("loca")
    ttFont["glyf"] = glyf = newTable("glyf")
    glyf.glyphOrder = glyphOrder
    glyf.glyphs = glyphs_to_quadratic(ttFont.getGlyphSet(), **kwargs)
    del ttFont["CFF "]

    ttFont["maxp"] = maxp = newTable("maxp")
    maxp.tableVersion = 0x00010000
    maxp.maxZones = 1
    maxp.maxTwilightPoints = 0
    maxp.maxStorage = 0
    maxp.maxFunctionDefs = 0
    maxp.maxInstructionDefs = 0
    maxp.maxStackElements = 0
    maxp.maxSizeOfInstructions = 0
    maxp.maxComponentElements = max(
        len(g.components if hasattr(g, 'components') else [])
        for g in glyf.glyphs.values())

    post = ttFont["post"]
    post.formatType = post_format
    post.extraNames = []
    post.mapping = {}
    post.glyphOrder = glyphOrder

    ttFont.sfntVersion = "\000\001\000\000"

def otf_to_ttf(fpath, new_fpath):
    font = TTFont(fpath)
    try:
        otf_to_ttf_do(font, post_format=POST_FORMAT,
               max_err=MAX_ERR,
               reverse_direction=REVERSE_DIRECTION)
    except (NotImplementedError, ValueError):
        raise ValueError("cannot convert this font " +
            "from otf to ttf: " + str(fpath))
    font.save(new_fpath)
    return new_fpath

