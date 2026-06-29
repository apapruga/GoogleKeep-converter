#!/bin/bash
# Запуск веб-интерфейса конвертера Google Keep → Apple Notes.
# Двойной клик в Finder открывает Terminal и запускает сервер.
# Остановка: Ctrl+C в окне Terminal.

# Переходим в папку, где лежит этот .command файл (независимо от того,
# откуда его запустили — рабочий каталог при двойном клике обычно $HOME).
cd "$(dirname "$0")" || {
    echo "Не удалось перейти в папку проекта."
    echo "Нажмите Enter для закрытия..."
    read
    exit 1
}

echo "=== Конвертер Google Keep → Apple Notes (.enex) ==="
echo "Папка проекта: $(pwd)"
echo

# Проверяем python3.
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 не найден."
    echo "   Установите Python 3: https://www.python.org/downloads/  или  brew install python"
    echo
    echo "Нажмите Enter для закрытия..."
    read
    exit 1
fi

echo "Python: $(python3 --version 2>&1)"

# Подсказка про опциональную фичу уменьшения картинок.
if python3 -c "import PIL, pillow_heif" 2>/dev/null; then
    echo "Pillow + pillow-heif: установлены (уменьшение картинок доступно)"
else
    echo "Pillow/pillow-heif: НЕ установлены (уменьшение картинок недоступно)."
    echo "   Для уменьшения картинок выполните:  pip3 install Pillow pillow-heif"
fi
echo

echo "Запускаю сервер... Браузер откроется автоматически."
echo "Остановка сервера: Ctrl+C"
echo

python3 server.py

# Если сервер завершился (не по Ctrl+C, а из-за ошибки) — оставляем окно,
# чтобы пользователь увидел сообщение.
echo
echo "Сервер остановлен. Нажмите Enter для закрытия окна..."
read
