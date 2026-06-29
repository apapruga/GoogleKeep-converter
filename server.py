from __future__ import annotations

import os
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MAX_BODY_SIZE = 200 * 1024 * 1024  # 200 МБ


def sanitize_filename(name):
    """Защита от path-traversal: оставить только basename, отбросить каталоги."""
    if not name:
        return ""
    # нормализуем, берём последний компонент пути
    name = os.path.basename(name.replace("\\", "/"))
    # отбрасываем точечные сегменты
    if name in (".", "..", ""):
        return ""
    return name


def find_keep_root(tempdir):
    """Найти общий родитель всех *.json (рекурсивно). Нет json → None."""
    import glob
    json_files = glob.glob(os.path.join(tempdir, "**", "*.json"), recursive=True)
    if not json_files:
        return None
    common = os.path.commonpath([os.path.abspath(p) for p in json_files])
    if os.path.isfile(common):
        common = os.path.dirname(common)
    return common


def extract_zip_to(zip_bytes, dest):
    """Распаковать zip-байты в dest. Вернуть корень Keep (через find_keep_root).
    Бросает ValueError, если архив битый."""
    import io
    import zipfile
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(dest)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Не удалось распаковать архив: {exc}") from exc
    root = find_keep_root(dest)
    return root if root else dest


def has_resize_deps():
    """True, если доступны Pillow и pillow-heif."""
    try:
        import PIL  # noqa: F401
        import pillow_heif  # noqa: F401
        return True
    except ImportError:
        return False


class _ClientError(Exception):
    """Ошибка, которую нужно вернуть клиенту как 400."""


def parse_multipart(body, content_type):
    """Разобрать multipart-тело. Вернуть (files, options).
    files: list[{'name':..., 'data':bytes}].
    options: dict с include_trashed, resize_enabled, resize_threshold, resize_scale."""
    files = []
    options = {
        "include_trashed": False,
        "resize_enabled": False,
        "resize_threshold": 0,
        "resize_scale": 0.5,
    }
    if "boundary=" not in content_type:
        return files, options
    boundary = content_type.split("boundary=", 1)[1].strip()
    if boundary.startswith('"') and boundary.endswith('"'):
        boundary = boundary[1:-1]
    delim = b"--" + boundary.encode()

    text_fields = {}  # name -> data bytes

    chunks = body.split(delim)
    for chunk in chunks:
        if not chunk or chunk == b"--" or chunk == b"--\r\n" or chunk.startswith(b"--"):
            continue
        chunk = chunk.strip(b"\r\n")
        if b"\r\n\r\n" not in chunk:
            continue
        header_blob, _, data = chunk.partition(b"\r\n\r\n")
        headers = header_blob.decode("utf-8", "replace")
        name = None
        filename = None
        for line in headers.split("\r\n"):
            low = line.lower()
            if low.startswith("content-disposition:"):
                for part in line.split(";"):
                    part = part.strip()
                    if part.startswith("name="):
                        name = part[5:].strip('"')
                    elif part.startswith("filename="):
                        filename = part[9:].strip('"')
        if filename is not None:
            files.append({"name": filename, "data": data})
        elif name is not None:
            text_fields[name] = data

    # разбор текстовых полей в options
    def _str(name):
        return text_fields.get(name, b"").decode("utf-8", "replace").strip()

    if _str("include_trashed") in ("1", "true", "on"):
        options["include_trashed"] = True
    if _str("resize_enabled") in ("1", "true", "on"):
        options["resize_enabled"] = True
    try:
        options["resize_threshold"] = int(_str("resize_threshold"))
    except ValueError:
        pass
    try:
        options["resize_scale"] = float(_str("resize_scale")) if _str("resize_scale") else 0.5
    except ValueError:
        pass

    return files, options


def main(argv=None):
    import argparse
    import threading
    import webbrowser
    import time
    parser = argparse.ArgumentParser(description="Веб-интерфейс конвертера Google Keep → ENEX.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true", help="не открывать браузер")
    args = parser.parse_args(argv)

    httpd = ThreadingHTTPServer((args.host, args.port), KeepHandler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Сервер запущен: {url}  (Ctrl+C для остановки)")
    if not args.no_browser:
        def _open():
            time.sleep(0.5)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановка...")
        httpd.shutdown()
    return 0


class KeepHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html; charset=utf-8")
            return
        if self.path.startswith("/static/"):
            rel = os.path.normpath(self.path[len("/static/"):])
            full = os.path.join(STATIC_DIR, rel)
            # защита от выхода за static
            if not os.path.abspath(full).startswith(STATIC_DIR):
                self._send_json(403, {"error": "forbidden"})
                return
            ctype, _ = mimetypes.guess_type(full)
            self._serve_file(full, ctype or "application/octet-stream")
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/convert":
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > MAX_BODY_SIZE:
            self._send_json(413, {"error": "Превышен лимит размера (200 МБ)"})
            return
        body = self.rfile.read(length)
        try:
            self._handle_convert(body)
        except _ClientError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._send_json(500, {"error": "Внутренняя ошибка сервера", "detail": str(exc)})

    def _handle_convert(self, body):
        import tempfile
        import shutil
        import convert as _convert
        files, include_trashed = parse_multipart(body, self.headers.get("Content-Type", ""))
        if not files:
            raise _ClientError("Не найдено ни одного файла")

        tmp = tempfile.mkdtemp()
        try:
            zips = [f for f in files if f["name"].lower().endswith(".zip")]
            if zips:
                root = None
                for z in zips:
                    root = extract_zip_to(z["data"], tmp) or root
                keep_root = root
            else:
                for f in files:
                    safe = sanitize_filename(f["name"])
                    if not safe:
                        continue
                    with open(os.path.join(tmp, safe), "wb") as fh:
                        fh.write(f["data"])
                keep_root = find_keep_root(tmp)
            if not keep_root:
                raise _ClientError("Не найдено ни одного .json файла")

            out = os.path.join(tmp, "out.enex")
            report = _convert.convert_directory(keep_root, out, include_trashed=include_trashed)

            with open(out, "rb") as fh:
                data = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", 'attachment; filename="GoogleKeep.enex"')
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Notes", str(report["processed"]))
            self.send_header("X-Attachments", str(report["with_attachments"]))
            self.end_headers()
            self.wfile.write(data)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _serve_file(self, path, ctype):
        if not os.path.isfile(path):
            self._send_json(404, {"error": "not found"})
            return
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, code, obj):
        import json
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    raise SystemExit(main())
