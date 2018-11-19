
import sys
import time

from wobblui.richtext import RichText
from wobblui.uiconf import config

def test_perf(capsys):
    try:
        with capsys.disabled():  # ensure perf data is printed
            config.set("perf_debug", False)
            text_setting_times = 0.0
            layouting_times = 0.0
            i = 0
            while i < 20:
                obj = RichText()
                test_text = ("Lorem ipsum - this is a " +
                    "test text. It is very long.") * 50
                t1 = time.monotonic()
                obj.set_text(test_text)
                t2 = time.monotonic()
                obj.layout(max_width=(100 / max(1, i)))
                t3 = time.monotonic()
                text_setting_times += (t2 - t1)
                layouting_times += (t3 - t2)
                i += 1
            text_setting_times /= i
            layouting_times /= i
            print("Times: setting text: " +
                str(round(text_setting_times * 1000)) + "ms" +
                ", layouting: " +
                str(round(layouting_times * 1000)) + "ms",
                    file=sys.stderr, flush=True)
    except Exception as e:
        raise e



