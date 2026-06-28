import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_note_xml_structure():
    note = convert.Note(
        title="#Работа",
        text_content="hello",
        created_usec=1404630578154000,
        edited_usec=1496762375677000,
        source_name="Работа",
    )
    xml = convert.note_to_xml(note, FIXTURES)
    assert xml.startswith("<note>")
    assert xml.endswith("</note>")
    assert "<title>#Работа</title>" in xml
    assert "<created>20140706T070938Z</created>" in xml
    assert "<updated>20170606T151935Z</updated>" in xml
    assert "<note-attributes><source>Google Keep</source></note-attributes>" in xml
    assert "<en-note>" in xml
    assert "<div>hello</div>" in xml
    assert "<![CDATA[" in xml


def test_note_xml_empty_title_uses_source_name():
    note = convert.Note(title="", source_name="My Note", text_content="x")
    xml = convert.note_to_xml(note, FIXTURES)
    assert "<title>My Note</title>" in xml


def test_note_xml_escapes_title():
    note = convert.Note(title="a & b < c", text_content="x")
    xml = convert.note_to_xml(note, FIXTURES)
    assert "<title>a &amp; b &lt; c</title>" in xml


def test_note_xml_includes_resource_when_attachment_present():
    note = convert.Note(
        title="t",
        attachments=[{"filePath": "img1.png", "mimetype": "image/png"}],
    )
    xml = convert.note_to_xml(note, FIXTURES)
    assert "<en-media" in xml
    assert "<resource>" in xml


if __name__ == "__main__":
    run(sys.modules[__name__])
