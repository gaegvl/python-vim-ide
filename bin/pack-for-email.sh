#!/bin/bash
# Упаковка wheels в .txt для почты Astra.

# Фильтр режет: «опасные» расширения и файлы, где 1-я строка начинается с #!
# Не режет по размеру. Поэтому: только *.txt, первая строка БЕЗ #!
#
#   ./bin/pack-for-email.sh --minimal
#   ./bin/pack-for-email.sh --full
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${PYIDE_MAIL_OUT:-$ROOT/dist/email}"
CHUNK_MB=0
FULL=0
MINIMAL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) FULL=1; shift ;;
    --minimal|--jedi) MINIMAL=1; shift ;;
    --chunk) CHUNK_MB="${2:-0}"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

mkdir -p "$OUT"
rm -f "$OUT"/pyide-*.txt "$OUT"/MANIFEST.txt

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

if [[ "$FULL" -eq 1 ]]; then
  echo "Упаковываю весь python-vim-ide..."
  tar -C "$ROOT/.." \
    --exclude='python-vim-ide/.git' \
    --exclude='python-vim-ide/dist' \
    -czf "$STAGE/payload.tgz" python-vim-ide
  KIND=full
elif [[ "$MINIMAL" -eq 1 ]]; then
  echo "Упаковываю минимум: jedi + parso..."
  mkdir -p "$STAGE/vendor/wheels"
  shopt -s nullglob
  local_files=("$ROOT"/vendor/wheels/jedi-*.whl "$ROOT"/vendor/wheels/parso-*.whl)
  shopt -u nullglob
  if [[ ${#local_files[@]} -eq 0 ]]; then
    echo "Нет jedi/parso wheels. Сначала: ./bin/fetch-wheels.sh"
    exit 1
  fi
  for f in "${local_files[@]}"; do
    cp -a "$f" "$STAGE/vendor/wheels/"
  done
  tar -C "$STAGE" -czf "$STAGE/payload.tgz" vendor/wheels
  KIND=jedi
else
  echo "Упаковываю vendor/wheels..."
  shopt -s nullglob
  all_wheels=("$ROOT"/vendor/wheels/*.whl)
  shopt -u nullglob
  if [[ ${#all_wheels[@]} -eq 0 ]]; then
    echo "Нет wheels. Сначала: ./bin/fetch-wheels.sh"
    exit 1
  fi
  tar -C "$ROOT" -czf "$STAGE/payload.tgz" vendor/wheels
  KIND=wheels
fi

SIZE=$(wc -c < "$STAGE/payload.tgz" | tr -d ' ')
SUM=$(sha256sum "$STAGE/payload.tgz" | awk '{print $1}')
echo "payload: ${SIZE} bytes, sha256=$SUM"

# Важно: первая строка НЕ должна быть #!  (фильтр почты)
# Имя файла — только .txt (без .py / .whl / .sh в имени)
write_b64_file() {
  local dest="$1"
  local part_label="${2:-}"
  {
    echo "PyIDE-mail-pack kind=${KIND} sha256=${SUM} bytes=${SIZE}${part_label}"
    echo "RESTORE: python3 unpack-pyide.txt pyide-${KIND}-*.txt"
    echo "BEGIN"
    if [[ -n "${3:-}" ]]; then
      cat "$3"
    else
      base64 < "$STAGE/payload.tgz"
    fi
    echo "END"
  } > "$dest"
  # страховка: первая строка не shebang
  local first
  first=$(head -n1 "$dest")
  if [[ "$first" == \#!* ]]; then
    echo "BUG: shebang in $dest" >&2
    exit 3
  fi
}

B64="$OUT/pyide-${KIND}.txt"
write_b64_file "$B64"

# Распаковщик: только .txt в имени, без #! в первой строке
cp "$ROOT/bin/unpack-from-email.py" "$OUT/unpack-pyide.txt"
if head -n1 "$OUT/unpack-pyide.txt" | grep -q '^#!'; then
  echo "BUG: unpacker has shebang — почта заблокирует" >&2
  exit 3
fi

cat > "$OUT/MANIFEST.txt" <<EOF
PyIDE mail pack (Astra-safe)
kind=$KIND
bytes=$SIZE
sha256=$SUM
created=$(date -u +%Y-%m-%dT%H:%M:%SZ)

Правила вашего фильтра:
  - не слать .py / .whl / .sh / .exe (и похожие)
  - не слать файлы, у которых 1-я строка начинается с #!
  - размер не важен → можно слать один большой .txt

Что отправить (все с расширением .txt):
  - unpack-pyide.txt
  - pyide-${KIND}.txt
  - (если есть) pyide-${KIND}-part000.txt ...

На Astra:
  python3 unpack-pyide.txt pyide-${KIND}.txt
  # или куски:
  python3 unpack-pyide.txt pyide-${KIND}-part*.txt
EOF

if [[ "$CHUNK_MB" -gt 0 ]]; then
  echo "Режу на куски по ${CHUNK_MB} МБ..."
  rm -f "$OUT"/pyide-"${KIND}"-part*.txt
  LINES_PER=$(( CHUNK_MB * 1024 * 1024 / 76 ))
  [[ "$LINES_PER" -lt 100 ]] && LINES_PER=5000
  BODY="$STAGE/body.b64"
  # тело между BEGIN/END
  awk 'BEGIN{p=0} /^BEGIN$/{p=1;next} /^END$/{p=0;next} p' "$B64" > "$BODY"
  split -l "$LINES_PER" -d -a 3 "$BODY" "$STAGE/part-"
  n=0
  for f in "$STAGE"/part-*; do
    part=$(printf '%03d' "$n")
    write_b64_file "$OUT/pyide-${KIND}-part${part}.txt" " part=${part}" "$f"
    n=$((n + 1))
  done
  echo "parts=$n" >> "$OUT/MANIFEST.txt"
  # цельный файл > лимита почты (часто 25 МБ) — не отправлять
  rm -f "$B64"
  echo "Создано частей: $n (цельный файл удалён — шлите только part*.txt)"
fi

echo ""
echo "Готово → $OUT"
ls -lh "$OUT"
echo ""
echo "Отправьте ТОЛЬКО *.txt (без #! в первой строке)."
if [[ "$CHUNK_MB" -gt 0 ]]; then
  echo "На Astra: python3 unpack-pyide.txt pyide-${KIND}-part*.txt"
else
  echo "На Astra: python3 unpack-pyide.txt pyide-${KIND}.txt"
  echo "Если письмо > 25 МБ:  ./bin/pack-for-email.sh --chunk 20"
fi
