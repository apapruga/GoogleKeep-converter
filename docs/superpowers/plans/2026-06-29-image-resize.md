# Уменьшение картинок в веб-интерфейсе — План реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в веб-UI опцию уменьшения картинок (jpg/jpeg/png/heic/gif) перед встраиванием в `.enex`: пользователь выбирает порог размера (КБ/МБ, по умолч. 1 МБ) и степень (75/50/25%, по умолч. 50%); картинки крупнее порога масштабируются по габаритам и сохраняются в исходном формате.

**Architecture:** Подход A — логика в `server.py`, `convert.py` не трогается. Новые функции `has_resize_deps()` и `resize_directory()`, вызываемые в `_handle_convert` до `convert_directory()`. Парсинг настроек расширяется до общего dict `options`. UI получает чекбокс + раскрывающийся блок настроек.

**Tech Stack:** Python 3.9 stdlib + Pillow + pillow-heif (опционально, проверяется в runtime). Vanilla JS.

**Спецификация:** `docs/superpowers/specs/2026-06-29-image-resize-design.md`

**Окружение проекта:** `/Users/apapr/Library/CloudStorage/OneDrive-Личная/Документы/Программирование/2026-06-28 Gkeep to Apple Notes (z)`. Python 3.9, Pillow 11.3 + pillow-heif 1.1.1 установлены.

---

## Структура файлов

| Файл | Ответственность |
|---|---|
| `server.py` | Новые функции `has_resize_deps`, `resize_directory`; расширение `parse_multipart` (options dict); вызов resize в `_handle_convert`; заголовок `X-Resized`. |
| `static/index.html` | Чекбокс «Уменьшить картинки» + раскрывающийся блок настроек + кнопки Применить/Отмена + строка-сводка; отправка полей в FormData; показ `X-Resized` в сводке успеха. |
| `tests/test_server.py` | Новые unit-тесты (deps, parse, resize_directory) + HTTP-интеграционный тест с resize. |
| `README.md` | Подраздел про уменьшение картинок (опциональность, install, поведение GIF). |

## Соглашения

- Тест запускается: `python3 tests/test_server.py` (раннер печатает PASS/FAIL).
- Тесты с реальным ресайзом **guard** на `has_resize_deps()` — пропускаются без Pillow, печатают `SKIP`.
- Раннер `_runner.py` нужно расширить, чтобы `SKIP` (когда функция возвращает специальный маркер) не считался провалом. Используется паттерн: функция-тест возвращает строку `"skip"` → раннер печатает `SKIP` и не считает failed.

---

## Task 1: Расширить `_runner.py` для SKIP + `has_resize_deps()`

**Files:**
- Modify: `tests/_runner.py`
- Modify: `server.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Расширить раннер для SKIP**

Заменить в `tests/_runner.py` тело цикла на:
```python
def run(module):
    tests = sorted(
        (name, fn)
        for name, fn in vars(module).items()
        if name.startswith("test_") and callable(fn)
    )
    failed = 0
    skipped = 0
    for name, fn in tests:
        try:
            result = fn()
            if result == "skip":
                skipped += 1
                print(f"SKIP {name}")
            else:
                print(f"PASS {name}")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    run_count = len(tests) - skipped
    print(f"\n{run_count - failed}/{run_count} passed, {skipped} skipped")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Добавить тест на `has_resize_deps`**

Дополнить `tests/test_server.py` (после импортов, перед первым test_):
```python
def test_has_resize_deps_returns_bool():
    result = server.has_resize_deps()
    assert result is True or result is False
```

- [ ] **Step 3: Запустить тест, убедиться в провале**

Run: `python3 tests/test_server.py`
Expected: FAIL (`has_resize_deps` не определена)

- [ ] **Step 4: Реализовать `has_resize_deps`**

Добавить в `server.py` (после `extract_zip_to`, перед `class _ClientError`):
```python
def has_resize_deps():
    """True, если доступны Pillow и pillow-heif."""
    try:
        import PIL  # noqa: F401
        import pillow_heif  # noqa: F401
        return True
    except ImportError:
        return False
```

- [ ] **Step 5: Запустить тесты, убедиться в успехе**

Run: `python3 tests/test_server.py`
Expected: все passed (старые 13 + новый 1 = 14)

- [ ] **Step 6: Коммит**

```bash
git add tests/_runner.py server.py tests/test_server.py
git commit -m "feat(server): has_resize_deps + SKIP support in runner"
```

---

## Task 2: Расширить `parse_multipart` — общий dict `options`

**Files:**
- Modify: `server.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Добавить тесты на новые поля и обратную совместимость**

Дополнить `tests/test_server.py`:
```python
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
```

- [ ] **Step 2: Запустить тесты, убедиться в провале**

Run: `python3 tests/test_server.py`
Expected: FAIL (старые тесты `parse_multipart` падают — старый возврат `(files, include_trashed)` несовместим с распаковкой `options[...]`)

- [ ] **Step 2b: Поправить существующие тесты под новую сигнатуру**

В `tests/test_server.py` найти строки, где вызывается `server.parse_multipart(...)` (если есть прямые вызовы в тестах) и проверить, что HTTP-тесты `_handle_convert` тоже работают. Реальная замена: в коде `_handle_convert` (Task 4) меняется `files, include_trashed = parse_multipart(...)` → `files, options = parse_multipart(...)`. Тесты HTTP сейчас используют `urllib`, а не прямой вызов `parse_multipart`, поэтому провалятся только новые прямые тесты Task 2.

- [ ] **Step 3: Изменить `parse_multipart` в `server.py`**

Заменить функцию `parse_multipart` целиком:
```python
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
```

- [ ] **Step 4: Запустить тесты, убедиться в успехе**

Run: `python3 tests/test_server.py`
Expected: все passed (15)

- [ ] **Step 5: Коммит**

```bash
git add server.py tests/test_server.py
git commit -m "feat(server): parse_multipart returns options dict with resize fields"
```

---

## Task 3: `resize_directory()` — масштабирование картинок

**Files:**
- Modify: `server.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Добавить тесты (с guard на Pillow)**

Дополнить `tests/test_server.py`:
```python
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
```

- [ ] **Step 2: Запустить тесты, убедиться в провале (или SKIP без Pillow)**

Run: `python3 tests/test_server.py`
Expected: FAIL (`resize_directory` не определена); skip-тесты не пройдут, а вернут исключение AttributeError.

- [ ] **Step 3: Реализовать `resize_directory`**

Добавить в `server.py` (после `has_resize_deps`, перед `class _ClientError`):
```python
import glob as _glob

RESIZE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".heic", ".gif")


def resize_directory(keep_dir, threshold_bytes, scale):
    """Уменьшить картинки в keep_dir крупнее threshold_bytes до scale от габаритов.
    Возвращает dict-отчёт: {scanned, resized, skipped, errors}."""
    from PIL import Image
    import pillow_heif
    pillow_heif.register_heif_opener()

    report = {"scanned": 0, "resized": 0, "skipped": 0, "errors": 0}
    # соберём кандидатов (нижний + верхний регистр расширений)
    candidates = set()
    for root, _dirs, files in os.walk(keep_dir):
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext in RESIZE_EXTENSIONS:
                candidates.add(os.path.join(root, fn))

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
```

- [ ] **Step 4: Запустить тесты, убедиться в успехе**

Run: `python3 tests/test_server.py`
Expected: все passed (плюс 2 resize-теста, если Pillow есть)

- [ ] **Step 5: Коммит**

```bash
git add server.py tests/test_server.py
git commit -m "feat(server): resize_directory scales images above threshold"
```

---

## Task 4: Интеграция в `_handle_convert` + валидация + `X-Resized`

**Files:**
- Modify: `server.py`

- [ ] **Step 1: Реализовать интеграцию (правка `_handle_convert`)**

В `server.py` найти блок в `_handle_convert`:
```python
        files, include_trashed = parse_multipart(body, self.headers.get("Content-Type", ""))
        if not files:
            raise _ClientError("Не найдено ни одного файла")
```
Заменить на:
```python
        files, options = parse_multipart(body, self.headers.get("Content-Type", ""))
        if not files:
            raise _ClientError("Не найдено ни одного файла")

        # валидация настроек уменьшения
        resized_count = 0
        if options["resize_enabled"]:
            if options["resize_threshold"] <= 0 or options["resize_scale"] not in (0.25, 0.5, 0.75):
                raise _ClientError("Некорректные настройки уменьшения")
            if not has_resize_deps():
                raise _ClientError("Уменьшение картинок недоступно. Установите Pillow: pip install Pillow pillow-heif")
```

Затем найти:
```python
            if not keep_root:
                raise _ClientError("Не найдено ни одного .json файла")

            out = os.path.join(tmp, "out.enex")
            report = _convert.convert_directory(keep_root, out, include_trashed=include_trashed)
```
Заменить на:
```python
            if not keep_root:
                raise _ClientError("Не найдено ни одного .json файла")

            if options["resize_enabled"]:
                rreport = resize_directory(keep_root, options["resize_threshold"], options["resize_scale"])
                resized_count = rreport["resized"]

            out = os.path.join(tmp, "out.enex")
            report = _convert.convert_directory(keep_root, out, include_trashed=options["include_trashed"])
```

Затем найти отправку заголовков (где `X-Attachments`) и добавить:
```python
            self.send_header("X-Notes", str(report["processed"]))
            self.send_header("X-Attachments", str(report["with_attachments"]))
            self.send_header("X-Resized", str(resized_count))
```

- [ ] **Step 2: Smoke-проверка API (POST без resize работает как раньше)**

Run:
```bash
cd "/Users/apapr/Library/CloudStorage/OneDrive-Личная/Документы/Программирование/2026-06-28 Gkeep to Apple Notes (z)"
python3 -c "
import server, threading, time, io, os, zipfile, urllib.request
from http.server import ThreadingHTTPServer
httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.KeepHandler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
base=f'http://127.0.0.1:{httpd.server_address[1]}'
# zip с фикстурой + включённым resize (порог 0, scale 0.5)
FIX='tests/fixtures'
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w') as z:
    for fn in os.listdir(FIX):
        with open(os.path.join(FIX,fn),'rb') as f: z.writestr('Google Keep/'+fn, f.read())
parts=[b'--keepbnd', b'Content-Disposition: form-data; name=\"files\"; filename=\"keep.zip\"', b'Content-Type: application/zip', b'', buf.getvalue(), b'--keepbnd--', b'']
body=b'\r\n'.join(parts)
r=urllib.request.urlopen(urllib.request.Request(base+'/convert', data=body, method='POST', headers={'Content-Type':'multipart/form-data; boundary=keepbnd'}))
print('no-resize X-Resized:', r.headers.get('X-Resized'))
httpd.shutdown()
" 2>&1 | grep -v "127.0.0.1"
```
Expected: `no-resize X-Resized: 0`

- [ ] **Step 3: Коммит**

```bash
git add server.py
git commit -m "feat(server): integrate resize into _handle_convert with X-Resized"
```

---

## Task 5: UI настроек уменьшения в `static/index.html`

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: Добавить HTML блока настроек**

Найти в `static/index.html` строку с чекбоксом корзины:
```html
<label><input type="checkbox" id="include_trashed"> Включить удалённые (корзину)</label>
```
Добавить **после** неё:
```html
<label><input type="checkbox" id="resize_enabled"> Уменьшить картинки</label>
<div id="resize_panel" style="display:none; margin-left:24px; padding:12px; border-left:2px solid #888;">
  <div>Порог размера:</div>
  <div style="margin:6px 0;">
    <input type="number" id="resize_value" value="1" min="1" style="width:80px;">
    <label style="display:inline;"><input type="radio" name="resize_unit" value="kb"> КБ</label>
    <label style="display:inline;"><input type="radio" name="resize_unit" value="mb" checked> МБ</label>
  </div>
  <div>Степень уменьшения:</div>
  <div style="margin:6px 0;">
    <label style="display:inline;"><input type="radio" name="resize_scale" value="0.75"> 75%</label>
    <label style="display:inline;"><input type="radio" name="resize_scale" value="0.5" checked> 50%</label>
    <label style="display:inline;"><input type="radio" name="resize_scale" value="0.25"> 25%</label>
  </div>
  <button id="resize_apply" type="button">Применить</button>
  <button id="resize_cancel" type="button">Отмена</button>
  <div id="resize_summary" style="margin-top:8px; color:#666;"></div>
</div>
```

- [ ] **Step 2: Добавить JS-логику**

Найти в `<script>` функцию `convertBtn.onclick = async () => {` и **перед** ней вставить:
```javascript
// === Настройки уменьшения картинок ===
const resizeCheckbox = document.getElementById('resize_enabled');
const resizePanel = document.getElementById('resize_panel');
const resizeApply = document.getElementById('resize_apply');
const resizeCancel = document.getElementById('resize_cancel');
const resizeSummary = document.getElementById('resize_summary');
let resizeApplied = false;  // применил ли пользователь настройки

function _resizeSummaryText() {
  const v = document.getElementById('resize_value').value || '1';
  const unit = document.querySelector('input[name=resize_unit]:checked').value;
  const scale = document.querySelector('input[name=resize_scale]:checked').value;
  const scalePct = ({'0.75':'75%','0.5':'50%','0.25':'25%'})[scale];
  return `🖼 Порог >${v} ${unit.toUpperCase()} · масштаб ${scalePct}`;
}

resizeCheckbox.onchange = () => {
  if (resizeCheckbox.checked) {
    resizePanel.style.display = 'block';
    resizeApplied = false;
    resizeSummary.textContent = 'Нажмите «Применить» для подтверждения.';
  } else {
    resizePanel.style.display = 'none';
    resizeSummary.textContent = '';
    resizeApplied = false;
  }
};

resizeApply.onclick = () => {
  const v = parseInt(document.getElementById('resize_value').value, 10);
  if (!v || v < 1) return;  // защита
  resizeApplied = true;
  resizePanel.style.display = 'none';
  resizeSummary.textContent = _resizeSummaryText();
};

resizeCancel.onclick = () => {
  resizeApplied = false;
  resizePanel.style.display = 'none';
  resizeSummary.textContent = '';
};
```

Затем найти в `convertBtn.onclick` строки формирования FormData:
```javascript
  const fd = new FormData();
  for (const f of files) fd.append('files', f);
  if (document.getElementById('include_trashed').checked) fd.append('include_trashed', '1');
```
Добавить **после** них:
```javascript
  if (resizeCheckbox.checked && resizeApplied) {
    const v = parseInt(document.getElementById('resize_value').value, 10);
    const unit = document.querySelector('input[name=resize_unit]:checked').value;
    const scale = document.querySelector('input[name=resize_scale]:checked').value;
    const bytes = unit === 'kb' ? v * 1024 : v * 1024 * 1024;
    fd.append('resize_enabled', '1');
    fd.append('resize_threshold', String(bytes));
    fd.append('resize_scale', scale);
  }
```

Затем найти обработку ответа (блок сводки успеха) — строку с `X-Attachments`:
```javascript
      const notes = resp.headers.get('X-Notes') || '?';
      const atts = resp.headers.get('X-Attachments') || '?';
```
Добавить **после** неё и в `status.innerHTML` добавить строку про уменьшение, если `X-Resized > 0`:
```javascript
      const notes = resp.headers.get('X-Notes') || '?';
      const atts = resp.headers.get('X-Attachments') || '?';
      const resized = parseInt(resp.headers.get('X-Resized') || '0', 10);
      const resizedLine = resized > 0 ? '<br>🖼 Уменьшено картинок: ' + resized : '';
```
И в строку `status.innerHTML = '<span class="ok">✅ Готово! ...` добавить `+ resizedLine` перед закрывающей `</span>`.

- [ ] **Step 3: Ручная проверка в браузере**

Run в терминале:
```bash
cd "/Users/apapr/Library/CloudStorage/OneDrive-Личная/Документы/Программирование/2026-06-28 Gkeep to Apple Notes (z)"
python3 server.py
```
Ожидается: на странице чекбокс «Уменьшить картинки», при отметке раскрывается панель с порогом/степенью и кнопками; «Применить» сворачивает панель с показом сводки.

- [ ] **Step 4: Коммит**

```bash
git add static/index.html
git commit -m "feat(ui): image resize settings panel with apply/cancel"
```

---

## Task 6: HTTP-интеграционный тест с resize + README

**Files:**
- Modify: `tests/test_server.py`
- Modify: `README.md`

- [ ] **Step 1: Добавить HTTP-тесты (с guard)**

Дополнить `tests/test_server.py`:
```python
def test_post_convert_resize_without_deps_returns_400(monkeypatch_via_env=None):
    """Без зависимостей (эмулируем monkeypatch) resize → 400. Проходит без Pillow."""
    import urllib.request, urllib.error
    httpd = _start_server()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    # принудительно подменяем has_resize_deps через временную замену
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
            import json as _json
            err = _json.loads(e.read().decode("utf-8"))
            assert "Уменьшение" in err["error"] or "Pillow" in err["error"]
    finally:
        server.has_resize_deps = original
        httpd.shutdown()


def _zip_bytes(mapping):
    import io, zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in mapping.items():
            data = content.encode("utf-8") if isinstance(content, str) else content
            z.writestr(name, data)
    return buf.getvalue()


def test_post_convert_with_resize_succeeds_when_deps_available():
    if not server.has_resize_deps():
        return "skip"
    import io, os, urllib.request, zipfile
    from PIL import Image
    httpd = _start_server()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    # создаём большой PNG во временном zip
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
```

(Удалить старую локальную `_zip_bytes`/`_build_multipart`, если они дублируют — оставить одну пару наверху.)

- [ ] **Step 2: Запустить тесты, убедиться в успехе**

Run: `python3 tests/test_server.py`
Expected: все passed (+SKIP если Pillow отсутствует)

- [ ]  **Step 3: Обновить README — подраздел про уменьшение**

В `README.md` найти раздел «Как преобразуются данные» (таблицу) и добавить **после** таблицы новый подраздел:
```markdown
### Уменьшение картинок (опционально, только в веб-интерфейсе)

В веб-интерфейсе есть опция **«Уменьшить картинки»**: позволяет уменьшить большие изображения перед встраиванием в `.enex`.

- **Требует** `pip install Pillow pillow-heif` (без них опция вернёт ошибку установки).
- **Порог размера**: файлы крупнее порога (КБ/МБ, по умолчанию 1 МБ) масштабируются; мельче — не трогаются.
- **Степень**: габариты (ширина и высота) умножаются на 75/50/25%.
- **Формат**: сохраняется исходный (JPEG/PNG/HEIC/GIF).
- **Ограничение**: анимированные GIF при уменьшении теряют анимацию (сохраняется первый кадр) — особенность Pillow.
```

- [ ] **Step 4: Финальная проверка всего набора тестов**

Run:
```bash
cd "/Users/apapr/Library/CloudStorage/OneDrive-Личная/Документes/Программирование/2026-06-28 Gkeep to Apple Notes (z)"
for t in tests/test_*.py; do echo "=== $t ==="; python3 "$t" || break; done
```
Expected: все тестовые файлы — PASS (с возможными SKIP для resize-тестов без Pillow).

- [ ] **Step 5: Коммит**

```bash
git add tests/test_server.py README.md
git commit -m "test+docs: resize integration test + README section"
```

---

## Финальная проверка

- [ ] Все тесты (`tests/test_*.py`) — PASS (SKIP допустим для resize без Pillow).
- [ ] Веб-UI: чекбокс раскрывает панель настроек; «Применить» сворачивает с показом сводки.
- [ ] POST `/convert` с включённым resize уменьшает картинки > порога до scale габаритов, `X-Resized > 0`.
- [ ] POST `/convert` без resize работает как раньше (`X-Resized: 0`).
- [ ] POST `/convert` с resize без зависимостей → 400 с текстом про установку Pillow.
- [ ] README обновлён.
