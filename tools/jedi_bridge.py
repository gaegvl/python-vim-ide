#!/usr/bin/env python3
"""Офлайн-мост Vim ↔ Jedi / fallback без Jedi."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _try_jedi():
    try:
        import jedi  # type: ignore
        return jedi
    except Exception:
        return None


def cmd_complete(path: str, line: int, column: int, source_path: str) -> None:
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    jedi = _try_jedi()
    items = []
    if jedi is not None:
        script = jedi.Script(code=src, path=source_path or path)
        for c in script.complete(line, column - 1):
            kind = (c.type or "")[:1].upper()
            items.append(
                {
                    "word": c.name,
                    "kind": kind,
                    "menu": (c.description or "")[:60],
                    "info": (c.docstring() or "")[:500],
                }
            )
    else:
        # Простой fallback: имена из текущего файла
        import re

        names = sorted(set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b", src)))
        items = [{"word": n, "kind": "", "menu": "buffer", "info": ""} for n in names]
    print(json.dumps(items, ensure_ascii=False))


def cmd_goto(path: str, line: int, column: int, source_path: str, mode: str) -> None:
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    jedi = _try_jedi()
    if jedi is None:
        print(json.dumps({"error": "jedi not installed"}))
        return
    script = jedi.Script(code=src, path=source_path or path)
    if mode == "assignment":
        defs = script.goto(line, column - 1)
    elif mode == "references":
        defs = script.get_references(line, column - 1)
    else:
        defs = script.goto(line, column - 1, follow_imports=True)
    out = []
    for d in defs:
        if d.line is None:
            continue
        out.append(
            {
                "file": str(d.module_path) if d.module_path else source_path,
                "line": d.line,
                "col": (d.column or 0) + 1,
                "name": d.name,
                "desc": d.description,
            }
        )
    print(json.dumps(out, ensure_ascii=False))


def cmd_doc(path: str, line: int, column: int, source_path: str) -> None:
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    jedi = _try_jedi()
    if jedi is None:
        print(json.dumps({"doc": "Установите jedi: pip install jedi (офлайн wheel)"}))
        return
    script = jedi.Script(code=src, path=source_path or path)
    docs = []
    for h in script.help(line, column - 1):
        docs.append(h.docstring() or h.description)
    print(json.dumps({"doc": "\n\n".join(docs) if docs else "Нет документации"}))


def cmd_rename(path: str, line: int, column: int, source_path: str, new_name: str) -> None:
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    jedi = _try_jedi()
    if jedi is None:
        print(json.dumps({"error": "jedi not installed"}))
        return
    script = jedi.Script(code=src, path=source_path or path)
    try:
        ref = script.rename(line, column - 1, new_name=new_name)
        # Jedi 0.18+ returns Refactoring
        if hasattr(ref, "apply"):
            ref.apply()
            print(json.dumps({"ok": True, "files": [source_path]}))
            return
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return
    print(json.dumps({"error": "rename unsupported in this jedi version"}))


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: jedi_bridge.py <complete|goto|references|assignment|doc|rename> ...", file=sys.stderr)
        sys.exit(2)
    op = sys.argv[1]
    if op == "complete":
        cmd_complete(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    elif op in ("goto", "assignment", "references"):
        cmd_goto(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], op)
    elif op == "doc":
        cmd_doc(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    elif op == "rename":
        cmd_rename(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], sys.argv[6])
    else:
        print(json.dumps({"error": f"unknown op {op}"}))
        sys.exit(2)


if __name__ == "__main__":
    main()
