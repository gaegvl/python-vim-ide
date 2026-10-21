#!/usr/bin/env bash
# Офлайн-установка Python-инструментов IDE из vendor/wheels
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WHEELS="$ROOT/vendor/wheels"
VENV="${PYIDE_VENV:-$HOME/.local/share/pyide/venv}"
TARGET="${PYIDE_TARGET:-$HOME/.local/share/pyide/pyroot}"

if [[ ! -d "$WHEELS" ]] || ! ls "$WHEELS"/*.whl >/dev/null 2>&1; then
  echo "Нет wheel-файлов в $WHEELS"
  echo "На машине с интернетом: $ROOT/bin/fetch-wheels.sh"
  exit 1
fi

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null || { echo "python3 не найден"; exit 1; }

install_one() {
  local pkg="$1"
  shift
  if "$@"; then
    echo "  OK  $pkg"
  else
    echo "  SKIP $pkg (нет подходящего wheel)"
  fi
  return 0
}

MODE=""
if "$PY" -m venv "$VENV" 2>/dev/null; then
  MODE=venv
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  python -m pip install -q --upgrade pip 2>/dev/null || true
  PIP=(python -m pip install -q --no-index --find-links="$WHEELS")
  BIN="$VENV/bin"
  PYBIN="$VENV/bin/python"
  echo "Режим: venv ($VENV)"
else
  MODE=target
  mkdir -p "$TARGET"
  PIP=("$PY" -m pip install -q --no-index --find-links="$WHEELS" --target "$TARGET")
  BIN="$TARGET/bin"
  mkdir -p "$BIN"
  PYBIN="$PY"
  echo "Режим: --target ($TARGET)  [python3-venv недоступен]"
fi

echo "Ставлю пакеты из $WHEELS ..."
for pkg in jedi parso ruff pytest isort debugpy; do
  install_one "$pkg" "${PIP[@]}" "$pkg"
done

# В режиме target добавим обёртки в PATH
if [[ "$MODE" == "target" ]]; then
  export PYTHONPATH="$TARGET${PYTHONPATH:+:$PYTHONPATH}"
  # console scripts могут лежать в TARGET/bin
  if [[ -d "$TARGET/bin" ]]; then
    BIN="$TARGET/bin"
  fi
fi

echo ""
echo "Проверка:"
if [[ "$MODE" == "venv" ]]; then
  "$PYBIN" -c "import jedi; print('  jedi', jedi.__version__)" 2>/dev/null || echo "  jedi НЕ установлен"
  command -v "$BIN/ruff" >/dev/null && echo "  ruff $($BIN/ruff --version)" || echo "  ruff нет"
  "$PYBIN" -c "import pytest; print('  pytest', pytest.__version__)" 2>/dev/null || echo "  pytest нет"
else
  PYTHONPATH="$TARGET" "$PY" -c "import jedi; print('  jedi', jedi.__version__)" 2>/dev/null || echo "  jedi НЕ установлен"
  PYTHONPATH="$TARGET" "$PY" -c "import pytest; print('  pytest', pytest.__version__)" 2>/dev/null || echo "  pytest нет"
  [[ -x "$TARGET/bin/ruff" ]] && echo "  ruff $($TARGET/bin/ruff --version)" || echo "  ruff нет"
fi

MARKER="$HOME/.local/share/pyide/env.sh"
mkdir -p "$(dirname "$MARKER")"
if [[ "$MODE" == "venv" ]]; then
  cat > "$MARKER" <<EOF
export PATH="$BIN:\$PATH"
export PYIDE_PYTHON="$PYBIN"
EOF
else
  cat > "$MARKER" <<EOF
export PYTHONPATH="$TARGET\${PYTHONPATH:+:\$PYTHONPATH}"
export PATH="$BIN:\$PATH"
export PYIDE_PYTHON="$PY"
export PYIDE_PYTHONPATH="$TARGET"
EOF
fi

# Для Vim: маленький хинт-файл
echo "$MODE" > "$HOME/.local/share/pyide/install-mode"
[[ "$MODE" == "target" ]] && echo "$TARGET" > "$HOME/.local/share/pyide/pythonpath" || true
[[ "$MODE" == "venv" ]] && echo "$PYBIN" > "$HOME/.local/share/pyide/python" || true

echo ""
echo "Готово. Опционально: source $MARKER"
