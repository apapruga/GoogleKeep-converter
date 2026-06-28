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


def main(argv=None):
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
