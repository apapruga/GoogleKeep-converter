import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import server
from _runner import run


def test_sanitize_filename_plain():
    assert server.sanitize_filename("note.json") == "note.json"
    assert server.sanitize_filename("картинка (1).jpg") == "картинка (1).jpg"


def test_has_resize_deps_returns_bool():
    result = server.has_resize_deps()
    assert result is True or result is False


def test_parse_multipart_resize_disabled_by_default():
    files, options = server.parse_multipart(b"--b--\r\n", "multipart/form-data; boundary=b")
    assert options["include_trashed"] is False
    assert options["resize_enabled"] is False
    assert options["resize_threshold"] == 0
    assert options["resize_scale"] == 0.5


def test_parse_multipart_resize_fields():
    body = (
        b"--keepbnd\r\n"
        b'Content-Disposition: form-data; name="resize_enabled"\r\n\r\n'
        b"1\r\n"
        b"--keepbnd\r\n"
        b'Content-Disposition: form-data; name="resize_threshold"\r\n\r\n'
        b"1048576\r\n"
        b"--keepbnd\r\n"
        b'Content-Disposition: form-data; name="resize_scale"\r\n\r\n'
        b"0.25\r\n"
        b"--keepbnd--\r\n"
    )
    files, options = server.parse_multipart(body, "multipart/form-data; boundary=keepbnd")
    assert options["resize_enabled"] is True
    assert options["resize_threshold"] == 1048576
    assert options["resize_scale"] == 0.25


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


def _build_multipart(fields):
    """fields: {name: [(filename, bytes, ctype), ...]} или {name: value}."""
    boundary = "keepbnd"
    parts = []
    for name, val in fields.items():
        items = val if isinstance(val, list) else [(None, val, None)]
        for filename, data, ctype in items:
            parts.append(b"--" + boundary.encode())
            if filename:
                parts.append(b'Content-Disposition: form-data; name="' + name.encode() + b'"; filename="' + filename.encode() + b'"')
                parts.append(b"Content-Type: " + ctype.encode())
            else:
                parts.append(b'Content-Disposition: form-data; name="' + name.encode() + b'"')
            parts.append(b"")
            parts.append(data if isinstance(data, bytes) else str(data).encode())
    parts.append(b"--" + boundary.encode() + b"--")
    parts.append(b"")
    return b"\r\n".join(parts)


def _start_server():
    from http.server import ThreadingHTTPServer
    import threading
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.KeepHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def test_post_convert_zip_returns_enex():
    import io, urllib.request
    httpd = _start_server()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for fn in os.listdir(FIXTURES):
            with open(os.path.join(FIXTURES, fn), "rb") as f:
                z.writestr("Google Keep/" + fn, f.read())
    body = _build_multipart({"files": [("keep.zip", buf.getvalue(), "application/zip")]})
    req = urllib.request.Request(base + "/convert", data=body, method="POST",
                                 headers={"Content-Type": "multipart/form-data; boundary=keepbnd"})
    resp = urllib.request.urlopen(req)
    assert resp.status == 200
    assert "octet-stream" in resp.headers.get("Content-Type", "")
    assert resp.headers.get("X-Notes") == "4"
    data = resp.read()
    assert b"<en-export " in data
    assert "☐ молоко".encode() in data
    assert "☑ хлеб".encode() in data
    httpd.shutdown()


def test_post_convert_no_files_returns_400():
    import urllib.request, urllib.error
    httpd = _start_server()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    body = _build_multipart({})
    req = urllib.request.Request(base + "/convert", data=body, method="POST",
                                 headers={"Content-Type": "multipart/form-data; boundary=keepbnd"})
    try:
        urllib.request.urlopen(req)
        assert False, "должен быть 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400
    httpd.shutdown()


if __name__ == "__main__":
    run(sys.modules[__name__])
