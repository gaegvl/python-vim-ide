#!/usr/bin/env bash
# Полная установка PyIDE: Vim-конфиг + офлайн Python-инструменты
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
touch "$VIMRC"
if grep -Fq "python-vim-ide/vimrc" "$VIMRC" 2>/dev/null; then
  echo "Vimrc уже подключает PyIDE"
else
  {
    echo ""
    echo "\" PyIDE — offline Python IDE"
    echo "$LINE"
  } >> "$VIMRC"
  echo "Добавлено в $VIMRC"
fi

# Инструменты из vendor/wheels
if [[ -d "$TARGET/vendor/wheels" ]] && ls "$TARGET/vendor/wheels"/*.whl >/dev/null 2>&1; then
  echo "Ставлю Python-инструменты офлайн..."
  PYIDE_VENV="${PYIDE_VENV:-$HOME/.local/share/pyide/venv}" \
    bash "$TARGET/bin/install-tools.sh" || echo "Предупреждение: часть tools не установилась (другая платформа/версия Python)"
else
  echo "vendor/wheels пуст — только Vim-плагины. На машине с сетью: bin/fetch-wheels.sh"
fi

# Шаблон .gitignore для проектов
mkdir -p "$HOME/.local/share/pyide"
cp -f "$TARGET/templates/project.gitignore" "$HOME/.local/share/pyide/project.gitignore" 2>/dev/null || true

echo ""
echo "=== Установка завершена ==="
echo "  Пакет:  $TARGET"
echo "  Vimrc:  $LINE"
echo "  Tools:  ~/.local/share/pyide/venv"
echo ""
echo "Запуск:  vim $TARGET/examples/demo.py"
echo "Проверка: vim -c 'PyIdeHealth' -c 'qa'"
echo "Справка:  в Vim нажмите <Space>?"
