#!/bin/bash
# Запускать на машине С интернетом — наполняет vendor/wheels для Astra
# Запуск: bash bin/fetch-wheels.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/vendor/wheels"
mkdir -p "$DEST"

PYVER="${1:-}"
ARGS=(download -d "$DEST")
if [[ -n "$PYVER" ]]; then
  ARGS+=(--python-version "$PYVER")
fi

echo "Качаю IDE-зависимости в $DEST ..."
python3 -m pip "${ARGS[@]}" jedi parso
python3 -m pip "${ARGS[@]}" --only-binary=:all: ruff || \
  python3 -m pip download -d "$DEST" ruff
python3 -m pip "${ARGS[@]}" pytest pluggy iniconfig packaging
python3 -m pip "${ARGS[@]}" isort || true
python3 -m pip "${ARGS[@]}" --only-binary=:all: debugpy || \
  python3 -m pip download -d "$DEST" debugpy || true

echo ""
du -sh "$DEST"
ls -lh "$DEST"
echo "Скопируйте весь каталог python-vim-ide (с vendor/) на Astra."
