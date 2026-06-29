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


def _make_png(path, size_px):
    from PIL import Image
    img = Image.new("RGB", (size_px, size_px), (255, 0, 0))
    img.save(path, format="PNG")


def test_resize_directory_skips_small_files():
    if not server.has_resize_deps():
        return "skip"
    import os, tempfile
    d = tempfile.mkdtemp()
    small = os.path.join(d, "small.png")
    _make_png(small, 100)
    before = open(small, "rb").read()
    report = server.resize_directory(d, threshold_bytes=10 * 1024 * 1024, scale=0.5)
    after = open(small, "rb").read()
    assert report["resized"] == 0
    assert report["skipped"] == 1
    assert before == after  # файл не изменён


def test_resize_directory_resizes_large_file():
    if not server.has_resize_deps():
        return "skip"
    import os, tempfile
    from PIL import Image
    d = tempfile.mkdtemp()
    big = os.path.join(d, "big.png")
    _make_png(big, 2000)
    report = server.resize_directory(d, threshold_bytes=0, scale=0.5)
    assert report["resized"] == 1
    with Image.open(big) as im:
        assert im.width == 1000 and im.height == 1000
        assert im.format == "PNG"


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


def _zip_bytes(mapping):
    import io, zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in mapping.items():
            data = content.encode("utf-8") if isinstance(content, str) else content
            z.writestr(name, data)
    return buf.getvalue()


def test_post_convert_resize_without_deps_returns_400():
    """Эмулируем отсутствие зависимостей → resize должен вернуть 400.
    Проходит без Pillow (через monkeypatch has_resize_deps)."""
    import urllib.request, urllib.error, json as _json
    httpd = _start_server()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    original = server.has_resize_deps
    server.has_resize_deps = lambda: False
    try:
        body = _build_multipart({
            "files": [("keep.zip", _zip_bytes({"a.json": '{"title":"A"}'}), "application/zip")],
            "resize_enabled": "1",
            "resize_threshold": "1048576",
            "resize_scale": "0.5",
        })
        req = urllib.request.Request(base + "/convert", data=body, method="POST",
                                     headers={"Content-Type": "multipart/form-data; boundary=keepbnd"})
        try:
            urllib.request.urlopen(req)
            assert False, "должен быть 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400
            err = _json.loads(e.read().decode("utf-8"))
            assert "Уменьшение" in err["error"] or "Pillow" in err["error"]
    finally:
        server.has_resize_deps = original
        httpd.shutdown()


def test_post_convert_with_resize_succeeds_when_deps_available():
    if not server.has_resize_deps():
        return "skip"
    import io, urllib.request, zipfile
    from PIL import Image
    httpd = _start_server()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    buf_png = io.BytesIO()
    img = Image.new("RGB", (2000, 2000), (0, 128, 255))
    img.save(buf_png, format="PNG")
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        z.writestr("Google Keep/big.png", buf_png.getvalue())
        z.writestr("Google Keep/note.json", '{"title":"N","attachments":[{"filePath":"big.png","mimetype":"image/png"}]}')
    body = _build_multipart({
        "files": [("k.zip", zbuf.getvalue(), "application/zip")],
        "resize_enabled": "1",
        "resize_threshold": "1",  # 1 байт → всё масштабируется
        "resize_scale": "0.5",
    })
    req = urllib.request.Request(base + "/convert", data=body, method="POST",
                                 headers={"Content-Type": "multipart/form-data; boundary=keepbnd"})
    resp = urllib.request.urlopen(req)
    assert resp.status == 200
    assert int(resp.headers.get("X-Resized", "0")) == 1
    data = resp.read()
    assert b"<en-export " in data
    httpd.shutdown()


def test_parse_multipart_lang_default_ru():
    files, options = server.parse_multipart(b"--b--\r\n", "multipart/form-data; boundary=b")
    assert options["lang"] == "ru"


def test_parse_multipart_lang_en():
    body = (
        b"--keepbnd\r\n"
        b'Content-Disposition: form-data; name="lang"\r\n\r\n'
        b"en\r\n"
        b"--keepbnd--\r\n"
    )
    files, options = server.parse_multipart(body, "multipart/form-data; boundary=keepbnd")
    assert options["lang"] == "en"


def test_msg_falls_back_to_ru_for_unknown_lang():
    assert server.MSG("no_files", "de") == server.MESSAGES["no_files"]["ru"]
    assert server.MSG("no_files", "en") == "No files found"
    assert server.MSG("unknown_key", "en") == "unknown_key"


def test_post_convert_no_files_error_localized_en():
    import urllib.request, urllib.error, json as _json
    httpd = _start_server()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    body = _build_multipart({"lang": "en"})
    req = urllib.request.Request(base + "/convert", data=body, method="POST",
                                 headers={"Content-Type": "multipart/form-data; boundary=keepbnd"})
    try:
        urllib.request.urlopen(req)
        assert False, "должен быть 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        err = _json.loads(e.read().decode("utf-8"))
        assert err["error"] == "No files found"
    httpd.shutdown()


def test_post_convert_resize_without_deps_localized_en():
    import urllib.request, urllib.error, json as _json
    httpd = _start_server()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    original = server.has_resize_deps
    server.has_resize_deps = lambda: False
    try:
        body = _build_multipart({
            "files": [("keep.zip", _zip_bytes({"a.json": '{"title":"A"}'}), "application/zip")],
            "resize_enabled": "1",
            "resize_threshold": "1048576",
            "resize_scale": "0.5",
            "lang": "en",
        })
        req = urllib.request.Request(base + "/convert", data=body, method="POST",
                                     headers={"Content-Type": "multipart/form-data; boundary=keepbnd"})
        try:
            urllib.request.urlopen(req)
            assert False, "должен быть 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400
            err = _json.loads(e.read().decode("utf-8"))
            assert "Pillow" in err["error"] and "unavailable" in err["error"]
    finally:
        server.has_resize_deps = original
        httpd.shutdown()


def test_post_convert_error_defaults_ru_without_lang():
    import urllib.request, urllib.error, json as _json
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
        err = _json.loads(e.read().decode("utf-8"))
        assert err["error"] == "Не найдено ни одного файла"
    httpd.shutdown()


if __name__ == "__main__":
    run(sys.modules[__name__])
