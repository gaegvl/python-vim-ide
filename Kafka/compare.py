"""Сравнение двух JSON/dict: состав полей и значения."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, Union


# Epoch только в «разумном» диапазоне лет (иначе коды вроде call_cd=10600003
# ошибочно превращаются в даты 1970-05-...).
_EPOCH_YEAR_MIN = 2000
_EPOCH_YEAR_MAX = 2100
_EPOCH_SEC_MIN = int(datetime(_EPOCH_YEAR_MIN, 1, 1, tzinfo=timezone.utc).timestamp())
_EPOCH_SEC_MAX = int(datetime(_EPOCH_YEAR_MAX, 1, 1, tzinfo=timezone.utc).timestamp())


def flatten(obj: Any, prefix: str = "") -> Dict[str, Any]:
    out = {}  # type: Dict[str, Any]
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


def _in_epoch_year_range(seconds: float) -> bool:
    return _EPOCH_SEC_MIN <= seconds <= _EPOCH_SEC_MAX


def _epoch_to_datetime(n: Union[int, float]) -> Optional[datetime]:
    """
    Seconds / ms / µs / ns since epoch → UTC datetime.
    Только если результат попадает в 2000–2100 (не путаем с кодами/decimal).
    """
    try:
        x = float(n)
    except (TypeError, ValueError):
        return None
    abs_n = abs(x)
    try:
        if abs_n < 1_000_000_000_000:  # < 1e12 → секунды
            seconds = x
            us = int(round((x - int(x)) * 1_000_000)) if not float(x).is_integer() else 0
            ts = int(x)
        elif abs_n < 1_000_000_000_000_000:  # ms
            ts, rem = divmod(int(x), 1_000)
            seconds = ts
            us = rem * 1_000
        elif abs_n < 1_000_000_000_000_000_000:  # µs
            ts, us = divmod(int(x), 1_000_000)
            seconds = ts
        else:  # ns
            ts, rem = divmod(int(x), 1_000_000_000)
            seconds = ts
            us = rem // 1_000
        if not _in_epoch_year_range(seconds):
            return None
        us = max(0, min(999999, us))
        return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=us)
    except (OverflowError, OSError, ValueError):
        return None


def parse_datetime(v: Any) -> Optional[datetime]:
    """ISO-дата / epoch (в диапазоне 2000–2100) / datetime → UTC datetime."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)
    if isinstance(v, Decimal):
        # decimal-коды не считаем датами; только целые «похожие на epoch»
        if v == v.to_integral_value():
            return _epoch_to_datetime(int(v))
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return _epoch_to_datetime(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        # чистое число → epoch только если в диапазоне лет
        if re.fullmatch(r"-?\d+(\.\d+)?", s):
            try:
                if "." in s:
                    return _epoch_to_datetime(float(s))
                return _epoch_to_datetime(int(s))
            except ValueError:
                return None
        # 2026-11-19 04:53:28.858000+00:00 / ISO
        s2 = s.replace("Z", "+00:00")
        if " " in s2 and "T" not in s2[:20]:
            s2 = s2.replace(" ", "T", 1)
        try:
            dt = datetime.fromisoformat(s2)
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return None


def format_datetime(dt: datetime) -> str:
    """Единый читаемый вид UTC."""
    return dt.astimezone(timezone.utc).isoformat(sep=" ", timespec="microseconds")


def to_decimal(v: Any) -> Optional[Decimal]:
    """int/float/Decimal/числовая строка → Decimal (не даты)."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        try:
            return Decimal(str(v))
        except (InvalidOperation, ValueError):
            return None
    if isinstance(v, str):
        s = v.strip().replace(" ", "")
        if not s or not re.fullmatch(r"-?\d+(\.\d+)?", s):
            return None
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            return None
    return None


def format_decimal(d: Decimal) -> str:
    """Читаемый decimal без scientific notation, без лишних нулей справа."""
    t = d.normalize()
    s = format(t, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _is_numeric_scalar(v: Any) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float, Decimal)):
        return True
    if isinstance(v, str):
        return bool(re.fullmatch(r"-?\d+(\.\d+)?", v.strip()))
    return False


def normalize_value(v: Any) -> Any:
    """
    Для сравнения:
    1) datetime / ISO-строка → ISO UTC
    2) epoch только если число даёт год 2000–2100
    3) иначе числа (decimal/double) → Decimal
    """
    if isinstance(v, datetime):
        return format_datetime(
            v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)
        )

    # Текстовые даты (не чистое число)
    if isinstance(v, str) and not _is_numeric_scalar(v):
        dt = parse_datetime(v)
        if dt is not None:
            return format_datetime(dt)
        return v

    if _is_numeric_scalar(v):
        dt = parse_datetime(v)
        if dt is not None:
            # правдоподобный epoch (µs даты 2026 и т.п.)
            return format_datetime(dt)
        dec = to_decimal(v)
        if dec is not None:
            return dec

    return v


def values_equal(a: Any, b: Any) -> bool:
    if a == b:
        return True
    na, nb = normalize_value(a), normalize_value(b)
    if na == nb:
        return True
    if isinstance(na, Decimal) and isinstance(nb, Decimal):
        return na == nb
    return False


def _fmt(v: Any) -> str:
    if v is None:
        return "∅ (пусто)"
    if isinstance(v, bool):
        return "да" if v else "нет"
    if isinstance(v, datetime):
        return format_datetime(
            v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)
        )

    if isinstance(v, str) and not _is_numeric_scalar(v):
        dt = parse_datetime(v)
        if dt is not None:
            return format_datetime(dt)

    if _is_numeric_scalar(v):
        dt = parse_datetime(v)
        if dt is not None:
            return "{0}  (epoch {1})".format(format_datetime(dt), v)
        dec = to_decimal(v)
        if dec is not None:
            return format_decimal(dec)

    if isinstance(v, Decimal):
        return format_decimal(v)
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


def unwrap_payload(obj: Any, mode: str = "auto") -> Tuple[Any, Optional[str]]:
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

    def take(field: str) -> Optional[Any]:
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
    all_fields = []  # type: List[Dict[str, Any]]

    def row(
        field: str,
        status: str,
        va: Any = None,
        vb: Any = None,
        comment: str = "",
    ) -> Dict[str, Any]:
        return {
            "поле": field,
            "статус": status,
            name_a: va,
            name_b: vb,
            f"{name_a}_текст": _fmt(va),
            f"{name_b}_текст": _fmt(vb),
            f"{name_a}_нормализовано": normalize_value(va),
            f"{name_b}_нормализовано": normalize_value(vb),
            "комментарий": comment,
        }

    for k in only_a:
        va = fa[k]
        all_fields.append(
            row(k, "только_слева", va, None, f"только в {name_a}")
        )
    for k in only_b:
        vb = fb[k]
        all_fields.append(
            row(k, "только_справа", None, vb, f"только в {name_b}")
        )

    for k in both:
        va, vb = fa[k], fb[k]
        ea, eb = is_empty(va), is_empty(vb)
        if not ea and not eb:
            both_filled.append(k)
            if values_equal(va, vb):
                same_values.append(k)
                all_fields.append(row(k, "совпадает", va, vb))
            else:
                item = row(k, "различие", va, vb)
                value_diff.append(item)
                all_fields.append(item)
        elif not ea and eb:
            only_a_filled.append(k)
            item = row(k, "различие", va, vb, f"заполнено только в {name_a}")
            value_diff.append(item)
            all_fields.append(item)
        elif ea and not eb:
            only_b_filled.append(k)
            item = row(k, "различие", va, vb, f"заполнено только в {name_b}")
            value_diff.append(item)
            all_fields.append(item)
        else:
            both_empty.append(k)
            all_fields.append(row(k, "совпадает", va, vb, "оба пусты"))

    # стабильный порядок: имя поля
    all_fields.sort(key=lambda r: str(r.get("поле") or ""))

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
            "всего_полей": len(all_fields),
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
        "все_поля": all_fields,
        "имена": {"левый": name_a, "правый": name_b},
    }
