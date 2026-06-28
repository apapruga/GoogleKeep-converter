import json
import os
import sys
import tempfile
from xml.dom import minidom

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def _make_keep_dir():
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "Text.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "Text", "textContent": "hello", "createdTimestampUsec": 1404630578154000}, f)
    with open(os.path.join(d, "Trashed.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "Trashed", "textContent": "bye", "isTrashed": True}, f)
    return d


def test_convert_directory_returns_report_and_writes_file():
    keep_dir = _make_keep_dir()
    out = os.path.join(keep_dir, "out.enex")
    report = convert.convert_directory(keep_dir, out)
    assert report["processed"] == 1  # Trashed пропущена
    assert report["trashed"] == 1
    assert report["with_attachments"] == 0
    assert report["missing_attachments"] == 0
    assert report["size_bytes"] > 0
    assert os.path.isfile(out)
    dom = minidom.parse(out)
    assert len(dom.getElementsByTagName("note")) == 1


def test_convert_directory_include_trashed():
    keep_dir = _make_keep_dir()
    out = os.path.join(keep_dir, "out.enex")
    report = convert.convert_directory(keep_dir, out, include_trashed=True)
    assert report["processed"] == 2
    assert report["trashed"] == 0


def test_convert_directory_progress_cb():
    keep_dir = _make_keep_dir()
    out = os.path.join(keep_dir, "out.enex")
    calls = []
    convert.convert_directory(keep_dir, out, progress_cb=lambda done, total: calls.append((done, total)))
    assert calls[-1][0] == 2  # оба json обработаны (до фильтра trashed)
    assert all(t == 2 for _, t in calls)


if __name__ == "__main__":
    run(sys.modules[__name__])
