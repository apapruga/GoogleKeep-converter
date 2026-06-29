# Google Keep → Apple Notes (.enex)

[English](#english) · **Русский**

Конвертер выгрузки [Google Takeout](https://takeout.google.com/) (папка «Google Keep») в файл `.enex` для импорта в приложение **Apple Notes** (macOS / iOS).

- **Без зависимостей** — только стандартная библиотека Python 3 (проверено на 3.9+). Единственная опциональная зависимость — Pillow для уменьшения картинок.
- **Два режима работы:**
  - **CLI** (`convert.py`) — пакетная конвертация папки из терминала.
  - **Веб-интерфейс** (`server.py`) — загрузка файлов через браузер (zip или drag&drop), с настройками.
- **Локально и приватно** — сервер слушает только `127.0.0.1`, данные никуда не уходят.
- **Двуязычный UI** — переключатель RUS / ENG в правом верхнем углу.
- **Картинки** встраиваются в `.enex` (base64) — файл самодостаточен, опционально можно уменьшить.

---

## Возможности

| Функция | CLI | Веб-интерфейс |
|---|:---:|:---:|
| Конвертация папки Keep → `.enex` | ✅ | ✅ |
| Загрузка `.zip` архива | — | ✅ |
| Drag & drop отдельных файлов | — | ✅ |
| Включение удалённых заметок (корзины) | ✅ | ✅ |
| Уменьшение картинок (jpg/png/heic/gif) | — | ✅ |
| Прогресс-лог | ✅ | спиннер |
| Сводка результата | ✅ | ✅ |

**Что переносится из заметок:**
- Заголовок, текст и HTML-форматирование (санитизируется под ENML).
- Чек-листы → списки с символами ☑ (отмечено) / ☐ (не отмечено).
- Теги (labels) → блок `🏷 #Тег #Тег` серым в начале тела.
- Веб-ссылки (annotations) → кликабельный блок «Ссылки:».
- Картинки (attachments) → встроены как `<resource>` с MD5-хешем.
- Даты создания и изменения (из микросекундных timestamp'ов Keep).
- Архивированные заметки включаются; корзина по умолчанию исключается (можно включить).

---

## Установка

Ничего ставить не нужно — нужен только предустановленный `python3`.

```bash
git clone <repo> gkeep-to-enex
cd gkeep-to-enex
```

Для опциональной функции **уменьшения картинок**:

```bash
pip3 install Pillow pillow-heif
```

Структура проекта:

```
convert.py                  ядро конверсии + CLI
server.py                   веб-сервер (http.server) + уменьшение картинок
static/index.html           веб-интерфейс (двуязычный)
smoke_test.py               smoke-тест на реальной выгрузке
tests/                      юнит- и интеграционные тесты
docs/superpowers/           спецификации и планы реализации
Запустить конвертер.command  ярлык запуска для macOS (двойной клик)
```

---

## Получение исходных данных

1. Зайди на https://takeout.google.com/
2. Сними всё, кроме **Google Keep**.
3. Создай экспорт → скачается архив `takeout-…zip`.
4. Распакуй его — внутри будет папка `Takeout/Google Keep/` с парами `.json` + `.html` и файлами картинок.

Дальше выбери способ запуска: **веб-интерфейс**, **CLI** или **ярлык macOS**.

---

## Способ 1. Веб-интерфейс (проще)

```bash
python3 server.py
```

Браузер **автоматически откроется** на `http://127.0.0.1:8000/`.
Остановка сервера — `Ctrl+C`.

Опции запуска:

```bash
python3 server.py --port 8080        # другой порт
python3 server.py --no-browser       # не открывать браузер
python3 server.py --host 0.0.0.0     # слушать все интерфейсы (осторожно: доступен из сети)
```

**В браузере:**

1. Переключатель **RUS / ENG** в правом верхнем углу — выбор языка интерфейса.
2. Перетащи файлы в зону (или нажми → выбери файлы):
   - **`.zip`** — архив папки `Google Keep` (например, сжать папку в Finder: «Сжать»), **или**
   - **все файлы** из папки `Google Keep` сразу (`.json` + картинки).
   - Если есть `.zip`, отдельные файлы игнорируются (приоритет у zip).
3. (Опц.) галочка **«Включить удалённые (корзину)»**.
4. (Опц.) галочка **«Уменьшить картинки»** → настрой порог размера и степень → нажми **«Применить»**. Картинки крупнее порога уменьшатся по габаритам с сохранением формата (см. [Уменьшение картинок](#уменьшение-картинок)).
5. Нажми **«Конвертировать»**.
6. Скачается `GoogleKeep.enex` → импортируй в Apple Notes.

## Способ 2. CLI

```bash
python3 convert.py <папка_Google_Keep> <выход.enex>
```

Пример:

```bash
python3 convert.py \
  ~/Downloads/takeout-20260628T161542Z-3-001/Takeout/Google\ Keep \
  GoogleKeep.enex
```

Флаги:

| Флаг | Назначение |
|---|---|
| `--include-trashed` | включить удалённые заметки (по умолчанию корзина исключается) |
| `--verbose` | печатать прогресс каждые 50 заметок |

## Способ 3. Ярлык macOS (двойной клик)

В папке проекта есть файл **`Запустить конвертер.command`**. Двойной клик в Finder откроет Terminal и запустит сервер, браузер откроется автоматически. При первом запуске macOS может спросить разрешение (System Settings → Privacy & Security → «Открыть»). Остановка — `Ctrl+C`.

---

## Импорт в Apple Notes

1. Открой **Apple Notes**.
2. Меню **Файл → Импорт в Notes…** (macOS) или **Импорт в Notes** (iOS — через «Поделиться» файлом `.enex`).
3. Выбери сгенерированный `GoogleKeep.enex`.

Все заметки появятся отдельными записями.

---

## Как преобразуются данные

| Google Keep | В Apple Notes (.enex) |
|---|---|
| `title` | заголовок заметки (пустой → имя файла) |
| `textContent` / `textContentHtml` | тело заметки (HTML санитизируется под ENML) |
| `listContent` (чек-лист) | список с ☑ (отмечено) / ☐ (не отмечено) |
| `labels` (теги) | блок `🏷 #Тег #Тег` серым в начале тела |
| `annotations` (веб-ссылки) | блок «Ссылки:» с кликабельными `<a href>` |
| `attachments` (картинки) | встроены в `.enex` как `<resource>` (base64 + MD5) |
| `createdTimestampUsec` / `userEditedTimestampUsec` | даты создания/изменения |
| `isTrashed` | пропускается (если не `--include-trashed`) |
| `isArchived` | включается |
| `color`, `isPinned`, `sharees`, аудио | не переносятся (в Keep Takeout нет полных данных) |

### Уменьшение картинок (опционально, только в веб-интерфейсе)

Опция **«Уменьшить картинки»** позволяет уменьшить большие изображения перед встраиванием в `.enex`.

- **Требует** `pip install Pillow pillow-heif` (без них опция вернёт ошибку установки).
- **Порог размера**: файлы крупнее порога (КБ/МБ, по умолчанию 1 МБ) масштабируются; мельче — не трогаются.
- **Степень**: габариты (ширина и высота) умножаются на 75/50/25%.
- **Формат**: сохраняется исходный (JPEG/PNG/HEIC/GIF).
- **Ограничение**: анимированные GIF при уменьшении теряют анимацию (сохраняется первый кадр) — особенность Pillow.

---

## Тесты

Тестовый раннер — собственный, без pytest. Запуск одного файла:

```bash
python3 tests/test_server.py
```

Запуск всех тестов:

```bash
for t in tests/test_*.py; do python3 "$t" || break; done
```

Smoke-тест на реальной выгрузке (папка захардкожена в `smoke_test.py` — поправь путь под себя):

```bash
python3 smoke_test.py
```

Покрытие:
- `test_timestamp.py` — `format_timestamp` (мкс → `YYYYMMDDTHHMMSSZ`)
- `test_sanitize.py` — `sanitize_html`, `xml_text_escape`
- `test_render_text.py` — `render_text`, `render_checklist`
- `test_render_meta.py` — `render_labels`, `render_annotations`
- `test_parse.py` — `Note`, `parse_note`
- `test_render_body.py` — `render_body`
- `test_media.py` — `media_and_resources` (base64, MD5, MIME-фолбэк)
- `test_note_xml.py` — `note_to_xml`
- `test_build_enex.py` — `build_enex`
- `test_cli.py` — CLI `main` (фильтр корзины, валидность XML)
- `test_convert_directory.py` — ядро `convert_directory` (отчёт, прогресс-колбэк)
- `test_integration.py` — 4 типа заметок end-to-end
- `test_server.py` — веб-сервер (sanitize, find_keep_root, zip, HTTP `/convert`, resize)

---

## Технические детали

- **Кодировка:** UTF-8 во всём.
- **Контент заметки** оборачивается в `<![CDATA[…]]>` — экранировать тело не нужно.
- **MIME** вложения: из `attachments[].mimetype`, фолбэк по расширению (`.jpg/.jpeg/.png/.gif`).
- **Media-hash:** MD5 от бинарника файла; один и тот же хеш в `<en-media>` и `<resource>`.
- **Лимит запроса** в веб-сервере: 200 МБ (`MAX_BODY_SIZE` в `server.py`). Превышение → `413`.
- **Безопасность:** сервер слушает только `127.0.0.1` по умолчанию; имена загруженных файлов санитизируются от path-traversal; статику нельзя покинуть через `/static/..`.

---

## Документация проектирования

- `docs/superpowers/specs/2026-06-28-gkeep-to-enex-design.md` — спецификация конвертера.
- `docs/superpowers/specs/2026-06-28-web-ui-design.md` — спецификация веб-интерфейса.
- `docs/superpowers/specs/2026-06-29-image-resize-design.md` — спецификация уменьшения картинок.
- `docs/superpowers/plans/2026-06-28-gkeep-to-enex.md` — план реализации конвертера.
- `docs/superpowers/plans/2026-06-28-web-ui.md` — план реализации веб-интерфейса.
- `docs/superpowers/plans/2026-06-29-image-resize.md` — план реализации уменьшения картинок.

---
---

# English

# Google Keep → Apple Notes (.enex)

**English** · [Русский](#google-keep--apple-notes-enex)

A converter for a [Google Takeout](https://takeout.google.com/) export (the «Google Keep» folder) into a `.enex` file for import into **Apple Notes** (macOS / iOS).

- **No dependencies** — Python 3 standard library only (tested on 3.9+). The only optional dependency is Pillow for image resizing.
- **Two modes:**
  - **CLI** (`convert.py`) — batch-convert a folder from the terminal.
  - **Web UI** (`server.py`) — upload files through a browser (zip or drag & drop), with settings.
- **Local and private** — the server listens on `127.0.0.1` only; your data never leaves your machine.
- **Bilingual UI** — RUS / ENG switch in the top-right corner.
- **Images** are embedded into the `.enex` (base64) — the file is self-contained, with optional resizing.

---

## Features

| Feature | CLI | Web UI |
|---|:---:|:---:|
| Convert a Keep folder → `.enex` | ✅ | ✅ |
| Upload a `.zip` archive | — | ✅ |
| Drag & drop individual files | — | ✅ |
| Include deleted notes (trash) | ✅ | ✅ |
| Resize images (jpg/png/heic/gif) | — | ✅ |
| Progress log | ✅ | spinner |
| Result summary | ✅ | ✅ |

**What gets migrated from your notes:**
- Title, text and HTML formatting (sanitized to ENML).
- Checklists → lists with ☑ (checked) / ☐ (unchecked) symbols.
- Tags (labels) → a `🏷 #Tag #Tag` block in grey at the top of the body.
- Web links (annotations) → a clickable «Links:» block.
- Images (attachments) → embedded as `<resource>` with an MD5 hash.
- Creation and modification dates (from Keep's microsecond timestamps).
- Archived notes are included; trash is excluded by default (can be included).

---

## Installation

Nothing to install — only a preinstalled `python3` is required.

```bash
git clone <repo> gkeep-to-enex
cd gkeep-to-enex
```

For the optional **image resizing** feature:

```bash
pip3 install Pillow pillow-heif
```

Project structure:

```
convert.py                  core conversion logic + CLI
server.py                   web server (http.server) + image resizing
static/index.html           web UI (bilingual)
smoke_test.py               smoke test on a real export
tests/                      unit and integration tests
docs/superpowers/           design specs and implementation plans
Запустить конвертер.command  macOS launcher (double-click)
```

---

## Getting the source data

1. Go to https://takeout.google.com/
2. Deselect everything except **Google Keep**.
3. Create the export → download the `takeout-….zip` archive.
4. Unzip it — inside you'll find `Takeout/Google Keep/` with pairs of `.json` + `.html` files and image files.

Then pick a way to run it: **Web UI**, **CLI** or the **macOS launcher**.

---

## Option 1. Web UI (easiest)

```bash
python3 server.py
```

The browser **opens automatically** at `http://127.0.0.1:8000/`.
Stop the server with `Ctrl+C`.

Launch options:

```bash
python3 server.py --port 8080        # different port
python3 server.py --no-browser       # do not open the browser
python3 server.py --host 0.0.0.0     # listen on all interfaces (caution: reachable from the network)
```

**In the browser:**

1. **RUS / ENG** switch in the top-right corner — pick the UI language.
2. Drag files into the zone (or click → choose files):
   - either a **`.zip`** archive of the `Google Keep` folder (e.g. compress the folder in Finder), **or**
   - **all files** from the `Google Keep` folder at once (`.json` + images).
   - If a `.zip` is present, separate files are ignored (zip takes priority).
3. (Optional) tick **«Include deleted (trash)»**.
4. (Optional) tick **«Resize images»** → set a size threshold and scale → click **«Apply»**. Images larger than the threshold get resized by dimensions, keeping the original format (see [Image resizing](#image-resizing)).
5. Click **«Convert»**.
6. `GoogleKeep.enex` downloads → import it into Apple Notes.

## Option 2. CLI

```bash
python3 convert.py <Google_Keep_folder> <output.enex>
```

Example:

```bash
python3 convert.py \
  ~/Downloads/takeout-20260628T161542Z-3-001/Takeout/Google\ Keep \
  GoogleKeep.enex
```

Flags:

| Flag | Purpose |
|---|---|
| `--include-trashed` | include deleted notes (excluded by default) |
| `--verbose` | print progress every 50 notes |

## Option 3. macOS launcher (double-click)

The project folder contains **`Запустить конвертер.command`**. Double-clicking it in Finder opens Terminal, starts the server, and the browser opens automatically. On first launch macOS may ask for permission (System Settings → Privacy & Security → «Open»). Stop with `Ctrl+C`.

---

## Importing into Apple Notes

1. Open **Apple Notes**.
2. Menu **File → Import to Notes…** (macOS), or **Import to Notes** (iOS — via «Share» on the `.enex` file).
3. Select the generated `GoogleKeep.enex`.

All notes appear as separate entries.

---

## How data is transformed

| Google Keep | In Apple Notes (.enex) |
|---|---|
| `title` | note title (empty → file name) |
| `textContent` / `textContentHtml` | note body (HTML sanitized to ENML) |
| `listContent` (checklist) | list with ☑ (checked) / ☐ (unchecked) |
| `labels` (tags) | `🏷 #Tag #Tag` block in grey at the top of the body |
| `annotations` (web links) | «Links:» block with clickable `<a href>` |
| `attachments` (images) | embedded in `.enex` as `<resource>` (base64 + MD5) |
| `createdTimestampUsec` / `userEditedTimestampUsec` | creation/modification dates |
| `isTrashed` | skipped (unless `--include-trashed`) |
| `isArchived` | included |
| `color`, `isPinned`, `sharees`, audio | not migrated (Keep Takeout lacks the full data) |

### Image resizing (optional, web UI only)

The **«Resize images»** option downsizes large images before embedding them into the `.enex`.

- **Requires** `pip install Pillow pillow-heif` (without them the option returns an install error).
- **Size threshold**: files larger than the threshold (KB/MB, default 1 MB) are resized; smaller ones are left untouched.
- **Scale**: the dimensions (width and height) are multiplied by 75/50/25%.
- **Format**: the original is preserved (JPEG/PNG/HEIC/GIF).
- **Limitation**: animated GIFs lose their animation when resized (only the first frame is kept) — a Pillow limitation.

---

## Tests

The test runner is custom, no pytest. Run a single file:

```bash
python3 tests/test_server.py
```

Run all tests:

```bash
for t in tests/test_*.py; do python3 "$t" || break; done
```

Smoke test on a real export (the folder is hardcoded in `smoke_test.py` — adjust the path for yourself):

```bash
python3 smoke_test.py
```

Coverage:
- `test_timestamp.py` — `format_timestamp` (µs → `YYYYMMDDTHHMMSSZ`)
- `test_sanitize.py` — `sanitize_html`, `xml_text_escape`
- `test_render_text.py` — `render_text`, `render_checklist`
- `test_render_meta.py` — `render_labels`, `render_annotations`
- `test_parse.py` — `Note`, `parse_note`
- `test_render_body.py` — `render_body`
- `test_media.py` — `media_and_resources` (base64, MD5, MIME fallback)
- `test_note_xml.py` — `note_to_xml`
- `test_build_enex.py` — `build_enex`
- `test_cli.py` — CLI `main` (trash filter, XML validity)
- `test_convert_directory.py` — core `convert_directory` (report, progress callback)
- `test_integration.py` — 4 note types end-to-end
- `test_server.py` — web server (sanitize, find_keep_root, zip, HTTP `/convert`, resize)

---

## Technical details

- **Encoding:** UTF-8 everywhere.
- **Note content** is wrapped in `<![CDATA[…]]>` — no need to escape the body.
- **MIME** of an attachment: from `attachments[].mimetype`, fallback by extension (`.jpg/.jpeg/.png/.gif`).
- **Media-hash:** MD5 of the file's bytes; the same hash in `<en-media>` and `<resource>`.
- **Request limit** in the web server: 200 MB (`MAX_BODY_SIZE` in `server.py`). Exceeding it → `413`.
- **Security:** the server listens on `127.0.0.1` only by default; uploaded file names are sanitized against path-traversal; static assets cannot be escaped via `/static/..`.

---

## Design documentation

- `docs/superpowers/specs/2026-06-28-gkeep-to-enex-design.md` — converter spec.
- `docs/superpowers/specs/2026-06-28-web-ui-design.md` — web UI spec.
- `docs/superpowers/specs/2026-06-29-image-resize-design.md` — image resize spec.
- `docs/superpowers/plans/2026-06-28-gkeep-to-enex.md` — converter implementation plan.
- `docs/superpowers/plans/2026-06-28-web-ui.md` — web UI implementation plan.
- `docs/superpowers/plans/2026-06-29-image-resize.md` — image resize implementation plan.
