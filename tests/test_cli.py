import glob
import json
import os
import sys
import tempfile
from xml.dom import minidom

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _make_keep_dir():
    d = tempfile.mkdtemp()
    # текстовая заметка
    with open(os.path.join(d, "Text.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "Text", "textContent": "hello", "createdTimestampUsec": 1404630578154000}, f)
    # заметка с вложением (используем существующую фикстуру-байты)
    with open(os.path.join(d, "WithImg.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "WithImg", "attachments": [{"filePath": "img1.png", "mimetype": "image/png"}]}, f)
    with open(os.path.join(d, "img1.png"), "wb") as f:
        f.write(b"FAKEIMAGEBYTES")
    # удалённая заметка (должна быть пропущена по умолчанию)
    with open(os.path.join(d, "Trashed.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "Trashed", "textContent": "bye", "isTrashed": True}, f)
    return d


def test_main_produces_valid_enex_and_skips_trashed():
    keep_dir = _make_keep_dir()
    out = os.path.join(keep_dir, "out.enex")
    rc = convert.main([keep_dir, out])
    assert rc == 0
    assert os.path.isfile(out)

    dom = minidom.parse(out)  # бросится, если XML невалиден
    notes = dom.getElementsByTagName("note")
    # Text + WithImg, Trashed пропущена
    assert len(notes) == 2


def test_main_include_trashed_flag_keeps_all():
    keep_dir = _make_keep_dir()
    out = os.path.join(keep_dir, "out.enex")
    convert.main([keep_dir, out, "--include-trashed"])
    dom = minidom.parse(out)
    notes = dom.getElementsByTagName("note")
    assert len(notes) == 3


if __name__ == "__main__":
    run(sys.modules[__name__])
