from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from kafka import KafkaConsumer, TopicPartition

from conf import build_ssl_conf, prepare_ssl_files

try:
    from avro_decode import decode_avro_value, hex_prefix, peek_confluent_schema_id
except ImportError:
    decode_avro_value = None
    hex_prefix = None  # type: ignore
    peek_confluent_schema_id = None  # type: ignore

_WIRE_META_KEYS = ("__wire", "__schema_id", "__hex")
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def _split_wire_meta(data: Any) -> Tuple[Any, Dict[str, Any]]:
    """Достаём служебные __wire/__schema_id из успешного decode."""
    meta = {}  # type: Dict[str, Any]
    if not isinstance(data, dict):
        return data, meta
    if not any(k in data for k in _WIRE_META_KEYS):
        return data, meta
    clean = dict(data)
    for k in _WIRE_META_KEYS:
        if k in clean:
            meta[k[2:]] = clean.pop(k)  # wire / schema_id / hex
    return clean, meta


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
    """Читаемое представление key; UUID вытаскиваем если есть."""
    if msg_key is None:
        return ""
    raw = bytes(msg_key) if isinstance(msg_key, (bytes, bytearray)) else None
    if raw is not None:
        # ASCII UUID внутри Confluent key (header + avro string)
        try:
            latin = raw.decode("latin-1", errors="ignore")
        except Exception:
            latin = ""
        m = _UUID_RE.search(latin)
        if m:
            return m.group(0)
        # binary UUID (16 bytes) после header/длины
        for start in (0, 5, 6):
            if len(raw) >= start + 16:
                chunk = raw[start : start + 16]
                try:
                    return str(UUID(bytes=chunk))
                except ValueError:
                    pass
        return "key[{0}b] hex[{1}]".format(
            len(raw),
            " ".join("{:02x}".format(b) for b in raw[:12]),
        )
    return str(msg_key)


def _needle_variants(target: str) -> List[bytes]:
    """
    Чем искать UUID в бинарном key (как Offset Explorer):
    - строка с дефисами / без
    - 16 сырых байт UUID
    """
    out = []  # type: List[bytes]
    s = str(target).strip()
    if not s:
        return out

    def add(b: bytes):
        if b and b not in out:
            out.append(b)

    add(s.encode("utf-8"))
    add(s.encode("latin-1", errors="ignore"))
    compact = s.replace("-", "").replace("{", "").replace("}", "")
    if compact != s:
        add(compact.encode("utf-8"))
        add(compact.lower().encode("utf-8"))
        add(compact.upper().encode("utf-8"))
    try:
        u = UUID(s)
    except ValueError:
        try:
            u = UUID(compact) if len(compact) == 32 else None
        except ValueError:
            u = None
    if u is not None:
        add(str(u).encode("utf-8"))
        add(str(u).replace("-", "").encode("utf-8"))
        add(u.bytes)  # RFC binary
        add(u.bytes_le)
    return out


def _key_blobs(msg_key: Any) -> List[bytes]:
    """Срезы key, где может лежать UUID (raw / без Confluent header / без avro length)."""
    blobs = []  # type: List[bytes]
    if msg_key is None:
        return blobs

    if isinstance(msg_key, (bytes, bytearray)):
        raw = bytes(msg_key)
    else:
        # на случай если кто-то снова включит str-deserializer
        text = str(msg_key)
        raw = text.encode("latin-1", errors="ignore")
        blobs.append(text.encode("utf-8", errors="ignore"))

    blobs.append(raw)
    if len(raw) >= 5 and raw[0] == 0:
        payload = raw[5:]
        blobs.append(payload)
        # Avro string: zigzag length (обычно 1 байт 0x48=36) + uuid
        if payload:
            blobs.append(payload[1:])
        if len(payload) >= 2:
            blobs.append(payload[2:])
    return blobs


def matches_key(msg_key: Any, target: str, *, contains: bool = True) -> bool:
    """
    contains=True (по умолчанию): ищем UUID/строку ВНУТРИ key.
    Confluent Avro key = magic(1)+schema_id(4)+avro(string UUID) — как в Offset Explorer.
    """
    if target is None or target == "":
        return False
    needles = _needle_variants(str(target))
    if not needles:
        return False
    blobs = _key_blobs(msg_key)
    target_s = str(target).strip()

    for blob in blobs:
        if contains:
            for n in needles:
                if n in blob:
                    return True
            # текстовый fallback
            try:
                if target_s in blob.decode("latin-1", errors="ignore"):
                    return True
            except Exception:
                pass
        else:
            for n in needles:
                if blob == n or blob.endswith(n):
                    return True
            if target_s and (
                blob == target_s.encode("utf-8")
                or blob.endswith(target_s.encode("utf-8"))
            ):
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
        # raw bytes: UTF-8 deserializer ломает поиск UUID в Confluent key
        key_deserializer=lambda v: v,
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

            # Только peek: raw[0]==0 ещё не доказательство Confluent
            peek_id = None
            if peek_confluent_schema_id and isinstance(raw_value, (bytes, bytearray)):
                peek_id = peek_confluent_schema_id(bytes(raw_value))
            if hex_prefix and isinstance(raw_value, (bytes, bytearray)):
                print(
                    "# [{0}] value len={1} hex[{2}] peek_schema_id={3}".format(
                        cluster["name"],
                        len(raw_value),
                        hex_prefix(bytes(raw_value)),
                        peek_id,
                    ),
                    file=sys.stderr,
                )

            data = try_parse(raw_value, avro_schema=avro_schema)
            data, wire_meta = _split_wire_meta(data)
            decode_error = None
            wire = wire_meta.get("wire")
            schema_id = wire_meta.get("schema_id")
            if isinstance(data, dict) and data.get("_binary") and data.get("_error"):
                decode_error = data.get("_error")
                schema_id = data.get("_schema_id", peek_id)
                wire = data.get("_wire_guess") or wire
                print(
                    "# [{0}] decode error wire={1} schema_id={2}: {3}".format(
                        cluster["name"], wire, schema_id, decode_error
                    ),
                    file=sys.stderr,
                )
            elif wire == "confluent":
                # id достоверен только если decode прошёл в режиме confluent
                schema_id = wire_meta.get("schema_id")
            else:
                # raw Avro: peek_id мог быть ложным (байты payload)
                schema_id = None

            if with_meta:
                return {
                    "cluster": cluster["name"],
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                    "key": key_text(msg.key) or msg.key,
                    "value": data,
                    "raw_value": raw_value,
                    "schema_id": schema_id,
                    "peek_schema_id": peek_id,
                    "wire": wire,
                    "value_hex": wire_meta.get("hex") or (
                        hex_prefix(bytes(raw_value))
                        if hex_prefix and isinstance(raw_value, (bytes, bytearray))
                        else None
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
