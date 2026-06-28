import os
import sys
import tempfile
from xml.dom import minidom

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _run_on_fixtures():
    keep_dir = FIXTURES
    out_dir = tempfile.mkdtemp()
    out = os.path.join(out_dir, "integration.enex")
    rc = convert.main([keep_dir, out])
    assert rc == 0
    return out


def test_integration_valid_xml_with_expected_notes():
    out = _run_on_fixtures()
    dom = minidom.parse(out)
    notes = dom.getElementsByTagName("note")
    titles = []
    for note in notes:
        t = note.getElementsByTagName("title")
        if t:
            titles.append(t[0].firstChild.nodeValue if t[0].firstChild else "")
    # все json-фикстуры, кроме test_* файлов (их нет в fixtures). Ожидаются 4:
    assert "Текстовая заметка" in titles
    assert "Список покупок" in titles
    assert "С картинкой" in titles
    assert "empty_note" in titles  # пустой title → имя файла
    assert len(notes) == 4


def test_integration_checklist_has_marks():
    out = _run_on_fixtures()
    content = open(out, encoding="utf-8").read()
    assert "☐ молоко" in content
    assert "☑ хлеб" in content


def test_integration_text_note_has_labels_and_link():
    out = _run_on_fixtures()
    content = open(out, encoding="utf-8").read()
    assert "🏷 #Работа" in content
    assert '<a href="http://example.com">Пример</a>' in content


def test_integration_attachment_note_has_resource():
    out = _run_on_fixtures()
    dom = minidom.parse(out)
    resources = dom.getElementsByTagName("resource")
    assert len(resources) >= 1
    content = open(out, encoding="utf-8").read()
    assert "<en-media" in content


if __name__ == "__main__":
    run(sys.modules[__name__])
