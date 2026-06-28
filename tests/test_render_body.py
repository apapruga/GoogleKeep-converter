import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def test_body_prefers_html_over_text():
    note = convert.Note(title="t", text_content="plain", text_content_html="<div>rich</div>")
    body = convert.render_body(note)
    assert "<div>rich</div>" in body
    assert "plain" not in body


def test_body_falls_back_to_text_when_html_blank():
    note = convert.Note(title="t", text_content="plain", text_content_html="")
    body = convert.render_body(note)
    assert "<div>plain</div>" in body


def test_body_uses_checklist_when_list_present():
    note = convert.Note(
        title="t",
        list_content=[{"text": "x", "isChecked": False}],
        text_content="ignored",
    )
    body = convert.render_body(note)
    assert "<ul><li>☐ x</li></ul>" in body
    assert "ignored" not in body


def test_body_includes_labels_and_annotations():
    note = convert.Note(
        title="t",
        text_content="hi",
        labels=[{"name": "Работа"}],
        annotations=[{"source": "WEBLINK", "title": "T", "url": "http://x"}],
    )
    body = convert.render_body(note)
    assert "🏷 #Работа" in body
    assert "<div>hi</div>" in body
    assert "Ссылки:" in body
    assert '<a href="http://x">T</a>' in body


def test_body_empty_note():
    note = convert.Note(title="t")
    assert convert.render_body(note) == ""


def test_body_sanitizes_html():
    note = convert.Note(title="t", text_content_html="<div>a</div><script>x</script>")
    body = convert.render_body(note)
    assert "<div>a</div>" in body
    assert "<script>" not in body


if __name__ == "__main__":
    run(sys.modules[__name__])
