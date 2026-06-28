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


def test_find_keep_root_flat():
    import tempfile
    d = tempfile.mkdtemp()
    open(os.path.join(d, "a.json"), "w").write("{}")
    open(os.path.join(d, "b.json"), "w").write("{}")
    assert server.find_keep_root(d) == d


def test_find_keep_root_nested():
    import tempfile
    d = tempfile.mkdtemp()
    sub = os.path.join(d, "Google Keep")
    os.makedirs(sub)
    open(os.path.join(sub, "a.json"), "w").write("{}")
    assert server.find_keep_root(d) == sub


def test_find_keep_root_deep_nested():
    import tempfile
    d = tempfile.mkdtemp()
    sub = os.path.join(d, "Takeout", "Google Keep")
    os.makedirs(sub)
    open(os.path.join(sub, "a.json"), "w").write("{}")
    open(os.path.join(sub, "b.json"), "w").write("{}")
    assert server.find_keep_root(d) == sub


def test_find_keep_root_no_json_returns_none():
    import tempfile
    d = tempfile.mkdtemp()
    assert server.find_keep_root(d) is None


def test_extract_zip_to_flat():
    import io, tempfile, zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.json", '{"title":"A"}')
        z.writestr("img.png", "PNG")
    dest = tempfile.mkdtemp()
    root = server.extract_zip_to(buf.getvalue(), dest)
    assert root == dest
    assert os.path.isfile(os.path.join(dest, "a.json"))


def test_extract_zip_to_nested_returns_keep_root():
    import io, tempfile, zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Google Keep/a.json", '{"title":"A"}')
        z.writestr("Google Keep/b.json", '{"title":"B"}')
    dest = tempfile.mkdtemp()
    root = server.extract_zip_to(buf.getvalue(), dest)
    assert root == os.path.join(dest, "Google Keep")
    assert os.path.isfile(os.path.join(root, "a.json"))


def test_extract_zip_to_bad_zip():
    import tempfile
    dest = tempfile.mkdtemp()
    try:
        server.extract_zip_to(b"not a zip", dest)
        assert False, "должно бросить"
    except ValueError:
        pass


if __name__ == "__main__":
    run(sys.modules[__name__])
