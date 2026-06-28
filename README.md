# Google Keep → Apple Notes (.enex)

Конвертер выгрузки [Google Takeout](https://takeout.google.com/) (папка «Google Keep») в файл `.enex` для импорта в приложение **Apple Notes** (macOS / iOS).

- **Без зависимостей** — только стандартная библиотека Python 3 (проверено на 3.9).
- **CLI** для пакетной конвертации папки.
- **Локальный веб-интерфейс** — загрузка файлов через браузер (zip или drag&drop).
- Картинки встраиваются в `.enex` (base64) — файл самодостаточен.
- Чек-листы → списки с ☑/☐, теги → текстом в теле заметки.

---

## Установка

Ничего ставить не нужно. Нужен только предустановленный `python3`.

```bash
git clone <repo> gkeep-to-enex
cd gkeep-to-enex
```

Структура проекта:

```
convert.py            ядро конверсии + CLI
server.py             веб-сервер (http.server)
static/index.html     веб-интерфейс
smoke_test.py         smoke-тест на реальной выгрузке
tests/                юнит- и интеграционные тесты
docs/superpowers/     спецификация и план реализации
```

---

## Получение исходных данных

1. Зайди на https://takeout.google.com/
2. Сними всё, кроме **Google Keep**.
3. Создай экспорт → скачается архив `takeout-…zip`.
4. Распакуй его — внутри будет папка `Takeout/Google Keep/` с парами `.json` + `.html` и файлами картинок.

Дальше выбери способ запуска: **веб-интерфейс** или **CLI**.

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

В браузере:

1. Перетащи файлы в зону (или нажми → выбери файлы):
   - **`.zip`** — архив папки `Google Keep` (например, сжать папку в Finder: «Сжать»), **или**
   - **все файлы** из папки `Google Keep` сразу (`.json` + картинки).
   - Если есть `.zip`, отдельные файлы игнорируются (приоритет у zip).
2. (Опц.) поставь галочку **«Включить удалённые (корзину)»**.
3. Нажми **«Конвертировать»**.
4. Скачается `GoogleKeep.enex` → импортируй в Apple Notes: **Файл → Импорт в Notes…**

---

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

В конце работы печатается сводка: сколько заметок обработано, сколько с вложениями, сколько пропущено, размер файла.

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
- `test_server.py` — веб-сервер (sanitize, find_keep_root, zip, HTTP `/convert`)

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
- `docs/superpowers/plans/2026-06-28-gkeep-to-enex.md` — план реализации конвертера.
- `docs/superpowers/plans/2026-06-28-web-ui.md` — план реализации веб-интерфейса.
