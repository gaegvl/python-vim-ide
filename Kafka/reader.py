from __future__ import annotations

import json
import sys
from typing import Any, Optional, Tuple, Union

from kafka import KafkaConsumer, TopicPartition

from conf import build_ssl_conf, prepare_ssl_files

try:
    from avro_decode import decode_avro_value
except ImportError:
    decode_avro_value = None


def safe_decode(v: Optional[Union[bytes, str]]) -> Optional[Union[str, bytes]]:
    if v is None:
        return None
    if isinstance(v, str):
        return v
    try:
        return v.decode("utf-8")
    except UnicodeDecodeError:
        return v


def try_parse(
    value: Optional[Union[str, bytes]],
    *,
    avro_schema=None,
) -> Any:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)) and avro_schema is not None and decode_avro_value:
        return decode_avro_value(bytes(value), avro_schema)
    if isinstance(value, bytes):
        return {"_binary": True, "_size": len(value), "_why": "no avro schema"}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def key_text(msg_key: Any) -> str:
    if msg_key is None:
        return ""
    if isinstance(msg_key, bytes):
        # Confluent: 0x00 + schema_id(4) + payload — UUID часто внутри payload
        return msg_key.decode("latin-1", errors="ignore")
    return str(msg_key)


def _key_blobs(msg_key: Any):
    """Варианты представления key для поиска вхождения UUID."""
    blobs = []
    if msg_key is None:
        return blobs
    if isinstance(msg_key, (bytes, bytearray)):
        raw = bytes(msg_key)
        blobs.append(raw)
        if len(raw) >= 5 and raw[0] == 0:
            blobs.append(raw[5:])  # без Confluent header
        blobs.append(raw.decode("latin-1", errors="ignore"))
        blobs.append(raw.decode("utf-8", errors="ignore"))
    else:
        text = str(msg_key)
        blobs.append(text)
        # если пришло как str с «битыми» символами префикса — всё равно ищем UUID
    return blobs


def matches_key(msg_key: Any, target: str, *, contains: bool = True) -> bool:
    """
    contains=True (по умолчанию): ищем вхождение target в key
    (нужно для Confluent Avro key = 6 байт + UUID).
    """
    if target is None or target == "":
        return False
    target_s = str(target)
    target_b = target_s.encode("utf-8")

    for blob in _key_blobs(msg_key):
        if contains:
            if isinstance(blob, (bytes, bytearray)):
                if target_b in blob or target_s.encode("latin-1", errors="ignore") in blob:
                    return True
            else:
                if target_s in blob:
                    return True
        else:
            if isinstance(blob, (bytes, bytearray)):
                if blob == target_b or blob.endswith(target_b):
                    return True
            else:
                if blob == target_s or blob.endswith(target_s) or target_s in blob:
                    return True
    return False


def resolve_start_offset(
    consumer: KafkaConsumer,
    tp: TopicPartition,
    *,
    offset: Optional[int],
    from_end: Optional[int],
) -> Tuple[int, int, int]:
    begin = consumer.beginning_offsets([tp])[tp]
    end = consumer.end_offsets([tp])[tp]

    if offset is not None:
        if not (begin <= offset < end):
            raise SystemExit(f"offset {offset} вне диапазона [{begin}, {end})")
        return offset, begin, end

    if from_end is not None:
        if from_end < 0:
            raise SystemExit("--from-end должен быть >= 0")
        return max(begin, end - from_end), begin, end

    return begin, begin, end


def read_from_cluster(
    cluster: dict,
    *,
    topic: str,
    offset: Optional[int] = None,
    from_end: Optional[int] = None,
    partition: int = 0,
    key: Optional[str] = None,
    field: str = "task_id",
    key_contains: bool = True,
    max_messages: int = 500_000,
    with_meta: bool = True,
    avro_schema=None,
) -> Any:
    """
    Чтение сообщения из кластера.
    avro_schema — уже загруженная схема (compare передаёт сам).
    Для простого cli можно не передавать (value JSON/текст или _binary).
    """
    if key is None and offset is None:
        raise SystemExit(
            f"[{cluster['name']}] без --key нужен точный --offset"
        )

    ca, cert, keyfile, tmp = prepare_ssl_files(cluster)
    print(f"# [{cluster['name']}] ssl tmp: {tmp}", file=sys.stderr)

    conf = build_ssl_conf(cluster["bootstrap"], ca, cert, keyfile)
    consumer = KafkaConsumer(
        **conf,
        key_deserializer=safe_decode,
        value_deserializer=lambda v: v,
    )
    tp = TopicPartition(topic, partition)
    consumer.assign([tp])

    try:
        start, begin, end = resolve_start_offset(
            consumer, tp, offset=offset, from_end=from_end
        )
    except SystemExit:
        consumer.close()
        raise

    print(
        f"# [{cluster['name']}] range [{begin}, {end}), start={start}, "
        f"key={key!r}, from_end={from_end}",
        file=sys.stderr,
    )

    if start >= end:
        consumer.close()
        raise SystemExit(f"[{cluster['name']}] партиция пуста")

    consumer.seek(tp, start)
    scanned = 0
    try:
        for msg in consumer:
            if msg.offset >= end:
                break
            scanned += 1
            raw_value = msg.value

            if key is not None:
                if not matches_key(msg.key, key, contains=key_contains):
                    if scanned >= max_messages:
                        break
                    continue
            elif offset is not None and msg.offset != offset:
                continue

            schema_id = None
            if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) >= 5 and raw_value[0] == 0:
                schema_id = int.from_bytes(raw_value[1:5], "big")

            data = try_parse(raw_value, avro_schema=avro_schema)
            decode_error = None
            if isinstance(data, dict) and data.get("_binary") and data.get("_error"):
                decode_error = data.get("_error")
                print(
                    "# [{0}] decode error schema_id={1}: {2}".format(
                        cluster["name"], schema_id, decode_error
                    ),
                    file=sys.stderr,
                )

            if with_meta:
                return {
                    "cluster": cluster["name"],
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                    "key": key_text(msg.key) or msg.key,
                    "value": data,
                    "raw_value": raw_value,
                    "schema_id": schema_id if schema_id is not None else (
                        data.get("_schema_id") if isinstance(data, dict) else None
                    ),
                    "decode_error": decode_error,
                }
            return data
    finally:
        consumer.close()

    hint = f"key={key!r}" if key else f"offset={offset}"
    raise SystemExit(
        f"[{cluster['name']}] не найдено ({hint}) от start={start} "
        f"(просмотрено {scanned}, конец {end})"
    )
