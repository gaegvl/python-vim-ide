"""Декод Confluent-Avro / сырого Avro по уже загруженной схеме."""
from __future__ import annotations

import io
import json
import sys
from typing import Any, Dict, Optional, Tuple, Union

from fastavro import schemaless_reader


def hex_prefix(raw: bytes, n: int = 16) -> str:
    """Первые n байт value — для проверки wire-формата глазами."""
    chunk = bytes(raw)[:n]
    return " ".join("{:02x}".format(b) for b in chunk)


def look_like_confluent(raw: bytes) -> Tuple[bool, Optional[int]]:
    """
    Confluent wire: magic 0x00 + schema_id uint32 BE + payload.

    Важно: сырой Avro тоже часто начинается с 0x00 (union index / null / 0).
    Один только magic — недостаточно; вызывающий должен пробовать оба варианта.
    """
    if not isinstance(raw, (bytes, bytearray)) or len(raw) < 6:
        return False, None
    if raw[0] != 0:
        return False, None
    schema_id = int.from_bytes(raw[1:5], "big")
    # id=0 в SR не бывает; слишком огромные id — почти наверняка не header
    if schema_id <= 0 or schema_id > 50_000_000:
        return False, None
    return True, schema_id


def strip_confluent_header(raw: bytes) -> Tuple[bytes, Optional[int]]:
    ok, schema_id = look_like_confluent(raw)
    if ok:
        return raw[5:], schema_id
    return raw, None


def _score_decoded(obj: Any) -> int:
    """Грубо предпочитаем Debezium/envelope или dict с полями."""
    if not isinstance(obj, dict):
        return 0
    score = min(len(obj), 20)
    for k in ("after", "before", "op", "Value", "payload", "source"):
        if k in obj:
            score += 5
    if obj.get("_binary") or obj.get("_error"):
        return -1
    return score


def decode_avro_value(raw: Optional[Union[bytes, str]], schema) -> Any:
    """
    Декод value:
      1) Confluent (срез 5 байт), если похоже на header
      2) сырой schemaless Avro без среза
    Берём успешный вариант; если оба ок — с большим score (envelope).
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    if not isinstance(raw, (bytes, bytearray)):
        return raw

    raw_b = bytes(raw)
    attempts = []  # type: list
    looks, maybe_id = look_like_confluent(raw_b)
    if looks:
        attempts.append(("confluent", raw_b[5:], maybe_id))
    attempts.append(("raw", raw_b, None))

    best = None  # type: Optional[Tuple[int, str, Optional[int], Any]]
    errors = []  # type: list

    for kind, payload, sid in attempts:
        try:
            obj = schemaless_reader(io.BytesIO(payload), schema)
        except Exception as e:
            errors.append("{0}: {1}".format(kind, e))
            continue
        score = _score_decoded(obj)
        if best is None or score > best[0]:
            best = (score, kind, sid, obj)

    if best is not None:
        _score, kind, sid, obj = best
        if isinstance(obj, dict):
            # служебные пометки для отчёта / retry — не бизнес-поля
            meta = {
                "_wire": kind,
                "_schema_id": sid,
                "_hex": hex_prefix(raw_b),
            }
            # не засоряем payload: вернём чистый obj, meta положим рядом через обёртку?
            # compare ждёт чистый dict — meta только в stderr + отдельные ключи при ошибке.
            print(
                "# avro decode ok wire={0} schema_id={1} len={2} hex[{3}] keys={4}".format(
                    kind,
                    sid,
                    len(raw_b),
                    hex_prefix(raw_b),
                    list(obj.keys())[:12] if isinstance(obj, dict) else type(obj).__name__,
                ),
                file=sys.stderr,
            )
            # пометим wire на объекте только скрытыми ключами если пустой? нет —
            # передадим через атрибут невозможно. Читатель смотрит stderr.
            # Чтобы reader знал wire/sid при успехе — добавим в return только если
            # вызывающий умеет; для успеха sid надёжен лишь при wire=confluent.
            obj = dict(obj)
            obj["__wire"] = kind
            if sid is not None:
                obj["__schema_id"] = sid
            obj["__hex"] = hex_prefix(raw_b)
            return obj

        return obj

    print(
        "# avro decode failed (len={0}, hex[{1}]): {2}".format(
            len(raw_b), hex_prefix(raw_b), " | ".join(errors) or "unknown"
        ),
        file=sys.stderr,
    )
    return {
        "_binary": True,
        "_size": len(raw_b),
        "_error": " | ".join(errors) or "decode failed",
        "_schema_id": maybe_id if looks else None,
        "_hex": hex_prefix(raw_b),
        "_wire_guess": "confluent?" if looks else "raw",
    }


def peek_confluent_schema_id(raw: Optional[bytes]) -> Optional[int]:
    """Только peek; не доказательство, что формат Confluent."""
    if not isinstance(raw, (bytes, bytearray)):
        return None
    ok, sid = look_like_confluent(bytes(raw))
    return sid if ok else None
