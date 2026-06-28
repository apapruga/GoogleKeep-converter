import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def test_build_enex_wraps_notes():
    enex = convert.build_enex(["<note>x</note>", "<note>y</note>"])
    assert enex.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<!DOCTYPE en-export SYSTEM" in enex
    assert "<en-export " in enex
    assert enex.rstrip().endswith("</en-export>")
    assert "<note>x</note>" in enex
    assert "<note>y</note>" in enex
    assert 'application="GoogleKeep Converter"' in enex


def test_build_enex_export_date_format():
    enex = convert.build_enex([])
    m = re.search(r'export-date="(\d{8}T\d{6}Z)"', enex)
    assert m is not None, enex


def test_build_enex_empty():
    enex = convert.build_enex([])
    assert "<en-export" in enex
    assert "</en-export>" in enex


if __name__ == "__main__":
    run(sys.modules[__name__])
