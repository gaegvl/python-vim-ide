"""Декод Confluent-Avro / сырого Avro по уже загруженной схеме."""
from __future__ import annotations

import io
import json
import sys
from typing import Any

from fastavro import schemaless_reader


def strip_confluent_header(raw: bytes) -> tuple[bytes, int | None]:
    if len(raw) >= 5 and raw[0] == 0:
        return raw[5:], int.from_bytes(raw[1:5], "big")
    return raw, None


def decode_avro_value(raw: bytes | str | None, schema) -> Any:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    if not isinstance(raw, (bytes, bytearray)):
        return raw

    payload, schema_id = strip_confluent_header(bytes(raw))
    try:
        return schemaless_reader(io.BytesIO(payload), schema)
    except Exception as e:
        print(
            f"# avro decode failed (schema_id={schema_id}, len={len(raw)}): {e}",
            file=sys.stderr,
        )
        return {
            "_binary": True,
            "_size": len(raw),
            "_error": str(e),
            "_schema_id": schema_id,
        }
