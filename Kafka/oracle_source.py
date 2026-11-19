"""Чтение строки из Oracle для сравнения с Kafka."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

_IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]*$")

# Oracle TIMESTAMP часто в MSK (+3) без tzinfo; Kafka — UTC.
# По умолчанию вычитаем 3 часа. DATE (только день) не трогаем.
_DEFAULT_TS_SHIFT_HOURS = -3


def _check_ident(name: str, what: str) -> str:
    parts = name.split(".")
    for p in parts:
        if not _IDENT.match(p):
            raise SystemExit(f"Недопустимый Oracle {what}: {name!r}")
    return name


def _is_date_only(dt: datetime) -> bool:
    return (
        dt.hour == 0
        and dt.minute == 0
        and dt.second == 0
        and getattr(dt, "microsecond", 0) == 0
    )


def _shift_oracle_timestamp(
    v: datetime,
    shift_hours: float,
) -> datetime:
    """
    Приводим Oracle TIMESTAMP к UTC-подобному виду для сравнения с Kafka.
    • если tzinfo есть — просто в UTC;
    • naive TIMESTAMP: shift_hours=-3 → вычесть 3ч (MSK);
    • DATE-only (00:00:00) не сдвигаем.
    """
    if v.tzinfo is not None:
        return v.astimezone(timezone.utc)
    if shift_hours == 0 or _is_date_only(v):
        return v.replace(tzinfo=timezone.utc)
    return (v + timedelta(hours=shift_hours)).replace(tzinfo=timezone.utc)


def _cell(v: Any, *, ts_shift_hours: float = _DEFAULT_TS_SHIFT_HOURS) -> Any:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, Decimal):
        return v
    if isinstance(v, datetime):
        return _shift_oracle_timestamp(v, ts_shift_hours)
    if isinstance(v, date):
        # чистый DATE — без сдвига часов
        return datetime(v.year, v.month, v.day, tzinfo=timezone.utc)
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8")
        except UnicodeDecodeError:
            return v.hex()
    if isinstance(v, (int, float, str)):
        return v
    return str(v)


def row_to_dict(
    columns,
    values,
    *,
    ts_shift_hours: float = _DEFAULT_TS_SHIFT_HOURS,
) -> Dict[str, Any]:
    """Имена колонок в lower_case — как поля Kafka after.*."""
    out = {}  # type: Dict[str, Any]
    for col, val in zip(columns, values):
        key = str(col).lower()
        out[key] = _cell(val, ts_shift_hours=ts_shift_hours)
    return out


def resolve_ts_shift_hours(oracle_cfg: Optional[dict] = None) -> float:
    """
    Сдвиг TIMESTAMP из Oracle к UTC для сравнения с Kafka.

    oracle.timestamp_shift_hours: -3  (по умолчанию) — убрать +3 MSK
    oracle.timestamp_offset_hours: 3  — синоним «на сколько Oracle впереди UTC»
    """
    cfg = oracle_cfg or {}
    if cfg.get("timestamp_shift_hours") is not None:
        return float(cfg["timestamp_shift_hours"])
    if cfg.get("timestamp_offset_hours") is not None:
        # offset +3 (MSK) → shift -3
        return -float(cfg["timestamp_offset_hours"])
    if cfg.get("tz_offset_hours") is not None:
        return -float(cfg["tz_offset_hours"])
    return float(_DEFAULT_TS_SHIFT_HOURS)


def connect(oracle_cfg: dict):
    """
    oracle_cfg (только коннект + опционально сдвиг времени):
      user, password, dsn  (или host, port, service_name)
      timestamp_shift_hours: -3  (вычесть 3ч у TIMESTAMP; DATE не трогаем)
    prefix/table/pk задаются в pair.oracle
    """
    user = oracle_cfg.get("user") or oracle_cfg.get("username")
    password = oracle_cfg.get("password")
    if not user or password is None:
        raise SystemExit("В oracle нужны user и password")

    dsn = oracle_cfg.get("dsn")
    if not dsn:
        host = oracle_cfg.get("host")
        port = int(oracle_cfg.get("port") or 1521)
        service = oracle_cfg.get("service_name") or oracle_cfg.get("service")
        if not host or not service:
            raise SystemExit("В oracle нужен dsn или host+service_name")
        dsn = "{0}:{1}/{2}".format(host, port, service)

    try:
        import oracledb as db  # type: ignore
    except ImportError:
        try:
            import cx_Oracle as db  # type: ignore
        except ImportError:
            raise SystemExit(
                "Нужен пакет oracledb или cx_Oracle для чтения Oracle"
            )

    return db.connect(user=user, password=password, dsn=dsn)


def resolve_pair_oracle(pair_oracle: dict, global_oracle: Optional[dict] = None) -> dict:
    """
    Собирает параметры SCT/SOH для пары.

    prefix=rkk → rkk_sct.table / rkk_soh.h2_table
    """
    g = global_oracle or {}
    p = pair_oracle or {}
    # prefix / table / pk — в паре; глобальный oracle только login/dsn
    prefix = (p.get("prefix") or "").strip()
    if not prefix:
        raise SystemExit("В pair.oracle нужен prefix (например rkk)")
    table = (p.get("table") or p.get("table_name") or "").strip()
    if not table:
        raise SystemExit("В pair.oracle нужен table / table_name")

    pk = (p.get("pk_column") or "").strip()
    if not pk:
        raise SystemExit("В pair.oracle нужен pk_column")

    soh_table = (p.get("soh_table") or p.get("h2_table") or "").strip()
    if not soh_table:
        soh_table = "h2_" + table if not table.lower().startswith("h2_") else table

    sct_schema = (p.get("sct_schema") or "{0}_sct".format(prefix)).strip()
    soh_schema = (p.get("soh_schema") or "{0}_soh".format(prefix)).strip()

    _check_ident(sct_schema, "sct_schema")
    _check_ident(soh_schema, "soh_schema")
    _check_ident(table, "table")
    _check_ident(soh_table, "soh_table")
    _check_ident(pk, "pk_column")

    sct_name = p.get("sct_name") or "{0}_sct".format(prefix)
    soh_name = p.get("soh_name") or "{0}_soh".format(prefix)

    return {
        "prefix": prefix,
        "pk_column": pk,
        "sct_fqn": "{0}.{1}".format(sct_schema, table),
        "soh_fqn": "{0}.{1}".format(soh_schema, soh_table),
        "sct_name": sct_name,
        "soh_name": soh_name,
        "table": table,
        "soh_table": soh_table,
    }


def fetch_by_pk(
    conn,
    fqn: str,
    pk_column: str,
    key: Any,
    *,
    ts_shift_hours: float = _DEFAULT_TS_SHIFT_HOURS,
) -> Optional[Dict[str, Any]]:
    """
    SELECT * FROM schema.table WHERE pk = :key
    Возвращает одну строку (dict) или None.
    """
    for part in fqn.split("."):
        _check_ident(part, "ident")
    pk_column = _check_ident(pk_column, "pk_column")

    sql = "SELECT * FROM {0} WHERE {1} = :key".format(fqn, pk_column)
    cur = conn.cursor()
    try:
        cur.execute(sql, key=key)
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description]
        return row_to_dict(cols, row, ts_shift_hours=ts_shift_hours)
    finally:
        cur.close()


def fetch_pair_rows(
    conn,
    resolved: dict,
    key: Any,
    *,
    ts_shift_hours: float = _DEFAULT_TS_SHIFT_HOURS,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    sct = fetch_by_pk(
        conn,
        resolved["sct_fqn"],
        resolved["pk_column"],
        key,
        ts_shift_hours=ts_shift_hours,
    )
    soh = fetch_by_pk(
        conn,
        resolved["soh_fqn"],
        resolved["pk_column"],
        key,
        ts_shift_hours=ts_shift_hours,
    )
    return sct, soh
