import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def test_real_timestamp():
    # 1404630578154000 usec = 2014-07-06 07:09:38 UTC
    assert convert.format_timestamp(1404630578154000) == "20140706T070938Z"


def test_zero_timestamp_falls_back_to_now():
    result = convert.format_timestamp(0)
    assert re.fullmatch(r"\d{8}T\d{6}Z", result), result


def test_none_timestamp_falls_back_to_now():
    result = convert.format_timestamp(None)
    assert re.fullmatch(r"\d{8}T\d{6}Z", result), result


if __name__ == "__main__":
    run(sys.modules[__name__])
