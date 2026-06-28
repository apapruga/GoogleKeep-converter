import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import server
from _runner import run


def test_sanitize_filename_plain():
    assert server.sanitize_filename("note.json") == "note.json"
    assert server.sanitize_filename("картинка (1).jpg") == "картинка (1).jpg"


def test_sanitize_filename_strips_parent_dir():
    assert server.sanitize_filename("../evil.json") == "evil.json"
    assert server.sanitize_filename("a/../b.json") == "b.json"


def test_sanitize_filename_strips_absolute_paths():
    assert server.sanitize_filename("/etc/passwd.json") == "passwd.json"
    assert server.sanitize_filename("C:\\Windows\\x.json") == "x.json"


def test_sanitize_filename_rejects_empty_after_strip():
    assert server.sanitize_filename("../") == ""
    assert server.sanitize_filename("") == ""


if __name__ == "__main__":
    run(sys.modules[__name__])
