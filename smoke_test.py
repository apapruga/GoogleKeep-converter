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
