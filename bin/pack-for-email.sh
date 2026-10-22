#!/usr/bin/env bash
# Упаковка vendor/wheels (и опционально всего пакета) в .txt для отправки почтой.
# На машине С интернетом / с уже скачанным репо:
#   ./bin/pack-for-email.sh
#   ./bin/pack-for-email.sh --full          # весь python-vim-ide
#   ./bin/pack-for-email.sh --chunk 2       # куски по ~2 МБ (лимиты почты)
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
    --chunk) CHUNK_MB="${2:-2}"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,10p' "$0"
      exit 0
      ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

mkdir -p "$OUT"
rm -f "$OUT"/pyide-mail-*.txt "$OUT"/pyide-mail-*.sha256 "$OUT"/MANIFEST.txt

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

if [[ "$FULL" -eq 1 ]]; then
  echo "Упаковываю весь каталог python-vim-ide (без .git)..."
  tar -C "$ROOT/.." \
    --exclude='python-vim-ide/.git' \
    --exclude='python-vim-ide/dist' \
    -czf "$STAGE/payload.tgz" python-vim-ide
  KIND=full
elif [[ "$MINIMAL" -eq 1 ]]; then
  echo "Упаковываю минимум: jedi + parso (дополнение/навигация)..."
  mkdir -p "$STAGE/vendor/wheels"
  copied=0
  for f in "$ROOT"/vendor/wheels/jedi-*.whl "$ROOT"/vendor/wheels/parso-*.whl; do
    [[ -f "$f" ]] || continue
    cp -a "$f" "$STAGE/vendor/wheels/"
    copied=1
  done
  if [[ "$copied" -eq 0 ]]; then
    echo "Нет jedi/parso wheels. Сначала: ./bin/fetch-wheels.sh"
    exit 1
  fi
  tar -C "$STAGE" -czf "$STAGE/payload.tgz" vendor/wheels
  KIND=jedi
else
  echo "Упаковываю vendor/wheels..."
  if ! ls "$ROOT/vendor/wheels"/*.whl >/dev/null 2>&1; then
    echo "Нет wheels. Сначала: ./bin/fetch-wheels.sh"
    exit 1
  fi
  tar -C "$ROOT" -czf "$STAGE/payload.tgz" vendor/wheels
  KIND=wheels
fi

SIZE=$(wc -c < "$STAGE/payload.tgz" | tr -d ' ')
SUM=$(sha256sum "$STAGE/payload.tgz" | awk '{print $1}')
echo "payload: ${SIZE} bytes, sha256=$SUM"

# Один base64-файл (безопасное расширение .txt)
B64="$OUT/pyide-mail-${KIND}.b64.txt"
{
  echo "# PyIDE email pack"
  echo "# kind=$KIND"
  echo "# bytes=$SIZE"
  echo "# sha256=$SUM"
  echo "# restore: python3 unpack-from-email.py pyide-mail-${KIND}.b64.txt"
  echo "# ---BEGIN---"
  base64 < "$STAGE/payload.tgz"
  echo "# ---END---"
} > "$B64"

echo "$SUM  payload.tgz" > "$OUT/pyide-mail-${KIND}.sha256"
cat > "$OUT/MANIFEST.txt" <<EOF
PyIDE mail pack
kind=$KIND
bytes=$SIZE
sha256=$SUM
created=$(date -u +%Y-%m-%dT%H:%M:%SZ)

Как отправить:
  1) Прикрепите к письму файлы из этой папки с расширением .txt
  2) Если письмо режет большие вложения — пересоберите с --chunk 2
  3) На Astra сохраните вложения и запустите unpack-from-email.py

Восстановление на Astra:
  python3 unpack-from-email.py pyide-mail-${KIND}.b64.txt
  # или, если куски:
  python3 unpack-from-email.py pyide-mail-${KIND}.part*.b64.txt
EOF

# Копируем распаковщик рядом (тоже .txt — переименуете в .py на месте)
cp "$ROOT/bin/unpack-from-email.py" "$OUT/unpack-from-email.py.txt"
# Инструкция
cp "$ROOT/docs/EMAIL_TRANSFER.md" "$OUT/README.txt" 2>/dev/null || true

if [[ "$CHUNK_MB" -gt 0 ]]; then
  echo "Режу на куски по ${CHUNK_MB} МБ..."
  # режем только тело base64 (без заголовка) — проще резать весь файл через split
  rm -f "$OUT"/pyide-mail-"${KIND}".part*.b64.txt
  # split by lines approximating size: ~76 chars/line base64
  LINES_PER=$(( CHUNK_MB * 1024 * 1024 / 76 ))
  [[ "$LINES_PER" -lt 100 ]] && LINES_PER=5000
  # Extract body
  BODY="$STAGE/body.b64"
  sed -n '/^# ---BEGIN---$/,/^# ---END---$/p' "$B64" | sed '1d;$d' > "$BODY"
  split -l "$LINES_PER" -d -a 3 "$BODY" "$STAGE/part-"
  n=0
  for f in "$STAGE"/part-*; do
    part=$(printf '%03d' "$n")
    {
      echo "# PyIDE email pack PART $part"
      echo "# kind=$KIND"
      echo "# sha256=$SUM"
      echo "# bytes=$SIZE"
      echo "# part=$part"
      echo "# ---BEGIN---"
      cat "$f"
      echo "# ---END---"
    } > "$OUT/pyide-mail-${KIND}.part${part}.b64.txt"
    n=$((n + 1))
  done
  echo "parts=$n" >> "$OUT/MANIFEST.txt"
  echo "Создано частей: $n"
  # основной цельный можно оставить или удалить — оставляем
fi

echo ""
echo "Готово → $OUT"
ls -lh "$OUT"
echo ""
echo "Отправьте почтой *.txt из $OUT"
echo "На Astra: python3 unpack-from-email.py.txt  (после переименования в .py)"
