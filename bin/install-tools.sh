#!/bin/bash
# Офлайн-установка Python-инструментов IDE из vendor/wheels
#
#   bash bin/install-tools.sh
#
# Если «Отказано в доступе» — ставьте в домашний каталог:
#   PYIDE_VENV=$HOME/pyide/venv bash bin/install-tools.sh
set +e
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WHEELS="$ROOT/vendor/wheels"

die() { echo "ОШИБКА: $*" >&2; exit 1; }

need_writable_dir() {
  local d="$1"
  mkdir -p "$d" 2>/dev/null || return 1
  local t="$d/.pyide_write_test_$$"
  if touch "$t" 2>/dev/null; then
    rm -f "$t"
    return 0
  fi
  return 1
}

# Куда ставить: сначала явные переменные, потом ~/.local, потом ~/pyide
BASE=""
for cand in \
  "${PYIDE_HOME:-}" \
  "$HOME/.local/share/pyide" \
  "$HOME/pyide" \
  "/tmp/pyide-$USER"
do
  [[ -n "$cand" ]] || continue
  if need_writable_dir "$cand"; then
    BASE="$cand"
    break
  fi
done
[[ -n "$BASE" ]] || die "Нет ни одной доступной для записи папки (\$HOME/.local, \$HOME/pyide, /tmp). Проверьте права на домашний каталог."

VENV="${PYIDE_VENV:-$BASE/venv}"
TARGET="${PYIDE_TARGET:-$BASE/pyroot}"
MARKER="$BASE/env.sh"

echo "Каталог установки: $BASE"
echo "Wheels: $WHEELS"

[[ -d "$WHEELS" ]] || die "Нет каталога $WHEELS
Распакуйте почтовый пакет в корень PyIDE, чтобы появился vendor/wheels/"

# читаемость wheels
shopt -s nullglob
wheel_files=("$WHEELS"/*.whl)
shopt -u nullglob
[[ ${#wheel_files[@]} -gt 0 ]] || die "В $WHEELS нет .whl файлов"
if [[ ! -r "${wheel_files[0]}" ]]; then
  die "Нет прав на чтение $WHEELS (Отказано в доступе).
Сделайте:  chmod -R u+rX \"$WHEELS\"
или скопируйте wheels к себе:  cp -a \"$WHEELS\" \"\$HOME/pyide-wheels\" и
  WHEELS=\$HOME/pyide-wheels bash bin/install-tools.sh"
fi

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null || die "python3 не найден в PATH"

install_one() {
  local pkg="$1"
  shift
  if "$@"; then
    echo "  OK  $pkg"
  else
    echo "  SKIP $pkg (нет подходящего wheel / ошибка pip)"
  fi
  return 0
}

MODE=""
PYBIN=""
BIN=""

# 1) пробуем venv в доступном месте
rm -rf "$VENV" 2>/dev/null || true
if need_writable_dir "$(dirname "$VENV")" && "$PY" -m venv "$VENV" 2>"$BASE/venv-error.log"; then
  MODE=venv
  # shellcheck disable=SC1091
  # activate может требовать bash
  . "$VENV/bin/activate"
  python -m pip install -q --upgrade pip >/dev/null 2>&1 || true
  PIP=(python -m pip install -q --no-index --find-links="$WHEELS")
  BIN="$VENV/bin"
  PYBIN="$VENV/bin/python"
  echo "Режим: venv ($VENV)"
else
  echo "venv не создался (см. $BASE/venv-error.log) — ставлю в --target"
  MODE=target
  need_writable_dir "$TARGET" || die "Не могу писать в $TARGET (Отказано в доступе)"
  mkdir -p "$TARGET" "$TARGET/bin"
  PIP=("$PY" -m pip install -q --no-index --find-links="$WHEELS" --target "$TARGET")
  BIN="$TARGET/bin"
  PYBIN="$PY"
  echo "Режим: --target ($TARGET)"
fi

echo "Ставлю пакеты..."
for pkg in jedi parso ruff pytest isort debugpy; do
  install_one "$pkg" "${PIP[@]}" "$pkg"
done

if [[ "$MODE" == "target" ]]; then
  export PYTHONPATH="$TARGET${PYTHONPATH:+:$PYTHONPATH}"
fi

# Чиним shebang без /usr/bin/env (и без падения при отказе в доступе)
fix_shebangs() {
  local dir="$1"
  local py="$2"
  [[ -d "$dir" ]] || return 0
  local f first
  for f in "$dir"/*; do
    [[ -f "$f" ]] || continue
    # бинарники (ruff) не трогаем
    if grep -Iq . "$f" 2>/dev/null; then
      :
    else
      continue
    fi
    first=$(head -n1 "$f" 2>/dev/null | tr -d '\000' || true)
    case "$first" in
      '#!/usr/bin/env'*|'#! /usr/bin/env'*)
        if [[ ! -w "$f" ]]; then
          echo "  shebang skip (нет записи): $(basename "$f")"
          continue
        fi
        {
          printf '%s\n' "#!${py}"
          tail -n +2 "$f"
        } > "$f.tmp" 2>/dev/null && mv "$f.tmp" "$f" && chmod u+x "$f" 2>/dev/null
        echo "  shebang fix: $(basename "$f")"
        ;;
    esac
  done
}
fix_shebangs "$BIN" "$PYBIN"

echo ""
echo "Проверка:"
if [[ "$MODE" == "venv" ]]; then
  "$PYBIN" -c "import jedi; print('  jedi', jedi.__version__)" 2>/dev/null || echo "  jedi НЕ установлен"
  "$PYBIN" -c "import pytest; print('  pytest', pytest.__version__)" 2>/dev/null || echo "  pytest нет"
else
  PYTHONPATH="$TARGET" "$PY" -c "import jedi; print('  jedi', jedi.__version__)" 2>/dev/null || echo "  jedi НЕ установлен"
  PYTHONPATH="$TARGET" "$PY" -c "import pytest; print('  pytest', pytest.__version__)" 2>/dev/null || echo "  pytest нет"
fi

mkdir -p "$BASE" 2>/dev/null || true
if [[ "$MODE" == "venv" ]]; then
  cat > "$MARKER" <<EOF
export PATH="$BIN:\$PATH"
export PYIDE_PYTHON="$PYBIN"
EOF
  echo "venv" > "$BASE/install-mode"
  echo "$PYBIN" > "$BASE/python"
else
  cat > "$MARKER" <<EOF
export PYTHONPATH="$TARGET\${PYTHONPATH:+:\$PYTHONPATH}"
export PATH="$BIN:\$PATH"
export PYIDE_PYTHON="$PY"
export PYIDE_PYTHONPATH="$TARGET"
EOF
  echo "target" > "$BASE/install-mode"
  echo "$TARGET" > "$BASE/pythonpath"
fi 2>/dev/null || echo "Не удалось записать $MARKER (не критично)"

# Симлинк-совместимость со старым путём для Vim (~/.local/share/pyide)
LEGACY="$HOME/.local/share/pyide"
if [[ "$BASE" != "$LEGACY" ]]; then
  if need_writable_dir "$(dirname "$LEGACY")" 2>/dev/null; then
    mkdir -p "$LEGACY" 2>/dev/null || true
    # подсказки для autoload pyide#venv
    [[ "$MODE" == "venv" ]] && echo "$PYBIN" > "$LEGACY/python" 2>/dev/null || true
    [[ "$MODE" == "target" ]] && echo "$TARGET" > "$LEGACY/pythonpath" 2>/dev/null || true
  fi
fi

echo ""
echo "Готово."
echo "  source $MARKER"
echo "  В Vim: :PyIdeHealth"
echo ""
echo "Если снова «Отказано в доступе»:"
echo "  ls -la \"$WHEELS\""
echo "  chmod -R u+rwX \"$ROOT/vendor\""
echo "  PYIDE_HOME=\$HOME/pyide bash bin/install-tools.sh"
