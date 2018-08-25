
import os
import sys
sys.path = [os.path.abspath(os.path.dirname(__file__))] + sys.path
print("PATH: " + str(sys.path))

import htmlparse

def test_parser():
    result = htmlparse.parse("<a>&lt;3</a>")
    result_html = str(result)
    assert(result[0].serialize() == "<a>&lt;3</a>")
