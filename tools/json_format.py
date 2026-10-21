#!/usr/bin/env python3
"""Офлайн-форматирование JSON (unicode, стабильный indent, trailing newline)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--indent", type=int, default=2)
    p.add_argument("--sort-keys", action="store_true")
    args = p.parse_args()

    try:
        data = json.loads(Path(args.src).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"JSON error: {e}", file=sys.stderr)
        return 1

    text = json.dumps(
        data,
        ensure_ascii=False,
        indent=args.indent,
        sort_keys=args.sort_keys,
    )
    if not text.endswith("\n"):
        text += "\n"
    Path(args.dst).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
