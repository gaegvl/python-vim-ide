"""
Загрузка Avro-схемы:
1) основной путь — служебный топик Kafka (key = имя топика данных, берём последнее по времени)
2) вспомогательный — JSON-каталог на диске (как раньше)
"""
from __future__ import annotations

import json
import sys
from typing import Any, List, Optional, Tuple

from fastavro import parse_schema
from kafka import KafkaConsumer, TopicPartition

from conf import build_ssl_conf, prepare_ssl_files


def _parse_schema_obj(obj: Any):
    """Строка / dict / дважды сериализованный JSON → parse_schema."""
    if obj is None:
        raise ValueError("пустая схема")
    if isinstance(obj, str):
        obj = json.loads(obj)
    if isinstance(obj, str):
        obj = json.loads(obj)
    if not isinstance(obj, dict):
        raise ValueError(f"схема должна быть object, получено {type(obj)}")
    return parse_schema(obj)


def extract_schema_from_value(value: Any) -> Any:
    """Достаём Avro-schema из типичных обёрток каталога / registry."""
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            # возможно сама schema JSON-строка
            try:
                return json.loads(value) if value.strip().startswith("{") else value
            except json.JSONDecodeError:
                return value

    if not isinstance(value, dict):
        return value

    # наш каталог: { data: { schema: "..." }, schemaName: "..." }
    if isinstance(value.get("data"), dict) and "schema" in value["data"]:
        return value["data"]["schema"]
    if "schema" in value:
        return value["schema"]
    # иногда схема на верхнем уровне type=record
    if value.get("type") == "record" or "fields" in value:
        return value
    return value


def schema_key_matches(msg_key: Any, wanted: str) -> bool:
    if msg_key is None:
        return False
    if isinstance(msg_key, bytes):
        try:
            text = msg_key.decode("utf-8")
        except UnicodeDecodeError:
            text = msg_key.decode("latin-1", errors="ignore")
    else:
        text = str(msg_key)

    if text == wanted:
        return True
    # Confluent _schemas: key = {"subject": "...", "version": N}
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            subj = str(obj.get("subject") or "")
            if subj == wanted or subj.startswith(wanted) or wanted in subj:
                return True
    except json.JSONDecodeError:
        pass
    return wanted in text


def _catalog_entry_name(entry: Any) -> str:
    """schemaName / subject из записи; строка/не-dict — пусто."""
    if isinstance(entry, dict):
        return str(entry.get("schemaName") or entry.get("subject") or "")
    return ""


def _is_registry_doc(obj: Any) -> bool:
    return isinstance(obj, dict) and "schema" in obj and (
        "subject" in obj or "id" in obj or "version" in obj
    )


def _wanted_in_subject(wanted: str, subject: str) -> bool:
    """Ищем вхождение wanted (топик / schema_key) в subject."""
    if not wanted or not subject:
        return False
    if wanted == subject:
        return True
    if wanted in subject:
        return True
    # subject часто topic-value / topic-key
    if subject.endswith("-value") or subject.endswith("-key"):
        base = subject.rsplit("-", 1)[0]
        if wanted == base or wanted in base or base in wanted:
            return True
    w = wanted.replace("dbzm.", "").replace("csmr_", "")
    s = subject.replace("dbzm.", "").replace("csmr_", "")
    return bool(w) and (w == s or w in s or s in w)


def _topic_matches_name(topic: str, name: str) -> bool:
    return _wanted_in_subject(topic, name)


def _iter_catalog_entries(catalog: Any) -> List[Tuple[str, Any]]:
    """Нормализуем файл к списку (label, entry)."""
    if isinstance(catalog, list):
        out = []
        for i, item in enumerate(catalog):
            label = _catalog_entry_name(item) or f"[{i}]"
            out.append((label, item))
        return out

    if not isinstance(catalog, dict):
        return []

    # { "schemas": [ {...}, ... ] } или { "subjects": [...] }
    for wrap in ("schemas", "subjects", "items"):
        if isinstance(catalog.get(wrap), list):
            return _iter_catalog_entries(catalog[wrap])

    # один документ Registry
    if _is_registry_doc(catalog):
        return [(_catalog_entry_name(catalog) or "schema", catalog)]

    # каталог ключ → запись
    return [(str(k), v) for k, v in catalog.items()]


def _pick_catalog_entry(
    catalog: Any,
    wanted: str,
    topic: str,
    schema_id: Optional[int] = None,
) -> Any:
    """
    Ищем запись:
    1) по Confluent schema id (если задан)
    2) по schema_key/topic (ключ / subject)
    """
    entries = _iter_catalog_entries(catalog)
    if not entries:
        return None

    if schema_id is not None:
        for _label, entry in entries:
            if isinstance(entry, dict) and entry.get("id") is not None:
                try:
                    if int(entry.get("id")) == int(schema_id):
                        return entry
                except (TypeError, ValueError):
                    pass
        # id задан явно — не откатываемся на subject (иначе снова чужая схема)
        return None

    keys = []
    for k in (wanted, topic):
        if k and k not in keys:
            keys.append(k)

    # точное совпадение ключа
    for want in keys:
        for label, entry in entries:
            if label == want:
                return entry

    # вхождение wanted в subject / schemaName / label
    for want in keys:
        for label, entry in entries:
            subj = _catalog_entry_name(entry) or label
            if _wanted_in_subject(want, subj) or _wanted_in_subject(want, label):
                return entry

    # один документ в файле — берём его (обратная совместимость)
    if len(entries) == 1 and _is_registry_doc(entries[0][1]):
        return entries[0][1]

    return None


def load_schema_from_catalog_file(
    catalog_path: str,
    topic: str,
    schema_key: Optional[str] = None,
    schema_id: Optional[int] = None,
):
    """
    Вспомогательный путь: JSON на диске.

    Поиск: schema_id (предпочтительно) → schema_key/topic в subject.
    """
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    wanted = (schema_key or topic or "").strip()
    entry = _pick_catalog_entry(catalog, wanted, topic, schema_id=schema_id)

    if entry is None:
        hint = "id={0}".format(schema_id) if schema_id is not None else "topic≈{0!r}".format(wanted)
        raise SystemExit(
            "В каталоге {0} нет схемы для {1}".format(catalog_path, hint)
        )

    raw = extract_schema_from_value(entry)
    schema = _parse_schema_obj(raw)
    subj = _catalog_entry_name(entry) or wanted
    eid = entry.get("id") if isinstance(entry, dict) else None
    print(
        "# schema from file {0} subject={1!r} id={2} "
        "(wanted={3!r}, schema_id={4}) topic={5}".format(
            catalog_path, subj, eid, wanted, schema_id, topic
        ),
        file=sys.stderr,
    )
    return schema


def load_schema_from_kafka_topic(cluster: dict, data_topic: str):
    """
    Основной путь: читаем schema_topic, key ~= имя топика данных,
    берём сообщение с максимальным timestamp (последняя по времени).
    """
    schema_topic = cluster.get("schema_topic")
    if not schema_topic:
        raise SystemExit(
            f"[{cluster.get('name')}] не задан schema_topic и нет schema_catalog"
        )

    wanted_key = cluster.get("schema_key") or data_topic
    partition = int(cluster.get("schema_partition") or 0)

    ca, cert, keyfile, tmp = prepare_ssl_files(cluster)
    print(f"# [{cluster.get('name')}] schema ssl tmp: {tmp}", file=sys.stderr)

    conf = build_ssl_conf(cluster["bootstrap"], ca, cert, keyfile)
    conf["consumer_timeout_ms"] = int(
        cluster.get("schema_consumer_timeout_ms") or 20000
    )
    consumer = KafkaConsumer(
        **conf,
        key_deserializer=lambda v: v,
        value_deserializer=lambda v: v,
    )
    tp = TopicPartition(schema_topic, partition)
    consumer.assign([tp])

    begin = consumer.beginning_offsets([tp])[tp]
    end = consumer.end_offsets([tp])[tp]
    print(
        f"# [{cluster.get('name')}] schema_topic={schema_topic} "
        f"range=[{begin},{end}) want_key={wanted_key!r}",
        file=sys.stderr,
    )
    if begin >= end:
        consumer.close()
        raise SystemExit(f"[{cluster.get('name')}] schema_topic пуст: {schema_topic}")

    # можно ограничить хвостом
    from_end = cluster.get("schema_from_end")
    start = begin
    if from_end is not None:
        start = max(begin, end - int(from_end))
    consumer.seek(tp, start)

    best = None  # (ts, offset, value_bytes)
    scanned = 0
    try:
        for msg in consumer:
            if msg.offset >= end:
                break
            scanned += 1
            if not schema_key_matches(msg.key, wanted_key):
                continue
            ts = msg.timestamp or 0
            # если в value есть явная версия/время — учтём
            extra = 0
            try:
                preview = msg.value
                if isinstance(preview, (bytes, bytearray)):
                    preview = preview.decode("utf-8", errors="ignore")
                obj = json.loads(preview) if isinstance(preview, str) else None
                if isinstance(obj, dict):
                    for fld in ("version", "schemaVersion", "ts", "updated_at", "created_at"):
                        if fld in obj and obj[fld] is not None:
                            try:
                                extra = max(extra, int(obj[fld]))
                            except (TypeError, ValueError):
                                pass
                    # Confluent value: {"subject","version","id","schema",...}
                    if "version" in obj:
                        extra = max(extra, int(obj["version"]) * 10_000_000_000)
            except Exception:
                pass

            rank = (ts, extra, msg.offset)
            if best is None or rank > best[0]:
                best = (rank, msg.offset, msg.value, msg.key)
    finally:
        consumer.close()

    if best is None:
        raise SystemExit(
            f"[{cluster.get('name')}] в {schema_topic} не найдена схема "
            f"с key≈{wanted_key!r} (просмотрено {scanned})"
        )

    _rank, off, raw_val, raw_key = best
    extracted = extract_schema_from_value(raw_val)
    schema = _parse_schema_obj(extracted)
    print(
        f"# [{cluster.get('name')}] schema from Kafka {schema_topic}@{off} "
        f"key={raw_key!r}",
        file=sys.stderr,
    )
    return schema


def resolve_schema(
    cluster: dict,
    data_topic: str,
    schema_id: Optional[int] = None,
):
    """
    Приоритет:
    1) schema_topic в кластере (основной) — по topic/schema_key
    2) schema_catalog — файл; если передан schema_id, ищем по id

    schema_key — topic пары (left/right_topic).
    """
    schema_key = cluster.get("schema_key") or data_topic
    if cluster.get("schema_topic") and schema_id is None:
        return load_schema_from_kafka_topic(cluster, data_topic)
    if cluster.get("schema_catalog"):
        return load_schema_from_catalog_file(
            cluster["schema_catalog"],
            data_topic,
            schema_key=schema_key,
            schema_id=schema_id,
        )
    if cluster.get("schema_topic"):
        return load_schema_from_kafka_topic(cluster, data_topic)
    raise SystemExit(
        f"[{cluster.get('name')}] укажите schema_topic (основной) "
        f"или schema_catalog (файл, запасной)"
    )
