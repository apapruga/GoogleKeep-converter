import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def test_xml_escape_basic():
    assert convert.xml_text_escape("a & b < c > d") == "a &amp; b &lt; c &gt; d"


def test_sanitize_keeps_div():
    assert convert.sanitize_html("<div>hi</div>") == "<div>hi</div>"


def test_sanitize_strips_script():
    assert convert.sanitize_html("<script>alert(1)</script>") == ""


def test_sanitize_drops_style_attr():
    assert convert.sanitize_html('<span style="color:red">t</span>') == "<span>t</span>"


def test_sanitize_keeps_a_href():
    assert convert.sanitize_html('<a href="http://x">L</a>') == '<a href="http://x">L</a>'


def test_sanitize_escapes_amp_in_text():
    assert convert.sanitize_html("<span>Tom &amp; Jerry</span>") == "<span>Tom &amp; Jerry</span>"


def test_sanitize_empty():
    assert convert.sanitize_html("") == ""
    assert convert.sanitize_html(None) == ""


if __name__ == "__main__":
    run(sys.modules[__name__])
