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


RESIZE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".heic", ".gif")


# Локализованные сообщения сервера. lang: 'ru' | 'en'.
MESSAGES = {
    "no_files": {
        "ru": "Не найдено ни одного файла",
        "en": "No files found",
    },
    "bad_resize_settings": {
        "ru": "Некорректные настройки уменьшения",
        "en": "Invalid image resize settings",
    },
    "resize_no_deps": {
        "ru": "Уменьшение картинок недоступно. Установите Pillow: pip install Pillow pillow-heif",
        "en": "Image resizing is unavailable. Install Pillow: pip install Pillow pillow-heif",
    },
    "no_json": {
        "ru": "Не найдено ни одного .json файла",
        "en": "No .json files found",
    },
    "too_large": {
        "ru": "Превышен лимит размера (200 МБ)",
        "en": "Size limit exceeded (200 MB)",
    },
    "internal": {
        "ru": "Внутренняя ошибка сервера",
        "en": "Internal server error",
    },
    "not_found": {
        "ru": "не найдено",
        "en": "not found",
    },
    "forbidden": {
        "ru": "доступ запрещён",
        "en": "forbidden",
    },
}


def MSG(key, lang="ru"):
    """Локализованное сообщение. Падает на 'ru', если lang неизвестен."""
    entry = MESSAGES.get(key, {})
    return entry.get(lang) or entry.get("ru") or key


def resize_directory(keep_dir, threshold_bytes, scale):
    """Уменьшить картинки в keep_dir крупнее threshold_bytes до scale от габаритов.
    Возвращает dict-отчёт: {scanned, resized, skipped, errors}."""
    from PIL import Image
    import pillow_heif
    pillow_heif.register_heif_opener()

    report = {"scanned": 0, "resized": 0, "skipped": 0, "errors": 0}
    # соберём кандидатов (по расширению, нижний регистр)
    candidates = []
    for root, _dirs, files in os.walk(keep_dir):
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext in RESIZE_EXTENSIONS:
                candidates.append(os.path.join(root, fn))

    for path in sorted(candidates):
        report["scanned"] += 1
        try:
            if os.path.getsize(path) <= threshold_bytes:
                report["skipped"] += 1
                continue
            with Image.open(path) as im:
                fmt = im.format
                new_size = (max(1, int(im.width * scale)), max(1, int(im.height * scale)))
                resized = im.resize(new_size, Image.LANCZOS)
                resized.save(path, format=fmt)
            report["resized"] += 1
        except Exception as exc:
            print(f"RESIZE ERROR {path}: {exc}")
            report["errors"] += 1
    return report


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
        "lang": "ru",
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
    lang_value = _str("lang")
    if lang_value in ("ru", "en"):
        options["lang"] = lang_value

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
    lang = "ru"  # язык ответа по умолчанию (до разбора запроса)

    def _header_lang(self):
        """Язык из заголовка Accept-Language (запасной вариант до разбора FormData)."""
        al = (self.headers.get("Accept-Language", "") or "").lower()
        return "en" if al[:2] == "en" else "ru"

    def do_GET(self):
        self.lang = self._header_lang()
        if self.path == "/" or self.path == "/index.html":
            self._serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html; charset=utf-8")
            return
        if self.path.startswith("/static/"):
            rel = os.path.normpath(self.path[len("/static/"):])
            full = os.path.join(STATIC_DIR, rel)
            # защита от выхода за static
            if not os.path.abspath(full).startswith(STATIC_DIR):
                self._send_json(403, {"error": MSG("forbidden", self.lang)})
                return
            ctype, _ = mimetypes.guess_type(full)
            self._serve_file(full, ctype or "application/octet-stream")
            return
        self._send_json(404, {"error": MSG("not_found", self.lang)})

    def do_POST(self):
        self.lang = self._header_lang()
        if self.path != "/convert":
            self._send_json(404, {"error": MSG("not_found", self.lang)})
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > MAX_BODY_SIZE:
            self._send_json(413, {"error": MSG("too_large", self.lang)})
            return
        body = self.rfile.read(length)
        try:
            self._handle_convert(body)
        except _ClientError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._send_json(500, {"error": MSG("internal", self.lang), "detail": str(exc)})

    def _handle_convert(self, body):
        import tempfile
        import shutil
        import convert as _convert
        files, options = parse_multipart(body, self.headers.get("Content-Type", ""))
        # язык из FormData имеет приоритет над заголовком — используется и в обработчиках 500
        lang = self.lang = options["lang"]
        if not files:
            raise _ClientError(MSG("no_files", lang))

        # валидация настроек уменьшения
        resized_count = 0
        if options["resize_enabled"]:
            if options["resize_threshold"] <= 0 or options["resize_scale"] not in (0.25, 0.5, 0.75):
                raise _ClientError(MSG("bad_resize_settings", lang))
            if not has_resize_deps():
                raise _ClientError(MSG("resize_no_deps", lang))

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
                raise _ClientError(MSG("no_json", lang))

            if options["resize_enabled"]:
                rreport = resize_directory(keep_root, options["resize_threshold"], options["resize_scale"])
                resized_count = rreport["resized"]

            out = os.path.join(tmp, "out.enex")
            report = _convert.convert_directory(keep_root, out, include_trashed=options["include_trashed"])

            with open(out, "rb") as fh:
                data = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", 'attachment; filename="GoogleKeep.enex"')
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Notes", str(report["processed"]))
            self.send_header("X-Attachments", str(report["with_attachments"]))
            self.send_header("X-Resized", str(resized_count))
            self.end_headers()
            self.wfile.write(data)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _serve_file(self, path, ctype):
        if not os.path.isfile(path):
            self._send_json(404, {"error": MSG("not_found", self.lang)})
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
