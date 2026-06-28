# Дизайн: Конвертер Google Keep → ENEX (для импорта в Apple Notes)

**Дата:** 2026-06-28
**Цель:** Преобразовать выгрузку Google Takeout (папка «Google Keep» с парами `.json`+`.html` и файлами картинок) в один файл `.enex`, пригодный для импорта в приложение Apple Notes (macOS/iOS).

## Контекст исходных данных

Исходная папка: `~/Downloads/takeout-20260628T161542Z-3-001/Takeout/Google Keep`.

Структура выгрузки Keep:
- На каждую заметку — пара `<имя>.json` (метаданные + контент) и `<имя>.html` (рендеринг для просмотра). Все необходимые данные содержатся в `.json`; `.html` игнорируется.
- Файлы изображений (`*.jpg`, `*.png`) лежат в той же папке и ссылаются из поля `attachments[].filePath`.

Статистика по выгрузке (1505 заметок):
| Поле | Кол-во | Назначение |
|---|---|---|
| `title` | 1505 | Заголовок заметки |
| `textContent` | 1102 | Чистый текст заметки |
| `textContentHtml` | 953 | HTML-форматированный текст |
| `listContent` | 401 | Чек-листы (пункты с `isChecked`) |
| `tasks` | 582 | ID подзадач (метаданные; сам контент в `listContent`) |
| `labels` | 257 | Теги («Работа», «Путешествия» и т. п.) |
| `annotations` | 211 | Веб-ссылки (289 WEBLINK + 1 DOCS) |
| `attachments` | 191 | Вложения-картинки |
| `sharees` | 39 | Соавторы (игнорируются) |
| `isTrashed` | 0 | Корзина (в данной выгрузке пуста) |

Прочие поля: `color`, `isPinned`, `isArchived`, `createdTimestampUsec`, `userEditedTimestampUsec` (timestamps в микросекундах, UTC).

Edge-кейсы в данных:
- 77 заметок без `title`/`textContent`/`listContent`.
- 108 заметок только с вложениями (без текста/списка).
- 6 заметок, чьё `title` начинается с `#` (осмысленный текст пользователя — сохраняем как есть).

## Решения (выбрано на этапе брейншторма)

1. **Цель:** оптимизация под импорт в Apple Notes.
2. **Чек-листы:** список с символами ☑ (отмечено) / ☐ (не отмечено) перед текстом пункта.
3. **Теги:** записываются текстом в начале тела заметки (`#Работа #Путешествия`); папки и дубли не создаются.
4. **Картинки:** встраиваются в ENEX как `<resource>` с base64 (самодостаточный файл).
5. **Стек:** Python 3, только стандартная библиотека.
6. **Фильтр:** включаются все заметки, кроме `isTrashed=true` (по умолчанию; флаг `--include-trashed` меняет поведение).

## Архитектура

**Подход A — единый пайплайн.** Один файл `convert.py`, один проход по папке Keep. Преобразование Keep→ENML инкапсулировано в функциях; промежуточная модель `Note` (dataclass).

Поток:
```
glob *.json
  → parse_note()      : json.load → Note (dataclass)
  → filter            : skip isTrashed (unless --include-trashed)
  → render_body()     : Note → ENML-строка (тело <en-note>)
  → render_resource() : каждое вложение → <resource> с base64
  → note_to_xml()     : <note><title><content>...<resource>...</note>
собрать все <note> в один <en-export> → записать output.enex
```

### Структура файла `convert.py`

1. `Note` — dataclass, промежуточная модель заметки.
2. `parse_note(json_path)` → `Note` — чтение и нормализация Keep-JSON.
3. `render_body(note)` → str — тело `<en-note>` (диспетчер по типу содержимого).
4. `sanitize_html(html)` → str — санитизация `textContentHtml` до разрешённого ENML-подмножества.
5. `render_resource(att_path, mime, fname)` → str — `<resource>` с base64.
6. `note_to_xml(note, base_dir)` → str — полный `<note>` с контентом и ресурсами.
7. `build_enex(notes_xml)` → str — корневой `export.enex`.
8. `main()` — CLI, glob, фильтр, цикл, запись, отчёт.

### CLI

```
python3 convert.py <папка_Keep> <выход.enex>
                   [--include-trashed] [--verbose]
```

## Форматы и преобразования

- **Кодировка:** UTF-8 везде.
- **Контент:** всегда оборачивается в `<![CDATA[ ]]>`; внутри — полная ENML-декларация с `<en-note>`. Это снимает необходимость экранировать тело.
- **Timestamps:** `createdTimestampUsec`/`userEditedTimestampUsec` (мкс, UTC) → `YYYYMMDDTHHMMSSZ`. Нулевой/отсутствующий timestamp → текущее время (UTC).
- **Media-hash:** MD5 от бинарных данных файла вложения (hex). Используется и в `<en-media hash="...">` в теле, и сопоставляется с `<resource>`.

## Рендеринг тела заметки (Keep → ENML)

Тело — содержимое `<en-note>...</en-note>`. Apple Notes рендерит этот HTML. Порядок блоков в теле:

1. Лейблы-теги (если есть `labels`).
2. Текст ИЛИ чек-лист (взаимоисключающе).
3. Блок ссылок (если есть `annotations`).
4. Медиа (`<en-media>` для каждого вложения, в порядке массива `attachments`).

### Детали по типам

**Заголовок (`title`)** → идёт в `<note><title>` (мета ENEX), НЕ в тело.
- Пустой `title` → в `<title>` ставим имя файла `.json` без расширения (чтобы заметка была различима в списке Apple Notes).
- `title`, начинающийся с `#`, сохраняем как есть.

**Лейблы (`labels`)** → текстом в начале тела:
```xml
<div style="color:#999">🏷 #Работа #Путешествия</div>
<div><br/></div>
```

**Обычный текст (`textContent`/`textContentHtml`)**:
- Приоритет: `textContentHtml` (если есть и валиден после санитизации) > `textContent` > пусто.
- Чистый `textContent`: разбиваем по `\n` на абзацы `<div>...</div>`.
- `textContentHtml` проходит через `sanitize_html()`: оставляем разрешённые ENML-теги (`div, p, br, span, b, i, u, a, ul, ol, li, strong, em`), удаляем запрещённые (`script, style, head, meta, html, body`), упрощаем инлайн-стили (убираем `white-space:pre-wrap`, избыточные `font-family`/`font-size` от Keep-редактора).

**Чек-листы (`listContent`)** → маркированный список с ☑/☐:
```xml
<ul>
  <li>☐ Доктор мом пастилки</li>      <!-- isChecked=false -->
  <li>☑ Аспирин растворимый</li>      <!-- isChecked=true -->
</ul>
```
- ☐ (U+2610) для невыбранных, ☑ (U+2611) для выбранных, ставится в начало текста пункта + пробел.
- Текст пункта — из `listContent[i].text`.

**Поле `tasks`**: игнорируется (это ID подзадач; контент берётся из `listContent`).

**Веб-аннотации (`annotations`)** → блок в конце тела:
```xml
<div><br/></div>
<div style="color:#999">Ссылки:</div>
<div><a href="http://...">13 ненужных вещей...</a></div>
```
- WEBLINK → кликабельная `<a href="url">title</a>`. DOCS → текстовая ссылка (`url`/`title`).

**Вложения (`attachments`)**:
- На месте картинки в теле: `<en-media type="image/jpeg" hash="ХЭШ"/>`.
- Hash = MD5 бинарных данных файла (hex).
- Файл ищется по `attachments[i].filePath` относительно папки Keep.
- Если файл отсутствует → вместо `<en-media>` ставим `<div>[Вложение отсутствует: xxx.jpg]</div>`, `<resource>` не создаём (не падаем).

## Структура `export.enex`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE en-export SYSTEM "http://xml.evernote.com/pub/evernote-export3.dtd">
<en-export export-date="20260628T161542Z" application="GoogleKeep Converter" version="1.0">
  <note>
    <title>...заголовок...</title>
    <content><![CDATA[<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/evernote-compat3.dtd">
<en-note>...тело...</en-note>]]></content>
    <created>20170606T141935Z</created>
    <updated>20170606T141935Z</updated>
    <note-attributes><source>Google Keep</source></note-attributes>
    <resource>...</resource>
  </note>
  ...
</en-export>
```

### Ресурс `<resource>` (на каждое вложение)

```xml
<resource>
  <data encoding="base64">BASE64_БИНАРНЫХ_ДАННЫХ</data>
  <mime>image/jpeg</mime>
  <resource-attributes>
    <file-name>xxx.jpg</file-name>
  </resource-attributes>
</resource>
```
- MIME из `attachments[i].mimetype`. Фолбэк по расширению: `.jpg/.jpeg→image/jpeg`, `.png→image/png`, `.gif→image/gif`, прочее → `application/octet-stream`.
- `width`/`height` не добавляем: у Takeout-данных они часто отсутствуют/неточны, а Apple Notes принимает ресурс без них. Hash внутри `<resource>` для сопоставления с `<en-media>` — тот же MD5 hex.

## Обработка edge-кейсов

| Случай | Обработка |
|---|---|
| Нет `title`/`textContent`/`listContent` (77) | `<title>` = имя файла; тело = теги/ссылки/медиа или пустое `<en-note></en-note>` |
| `textContentHtml` битый | fallback на `textContent` |
| Файл вложения отсутствует | `[Вложение отсутствует: …]` в теле, без `<resource>` |
| Нет `mimetype` | определение по расширению |
| `title` начинается с `#` | сохраняем как есть |
| `isTrashed=true` | skip (если не `--include-trashed`) |
| `isArchived=true` | включаем |
| `.html` рядом с `.json` | игнорируем `.html` (все данные в `.json`) |

Парсер работает **только с `.json`** — надёжнее, чем парсить HTML.

## Тестирование (TDD)

- Тесты на pytest; если pytest недоступен — простой `assert`-раннер без внешних зависимостей.
- **Unit-тесты** на чистые функции:
  - `render_checklist()` → корректные ☑/☐.
  - `render_text("a\nb")` → два `<div>`.
  - `sanitize_html()` → удаляет `<script>`, оставляет `<div>`.
  - `format_timestamp(usec)` → `YYYYMMDDTHHMMSSZ`.
  - `enml_escape()` — корректность XML.
- **Интеграционный тест:** мини-фикстура (3–4 `.json` + 1 `.jpg`) → запуск `convert.py` → проверка, что `.enex` валидный XML (`xml.dom.minidom`), содержит ожидаемые `<note>`, `<en-media>`, символы галочек.
- **Smoke-тест на реальных данных:** прогон по всем 1505 заметкам → файл создаётся, парсится как XML, число `<note>` равно ожидаемому. Финальная проверка.

## Отчётность

По завершении скрипт печатает сводку:
- сколько заметок обработано;
- сколько с вложениями;
- сколько пропущено (trashed);
- сколько вложений не найдено;
- размер выходного файла.

## Не входит в рамки (YAGNI)

- Создание папок Apple Notes и распределение по ним.
- Аудио-вложения (в выгрузке отсутствуют; при появлении — фолбэк `application/octet-stream` + `[Вложение отсутствует/неподдерживаемый тип]`).
- Дедупликация заметок.
- Сохранение `color`/`isPinned`/`isArchived`/`sharees`.
- Интерактивный GUI.
