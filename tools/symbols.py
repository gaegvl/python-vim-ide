#!/usr/bin/env python3
"""Извлечь outline (классы/функции) из Python-файла через ast — без зависимостей."""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


def _walk(node: ast.AST, lines: list[dict], depth: int = 0) -> None:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "F"
            name = child.name
            if isinstance(node, ast.ClassDef):
                name = f"{node.name}.{child.name}"
            lines.append(
                {
                    "kind": kind,
                    "name": name,
                    "line": child.lineno,
                    "col": child.col_offset + 1,
                    "depth": depth,
                }
            )
            _walk(child, lines, depth + 1)
        elif isinstance(child, ast.ClassDef):
            lines.append(
                {
                    "kind": "C",
                    "name": child.name,
                    "line": child.lineno,
                    "col": child.col_offset + 1,
                    "depth": depth,
                }
            )
            _walk(child, lines, depth + 1)


def main() -> None:
    path = Path(sys.argv[1])
    src = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as e:
        print(json.dumps({"error": str(e), "symbols": []}))
        return
    symbols: list[dict] = []
    _walk(tree, symbols)
    print(json.dumps({"symbols": symbols}, ensure_ascii=False))


if __name__ == "__main__":
    main()
