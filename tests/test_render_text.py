import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def test_render_text_multiline():
    assert convert.render_text("a\nb") == "<div>a</div><div>b</div>"


def test_render_text_blank_line_becomes_br():
    assert convert.render_text("a\n\nb") == "<div>a</div><div><br/></div><div>b</div>"


def test_render_text_escapes():
    assert convert.render_text("x & y") == "<div>x &amp; y</div>"


def test_render_text_empty():
    assert convert.render_text("") == ""
    assert convert.render_text(None) == ""


def test_render_checklist_mixed():
    items = [
        {"text": "buy milk", "isChecked": False},
        {"text": "done task", "isChecked": True},
    ]
    assert convert.render_checklist(items) == "<ul><li>☐ buy milk</li><li>☑ done task</li></ul>"


def test_render_checklist_empty():
    assert convert.render_checklist([]) == "<ul></ul>"


if __name__ == "__main__":
    run(sys.modules[__name__])
