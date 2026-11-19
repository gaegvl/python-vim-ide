"""Сравнение двух JSON/dict: состав полей и значения."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, Union


# Epoch в диапазоне лет 1920–2100.
# Малые положительные «секунды» (0 … 1e9, т.е. 1970–2001) не считаем epoch:
# туда попадают коды вроде call_cd=10600003 (decimal/double), не даты.
# До 1970 — отрицательный unix time; с ~2001 — seconds >= 1e9; ms/µs/ns — как обычно.
# Debezium Date (io.debezium.time.Date) = дни с 1970-01-01 (например 20776 → 2026-11-19).
_EPOCH_YEAR_MIN = 1920
_EPOCH_YEAR_MAX = 2100
_EPOCH_SEC_MIN = int(datetime(_EPOCH_YEAR_MIN, 1, 1, tzinfo=timezone.utc).timestamp())
_EPOCH_SEC_MAX = int(datetime(_EPOCH_YEAR_MAX, 1, 1, tzinfo=timezone.utc).timestamp())
_EPOCH_SEC_AMBIGUOUS_MAX = 1_000_000_000  # ~2001-09-09
_EPOCH_DAY_MIN = (date(_EPOCH_YEAR_MIN, 1, 1) - date(1970, 1, 1)).days
_EPOCH_DAY_MAX = (date(_EPOCH_YEAR_MAX, 1, 1) - date(1970, 1, 1)).days
# без подсказки имени поля не трогаем малые day-count (calc_months=6 и т.п.)
_EPOCH_DAY_AMBIGUOUS = 10_000  # ~1997-05-19


def _field_looks_like_date(field: Optional[str]) -> bool:
    if not field:
        return False
    base = str(field).split(".")[-1].lower()
    if base.endswith("_dt") or base.endswith("_date") or base.endswith("date"):
        return True
    if base.endswith("_dttm") or base.endswith("_ts") or base.endswith("timestamp"):
        return True
    return base in ("date", "dt", "day")


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
    """
    Пусто для сравнения = только NULL/None.
    Oracle '' (пустая строка) — НЕ то же самое, оставляем как различие.
    """
    if v is None:
        return True
    if isinstance(v, (list, dict)) and len(v) == 0:
        return True
    return False


def _in_epoch_year_range(seconds: float) -> bool:
    return _EPOCH_SEC_MIN <= seconds <= _EPOCH_SEC_MAX


def _epoch_days_to_datetime(
    n: Union[int, float],
    *,
    force: bool = False,
) -> Optional[datetime]:
    """Debezium Date: дни с 1970-01-01 → UTC midnight."""
    try:
        x = float(n)
    except (TypeError, ValueError):
        return None
    if not float(x).is_integer():
        return None
    days = int(x)
    if not (_EPOCH_DAY_MIN <= days <= _EPOCH_DAY_MAX):
        return None
    if not force and abs(days) < _EPOCH_DAY_AMBIGUOUS:
        return None
    try:
        return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=days)
    except (OverflowError, OSError, ValueError):
        return None


def _epoch_to_datetime(n: Union[int, float]) -> Optional[datetime]:
    """
    Seconds / ms / µs / ns since epoch → UTC datetime.
    Годы 1920–2100. Секунды 0…1e9 (1970–2001) отбрасываем — это коды, не даты.
    """
    try:
        x = float(n)
    except (TypeError, ValueError):
        return None
    abs_n = abs(x)
    unit = "seconds"
    try:
        if abs_n < 1_000_000_000_000:  # < 1e12 → секунды
            seconds = x
            us = int(round((x - int(x)) * 1_000_000)) if not float(x).is_integer() else 0
            ts = int(x)
            unit = "seconds"
        elif abs_n < 1_000_000_000_000_000:  # ms
            ts, rem = divmod(int(x), 1_000)
            seconds = ts
            us = rem * 1_000
            unit = "ms"
        elif abs_n < 1_000_000_000_000_000_000:  # µs
            ts, us = divmod(int(x), 1_000_000)
            seconds = ts
            unit = "us"
        else:  # ns
            ts, rem = divmod(int(x), 1_000_000_000)
            seconds = ts
            us = rem // 1_000
            unit = "ns"
        if not _in_epoch_year_range(seconds):
            return None
        # call_cd=10600003 и т.п. — не timestamp
        if unit == "seconds" and 0 <= seconds < _EPOCH_SEC_AMBIGUOUS_MAX:
            return None
        us = max(0, min(999999, us))
        return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=us)
    except (OverflowError, OSError, ValueError):
        return None


def parse_datetime(v: Any, field: Optional[str] = None) -> Optional[datetime]:
    """ISO-дата / epoch sec|ms|µs|ns / Debezium days / datetime → UTC."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    prefer_days = _field_looks_like_date(field)

    def from_number(n: Union[int, float]) -> Optional[datetime]:
        # *_dt / Date: сначала дни (20776), иначе ms/µs stamp
        if prefer_days:
            got = _epoch_days_to_datetime(n, force=True)
            if got is not None:
                return got
        got = _epoch_to_datetime(n)
        if got is not None:
            return got
        return _epoch_days_to_datetime(n, force=prefer_days)

    if isinstance(v, Decimal):
        if v == v.to_integral_value():
            return from_number(int(v))
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return from_number(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        # чистое число → epoch
        if re.fullmatch(r"-?\d+(\.\d+)?", s):
            try:
                if "." in s:
                    return from_number(float(s))
                return from_number(int(s))
            except ValueError:
                return None
        # 2026-11-19 / ISO datetime
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            try:
                d = date.fromisoformat(s)
                return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
            except ValueError:
                return None
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


def normalize_value(v: Any, field: Optional[str] = None) -> Any:
    """
    Для сравнения:
    1) datetime / ISO-строка → ISO UTC
    2) epoch sec|ms|µs|ns или Debezium days (*_dt → 20776)
    3) иначе числа → Decimal
    null и '' не сливаются — это разные значения.
    """
    if v is None:
        return None

    if isinstance(v, datetime):
        return format_datetime(
            v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)
        )

    # Текстовые даты (не чистое число)
    if isinstance(v, str) and not _is_numeric_scalar(v):
        dt = parse_datetime(v, field=field)
        if dt is not None:
            return format_datetime(dt)
        return v

    if _is_numeric_scalar(v):
        dt = parse_datetime(v, field=field)
        if dt is not None:
            return format_datetime(dt)
        dec = to_decimal(v)
        if dec is not None:
            return dec

    return v


def values_equal(a: Any, b: Any, field: Optional[str] = None) -> bool:
    if a == b:
        return True
    na, nb = normalize_value(a, field=field), normalize_value(b, field=field)
    if na == nb:
        return True
    if isinstance(na, Decimal) and isinstance(nb, Decimal):
        return na == nb
    # дата без времени vs midnight
    if isinstance(na, str) and isinstance(nb, str):
        da, db = parse_datetime(na, field=field), parse_datetime(nb, field=field)
        if da is not None and db is not None and da == db:
            return True
    return False


def _fmt(v: Any, field: Optional[str] = None) -> str:
    if v is None:
        return "∅ (пусто)"
    # пустая строка Oracle — явно, чтобы не путать с NULL
    if isinstance(v, str) and v == "":
        return '""'
    if isinstance(v, str) and v.strip() == "":
        return repr(v)
    if isinstance(v, bool):
        return "да" if v else "нет"
    if isinstance(v, datetime):
        return format_datetime(
            v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)
        )

    if isinstance(v, str) and not _is_numeric_scalar(v):
        dt = parse_datetime(v, field=field)
        if dt is not None:
            return format_datetime(dt)

    if _is_numeric_scalar(v):
        dt = parse_datetime(v, field=field)
        if dt is not None:
            label = "days" if _field_looks_like_date(field) and _epoch_days_to_datetime(
                int(float(v)), force=True
            ) == dt else "epoch"
            return "{0}  ({1} {2})".format(format_datetime(dt), label, v)
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

    after/before часто string(JSON) в упрощённых схемах каталога — парсим.
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
        raw = obj.get(field)
        if raw is None:
            return None
        val = _maybe_json(raw)
        # двойной JSON: "{\"a\":1}" → dict
        if isinstance(val, str):
            val = _maybe_json(val)
        if isinstance(val, dict):
            return val
        # bytes → utf-8 JSON
        if isinstance(val, (bytes, bytearray)):
            try:
                val = _maybe_json(val.decode("utf-8"))
            except UnicodeDecodeError:
                return None
            if isinstance(val, dict):
                return val
        return None

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

    # auto: бизнес-payload из типичных обёрток (порядок важен)
    for wrap in ("after", "Value", "value", "payload", "data", "before"):
        got = take(wrap)
        if got is not None:
            return got, wrap
    return obj, None


def is_service_field(field: str) -> bool:
    """Служебные ods$/ods_ — показываем, но не сравниваем."""
    if not field:
        return False
    for part in str(field).split("."):
        if part.startswith("ods$") or part.startswith("ods_"):
            return True
    return False


def compare_sources(
    sources: Dict[str, Any],
    *,
    payload_field: str = "auto",
    unwrap_names: Optional[List[str]] = None,
) -> dict:
    """
    Сравнение N источников (Kafka / Oracle …).

    sources: упорядоченный dict {имя_столбца: value_dict_or_None}
    unwrap_names: к кому применять Debezium after/before (по умолчанию — все).
    """
    if not sources:
        raise SystemExit("compare_sources: пустой список источников")

    names = list(sources.keys())
    unwrap_set = set(unwrap_names) if unwrap_names is not None else set(names)

    flats = {}  # type: Dict[str, Dict[str, Any]]
    payload_meta = {"режим": payload_field}  # type: Dict[str, Any]
    present = {}  # type: Dict[str, bool]

    def is_meta(k: str) -> bool:
        return k.startswith("_") or "._" in k

    for name, raw in sources.items():
        if raw is None:
            flats[name] = {}
            present[name] = False
            payload_meta[name] = "нет строки"
            continue
        # Avro decode fail → иначе столб пустой (ключи _* отфильтровываются)
        if isinstance(raw, dict) and raw.get("_binary") and raw.get("_error"):
            flats[name] = {
                "ошибка_decode": raw.get("_error"),
                "schema_id_peek": raw.get("_schema_id"),
                "value_hex": raw.get("_hex"),
                "wire_guess": raw.get("_wire_guess"),
            }
            present[name] = True
            payload_meta[name] = "ошибка decode: {0}".format(raw.get("_error"))
            continue
        present[name] = True
        if name in unwrap_set:
            unwrapped, frm = unwrap_payload(raw, payload_field)
            payload_meta[name] = frm or "full"
        else:
            unwrapped, frm = raw, None
            payload_meta[name] = "full"
        if not isinstance(unwrapped, dict):
            unwrapped = {"value": unwrapped}
        flats[name] = {
            k: v for k, v in flatten(unwrapped).items() if not is_meta(k)
        }
        if not flats[name] and isinstance(unwrapped, dict):
            flats[name] = {
                "ошибка_decode": "пустой payload после unwrap ({0})".format(
                    payload_meta[name]
                )
            }
            payload_meta[name] = "{0} (пусто после unwrap)".format(
                payload_meta[name]
            )

    all_keys = sorted(set().union(*[set(f.keys()) for f in flats.values()]))
    same_values = []  # type: List[str]
    value_diff = []  # type: List[Dict[str, Any]]
    all_fields = []  # type: List[Dict[str, Any]]
    only_in = {n: [] for n in names}  # type: Dict[str, List[str]]
    service_fields = []  # type: List[str]

    for k in all_keys:
        vals = {}  # type: Dict[str, Any]
        have = []  # type: List[str]
        for n in names:
            if k in flats[n]:
                vals[n] = flats[n][k]
                have.append(n)
            else:
                vals[n] = None

        row = {
            "поле": k,
            "статус": "",
            "комментарий": "",
            "источники": have,
        }  # type: Dict[str, Any]
        for n in names:
            va = vals[n]
            row[n] = va
            row["{0}_текст".format(n)] = _fmt(va, field=k) if n in have else "—"
            row["{0}_нормализовано".format(n)] = (
                normalize_value(va, field=k) if n in have else None
            )

        if is_service_field(k):
            row["статус"] = "служебное"
            row["комментарий"] = "ods$/ods_ — не сравнивается"
            service_fields.append(k)
            all_fields.append(row)
            continue

        if len(have) == 1:
            row["статус"] = "частично"
            row["комментарий"] = "только в {0}".format(have[0])
            only_in[have[0]].append(k)
            all_fields.append(row)
            continue

        if len(have) < len(names):
            missing = [n for n in names if n not in have]
            # сравниваем значения там, где поле есть
            filled = [(n, vals[n]) for n in have if not is_empty(vals[n])]
            empty_all = all(is_empty(vals[n]) for n in have)
            if empty_all:
                row["статус"] = "частично"
                row["комментарий"] = "нет в: {0}".format(", ".join(missing))
            else:
                base = filled[0][1] if filled else vals[have[0]]
                equal = (
                    all(values_equal(base, vals[n], field=k) for n, _ in filled[1:])
                    if len(filled) > 1
                    else True
                )
                if equal and len(filled) <= 1:
                    row["статус"] = "частично"
                    row["комментарий"] = "нет в: {0}".format(", ".join(missing))
                elif equal:
                    row["статус"] = "частично"
                    row["комментарий"] = "совпадает где есть; нет в: {0}".format(
                        ", ".join(missing)
                    )
                    same_values.append(k)
                else:
                    row["статус"] = "различие"
                    row["комментарий"] = "нет в: {0}".format(", ".join(missing))
                    value_diff.append(row)
            all_fields.append(row)
            continue

        # поле во всех источниках
        empty_flags = [is_empty(vals[n]) for n in names]
        if all(empty_flags):
            row["статус"] = "совпадает"
            row["комментарий"] = "все пусты"
            same_values.append(k)
            all_fields.append(row)
            continue

        base_name = names[0]
        # берём первое непустое как эталон среди всех
        ref = None
        for n in names:
            if not is_empty(vals[n]):
                ref = vals[n]
                break
        equal = True
        for n in names:
            if is_empty(vals[n]) and not is_empty(ref):
                equal = False
                break
            if not is_empty(vals[n]) and not values_equal(ref, vals[n], field=k):
                equal = False
                break
        if equal:
            row["статус"] = "совпадает"
            same_values.append(k)
        else:
            row["статус"] = "различие"
            value_diff.append(row)
        all_fields.append(row)

    ok = all(
        r.get("статус") in ("совпадает", "служебное") for r in all_fields
    )
    summary = {
        "всего_полей": len(all_fields),
        "значения_совпали": len(same_values),
        "различия_значений": len(value_diff),
        "служебных_полей": len(service_fields),
        "источники": names,
    }  # type: Dict[str, Any]
    for n in names:
        summary["полей_только_в_" + n] = len(only_in[n])

    # обратная совместимость для 2 колонок
    names_map = {}  # type: Dict[str, str]
    if len(names) >= 1:
        names_map["левый"] = names[0]
    if len(names) >= 2:
        names_map["правый"] = names[1]
    for n in names:
        names_map[n] = n

    return {
        "итог": "совпадает" if ok else "есть различия",
        "payload": payload_meta,
        "сводка": summary,
        "одинаковые_значения": same_values,
        "различия_значений": value_diff,
        "все_поля": all_fields,
        "имена": names_map,
        "столбцы": names,
        "наличие": present,
    }


def compare_messages(
    a: Any,
    b: Any,
    name_a: str = "A",
    name_b: str = "B",
    *,
    payload_field: str = "auto",
) -> dict:
    return compare_sources(
        {name_a: a, name_b: b},
        payload_field=payload_field,
    )
