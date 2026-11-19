"""Человекочитаемый отчёт сравнения на русском (HTML + JSON)."""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _esc(x: Any) -> str:
    return html.escape("" if x is None else str(x))


def write_reports(results: list[dict], output_path: str, meta: dict | None = None) -> list[str]:
    """
    results — список результатов по парам.
    Пишет .html и рядом .json (те же данные).
    Возвращает пути записанных файлов.
    """
    out = Path(output_path)
    if out.suffix.lower() not in (".html", ".htm", ".md", ".json"):
        out = out.with_suffix(".html")

    base = out.with_suffix("")
    html_path = base.with_suffix(".html")
    json_path = base.with_suffix(".json")

    payload = {
        "сформирован": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "мета": meta or {},
        "пар": len(results),
        "с_различиями": sum(1 for r in results if r.get("сравнение", {}).get("итог") != "совпадает"),
        "без_различий": sum(1 for r in results if r.get("сравнение", {}).get("итог") == "совпадает"),
        "ошибки": sum(1 for r in results if r.get("ошибка")),
        "пары": results,
    }

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    html_path.write_text(_render_html(payload), encoding="utf-8")
    return [str(html_path), str(json_path)]


def _render_html(payload: dict) -> str:
    rows = []
    for i, pair in enumerate(payload["пары"], 1):
        rows.append(_render_pair(i, pair))

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <title>Отчёт сравнения Kafka</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; background: #f6f7f9; color: #1a1a1a; }}
    h1 {{ margin-top: 0; }}
    .card {{ background: #fff; border-radius: 12px; padding: 16px 20px; margin: 16px 0;
             box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    .ok {{ border-left: 6px solid #2e7d32; }}
    .bad {{ border-left: 6px solid #c62828; }}
    .err {{ border-left: 6px solid #ef6c00; }}
    .muted {{ color: #666; font-size: 14px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 8px; font-size: 14px; }}
    th, td {{ border: 1px solid #e0e0e0; padding: 6px 8px; vertical-align: top; text-align: left; }}
    th {{ background: #f0f2f5; }}
    code {{ background: #f0f2f5; padding: 1px 4px; border-radius: 4px; }}
    ul {{ margin: 6px 0; }}
    .pill {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 13px; font-weight: 600; }}
    .pill-ok {{ background: #e8f5e9; color: #1b5e20; }}
    .pill-bad {{ background: #ffebee; color: #b71c1c; }}
    .pill-err {{ background: #fff3e0; color: #e65100; }}
  </style>
</head>
<body>
  <h1>Отчёт сравнения топиков Kafka</h1>
  <p class="muted">Сформирован: {_esc(payload['сформирован'])}</p>
  <div class="card">
    <b>Сводка</b>
    <ul>
      <li>Пар топиков: {payload['пар']}</li>
      <li>Без различий: {payload['без_различий']}</li>
      <li>С различиями: {payload['с_различиями']}</li>
      <li>Ошибки чтения/схемы: {payload['ошибки']}</li>
    </ul>
  </div>
  {''.join(rows)}
</body>
</html>
"""


def _render_pair(idx: int, pair: dict) -> str:
    if pair.get("ошибка"):
        return f"""
<div class="card err">
  <h2>{idx}. {_esc(pair.get('название') or 'Пара')}</h2>
  <span class="pill pill-err">ошибка</span>
  <p><b>Левый топик:</b> <code>{_esc(pair.get('левый_топик'))}</code><br/>
     <b>Правый топик:</b> <code>{_esc(pair.get('правый_топик'))}</code></p>
  <p><b>Ошибка:</b> {_esc(pair['ошибка'])}</p>
</div>
"""

    cmp_ = pair.get("сравнение") or {}
    ok = cmp_.get("итог") == "совпадает"
    klass = "ok" if ok else "bad"
    pill = "pill-ok" if ok else "pill-bad"
    status = "совпадает" if ok else "есть различия"
    s = cmp_.get("сводка") or {}
    names = cmp_.get("имена") or {}
    left_n = names.get("левый") or "левый"
    right_n = names.get("правый") or "правый"

    only_l = cmp_.get(f"поля_только_в_{left_n}") or []
    only_r = cmp_.get(f"поля_только_в_{right_n}") or []
    diffs = cmp_.get("различия_значений") or []

    diff_rows = ""
    for d in diffs[:500]:
        diff_rows += (
            "<tr>"
            f"<td><code>{_esc(d.get('поле'))}</code></td>"
            f"<td>{_esc(d.get(f'{left_n}_текст', d.get(left_n)))}</td>"
            f"<td>{_esc(d.get(f'{right_n}_текст', d.get(right_n)))}</td>"
            f"<td>{_esc(d.get('комментарий') or '')}</td>"
            "</tr>"
        )
    if not diff_rows:
        diff_rows = "<tr><td colspan='4'>Нет различий значений</td></tr>"

    only_l_html = ", ".join(f"<code>{_esc(x)}</code>" for x in only_l[:100]) or "—"
    only_r_html = ", ".join(f"<code>{_esc(x)}</code>" for x in only_r[:100]) or "—"

    off = pair.get("смещения") or {}
    return f"""
<div class="card {klass}">
  <h2>{idx}. {_esc(pair.get('название') or 'Пара')}</h2>
  <span class="pill {pill}">{status}</span>
  <p class="muted">
    <b>Левый ({_esc(left_n)}):</b> <code>{_esc(pair.get('левый_топик'))}</code>
    offset={_esc((off.get('левый') or {}).get('offset'))}, schema_id={_esc((off.get('левый') or {}).get('schema_id'))}<br/>
    <b>Правый ({_esc(right_n)}):</b> <code>{_esc(pair.get('правый_топик'))}</code>
    offset={_esc((off.get('правый') or {}).get('offset'))}, schema_id={_esc((off.get('правый') or {}).get('schema_id'))}
  </p>
  <p><b>Ключ поиска:</b> <code>{_esc(pair.get('ключ'))}</code></p>
  <ul>
    <li>Полей только слева: {s.get('полей_только_в_' + left_n, len(only_l))}</li>
    <li>Полей только справа: {s.get('полей_только_в_' + right_n, len(only_r))}</li>
    <li>Значения совпали: {s.get('значения_совпали', 0)}</li>
    <li>Различия значений: {s.get('различия_значений', len(diffs))}</li>
  </ul>
  <p><b>Поля только в {_esc(left_n)}:</b> {only_l_html}</p>
  <p><b>Поля только в {_esc(right_n)}:</b> {only_r_html}</p>
  <h3>Различия значений</h3>
  <table>
    <tr><th>Поле</th><th>{_esc(left_n)}</th><th>{_esc(right_n)}</th><th>Комментарий</th></tr>
    {diff_rows}
  </table>
</div>
"""
