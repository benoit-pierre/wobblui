
import sys
import time

from wobblui.richtext import RichText
from wobblui.uiconf import config

def test_perf(capsys):
    try:
        with capsys.disabled():  # ensure perf data is printed
            config.set("perf_debug", True)
            i = 0
            while i < 5:
                obj = RichText()
                test_text = ("Lorem ipsum - this is a " +
                    "test text. It is very long.") * 50
                t1 = time.monotonic()
                obj.set_text(test_text)
                t2 = time.monotonic()
                obj.layout(max_width=100)
                t3 = time.monotonic()
                print("Times: setting text: " +
                    str(round((t2 - t1) * 1000.0)) + "ms" +
                    ", layouting: " +
                    str(round((t3 - t2) * 1000.0)) + "ms",
                    file=sys.stderr, flush=True)
                i += 1
    except Exception as e:
        raise e
