# Дизайн: Уменьшение картинок в веб-интерфейсе

**Дата:** 2026-06-29
**Цель:** Добавить в веб-UI опциональную возможность уменьшать картинки в выгрузке Google Keep перед встраиванием в `.enex`: пользователь выбирает порог размера (КБ/МБ, по умолчанию 1 МБ) и степень уменьшения (75/50/25%, по умолчанию 50%), и все картинки (jpg/jpeg/png/heic/gif) крупнее порога масштабируются по габаритам и сохраняются в исходном формате.

## Контекст

Текущий веб-интерфейс (`server.py` + `static/index.html`) принимает zip или перетаскиваемые файлы, готовит временную папку и вызывает `convert_directory()` из `convert.py`. Картинки встраиваются в `.enex` как есть. Новая фича вставляется между подготовкой временной папки и вызовом `convert_directory()`.

## Решения (выбрано на этапе брейншторма)

1. **Библиотека:** Pillow + pillow-heif (полная поддержка HEIC).
2. **«Масштабировать до 25%»:** габариты (ширина и высота) × 0.25, пропорции сохраняются.
3. **Формат вывода:** тот же, что и оригинал (JPEG→JPEG, PNG→PNG, HEIC→HEIC, GIF→GIF).
4. **Точка применения:** в `server.py`, **до** вызова `convert_directory()`. `convert.py` остаётся без зависимости от Pillow (CLI остаётся stdlib-only).
5. **Отсутствие Pillow:** без resize всё работает; при попытке использовать resize без установленных Pillow/pillow-heif → 400 с понятной ошибкой установки.
6. **Степень по умолчанию:** 50% (безопаснее 25%).

## Архитектура (Подход A)

Новые функции в `server.py`, `convert.py` не трогается:

- `has_resize_deps()` — проверка наличия Pillow + pillow-heif.
- `resize_directory(keep_dir, threshold_bytes, scale)` — сканирует папку, уменьшает подходящие картинки на месте.

Вызов в `_handle_convert` **до** `convert_directory()`, только если в запросе включён resize.

## UI настроек (`static/index.html`)

Чекбокс «Уменьшить картинки» с раскрывающимся блоком настроек:

```
☐ Уменьшить картинки                          ← основной чекбокс

  ┌─ раскрывается только когда чекбокс отмечен ─┐
  │  Порог размера:                              │
  │    [ 1  ] (●)КБ  (○)МБ     ← число + toggle  │
  │  Степень уменьшения:                         │
  │    (○)75%  (●)50%  (○)25%   ← radio          │
  │  [ Применить ]  [ Отмена ]                   │
  └─────────────────────────────────────────────┘
```

**Поведение:**
- Чекбокс снят → блок скрыт, в FormData ничего не уходит.
- Чекбокс отмечен → блок раскрывается.
  - **«Применить»** → фиксирует выбранные значения, сворачивает блок (остаётся строка-сводка: «🖼 Порог >1 МБ · масштаб 50%»), кнопка «Конвертировать» активна.
  - **«Отмена»** → сбрасывает настройки к последним применённым (или к умолчанию), сворачивает блок.

**Значения по умолчанию:** порог 1 МБ (число `1`, МБ); степень 50%.

**Поля в FormData** (только когда «Применить» нажато): `resize_enabled=1`, `resize_threshold=<байты>` (считаем на фронте: `значение * 1024` для КБ, `* 1024*1024` для МБ), `resize_scale=<0.75|0.5|0.25>`.

**Защита ввода:** число ≥1; пусто/≤0 → кнопка «Применить» disabled.

## Серверная часть

### Парсинг настроек

Сигнатура возврата `parse_multipart` меняется с `(files, include_trashed)` на `(files, options)`:
```python
def parse_multipart(body, content_type):
    ...
    return files, {
        "include_trashed": False,
        "resize_enabled": False,
        "resize_threshold": 0,   # байты
        "resize_scale": 0.5,     # 0.75/0.5/0.25
    }
```

### Валидация (в `_handle_convert`, после парсинга)

- `resize_enabled` истинно, но `resize_threshold <= 0` или `resize_scale` не в `{0.25, 0.5, 0.75}` → 400 `{error: "Некорректные настройки уменьшения"}`.

### Проверка зависимостей

```python
def has_resize_deps():
    """True, если доступны Pillow и pillow-heif."""
    try:
        import PIL  # noqa
        import pillow_heif  # noqa
        return True
    except ImportError:
        return False
```

Если `resize_enabled` и `not has_resize_deps()` → 400 `{error: "Уменьшение картинок недоступно. Установите Pillow: pip install Pillow pillow-heif"}`.

### `resize_directory()`

```python
def resize_directory(keep_dir, threshold_bytes, scale):
    """Уменьшить картинки в keep_dir крупнее threshold_bytes до scale от габаритов.
    Возвращает dict-отчёт: {scanned, resized, skipped, errors}."""
```

- **Какие файлы:** рекурсивный glob по `*.jpg, *.jpeg, *.png, *.heic, *.gif` (нижний + верхний регистр). Нестандартные расширения игнорируются.
- **Фильтр по размеру:** `os.path.getsize()`. Если `≤ threshold_bytes` → пропустить. Если `>` → масштабировать.
- **Масштабирование (Pillow):**
  ```python
  from PIL import Image
  import pillow_heif
  pillow_heif.register_heif_opener()
  with Image.open(path) as im:
      new_size = (int(im.width * scale), int(im.height * scale))
      im_resized = im.resize(new_size, Image.LANCZOS)
      im_resized.save(path, format=im.format)
  ```
- **Формат сохранения:** `im.format` — JPEG/PNG/HEIC/GIF в исходном формате.

### Точка вызова

```python
keep_root = find_keep_root(tmp)
if not keep_root:
    raise _ClientError("Не найдено ни одного .json файла")

if options["resize_enabled"]:
    resize_report = resize_directory(keep_root, options["resize_threshold"], options["resize_scale"])
else:
    resize_report = {"resized": 0}

out = os.path.join(tmp, "out.enex")
report = convert_directory(keep_root, out, include_trashed=options["include_trashed"])
```

### Заголовки ответа

Добавляется `X-Resized: <count>` (0 если resize выключен). Фронтенд показывает строку «🖼 Уменьшено картинок: N» только если `X-Resized > 0`.

## Edge cases

| Случай | Обработка |
|---|---|
| `resize_enabled` без зависимостей | 400 «Уменьшение картинок недоступно. Установите…» |
| `resize_threshold ≤ 0` или `resize_scale ∉ {0.25,0.5,0.75}` | 400 «Некорректные настройки уменьшения» |
| Картинка ≤ порога | пропускается, оригинал не трогается |
| Картинка битая/не открывается | лог в консоль, счётчик `errors`, продолжаем, оригинал сохраняется |
| Анимированный GIF | сохраняется только первый кадр (ограничение Pillow); упомянем в README |
| HEIC без pillow-heif | `has_resize_deps()` → False → 400 до обработки |
| PNG с прозрачностью | прозрачность сохраняется (LANCZOS + PNG) |
| `resize_enabled=false` | `resize_directory` не вызывается, поведение идентично текущему |

## Отчётность

Фронтенд: `X-Notes`, `X-Attachments` (есть), `X-Resized` (новый). UI сводка успеха:
```
✅ Готово! Обработано 1505 заметок, 191 вложений, 40.7 МБ
🖼 Уменьшено картинок: 87
```
Строка с уменьшением показывается только если `X-Resized > 0`.

## Тестирование (TDD, тот же assert-раннер)

**Unit-тесты в `tests/test_server.py`:**
- `test_has_resize_deps_returns_bool()` — True/False (без assertions на значение).
- `test_parse_multipart_resize_fields()` — FormData с `resize_enabled=1`, `resize_threshold=1048576`, `resize_scale=0.5` → парсится в `options`.
- `test_parse_multipart_resize_disabled_by_default()` — без полей → `resize_enabled=False`.
- `test_resize_directory_skips_small_files()` — PNG 100 КБ при пороге 1 МБ → не трогается. Guard на Pillow.
- `test_resize_directory_resizes_large_file()` — PNG 2000×2000 при пороге 0 байт и scale 0.5 → 1000×1000, формат PNG. Guard на Pillow.
- `test_resize_directory_preserves_format_heic()` — HEIC-фикстура → уменьшается, формат HEIC. Guard на pillow-heif.

**Создание фикстур:** PNG 2000×2000 генерируется на лету через Pillow в `tempfile` (если Pillow есть). HEIC — мини-файл `tests/fixtures/small.heic` (приложен).

**HTTP-интеграционный тест:**
- `test_post_convert_with_resize()` — POST с resize + PNG-фикстурой → 200, `X-Resized > 0`. Guard на Pillow.
- `test_post_convert_resize_without_deps_returns_400()` — monkeypatch `has_resize_deps` → False → POST с resize → 400 про установку. **Проходит без Pillow.**

**Готовность окружения:** тесты с реальным масштабированием требуют Pillow; без него корректно пропускаются (guard). Тест «нет зависимостей → 400» (через monkeypatch) гарантированно проходит без Pillow.

## Не входит в рамки (YAGNI)

- Прогресс-бар по картинкам (синхронная обработка, спиннер suffice).
- Изменение DPI/метаданных.
- Параллельное/многопоточное масштабирование.
- Применение resize в CLI (`convert.py` остаётся stdlib-only).
- Дожим качества JPEG до размера (только габариты × scale).
