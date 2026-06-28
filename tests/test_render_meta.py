import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def test_render_labels_basic():
    out = convert.render_labels([{"name": "Работа"}, {"name": "Путешествия"}])
    assert out == '<div style="color:#999">🏷 #Работа #Путешествия</div><div><br/></div>'


def test_render_labels_empty():
    assert convert.render_labels([]) == ""
    assert convert.render_labels(None) == ""


def test_render_annotations_weblink():
    ann = [{"source": "WEBLINK", "title": "T", "url": "http://x"}]
    out = convert.render_annotations(ann)
    assert "Ссылки:" in out
    assert '<a href="http://x">T</a>' in out


def test_render_annotations_empty():
    assert convert.render_annotations([]) == ""
    assert convert.render_annotations(None) == ""


if __name__ == "__main__":
    run(sys.modules[__name__])
