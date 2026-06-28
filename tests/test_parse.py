import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def _write_note(data, filename="Test Note.json"):
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


def test_parse_full_note():
    path = _write_note({
        "title": "#Работа ",
        "textContent": "hello",
        "listContent": [{"text": "x", "isChecked": True}],
        "labels": [{"name": "Работа"}],
        "annotations": [{"source": "WEBLINK", "title": "T", "url": "http://x"}],
        "attachments": [{"filePath": "a.jpg", "mimetype": "image/jpeg"}],
        "createdTimestampUsec": 1404630578154000,
        "userEditedTimestampUsec": 1496762375677000,
        "isTrashed": False,
        "isArchived": True,
    })
    note = convert.parse_note(path)
    assert note.title == "#Работа"
    assert note.text_content == "hello"
    assert note.list_content == [{"text": "x", "isChecked": True}]
    assert note.labels == [{"name": "Работа"}]
    assert note.annotations == [{"source": "WEBLINK", "title": "T", "url": "http://x"}]
    assert note.attachments == [{"filePath": "a.jpg", "mimetype": "image/jpeg"}]
    assert note.created_usec == 1404630578154000
    assert note.edited_usec == 1496762375677000
    assert note.is_trashed is False
    assert note.source_name == "Test Note"


def test_parse_minimal_note_defaults():
    path = _write_note({"title": "", "isTrashed": True})
    note = convert.parse_note(path)
    assert note.title == ""
    assert note.text_content == ""
    assert note.list_content == []
    assert note.labels == []
    assert note.attachments == []
    assert note.created_usec == 0
    assert note.is_trashed is True


if __name__ == "__main__":
    run(sys.modules[__name__])
