import base64
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_media_present_attachment():
    with open(os.path.join(FIXTURES, "img1.png"), "rb") as f:
        raw = f.read()
    expected_hash = hashlib.md5(raw).hexdigest()
    note = convert.Note(
        attachments=[{"filePath": "img1.png", "mimetype": "image/png"}],
    )
    media_html, resources_xml = convert.media_and_resources(note, FIXTURES)
    assert f'<en-media type="image/png" hash="{expected_hash}"/>' in media_html
    assert "<resource>" in resources_xml
    assert "<mime>image/png</mime>" in resources_xml
    assert "<file-name>img1.png</file-name>" in resources_xml
    # base64 в ресурсе декодируется в исходные байты
    import re
    m = re.search(r"<data encoding=\"base64\">(.*?)</data>", resources_xml, re.S)
    assert m is not None
    assert base64.b64decode(m.group(1)) == raw


def test_media_missing_file():
    note = convert.Note(attachments=[{"filePath": "nope.png", "mimetype": "image/png"}])
    media_html, resources_xml = convert.media_and_resources(note, FIXTURES)
    assert "[Вложение отсутствует: nope.png]" in media_html
    assert resources_xml == ""


def test_media_mime_fallback_by_extension():
    note = convert.Note(attachments=[{"filePath": "img1.png", "mimetype": ""}])
    media_html, resources_xml = convert.media_and_resources(note, FIXTURES)
    assert 'type="image/png"' in media_html
    assert "<mime>image/png</mime>" in resources_xml


def test_media_no_attachments():
    note = convert.Note()
    media_html, resources_xml = convert.media_and_resources(note, FIXTURES)
    assert media_html == ""
    assert resources_xml == ""


if __name__ == "__main__":
    run(sys.modules[__name__])
