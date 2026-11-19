"""Человекочитаемый отчёт сравнения на русском (HTML + JSON)."""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _esc(x: Any) -> str:
    return html.escape("" if x is None else str(x))


def write_reports(
    results: List[dict],
    output_path: str,
    meta: Optional[dict] = None,
) -> List[str]:
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
        "с_различиями": sum(
            1 for r in results if r.get("сравнение", {}).get("итог") != "совпадает"
        ),
        "без_различий": sum(
            1 for r in results if r.get("сравнение", {}).get("итог") == "совпадает"
        ),
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
    table {{ border-collapse: collapse; width: 100%; margin-top: 8px; font-size: 13px; }}
    th, td {{ border: 1px solid #e0e0e0; padding: 6px 8px; vertical-align: top; text-align: left; }}
    th {{ background: #f0f2f5; position: sticky; top: 0; z-index: 1; }}
    code {{ background: #f0f2f5; padding: 1px 4px; border-radius: 4px; }}
    ul {{ margin: 6px 0; }}
    .pill {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 13px; font-weight: 600; }}
    .pill-ok {{ background: #e8f5e9; color: #1b5e20; }}
    .pill-bad {{ background: #ffebee; color: #b71c1c; }}
    .pill-err {{ background: #fff3e0; color: #e65100; }}
    tr.row-match td {{ background: #e8f5e9; }}
    tr.row-diff td {{ background: #ffebee; }}
    tr.row-partial td {{ background: #fff8e1; }}
    tr.row-service td {{ background: #eceff1; color: #546e7a; }}
    .status-match {{ color: #1b5e20; font-weight: 600; }}
    .status-diff {{ color: #b71c1c; font-weight: 600; }}
    .status-partial {{ color: #e65100; font-weight: 600; }}
    .status-service {{ color: #546e7a; font-weight: 600; }}
    .legend span {{ display: inline-block; padding: 2px 8px; margin-right: 8px; border-radius: 4px; font-size: 13px; }}
    .leg-match {{ background: #e8f5e9; }}
    .leg-diff {{ background: #ffebee; }}
    .leg-partial {{ background: #fff8e1; }}
    .leg-service {{ background: #eceff1; }}
    .table-wrap {{ max-height: 70vh; overflow: auto; border: 1px solid #e0e0e0; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>Отчёт сравнения топиков Kafka / Oracle</h1>
  <p class="muted">Сформирован: {_esc(payload['сформирован'])}</p>
  <div class="card">
    <b>Сводка</b>
    <ul>
      <li>Пар: {payload['пар']}</li>
      <li>Без различий: {payload['без_различий']}</li>
      <li>С различиями: {payload['с_различиями']}</li>
      <li>Ошибки: {payload['ошибки']}</li>
    </ul>
  </div>
  {''.join(rows)}
</body>
</html>
"""


def _status_label(status: str) -> Tuple[str, str, str]:
    if status == "совпадает":
        return "row-match", "совпадает", "status-match"
    if status == "различие":
        return "row-diff", "различие", "status-diff"
    if status == "служебное":
        return "row-service", "служебное", "status-service"
    if status in ("частично", "только_слева", "только_справа"):
        return "row-partial", status.replace("_", " "), "status-partial"
    return "", status or "", ""


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
    cols = cmp_.get("столбцы") or []
    if not cols:
        names = cmp_.get("имена") or {}
        left_n = names.get("левый") or "левый"
        right_n = names.get("правый") or "правый"
        cols = [left_n, right_n]

    all_fields = cmp_.get("все_поля") or []
    diffs = cmp_.get("различия_значений") or []

    header_cols = "".join(f"<th>{_esc(c)}</th>" for c in cols)
    field_rows = []
    for d in all_fields:
        st = d.get("статус") or "различие"
        row_cls, label, st_cls = _status_label(st)
        cells = "".join(
            f"<td>{_esc(d.get(c + '_текст', d.get(c, '—')))}</td>" for c in cols
        )
        field_rows.append(
            f"<tr class='{row_cls}'>"
            f"<td><code>{_esc(d.get('поле'))}</code></td>"
            f"<td class='{st_cls}'>{_esc(label)}</td>"
            f"{cells}"
            f"<td>{_esc(d.get('комментарий') or '')}</td>"
            "</tr>"
        )
    if not field_rows:
        field_rows.append(
            f"<tr><td colspan='{2 + len(cols) + 1}'>Нет полей</td></tr>"
        )

    off = pair.get("смещения") or {}
    oracle_info = pair.get("oracle") or {}
    src_lines = []
    for c in cols:
        meta = off.get(c) or {}
        if meta.get("offset") is not None:
            src_lines.append(
                "<b>{0}:</b> <code>{1}</code> offset={2}, schema_id={3}".format(
                    _esc(c),
                    _esc(meta.get("topic") or pair.get("левый_топик") if c == cols[0] else pair.get("правый_топик")),
                    _esc(meta.get("offset")),
                    _esc(meta.get("schema_id")),
                )
            )
        elif meta.get("fqn"):
            src_lines.append(
                "<b>{0}:</b> <code>{1}</code> pk={2}".format(
                    _esc(c),
                    _esc(meta.get("fqn")),
                    _esc(meta.get("pk")),
                )
            )
        elif c in oracle_info:
            src_lines.append(
                "<b>{0}:</b> <code>{1}</code>".format(_esc(c), _esc(oracle_info.get(c)))
            )

    if not src_lines:
        src_lines.append(
            "<b>Левый:</b> <code>{0}</code><br/><b>Правый:</b> <code>{1}</code>".format(
                _esc(pair.get("левый_топик")),
                _esc(pair.get("правый_топик")),
            )
        )

    only_stats = "".join(
        "<li>Только в {0}: {1}</li>".format(
            _esc(c), s.get("полей_только_в_" + c, 0)
        )
        for c in cols
    )

    return f"""
<div class="card {klass}">
  <h2>{idx}. {_esc(pair.get('название') or 'Пара')}</h2>
  <span class="pill {pill}">{status}</span>
  <p class="muted">{"<br/>".join(src_lines)}</p>
  <p><b>Ключ пары:</b> <code>{_esc(pair.get('ключ'))}</code></p>
  <ul>
    <li>Всего полей: {s.get('всего_полей', len(all_fields))}</li>
    {only_stats}
    <li>Значения совпали: {s.get('значения_совпали', 0)}</li>
    <li>Различия значений: {s.get('различия_значений', len(diffs))}</li>
  </ul>
  <p class="legend muted">
    <span class="leg-match">совпадает</span>
    <span class="leg-diff">различие</span>
    <span class="leg-partial">частично</span>
    <span class="leg-service">служебное (ods)</span>
  </p>
  <h3>Все поля</h3>
  <div class="table-wrap">
  <table>
    <tr>
      <th>Поле</th><th>Статус</th>
      {header_cols}
      <th>Комментарий</th>
    </tr>
    {''.join(field_rows)}
  </table>
  </div>
</div>
"""
