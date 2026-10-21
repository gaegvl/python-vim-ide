#!/usr/bin/env bash
# Установка PyIDE в домашний каталог пользователя
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-$HOME/opt/python-vim-ide}"
VIMRC="${HOME}/.vimrc"

mkdir -p "$(dirname "$TARGET")"
if [[ "$ROOT" != "$TARGET" ]]; then
  rm -rf "$TARGET"
  cp -a "$ROOT" "$TARGET"
fi

LINE="source ${TARGET}/vimrc"
if [[ -f "$VIMRC" ]] && grep -Fq "python-vim-ide/vimrc" "$VIMRC"; then
  echo "Уже подключено в $VIMRC"
else
  {
    echo ""
    echo "\" PyIDE — offline Python IDE"
    echo "$LINE"
  } >> "$VIMRC"
  echo "Добавлено в $VIMRC:"
  echo "  $LINE"
fi

echo ""
echo "Проверка:"
vim -Nu NONE -S "${TARGET}/vimrc" -c 'PyIdeHealth' -c 'qa' 2>&1 | tail -n 30 || true
echo ""
echo "Готово. Запустите: vim ${TARGET}/examples/demo.py"
