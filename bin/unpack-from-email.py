#!/usr/bin/env python3
"""Собрать payload.tgz из .b64.txt вложений почты и распаковать.

Примеры:
  python3 unpack-from-email.py pyide-mail-wheels.b64.txt
  python3 unpack-from-email.py pyide-mail-wheels.part*.b64.txt
  python3 unpack-from-email.py --dest ~/opt pyide-mail-full.b64.txt
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import sys
import tarfile
from pathlib import Path


def read_b64_parts(paths: list[Path]) -> tuple[bytes, dict[str, str]]:
    meta: dict[str, str] = {}
    chunks: list[tuple[str, str]] = []  # (part_id, b64)

    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        part_id = "000"
        body_lines: list[str] = []
        in_body = False
        for line in text.splitlines():
            if line.startswith("# kind="):
                meta["kind"] = line.split("=", 1)[1].strip()
            elif line.startswith("# sha256="):
                meta["sha256"] = line.split("=", 1)[1].strip()
            elif line.startswith("# bytes="):
                meta["bytes"] = line.split("=", 1)[1].strip()
            elif line.startswith("# part="):
                part_id = line.split("=", 1)[1].strip()
            elif line.strip() == "# ---BEGIN---":
                in_body = True
                continue
            elif line.strip() == "# ---END---":
                in_body = False
                continue
            elif in_body:
                # skip blank / comment
                s = line.strip()
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
    ap = argparse.ArgumentParser(description="Unpack PyIDE email .b64.txt packs")
    ap.add_argument("files", nargs="+", help="*.b64.txt files (parts ok)")
    ap.add_argument("--dest", default=".", help="куда распаковать tar (по умолчанию .)")
    ap.add_argument("--keep-tar", action="store_true")
    args = ap.parse_args()

    paths = []
    for pattern in args.files:
        p = Path(pattern)
        if p.exists():
            paths.append(p)
        else:
            paths.extend(sorted(Path(".").glob(pattern)))
    # unique preserve order
    seen = set()
    uniq: list[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    if not uniq:
        print("Нет входных файлов", file=sys.stderr)
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
    if meta.get("bytes") and int(meta["bytes"]) != len(data):
        print(
            f"WARNING: size mismatch expected {meta['bytes']} got {len(data)}",
            file=sys.stderr,
        )

    dest = Path(args.dest).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    tar_path = dest / "pyide-payload.tgz"
    tar_path.write_bytes(data)
    print(f"wrote {tar_path}")

    with tarfile.open(tar_path, "r:gz") as tf:
        # safe extract (Python 3.12+ filter='data' if available)
        try:
            tf.extractall(dest, filter="data")
        except TypeError:
            tf.extractall(dest)

    if not args.keep_tar:
        tar_path.unlink(missing_ok=True)

    print(f"unpacked into {dest}")
    print("Дальше:")
    print("  bash bin/install.sh            # если распаковали полный пакет")
    print("  bash bin/install-tools.sh      # если только vendor/wheels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
