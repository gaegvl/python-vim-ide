"""Сравнение двух JSON/dict: состав полей и значения."""
from __future__ import annotations

import json
from typing import Any


def flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        if not obj and prefix:
            out[prefix] = obj
        for k, v in obj.items():
            if str(k).startswith("_") and k in ("_binary", "_error", "_why", "_schema_id", "_size"):
                key = f"{prefix}.{k}" if prefix else str(k)
                out[key] = v
                continue
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v, key))
    elif isinstance(obj, list):
        if not obj and prefix:
            out[prefix] = obj
        for i, v in enumerate(obj):
            key = f"{prefix}.{i}" if prefix else str(i)
            out.update(flatten(v, key))
    else:
        out[prefix] = obj
    return out


def is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    if isinstance(v, (list, dict)) and len(v) == 0:
        return True
    return False


def _fmt(v: Any) -> str:
    if v is None:
        return "∅ (пусто)"
    if isinstance(v, bool):
        return "да" if v else "нет"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, default=str)
    return str(v)


def _maybe_json(v: Any) -> Any:
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("{") or s.startswith("["):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                return v
    return v


def unwrap_payload(obj: Any, mode: str = "auto") -> tuple[Any, str | None]:
    """
    Достаём бизнес-payload из Debezium/CDC Envelope.

    mode:
      auto  — если есть dict/JSON в after (или before при delete) → берём его
      after — всегда after (ошибка если нет)
      before — всегда before
      full  — без разворачивания
    """
    obj = _maybe_json(obj)
    if not isinstance(obj, dict):
        return obj, None

    mode = (mode or "auto").lower().strip()
    if mode in ("full", "raw", "none", ""):
        return obj, None

    def take(field: str) -> Any | None:
        if field not in obj:
            return None
        val = _maybe_json(obj.get(field))
        return val if isinstance(val, dict) else None

    if mode == "after":
        got = take("after")
        if got is None:
            raise SystemExit("payload_field=after, но after отсутствует или не object")
        return got, "after"
    if mode == "before":
        got = take("before")
        if got is None:
            raise SystemExit("payload_field=before, но before отсутствует или не object")
        return got, "before"

    # auto: если after — object, сравниваем его (типичный Debezium Envelope).
    # Не требуем op/source: иначе after.* остаётся в отчёте как отдельные поля.
    after = take("after")
    if after is not None:
        return after, "after"
    before = take("before")
    if before is not None:
        return before, "before"
    return obj, None


def compare_messages(
    a: Any,
    b: Any,
    name_a: str = "A",
    name_b: str = "B",
    *,
    payload_field: str = "auto",
) -> dict:
    a_unwrapped, a_from = unwrap_payload(a, payload_field)
    b_unwrapped, b_from = unwrap_payload(b, payload_field)
    fa, fb = flatten(a_unwrapped), flatten(b_unwrapped)
    # служебные ключи decode не считаем бизнес-полями в «только слева», но покажем в meta
    def is_meta(k: str) -> bool:
        return k.startswith("_") or "._" in k

    keys_a = {k for k in fa if not is_meta(k)}
    keys_b = {k for k in fb if not is_meta(k)}

    only_a = sorted(keys_a - keys_b)
    only_b = sorted(keys_b - keys_a)
    both = sorted(keys_a & keys_b)

    both_filled = []
    only_a_filled = []
    only_b_filled = []
    both_empty = []
    same_values = []
    value_diff = []

    for k in both:
        va, vb = fa[k], fb[k]
        ea, eb = is_empty(va), is_empty(vb)
        if not ea and not eb:
            both_filled.append(k)
            if va == vb:
                same_values.append(k)
            else:
                value_diff.append(
                    {
                        "поле": k,
                        name_a: va,
                        name_b: vb,
                        f"{name_a}_текст": _fmt(va),
                        f"{name_b}_текст": _fmt(vb),
                    }
                )
        elif not ea and eb:
            only_a_filled.append(k)
            value_diff.append(
                {
                    "поле": k,
                    name_a: va,
                    name_b: vb,
                    f"{name_a}_текст": _fmt(va),
                    f"{name_b}_текст": _fmt(vb),
                    "комментарий": f"заполнено только в {name_a}",
                }
            )
        elif ea and not eb:
            only_b_filled.append(k)
            value_diff.append(
                {
                    "поле": k,
                    name_a: va,
                    name_b: vb,
                    f"{name_a}_текст": _fmt(va),
                    f"{name_b}_текст": _fmt(vb),
                    "комментарий": f"заполнено только в {name_b}",
                }
            )
        else:
            both_empty.append(k)

    ok = len(only_a) == 0 and len(only_b) == 0 and len(value_diff) == 0

    return {
        "итог": "совпадает" if ok else "есть различия",
        "payload": {
            name_a: a_from or "full",
            name_b: b_from or "full",
            "режим": payload_field,
        },
        "сводка": {
            "полей_только_в_" + name_a: len(only_a),
            "полей_только_в_" + name_b: len(only_b),
            "полей_в_обоих": len(both),
            "значения_совпали": len(same_values),
            "различия_значений": len(value_diff),
            "заполнено_в_обоих": len(both_filled),
            "заполнено_только_" + name_a: len(only_a_filled),
            "заполнено_только_" + name_b: len(only_b_filled),
            "оба_пусты": len(both_empty),
        },
        "поля_только_в_" + name_a: only_a,
        "поля_только_в_" + name_b: only_b,
        "заполняемость": {
            "заполнено_в_обоих": both_filled,
            "заполнено_только_" + name_a: only_a_filled,
            "заполнено_только_" + name_b: only_b_filled,
            "оба_пусты": both_empty,
        },
        "одинаковые_значения": same_values,
        "различия_значений": value_diff,
        "имена": {"левый": name_a, "правый": name_b},
    }
