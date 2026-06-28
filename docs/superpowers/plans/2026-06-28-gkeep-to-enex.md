# Конвертер Google Keep → ENEX — План реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Преобразовать выгрузку Google Takeout (папка «Google Keep», пары `.json`+`.html` и картинки) в один самодостаточный `.enex` для импорта в Apple Notes.

**Architecture:** Единый пайплайн в одном файле `convert.py` (Python 3, только stdlib). Поток: `glob *.json → parse_note → Note (dataclass) → фильтр trashed → render_body + media_and_resources → note_to_xml → build_enex → запись`. Тесты — простой assert-раннер без pytest (pytest недоступен).

**Tech Stack:** Python 3.9 (stdlib: `json, os, html, html.parser, hashlib, base64, dataclasses, datetime, argparse, glob, xml.dom.minidom`).

**Спецификация:** `docs/superpowers/specs/2026-06-28-gkeep-to-enex-design.md`

**Окружение проекта:** `/Users/apapr/Library/CloudStorage/OneDrive-Личная/Документы/Программирование/2026-06-28 Gkeep to Apple Notes (z)`. Реальные данные: `/Users/apapr/Downloads/takeout-20260628T161542Z-3-001/Takeout/Google Keep` (1505 заметок).

---

## Структура файлов

| Файл | Ответственность |
|---|---|
| `convert.py` | Вся логика конвертации (dataclass `Note` + функции + `main`). |
| `tests/_runner.py` | Крошечный assert-раннер (заменяет pytest). |
| `tests/test_*.py` | Юнит-тесты на функции `convert.py` (по одному файлу на группу функций). |
| `tests/fixtures/` | Фикстуры для интеграционного теста (`.json` + файл-«картинка»). |
| `smoke_test.py` | Smoke-тест на реальных данных (1505 заметок). |

## Соглашения

- Все файлы — UTF-8.
- `convert.py` начинается с `from __future__ import annotations` (безопасные аннотации на 3.9).
- Тест запускается: `python3 tests/test_<group>.py` (раннер печатает `PASS/FAIL` и выходит с кодом 0/1).
- Коммиты — после каждой задачи (частый cadence TDD).

---

## Task 1: Каркас проекта + git init + тест-раннер

**Files:**
- Create: `convert.py`
- Create: `tests/_runner.py`
- Create: `tests/.gitkeep`

- [ ] **Step 1: Инициализировать git и структуру папок**

Run:
```bash
cd "/Users/apapr/Library/CloudStorage/OneDrive-Личная/Документы/Программирование/2026-06-28 Gkeep to Apple Notes (z)"
git init
mkdir -p tests/fixtures
touch tests/.gitkeep
```

- [ ] **Step 2: Создать `convert.py` (стаб с импортами и заглушкой main)**

```python
from __future__ import annotations

import argparse
import base64
import glob
import hashlib
import html
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser


def main(argv=None):
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Создать `tests/_runner.py`**

```python
import sys
import traceback


def run(module):
    tests = sorted(
        (name, fn)
        for name, fn in vars(module).items()
        if name.startswith("test_") and callable(fn)
    )
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 4: Проверить, что раннер и стаб работают**

Run:
```bash
cd "/Users/apapr/Library/CloudStorage/OneDrive-Личная/Документы/Программирование/2026-06-28 Gkeep to Apple Notes (z)"
python3 -c "import convert; print('import ok')"
```
Expected: `import ok`

- [ ] **Step 5: Коммит**

```bash
git add convert.py tests/_runner.py tests/.gitkeep docs/
git commit -m "chore: scaffold project, test runner, design+spec docs"
```

---

## Task 2: `format_timestamp` — конвертация микросекунд → `YYYYMMDDTHHMMSSZ`

**Files:**
- Modify: `convert.py` (добавить функцию)
- Create: `tests/test_timestamp.py`

- [ ] **Step 1: Написать проваливающийся тест**

`tests/test_timestamp.py`:
```python
import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def test_real_timestamp():
    # 1404630578154000 usec = 2014-07-06 07:09:38 UTC
    assert convert.format_timestamp(1404630578154000) == "20140706T070938Z"


def test_zero_timestamp_falls_back_to_now():
    result = convert.format_timestamp(0)
    assert re.fullmatch(r"\d{8}T\d{6}Z", result), result


def test_none_timestamp_falls_back_to_now():
    result = convert.format_timestamp(None)
    assert re.fullmatch(r"\d{8}T\d{6}Z", result), result


if __name__ == "__main__":
    run(sys.modules[__name__])
```

- [ ] **Step 2: Запустить тест, убедиться в провале**

Run: `python3 tests/test_timestamp.py`
Expected: FAIL (`AttributeError: module 'convert' has no attribute 'format_timestamp'`)

- [ ] **Step 3: Реализовать**

Добавить в `convert.py` (после импортов, перед `main`):
```python
def format_timestamp(usec):
    """Микросекунды (UTC) -> 'YYYYMMDDTHHMMSSZ'. Пустой/0 -> текущее время UTC."""
    if not usec:
        usec = int(datetime.now(timezone.utc).timestamp() * 1_000_000)
    dt = datetime.fromtimestamp(usec / 1_000_000, tz=timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")
```

- [ ] **Step 4: Запустить тест, убедиться в успехе**

Run: `python3 tests/test_timestamp.py`
Expected: 3/3 passed

- [ ] **Step 5: Коммит**

```bash
git add convert.py tests/test_timestamp.py
git commit -m "feat: format_timestamp converts usec to ENEX datetime"
```

---

## Task 3: `xml_text_escape` + `sanitize_html`

**Files:**
- Modify: `convert.py`
- Create: `tests/test_sanitize.py`

- [ ] **Step 1: Написать проваливающиеся тесты**

`tests/test_sanitize.py`:
```python
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def test_xml_escape_basic():
    assert convert.xml_text_escape("a & b < c > d") == "a &amp; b &lt; c &gt; d"


def test_sanitize_keeps_div():
    assert convert.sanitize_html("<div>hi</div>") == "<div>hi</div>"


def test_sanitize_strips_script():
    assert convert.sanitize_html("<script>alert(1)</script>") == ""


def test_sanitize_drops_style_attr():
    assert convert.sanitize_html('<span style="color:red">t</span>') == "<span>t</span>"


def test_sanitize_keeps_a_href():
    assert convert.sanitize_html('<a href="http://x">L</a>') == '<a href="http://x">L</a>'


def test_sanitize_escapes_amp_in_text():
    assert convert.sanitize_html("<span>Tom &amp; Jerry</span>") == "<span>Tom &amp; Jerry</span>"


def test_sanitize_empty():
    assert convert.sanitize_html("") == ""
    assert convert.sanitize_html(None) == ""


if __name__ == "__main__":
    run(sys.modules[__name__])
```

- [ ] **Step 2: Запустить тест, убедиться в провале**

Run: `python3 tests/test_sanitize.py`
Expected: FAIL (функции не определены)

- [ ] **Step 3: Реализовать**

Добавить в `convert.py`:
```python
def xml_text_escape(text):
    """Экранирование &, <, > для текстовых XML-узлов (заголовок заметки)."""
    return html.escape(text or "", quote=False)


ALLOWED_TAGS = {"div", "p", "br", "span", "b", "i", "u", "a", "ul", "ol", "li", "strong", "em"}
SELF_CLOSING_TAGS = {"br"}
DROP_CONTENT_TAGS = {"script", "style", "head", "meta", "html", "body"}


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.skip_depth:
            return
        if tag in DROP_CONTENT_TAGS:
            self.skip_depth += 1
            return
        if tag in ALLOWED_TAGS:
            kept = []
            for key, value in attrs:
                if tag == "a" and key == "href" and value:
                    kept.append(f'href="{html.escape(value, quote=True)}"')
            attr_str = (" " + " ".join(kept)) if kept else ""
            if tag in SELF_CLOSING_TAGS:
                self.out.append(f"<{tag}{attr_str}/>")
            else:
                self.out.append(f"<{tag}{attr_str}>")
        # неизвестные теги: выбрасываем тег, но сохраняем внутренний текст.

    def handle_startendtag(self, tag, attrs):
        # <br/>, <img/> и т. п.
        if self.skip_depth:
            return
        if tag in DROP_CONTENT_TAGS:
            return
        if tag in ALLOWED_TAGS:
            self.handle_starttag(tag, attrs)
            if tag not in SELF_CLOSING_TAGS:
                self.out.append(f"</{tag}>")

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in ALLOWED_TAGS and tag not in SELF_CLOSING_TAGS:
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if self.skip_depth:
            return
        self.out.append(html.escape(data, quote=False))

    def result(self):
        return "".join(self.out)


def sanitize_html(html_text):
    """Очистить Keep-HTML до разрешённого ENML-подмножества тегов."""
    if not html_text:
        return ""
    sanitizer = _Sanitizer()
    sanitizer.feed(html_text)
    sanitizer.close()
    return sanitizer.result()
```

- [ ] **Step 4: Запустить тест, убедиться в успехе**

Run: `python3 tests/test_sanitize.py`
Expected: 7/7 passed

- [ ] **Step 5: Коммит**

```bash
git add convert.py tests/test_sanitize.py
git commit -m "feat: sanitize_html + xml_text_escape for ENML body"
```

---

## Task 4: `render_text` + `render_checklist`

**Files:**
- Modify: `convert.py`
- Create: `tests/test_render_text.py`

- [ ] **Step 1: Написать проваливающиеся тесты**

`tests/test_render_text.py`:
```python
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def test_render_text_multiline():
    assert convert.render_text("a\nb") == "<div>a</div><div>b</div>"


def test_render_text_blank_line_becomes_br():
    assert convert.render_text("a\n\nb") == "<div>a</div><div><br/></div><div>b</div>"


def test_render_text_escapes():
    assert convert.render_text("x & y") == "<div>x &amp; y</div>"


def test_render_text_empty():
    assert convert.render_text("") == ""
    assert convert.render_text(None) == ""


def test_render_checklist_mixed():
    items = [
        {"text": "buy milk", "isChecked": False},
        {"text": "done task", "isChecked": True},
    ]
    assert convert.render_checklist(items) == "<ul><li>☐ buy milk</li><li>☑ done task</li></ul>"


def test_render_checklist_empty():
    assert convert.render_checklist([]) == "<ul></ul>"


if __name__ == "__main__":
    run(sys.modules[__name__])
```

- [ ] **Step 2: Запустить тест, убедиться в провале**

Run: `python3 tests/test_render_text.py`
Expected: FAIL (функции не определены)

- [ ] **Step 3: Реализовать**

Добавить в `convert.py`:
```python
def render_text(text):
    """Чистый текст -> последовательность <div>-абзацев (ENML-совместимо)."""
    if not text:
        return ""
    parts = []
    for line in text.split("\n"):
        if line == "":
            parts.append("<div><br/></div>")
        else:
            parts.append(f"<div>{html.escape(line)}</div>")
    return "".join(parts)


def render_checklist(items):
    """listContent Keep -> <ul> с символами ☑/☐ перед текстом пункта."""
    parts = ["<ul>"]
    for item in items:
        mark = "☑" if item.get("isChecked", False) else "☐"
        text = item.get("text", "") or ""
        parts.append(f"<li>{mark} {html.escape(text)}</li>")
    parts.append("</ul>")
    return "".join(parts)
```

- [ ] **Step 4: Запустить тест, убедиться в успехе**

Run: `python3 tests/test_render_text.py`
Expected: 6/6 passed

- [ ] **Step 5: Коммит**

```bash
git add convert.py tests/test_render_text.py
git commit -m "feat: render_text + render_checklist (☑/☐ list)"
```

---

## Task 5: `render_labels` + `render_annotations`

**Files:**
- Modify: `convert.py`
- Create: `tests/test_render_meta.py`

- [ ] **Step 1: Написать проваливающиеся тесты**

`tests/test_render_meta.py`:
```python
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def test_render_labels_basic():
    out = convert.render_labels([{"name": "Работа"}, {"name": "Путешествия"}])
    assert out == '<div style="color:#999">🏷 #Работа #Путешествия</div><div><br/></div>'


def test_render_labels_empty():
    assert convert.render_labels([]) == ""
    assert convert.render_labels(None) == ""


def test_render_annotations_weblink():
    ann = [{"source": "WEBLINK", "title": "T", "url": "http://x"}]
    out = convert.render_annotations(ann)
    assert "Ссылки:" in out
    assert '<a href="http://x">T</a>' in out


def test_render_annotations_empty():
    assert convert.render_annotations([]) == ""
    assert convert.render_annotations(None) == ""


if __name__ == "__main__":
    run(sys.modules[__name__])
```

- [ ] **Step 2: Запустить тест, убедиться в провале**

Run: `python3 tests/test_render_meta.py`
Expected: FAIL (функции не определены)

- [ ] **Step 3: Реализовать**

Добавить в `convert.py`:
```python
def render_labels(labels):
    """labels Keep -> блок '#тег #тег' серым в начале тела."""
    if not labels:
        return ""
    tags = " ".join("#" + (lbl.get("name", "")).strip() for lbl in labels)
    return f'<div style="color:#999">🏷 {html.escape(tags)}</div><div><br/></div>'


def render_annotations(annotations):
    """annotations Keep -> блок кликабельных ссылок в конце тела."""
    if not annotations:
        return ""
    parts = ['<div><br/></div>', '<div style="color:#999">Ссылки:</div>']
    for ann in annotations:
        url = ann.get("url", "") or ""
        title = ann.get("title", "") or url or "ссылка"
        parts.append(
            f'<div><a href="{html.escape(url, quote=True)}">{html.escape(title)}</a></div>'
        )
    return "".join(parts)
```

- [ ] **Step 4: Запустить тест, убедиться в успехе**

Run: `python3 tests/test_render_meta.py`
Expected: 4/4 passed

- [ ] **Step 5: Коммит**

```bash
git add convert.py tests/test_render_meta.py
git commit -m "feat: render_labels + render_annotations blocks"
```

---

## Task 6: Dataclass `Note` + `parse_note`

**Files:**
- Modify: `convert.py`
- Create: `tests/test_parse.py`

- [ ] **Step 1: Написать проваливающиеся тесты**

`tests/test_parse.py`:
```python
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def _write_note(data, filename="Test Note.json"):
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


def test_parse_full_note():
    path = _write_note({
        "title": "#Работа ",
        "textContent": "hello",
        "listContent": [{"text": "x", "isChecked": True}],
        "labels": [{"name": "Работа"}],
        "annotations": [{"source": "WEBLINK", "title": "T", "url": "http://x"}],
        "attachments": [{"filePath": "a.jpg", "mimetype": "image/jpeg"}],
        "createdTimestampUsec": 1404630578154000,
        "userEditedTimestampUsec": 1496762375677000,
        "isTrashed": False,
        "isArchived": True,
    })
    note = convert.parse_note(path)
    assert note.title == "#Работа"
    assert note.text_content == "hello"
    assert note.list_content == [{"text": "x", "isChecked": True}]
    assert note.labels == [{"name": "Работа"}]
    assert note.annotations == [{"source": "WEBLINK", "title": "T", "url": "http://x"}]
    assert note.attachments == [{"filePath": "a.jpg", "mimetype": "image/jpeg"}]
    assert note.created_usec == 1404630578154000
    assert note.edited_usec == 1496762375677000
    assert note.is_trashed is False
    assert note.source_name == "Test Note"


def test_parse_minimal_note_defaults():
    path = _write_note({"title": "", "isTrashed": True})
    note = convert.parse_note(path)
    assert note.title == ""
    assert note.text_content == ""
    assert note.list_content == []
    assert note.labels == []
    assert note.attachments == []
    assert note.created_usec == 0
    assert note.is_trashed is True


if __name__ == "__main__":
    run(sys.modules[__name__])
```

- [ ] **Step 2: Запустить тест, убедиться в провале**

Run: `python3 tests/test_parse.py`
Expected: FAIL (`Note`/`parse_note` не определены)

- [ ] **Step 3: Реализовать**

Добавить в `convert.py` (после импортов, до `format_timestamp`):
```python
@dataclass
class Note:
    title: str = ""
    text_content: str = ""
    text_content_html: str = ""
    list_content: list = field(default_factory=list)
    labels: list = field(default_factory=list)
    annotations: list = field(default_factory=list)
    attachments: list = field(default_factory=list)
    created_usec: int = 0
    edited_usec: int = 0
    is_trashed: bool = False
    source_name: str = ""


def parse_note(json_path):
    """Прочитать .json выгрузки Keep в Note."""
    with open(json_path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return Note(
        title=(d.get("title") or "").strip(),
        text_content=d.get("textContent") or "",
        text_content_html=d.get("textContentHtml") or "",
        list_content=d.get("listContent") or [],
        labels=d.get("labels") or [],
        annotations=d.get("annotations") or [],
        attachments=d.get("attachments") or [],
        created_usec=d.get("createdTimestampUsec") or 0,
        edited_usec=d.get("userEditedTimestampUsec") or 0,
        is_trashed=bool(d.get("isTrashed")),
        source_name=os.path.splitext(os.path.basename(json_path))[0],
    )
```

- [ ] **Step 4: Запустить тест, убедиться в успехе**

Run: `python3 tests/test_parse.py`
Expected: 2/2 passed

- [ ] **Step 5: Коммит**

```bash
git add convert.py tests/test_parse.py
git commit -m "feat: Note dataclass + parse_note"
```

---

## Task 7: `render_body` — сборка тела `<en-note>` (без медиа)

**Files:**
- Modify: `convert.py`
- Create: `tests/test_render_body.py`

- [ ] **Step 1: Написать проваливающиеся тесты**

`tests/test_render_body.py`:
```python
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def test_body_prefers_html_over_text():
    note = convert.Note(title="t", text_content="plain", text_content_html="<div>rich</div>")
    body = convert.render_body(note)
    assert "<div>rich</div>" in body
    assert "plain" not in body


def test_body_falls_back_to_text_when_html_blank():
    note = convert.Note(title="t", text_content="plain", text_content_html="")
    body = convert.render_body(note)
    assert "<div>plain</div>" in body


def test_body_uses_checklist_when_list_present():
    note = convert.Note(
        title="t",
        list_content=[{"text": "x", "isChecked": False}],
        text_content="ignored",
    )
    body = convert.render_body(note)
    assert "<ul><li>☐ x</li></ul>" in body
    assert "ignored" not in body


def test_body_includes_labels_and_annotations():
    note = convert.Note(
        title="t",
        text_content="hi",
        labels=[{"name": "Работа"}],
        annotations=[{"source": "WEBLINK", "title": "T", "url": "http://x"}],
    )
    body = convert.render_body(note)
    assert "🏷 #Работа" in body
    assert "<div>hi</div>" in body
    assert "Ссылки:" in body
    assert '<a href="http://x">T</a>' in body


def test_body_empty_note():
    note = convert.Note(title="t")
    assert convert.render_body(note) == ""


def test_body_sanitizes_html():
    note = convert.Note(title="t", text_content_html="<div>a</div><script>x</script>")
    body = convert.render_body(note)
    assert "<div>a</div>" in body
    assert "<script>" not in body


if __name__ == "__main__":
    run(sys.modules[__name__])
```

- [ ] **Step 2: Запустить тест, убедиться в провале**

Run: `python3 tests/test_render_body.py`
Expected: FAIL (`render_body` не определён)

- [ ] **Step 3: Реализовать**

Добавить в `convert.py`:
```python
def render_body(note):
    """Собрать тело <en-note> (без медиа). Порядок: labels, content, annotations."""
    blocks = []

    labels_html = render_labels(note.labels)
    if labels_html:
        blocks.append(labels_html)

    if note.list_content:
        blocks.append(render_checklist(note.list_content))
    else:
        sanitized = sanitize_html(note.text_content_html)
        if sanitized.strip():
            blocks.append(sanitized)
        else:
            blocks.append(render_text(note.text_content))

    annotations_html = render_annotations(note.annotations)
    if annotations_html:
        blocks.append(annotations_html)

    return "".join(blocks)
```

- [ ] **Step 4: Запустить тест, убедиться в успехе**

Run: `python3 tests/test_render_body.py`
Expected: 6/6 passed

- [ ] **Step 5: Коммит**

```bash
git add convert.py tests/test_render_body.py
git commit -m "feat: render_body assembles en-note body"
```

---

## Task 8: `media_and_resources` — `<en-media>` + `<resource>` (base64, MD5, MIME)

**Files:**
- Modify: `convert.py`
- Create: `tests/fixtures/img1.png` (файл-«картинка» с известными байтами)
- Create: `tests/test_media.py`

- [ ] **Step 1: Создать фикстуру-вложение с известными байтами**

Run:
```bash
cd "/Users/apapr/Library/CloudStorage/OneDrive-Личная/Документы/Программирование/2026-06-28 Gkeep to Apple Notes (z)"
printf 'FAKEIMAGEBYTES' > tests/fixtures/img1.png
```
(Содержимое — произвольные байты; конвертер читает байты, считает MD5 и base64. Реальный PNG не требуется для теста структуры.)

- [ ] **Step 2: Написать проваливающиеся тесты**

`tests/test_media.py`:
```python
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
```

- [ ] **Step 3: Запустить тест, убедиться в провале**

Run: `python3 tests/test_media.py`
Expected: FAIL (`media_and_resources` не определён)

- [ ] **Step 4: Реализовать**

Добавить в `convert.py`:
```python
MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
}


def _mime_for(filename, mimetype):
    if mimetype:
        return mimetype
    ext = os.path.splitext(filename)[1].lower()
    return MIME_BY_EXTENSION.get(ext, "application/octet-stream")


def media_and_resources(note, base_dir):
    """Вернуть (media_html, resources_xml) для attachments заметки."""
    media_parts = []
    resource_parts = []
    for att in note.attachments:
        fname = att.get("filePath", "") or ""
        path = os.path.join(base_dir, fname)
        if not os.path.isfile(path):
            media_parts.append(f"<div>[Вложение отсутствует: {html.escape(fname)}]</div>")
            continue
        with open(path, "rb") as fh:
            data = fh.read()
        digest = hashlib.md5(data).hexdigest()
        mime = _mime_for(fname, att.get("mimetype", ""))
        media_parts.append(f'<en-media type="{mime}" hash="{digest}"/>')
        b64 = base64.b64encode(data).decode("ascii")
        resource_parts.append(
            "<resource>"
            f'<data encoding="base64">{b64}</data>'
            f"<mime>{mime}</mime>"
            "<resource-attributes>"
            f"<file-name>{html.escape(os.path.basename(fname))}</file-name>"
            "</resource-attributes>"
            "</resource>"
        )
    return "".join(media_parts), "".join(resource_parts)
```

- [ ] **Step 5: Запустить тест, убедиться в успехе**

Run: `python3 tests/test_media.py`
Expected: 4/4 passed

- [ ] **Step 6: Коммит**

```bash
git add convert.py tests/test_media.py tests/fixtures/img1.png
git commit -m "feat: media_and_resources embeds attachments (base64+md5)"
```

---

## Task 9: `note_to_xml` — полный `<note>` (title/content/created/updated/resources)

**Files:**
- Modify: `convert.py`
- Create: `tests/test_note_xml.py`

- [ ] **Step 1: Написать проваливающиеся тесты**

`tests/test_note_xml.py`:
```python
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_note_xml_structure():
    note = convert.Note(
        title="#Работа",
        text_content="hello",
        created_usec=1404630578154000,
        edited_usec=1496762375677000,
        source_name="Работа",
    )
    xml = convert.note_to_xml(note, FIXTURES)
    assert xml.startswith("<note>")
    assert xml.endswith("</note>")
    assert "<title>#Работа</title>" in xml
    assert "<created>20140706T070938Z</created>" in xml
    assert "<updated>20170606T141935Z</updated>" in xml
    assert "<note-attributes><source>Google Keep</source></note-attributes>" in xml
    assert "<en-note>" in xml
    assert "<div>hello</div>" in xml
    assert "<![CDATA[" in xml


def test_note_xml_empty_title_uses_source_name():
    note = convert.Note(title="", source_name="My Note", text_content="x")
    xml = convert.note_to_xml(note, FIXTURES)
    assert "<title>My Note</title>" in xml


def test_note_xml_escapes_title():
    note = convert.Note(title="a & b < c", text_content="x")
    xml = convert.note_to_xml(note, FIXTURES)
    assert "<title>a &amp; b &lt; c</title>" in xml


def test_note_xml_includes_resource_when_attachment_present():
    note = convert.Note(
        title="t",
        attachments=[{"filePath": "img1.png", "mimetype": "image/png"}],
    )
    xml = convert.note_to_xml(note, FIXTURES)
    assert "<en-media" in xml
    assert "<resource>" in xml


if __name__ == "__main__":
    run(sys.modules[__name__])
```

- [ ] **Step 2: Запустить тест, убедиться в провале**

Run: `python3 tests/test_note_xml.py`
Expected: FAIL (`note_to_xml` не определён)

- [ ] **Step 3: Реализовать**

Добавить в `convert.py`:
```python
NOTE_CONTENT_PREAMBLE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/evernote-compat3.dtd">'
)


def note_to_xml(note, base_dir):
    """Полный <note>: title, content (CDATA en-note), created/updated, resources."""
    title = xml_text_escape(note.title if note.title else note.source_name)
    created = format_timestamp(note.created_usec)
    updated = format_timestamp(note.edited_usec)

    body = render_body(note)
    media_html, resources_xml = media_and_resources(note, base_dir)
    inner = body + media_html

    content = f"{NOTE_CONTENT_PREAMBLE}<en-note>{inner}</en-note>"

    parts = [
        "<note>",
        f"<title>{title}</title>",
        f"<content><![CDATA[{content}]]></content>",
        f"<created>{created}</created>",
        f"<updated>{updated}</updated>",
        "<note-attributes><source>Google Keep</source></note-attributes>",
        resources_xml,
        "</note>",
    ]
    return "".join(parts)
```

- [ ] **Step 4: Запустить тест, убедиться в успехе**

Run: `python3 tests/test_note_xml.py`
Expected: 4/4 passed

- [ ] **Step 5: Коммит**

```bash
git add convert.py tests/test_note_xml.py
git commit -m "feat: note_to_xml builds full <note> element"
```

---

## Task 10: `build_enex` — корневой `<en-export>`

**Files:**
- Modify: `convert.py`
- Create: `tests/test_build_enex.py`

- [ ] **Step 1: Написать проваливающиеся тесты**

`tests/test_build_enex.py`:
```python
import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run


def test_build_enex_wraps_notes():
    enex = convert.build_enex(["<note>x</note>", "<note>y</note>"])
    assert enex.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<!DOCTYPE en-export SYSTEM" in enex
    assert "<en-export " in enex
    assert enex.rstrip().endswith("</en-export>")
    assert "<note>x</note>" in enex
    assert "<note>y</note>" in enex
    assert 'application="GoogleKeep Converter"' in enex


def test_build_enex_export_date_format():
    enex = convert.build_enex([])
    m = re.search(r'export-date="(\d{8}T\d{6}Z)"', enex)
    assert m is not None, enex


def test_build_enex_empty():
    enex = convert.build_enex([])
    assert "<en-export" in enex
    assert "</en-export>" in enex


if __name__ == "__main__":
    run(sys.modules[__name__])
```

- [ ] **Step 2: Запустить тест, убедиться в провале**

Run: `python3 tests/test_build_enex.py`
Expected: FAIL (`build_enex` не определён)

- [ ] **Step 3: Реализовать**

Добавить в `convert.py`:
```python
def build_enex(notes_xml):
    """Собрать корневой export.enex из списка строк <note>...</note>."""
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    header = '<?xml version="1.0" encoding="UTF-8"?>'
    doctype = '<!DOCTYPE en-export SYSTEM "http://xml.evernote.com/pub/evernote-export3.dtd">'
    root_open = (
        f'<en-export export-date="{now}" '
        'application="GoogleKeep Converter" version="1.0">'
    )
    return f"{header}\n{doctype}\n{root_open}\n{''.join(notes_xml)}\n</en-export>"
```

- [ ] **Step 4: Запустить тест, убедиться в успехе**

Run: `python3 tests/test_build_enex.py`
Expected: 3/3 passed

- [ ] **Step 5: Коммит**

```bash
git add convert.py tests/test_build_enex.py
git commit -m "feat: build_enex assembles root en-export"
```

---

## Task 11: `main` — CLI, фильтр, цикл, отчёт

**Files:**
- Modify: `convert.py` (заменить заглушку `main`)
- Create: `tests/test_cli.py`

- [ ] **Step 1: Написать проваливающиеся тесты**

`tests/test_cli.py`:
```python
import glob
import json
import os
import sys
import tempfile
from xml.dom import minidom

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _make_keep_dir():
    d = tempfile.mkdtemp()
    # текстовая заметка
    with open(os.path.join(d, "Text.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "Text", "textContent": "hello", "createdTimestampUsec": 1404630578154000}, f)
    # заметка с вложением (используем существующую фикстуру-байты)
    with open(os.path.join(d, "WithImg.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "WithImg", "attachments": [{"filePath": "img1.png", "mimetype": "image/png"}]}, f)
    with open(os.path.join(d, "img1.png"), "wb") as f:
        f.write(b"FAKEIMAGEBYTES")
    # удалённая заметка (должна быть пропущена по умолчанию)
    with open(os.path.join(d, "Trashed.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "Trashed", "textContent": "bye", "isTrashed": True}, f)
    return d


def test_main_produces_valid_enex_and_skips_trashed():
    keep_dir = _make_keep_dir()
    out = os.path.join(keep_dir, "out.enex")
    rc = convert.main([keep_dir, out])
    assert rc == 0
    assert os.path.isfile(out)

    dom = minidom.parse(out)  # бросится, если XML невалиден
    notes = dom.getElementsByTagName("note")
    # Text + WithImg, Trashed пропущена
    assert len(notes) == 2


def test_main_include_trashed_flag_keeps_all():
    keep_dir = _make_keep_dir()
    out = os.path.join(keep_dir, "out.enex")
    convert.main([keep_dir, out, "--include-trashed"])
    dom = minidom.parse(out)
    notes = dom.getElementsByTagName("note")
    assert len(notes) == 3


if __name__ == "__main__":
    run(sys.modules[__name__])
```

- [ ] **Step 2: Запустить тест, убедиться в провале**

Run: `python3 tests/test_cli.py`
Expected: FAIL (main возвращает 0 без создания файла / заметок 0)

- [ ] **Step 3: Реализовать**

Заменить заглушку `main` в `convert.py` на:
```python
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Конвертер Google Keep Takeout → ENEX (для Apple Notes)."
    )
    parser.add_argument("keep_dir", help="папка выгрузки Google Keep")
    parser.add_argument("output", help="выходной файл .enex")
    parser.add_argument("--include-trashed", action="store_true", help="включить удалённые заметки")
    parser.add_argument("--verbose", action="store_true", help="печатать прогресс")
    args = parser.parse_args(argv)

    json_files = sorted(glob.glob(os.path.join(args.keep_dir, "*.json")))

    notes_xml = []
    n_processed = 0
    n_trashed = 0
    n_with_attachments = 0
    n_missing_attachments = 0
    total = len(json_files)

    for i, json_path in enumerate(json_files):
        try:
            note = parse_note(json_path)
        except Exception as exc:
            if args.verbose:
                print(f"SKIP (ошибка парсинга): {json_path}: {exc}")
            continue

        if note.is_trashed and not args.include_trashed:
            n_trashed += 1
            continue

        if note.attachments:
            n_with_attachments += 1
        for att in note.attachments:
            fname = att.get("filePath", "") or ""
            if not os.path.isfile(os.path.join(args.keep_dir, fname)):
                n_missing_attachments += 1

        notes_xml.append(note_to_xml(note, args.keep_dir))
        n_processed += 1

        if args.verbose and (i + 1) % 50 == 0:
            print(f"  ...{i + 1}/{total}")

    enex = build_enex(notes_xml)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(enex)

    size = os.path.getsize(args.output)
    print("Готово.")
    print(f"  Заметок обработано: {n_processed}")
    print(f"  С вложениями: {n_with_attachments}")
    print(f"  Пропущено (корзина): {n_trashed}")
    print(f"  Вложений не найдено: {n_missing_attachments}")
    print(f"  Размер файла: {size} байт")
    return 0
```

- [ ] **Step 4: Запустить тест, убедиться в успехе**

Run: `python3 tests/test_cli.py`
Expected: 2/2 passed

- [ ] **Step 5: Прогнать весь набор тестов**

Run:
```bash
cd "/Users/apapr/Library/CloudStorage/OneDrive-Личная/Документы/Программирование/2026-06-28 Gkeep to Apple Notes (z)"
for t in tests/test_*.py; do echo "=== $t ==="; python3 "$t" || break; done
```
Expected: все файлы — PASS, ни одного FAIL.

- [ ] **Step 6: Коммит**

```bash
git add convert.py tests/test_cli.py
git commit -m "feat: main CLI with filter, loop and report"
```

---

## Task 12: Интеграционный тест на фикстурах (4 типа заметок)

**Files:**
- Create: `tests/fixtures/text_note.json`
- Create: `tests/fixtures/checklist_note.json`
- Create: `tests/fixtures/empty_note.json`
- Create: `tests/test_integration.py`
- (вложение `tests/fixtures/img1.png` и `with_attachment_note.json` создаются здесь)

- [ ] **Step 1: Создать фикстуры-заметки**

Run:
```bash
cd "/Users/apapr/Library/CloudStorage/OneDrive-Личная/Документы/Программирование/2026-06-28 Gkeep to Apple Notes (z)"
cat > tests/fixtures/text_note.json <<'EOF'
{"title":"Текстовая заметка","textContent":"Строка 1\nСтрока 2","labels":[{"name":"Работа"}],"annotations":[{"source":"WEBLINK","title":"Пример","url":"http://example.com"}],"createdTimestampUsec":1404630578154000,"userEditedTimestampUsec":1496762375677000,"isTrashed":false}
EOF
cat > tests/fixtures/checklist_note.json <<'EOF'
{"title":"Список покупок","listContent":[{"text":"молоко","isChecked":false},{"text":"хлеб","isChecked":true}],"createdTimestampUsec":1404630578154000,"isTrashed":false}
EOF
cat > tests/fixtures/with_attachment_note.json <<'EOF'
{"title":"С картинкой","attachments":[{"filePath":"img1.png","mimetype":"image/png"}],"createdTimestampUsec":1404630578154000,"isTrashed":false}
EOF
cat > tests/fixtures/empty_note.json <<'EOF'
{"title":"","isTrashed":false}
EOF
```

- [ ] **Step 2: Написать интеграционный тест**

`tests/test_integration.py`:
```python
import os
import sys
import tempfile
from xml.dom import minidom

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import convert
from _runner import run

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _run_on_fixtures():
    keep_dir = FIXTURES
    out_dir = tempfile.mkdtemp()
    out = os.path.join(out_dir, "integration.enex")
    rc = convert.main([keep_dir, out])
    assert rc == 0
    return out


def test_integration_valid_xml_with_expected_notes():
    out = _run_on_fixtures()
    dom = minidom.parse(out)
    notes = dom.getElementsByTagName("note")
    titles = []
    for note in notes:
        t = note.getElementsByTagName("title")
        if t:
            titles.append(t[0].firstChild.nodeValue if t[0].firstChild else "")
    # все json-фикстуры, кроме test_* файлов (их нет в fixtures). Ожидаются 4:
    assert "Текстовая заметка" in titles
    assert "Список покупок" in titles
    assert "С картинкой" in titles
    assert "empty_note" in titles  # пустой title → имя файла
    assert len(notes) == 4


def test_integration_checklist_has_marks():
    out = _run_on_fixtures()
    content = open(out, encoding="utf-8").read()
    assert "☐ молоко" in content
    assert "☑ хлеб" in content


def test_integration_text_note_has_labels_and_link():
    out = _run_on_fixtures()
    content = open(out, encoding="utf-8").read()
    assert "🏷 #Работа" in content
    assert '<a href="http://example.com">Пример</a>' in content


def test_integration_attachment_note_has_resource():
    out = _run_on_fixtures()
    dom = minidom.parse(out)
    resources = dom.getElementsByTagName("resource")
    assert len(resources) >= 1
    content = open(out, encoding="utf-8").read()
    assert "<en-media" in content


if __name__ == "__main__":
    run(sys.modules[__name__])
```

- [ ] **Step 3: Запустить тест, убедиться в успехе**

Run: `python3 tests/test_integration.py`
Expected: 4/4 passed

Если в `fixtures` оказались лишние `.json` (например, случайно созданные) — тест заметит лишние заметки; удалите лишнее или оставьте только 4 фикстуры + `img1.png`.

- [ ] **Step 4: Коммит**

```bash
git add tests/fixtures/ tests/test_integration.py
git commit -m "test: integration test covering 4 note types"
```

---

## Task 13: Smoke-тест на реальных данных (1505 заметок) + финальная валидация

**Files:**
- Create: `smoke_test.py`

- [ ] **Step 1: Написать smoke-тест**

`smoke_test.py` (в корне проекта):
```python
"""Smoke-тест: прогон конвертера на реальной выгрузке + валидация XML."""
import os
import sys
import tempfile
from xml.dom import minidom

sys.path.insert(0, os.path.dirname(__file__))
import convert

KEEP_DIR = "/Users/apapr/Downloads/takeout-20260628T161542Z-3-001/Takeout/Google Keep"


def main():
    if not os.path.isdir(KEEP_DIR):
        print(f"ОШИБКА: папка не найдена: {KEEP_DIR}")
        return 1

    out_dir = tempfile.mkdtemp()
    out = os.path.join(out_dir, "smoke.enex")

    print(f"Конвертация {KEEP_DIR} → {out} ...")
    rc = convert.main([KEEP_DIR, out, "--verbose"])
    if rc != 0:
        print("ОШИБКА: main завершился с кодом", rc)
        return 1

    print("Валидация XML ...")
    dom = minidom.parse(out)  # бросится при невалидном XML
    notes = dom.getElementsByTagName("note")
    resources = dom.getElementsByTagName("resource")

    # Подсчёт json в исходной папке (без trashed)
    import glob, json
    total_json = len(glob.glob(os.path.join(KEEP_DIR, "*.json")))
    print(f"Исходных .json: {total_json}")
    print(f"<note> в ENEX: {len(notes)}")
    print(f"<resource> в ENEX: {len(resources)}")

    assert len(notes) > 0, "Заметки не созданы"
    # в данной выгрузке isTrashed=0, поэтому note-количество должно совпадать с числом json
    assert len(notes) == total_json, f"Ожидалось {total_json} заметок, получено {len(notes)}"

    print("SMOKE-ТЕСТ ПРОЙДЕН ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Запустить smoke-тест**

Run:
```bash
cd "/Users/apapr/Library/CloudStorage/OneDrive-Личная/Документы/Программирование/2026-06-28 Gkeep to Apple Notes (z)"
python3 smoke_test.py
```
Expected: прогресс `...50/1505` и т. д., затем сводка и `SMOKE-ТЕСТ ПРОЙДЕН ✅`. Число `<note>` = 1505.

- [ ] **Step 3: Финальная проверка набора тестов**

Run:
```bash
cd "/Users/apapr/Library/CloudStorage/OneDrive-Личная/Документы/Программирование/2026-06-28 Gkeep to Apple Notes (z)"
for t in tests/test_*.py; do echo "=== $t ==="; python3 "$t" || break; done
```
Expected: все тестовые файлы — PASS.

- [ ] **Step 4: Коммит**

```bash
git add smoke_test.py
git commit -m "test: smoke test on real 1505-note export"
```

---

## Финальная проверка (после всех задач)

- [ ] Все юнит-тесты (`tests/test_*.py`) — PASS.
- [ ] Smoke-тест на реальных данных — PASS, `<note>` = 1505.
- [ ] Сгенерированный `.enex` открывается как валидный XML (`minidom.parse` без ошибок).
- [ ] Готовый `.enex` импортируется в Apple Notes (ручная проверка пользователем).
