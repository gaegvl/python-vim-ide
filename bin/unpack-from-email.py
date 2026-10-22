"""PyIDE unpack for email. Run: python3 unpack-from-email.py pyide-*.txt

Собрать payload из .txt вложений почты (без shebang — почтовый фильтр
блокирует файлы, у которых первая строка начинается с #!).

Примеры:
  python3 unpack-pyide.txt pyide-jedi.txt
  python3 unpack-pyide.txt pyide-jedi-part*.txt
  python3 unpack-from-email.py --dest ~/opt pyide-full.txt
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import re
import sys
import tarfile
from pathlib import Path


def read_b64_parts(paths: list[Path]) -> tuple[bytes, dict[str, str]]:
    meta: dict[str, str] = {}
    chunks: list[tuple[str, str]] = []

    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        part_id = "000"
        body_lines: list[str] = []
        in_body = False

        # header: PyIDE-mail-pack kind=... sha256=... bytes=... part=...
        first = text.splitlines()[0] if text else ""
        for key in ("kind", "sha256", "bytes", "part"):
            m = re.search(rf"\b{key}=([^\s]+)", first)
            if m:
                meta[key] = m.group(1)
                if key == "part":
                    part_id = m.group(1)

        for line in text.splitlines():
            s = line.strip()
            # new format
            if s == "BEGIN" or s == "# ---BEGIN---":
                in_body = True
                continue
            if s == "END" or s == "# ---END---":
                in_body = False
                continue
            # old header meta
            if s.startswith("# kind="):
                meta["kind"] = s.split("=", 1)[1].strip()
            elif s.startswith("# sha256="):
                meta["sha256"] = s.split("=", 1)[1].strip()
            elif s.startswith("# bytes="):
                meta["bytes"] = s.split("=", 1)[1].strip()
            elif s.startswith("# part="):
                part_id = s.split("=", 1)[1].strip()
                meta["part"] = part_id
            elif in_body:
                if s and not s.startswith("#"):
                    body_lines.append(s)

        chunks.append((part_id, "".join(body_lines)))

    chunks.sort(key=lambda x: x[0])
    b64 = "".join(c for _, c in chunks)
    try:
        data = base64.b64decode(b64, validate=False)
    except Exception as e:
        raise SystemExit(f"base64 decode failed: {e}") from e
    return data, meta


def main() -> int:
    ap = argparse.ArgumentParser(description="Unpack PyIDE email .txt packs")
    ap.add_argument("files", nargs="+", help="pyide-*.txt files (parts ok)")
    ap.add_argument("--dest", default=".", help="куда распаковать")
    ap.add_argument("--keep-tar", action="store_true")
    args = ap.parse_args()

    paths: list[Path] = []
    for pattern in args.files:
        p = Path(pattern)
        if p.exists():
            paths.append(p)
        else:
            paths.extend(sorted(Path(".").glob(pattern)))
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    if not uniq:
        print("Нет входных файлов", file=sys.stderr)
        return 1

    # не распаковывать сам скрипт, если попал в glob
    uniq = [p for p in uniq if p.name not in {"unpack-pyide.txt", "unpack-from-email.py", "MANIFEST.txt"}]
    if not uniq:
        print("Нет файлов данных (только unpack/manifest?)", file=sys.stderr)
        return 1

    data, meta = read_b64_parts(uniq)
    digest = hashlib.sha256(data).hexdigest()
    print(f"decoded {len(data)} bytes, sha256={digest}")
    if meta.get("sha256") and meta["sha256"] != digest:
        print(
            f"WARNING: sha256 mismatch!\n  expected {meta['sha256']}\n  got      {digest}",
            file=sys.stderr,
        )
        return 2

    dest = Path(args.dest).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    tar_path = dest / "pyide-payload.tgz"
    tar_path.write_bytes(data)
    print(f"wrote {tar_path}")

    with tarfile.open(tar_path, "r:gz") as tf:
        try:
            tf.extractall(dest, filter="data")
        except TypeError:
            tf.extractall(dest)

    if not args.keep_tar:
        tar_path.unlink(missing_ok=True)

    print(f"unpacked into {dest}")
    print("Дальше:")
    print("  bash bin/install.sh            # полный пакет")
    print("  bash bin/install-tools.sh      # только vendor/wheels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
