#!/usr/bin/env python3
"""Найти TODO/FIXME/XXX/HACK в проекте."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PAT = re.compile(r"\b(TODO|FIXME|XXX|HACK|NOTE)\b[:\s]*(.*)$", re.I)
SKIP = {".git", "__pycache__", ".venv", "venv", ".tox", "node_modules", "vendor"}


def scan(root: Path) -> list[dict]:
    out: list[dict] = []
    for path in root.rglob("*"):
        if any(p in SKIP for p in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".vim", ".md", ".toml", ".cfg", ".ini", ".txt", ".yml", ".yaml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            m = PAT.search(line)
            if m:
                out.append(
                    {
                        "file": str(path),
                        "line": i,
                        "kind": m.group(1).upper(),
                        "text": m.group(0).strip()[:120],
                    }
                )
    return out


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    print(json.dumps(scan(root), ensure_ascii=False))


if __name__ == "__main__":
    main()
