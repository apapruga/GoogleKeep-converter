from __future__ import annotations

import os


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


if __name__ == "__main__":
    raise SystemExit(main())
