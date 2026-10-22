#!/bin/bash
# Офлайн-установка Python-инструментов IDE из vendor/wheels
# На Astra запускайте так (не ./script — там может не быть /usr/bin/env):
#   bash bin/install-tools.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WHEELS="$ROOT/vendor/wheels"
VENV="${PYIDE_VENV:-$HOME/.local/share/pyide/venv}"
TARGET="${PYIDE_TARGET:-$HOME/.local/share/pyide/pyroot}"

if [[ ! -d "$WHEELS" ]]; then
  echo "Нет каталога $WHEELS"
  exit 1
fi
shopt -s nullglob
wheel_files=("$WHEELS"/*.whl)
shopt -u nullglob
if [[ ${#wheel_files[@]} -eq 0 ]]; then
  echo "Нет wheel-файлов в $WHEELS"
  echo "Сначала распакуйте почтовый пакет: python3 unpack-pyide.txt pyide-wheels-part*.txt"
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
    echo "  SKIP $pkg (нет подходящего wheel для этой платформы/Python)"
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

if [[ "$MODE" == "target" ]]; then
  export PYTHONPATH="$TARGET${PYTHONPATH:+:$PYTHONPATH}"
  if [[ -d "$TARGET/bin" ]]; then
    BIN="$TARGET/bin"
  fi
fi

# Astra: часто нет /usr/bin/env — чиним shebang у console_scripts (ruff, pytest, …)
fix_shebangs() {
  local dir="$1"
  local py="$2"
  [[ -d "$dir" ]] || return 0
  local f first
  for f in "$dir"/*; do
    [[ -f "$f" && -x "$f" ]] || continue
    first=$(head -n1 "$f" 2>/dev/null || true)
    case "$first" in
      '#!/usr/bin/env'*|'#! /usr/bin/env'*)
        # заменяем на прямой путь к python venv/системы
        sed -i "1c#!${py}" "$f" 2>/dev/null || \
          { printf '%s\n' "#!${py}" > "$f.tmp" && tail -n +2 "$f" >> "$f.tmp" && mv "$f.tmp" "$f" && chmod +x "$f"; }
        echo "  shebang fix: $(basename "$f")"
        ;;
    esac
  done
}
if [[ "$MODE" == "venv" ]]; then
  fix_shebangs "$BIN" "$PYBIN"
else
  fix_shebangs "$BIN" "$(command -v "$PY")"
fi

echo ""
echo "Проверка (через python -c / python -m, без shebang-скриптов):"
if [[ "$MODE" == "venv" ]]; then
  "$PYBIN" -c "import jedi; print('  jedi', jedi.__version__)" 2>/dev/null || echo "  jedi НЕ установлен"
  "$PYBIN" -c "import pytest; print('  pytest', pytest.__version__)" 2>/dev/null || echo "  pytest нет"
  # ruff: не вызываем bin/ruff (там #!/usr/bin/env — на Astra может не быть env)
  if "$PYBIN" -c "import ruff" 2>/dev/null; then
    echo "  ruff import OK"
  elif [[ -x "$BIN/ruff" ]]; then
    echo "  ruff binary есть ($BIN/ruff)"
  else
    echo "  ruff нет"
  fi
else
  PYTHONPATH="$TARGET" "$PY" -c "import jedi; print('  jedi', jedi.__version__)" 2>/dev/null || echo "  jedi НЕ установлен"
  PYTHONPATH="$TARGET" "$PY" -c "import pytest; print('  pytest', pytest.__version__)" 2>/dev/null || echo "  pytest нет"
  echo "  (ruff/isort — смотрите $BIN после установки)"
fi

MARKER="$HOME/.local/share/pyide/env.sh"
mkdir -p "$(dirname "$MARKER")"
if [[ "$MODE" == "venv" ]]; then
  cat > "$MARKER" <<EOF
# без shebang — source этот файл
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

echo "$MODE" > "$HOME/.local/share/pyide/install-mode"
[[ "$MODE" == "target" ]] && echo "$TARGET" > "$HOME/.local/share/pyide/pythonpath" || true
[[ "$MODE" == "venv" ]] && echo "$PYBIN" > "$HOME/.local/share/pyide/python" || true

echo ""
echo "Готово. Опционально: source $MARKER"
echo "В Vim: :PyIdeHealth"
