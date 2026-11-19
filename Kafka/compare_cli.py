#!/usr/bin/env python3
"""
Сравнение пар: 2 Kafka + опционально 2 Oracle (prefix_sct / prefix_soh).

  python compare_cli.py --config compare.json

Ключ задаётся в каждой pair.key (глобальный key — только запасной fallback).
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from compare import compare_sources
from reader import read_from_cluster, try_parse
from report import write_reports
from schema_source import resolve_schema

try:
    from oracle_source import connect as oracle_connect
    from oracle_source import fetch_pair_rows, resolve_pair_oracle, resolve_ts_shift_hours
except ImportError:
    oracle_connect = None  # type: ignore
    fetch_pair_rows = None  # type: ignore
    resolve_pair_oracle = None  # type: ignore
    resolve_ts_shift_hours = None  # type: ignore


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if "clusters" not in cfg or "left" not in cfg["clusters"] or "right" not in cfg["clusters"]:
        raise SystemExit("В конфиге нужны clusters.left и clusters.right")
    if not cfg.get("pairs") or not isinstance(cfg["pairs"], list):
        raise SystemExit("В конфиге нужен непустой массив pairs")
    return cfg


def main() -> int:
    p = argparse.ArgumentParser(
        description="Сравнение Kafka (+ Oracle SCT/SOH) по парам"
    )
    p.add_argument("--config", "-c", required=True, help="JSON с кластерами и pairs")
    args = p.parse_args()

    cfg = load_config(args.config)
    left = dict(cfg["clusters"]["left"])
    right = dict(cfg["clusters"]["right"])
    left.setdefault("name", "левый")
    right.setdefault("name", "правый")

    global_key = cfg.get("key")
    # по умолчанию — вхождение в key (Confluent Avro key = префикс + UUID)
    key_contains = bool(cfg.get("key_contains", True))
    if cfg.get("key_contains") is None:
        key_contains = True
    max_messages = int(cfg.get("max_messages") or 500_000)
    global_from_end = cfg.get("from_end")
    output = cfg.get("output") or "compare_report.html"
    global_oracle = cfg.get("oracle") or {}

    schema_cache = {}  # type: Dict[Tuple[Any, ...], object]
    oracle_conn = None

    def schema_for(cluster: dict, topic: str, schema_id: Optional[int] = None):
        # schema_key всегда = topic пары; schema_id — из Confluent-заголовка сообщения
        cache_key = (
            cluster["name"],
            topic,
            cluster.get("schema_catalog"),
            cluster.get("schema_topic"),
            schema_id,
        )
        if cache_key not in schema_cache:
            print(
                "# схема {0} / topic={1} schema_id={2}".format(
                    cluster["name"], topic, schema_id
                ),
                file=sys.stderr,
            )
            c = dict(cluster)
            c["schema_key"] = topic
            schema_cache[cache_key] = resolve_schema(
                c, topic, schema_id=schema_id
            )
        return schema_cache[cache_key]

    def ensure_oracle():
        nonlocal oracle_conn
        if oracle_conn is not None:
            return oracle_conn
        if not global_oracle:
            raise SystemExit("В паре указан oracle, но в конфиге нет секции oracle")
        if oracle_connect is None:
            raise SystemExit("Модуль oracle_source недоступен")
        print("# подключение к Oracle…", file=sys.stderr)
        oracle_conn = oracle_connect(global_oracle)
        return oracle_conn

    results = []
    for i, pair in enumerate(cfg["pairs"], 1):
        name = pair.get("name") or "Пара {0}".format(i)
        left_topic = pair.get("left_topic") or pair.get("topic_left")
        right_topic = pair.get("right_topic") or pair.get("topic_right")
        if not left_topic or not right_topic:
            results.append(
                {
                    "название": name,
                    "ошибка": "У пары не заданы left_topic и right_topic",
                }
            )
            continue

        # ключ — свой на пару; глобальный только fallback
        key = pair.get("key")
        if key is None:
            key = global_key
        pair_key_contains = pair.get("key_contains")
        if pair_key_contains is None:
            pair_key_contains = key_contains

        field = pair.get("key_field", pair.get("field"))
        if field is None or field == "" or str(field).lower() == "none":
            field = ""
        left_from_end = pair.get("left_from_end", pair.get("from_end", global_from_end))
        right_from_end = pair.get(
            "right_from_end", pair.get("from_end", global_from_end)
        )

        print("\n# === [{0}/{1}] {2} ===".format(i, len(cfg["pairs"]), name), file=sys.stderr)
        print("# key={0!r}".format(key), file=sys.stderr)
        print("# {0}  vs  {1}".format(left_topic, right_topic), file=sys.stderr)

        item = {
            "название": name,
            "левый_топик": left_topic,
            "правый_топик": right_topic,
            "ключ": key,
        }  # type: Dict[str, Any]

        warnings = []  # type: List[str]
        sources = {}  # type: Dict[str, Any]
        unwrap_names = []  # type: List[str]
        offsets = {}  # type: Dict[str, Any]
        oracle_meta = {}  # type: Dict[str, Any]

        def soft_fail(src_name: str, err: Any) -> None:
            msg = str(err)
            warnings.append("{0}: {1}".format(src_name, msg))
            print("# warning [{0}]: {1}".format(src_name, msg), file=sys.stderr)
            sources[src_name] = None
            offsets.setdefault(src_name, {})["error"] = msg
            offsets[src_name]["found"] = False

        def read_and_fix_schema(cluster, topic, sch, **kwargs):
            """
            Читаем по схеме subject/topic.
            Retry по schema_id — только если decode подтвердил wire=confluent.
            """
            from reader import _split_wire_meta

            msg = read_from_cluster(
                cluster, topic=topic, avro_schema=sch, **kwargs
            )
            val = msg.get("value")
            wire = msg.get("wire")
            sid = msg.get("schema_id")
            peek_id = msg.get("peek_schema_id")
            catalog = cluster.get("schema_catalog")
            raw = msg.get("raw_value")

            decode_failed = (
                isinstance(val, dict)
                and val.get("_binary")
                and val.get("_error")
            )

            print(
                "# [{0}] wire={1} schema_id={2} peek_id={3} hex[{4}] "
                "decode_ok={5}".format(
                    cluster["name"],
                    wire,
                    sid,
                    peek_id,
                    msg.get("value_hex"),
                    not decode_failed,
                ),
                file=sys.stderr,
            )

            if not decode_failed:
                return msg

            use_id = sid if wire == "confluent" else None
            if use_id is None and wire and "confluent" in str(wire) and peek_id:
                use_id = peek_id
            if not catalog or use_id is None:
                if peek_id and decode_failed:
                    print(
                        "# [{0}] peek_schema_id={1} не используем "
                        "(возможно не Confluent-header)".format(
                            cluster["name"], peek_id
                        ),
                        file=sys.stderr,
                    )
                return msg

            try:
                sch2 = schema_for(cluster, topic, schema_id=int(use_id))
            except Exception as e:
                print(
                    "# [{0}] schema by id failed: {1}".format(
                        cluster["name"], e
                    ),
                    file=sys.stderr,
                )
                return msg

            if raw is None:
                return msg
            data2 = try_parse(raw, avro_schema=sch2)
            data2, wire_meta = _split_wire_meta(data2)
            out = dict(msg)
            out["value"] = data2
            out["wire"] = wire_meta.get("wire") or out.get("wire")
            if wire_meta.get("schema_id") is not None:
                out["schema_id"] = wire_meta.get("schema_id")
            if isinstance(data2, dict) and data2.get("_error"):
                out["decode_error"] = data2.get("_error")
            else:
                out["decode_error"] = None
            return out

        def try_kafka(cluster, topic, from_end, partition, offset):
            src = cluster["name"]
            unwrap_names.append(src)
            if key is None and offset is None:
                soft_fail(
                    src,
                    "нужен key или offset для [{0}]".format(name),
                )
                return
            try:
                sch = schema_for(cluster, topic)
                msg = read_and_fix_schema(
                    cluster,
                    topic,
                    sch,
                    offset=offset,
                    from_end=from_end,
                    partition=int(partition or 0),
                    key=key,
                    field=field,
                    key_contains=bool(pair_key_contains),
                    max_messages=max_messages,
                )
                sources[src] = msg.get("value")
                offsets[src] = {
                    "topic": topic,
                    "offset": msg.get("offset"),
                    "partition": msg.get("partition"),
                    "schema_id": msg.get("schema_id"),
                    "peek_schema_id": msg.get("peek_schema_id"),
                    "wire": msg.get("wire"),
                    "hex": msg.get("value_hex"),
                    "key": msg.get("key"),
                    "decode_error": msg.get("decode_error"),
                    "found": True,
                    "payload": (
                        list(msg["value"].keys())[:20]
                        if isinstance(msg.get("value"), dict)
                        else type(msg.get("value")).__name__
                    ),
                }
            except (Exception, SystemExit) as e:
                soft_fail(src, e)
                offsets[src]["topic"] = topic

        try_kafka(
            left,
            left_topic,
            left_from_end,
            pair.get("left_partition"),
            pair.get("left_offset"),
        )
        try_kafka(
            right,
            right_topic,
            right_from_end,
            pair.get("right_partition"),
            pair.get("right_offset"),
        )

        pair_oracle = pair.get("oracle")
        if pair_oracle:
            try:
                if resolve_pair_oracle is None or fetch_pair_rows is None:
                    raise SystemExit("oracle_source не загружен")
                resolved = resolve_pair_oracle(pair_oracle, global_oracle)
                conn = ensure_oracle()
                print(
                    "# Oracle {0} / {1} pk={2} key={3!r}".format(
                        resolved["sct_fqn"],
                        resolved["soh_fqn"],
                        resolved["pk_column"],
                        key,
                    ),
                    file=sys.stderr,
                )
                ts_shift = (
                    resolve_ts_shift_hours(global_oracle)
                    if resolve_ts_shift_hours is not None
                    else -3
                )
                print(
                    "# Oracle TIMESTAMP shift_hours={0}".format(ts_shift),
                    file=sys.stderr,
                )
                sct_row, soh_row = fetch_pair_rows(
                    conn, resolved, key, ts_shift_hours=ts_shift
                )
                sct_name = resolved["sct_name"]
                soh_name = resolved["soh_name"]
                sources[sct_name] = sct_row
                sources[soh_name] = soh_row
                offsets[sct_name] = {
                    "fqn": resolved["sct_fqn"],
                    "pk": resolved["pk_column"],
                    "found": sct_row is not None,
                }
                offsets[soh_name] = {
                    "fqn": resolved["soh_fqn"],
                    "pk": resolved["pk_column"],
                    "found": soh_row is not None,
                }
                oracle_meta = {
                    sct_name: resolved["sct_fqn"],
                    soh_name: resolved["soh_fqn"],
                    "pk_column": resolved["pk_column"],
                    "prefix": resolved["prefix"],
                }
                if sct_row is None:
                    warnings.append(
                        "{0}: нет строки".format(resolved["sct_fqn"])
                    )
                    print(
                        "# warning: нет строки в {0}".format(
                            resolved["sct_fqn"]
                        ),
                        file=sys.stderr,
                    )
                if soh_row is None:
                    warnings.append(
                        "{0}: нет строки".format(resolved["soh_fqn"])
                    )
                    print(
                        "# warning: нет строки в {0}".format(
                            resolved["soh_fqn"]
                        ),
                        file=sys.stderr,
                    )
            except (Exception, SystemExit) as e:
                # Oracle целиком не вышел — колонки всё равно как пустые (—)
                try:
                    resolved = resolve_pair_oracle(pair_oracle, global_oracle)  # type: ignore
                    for nm, fqn in (
                        (resolved["sct_name"], resolved["sct_fqn"]),
                        (resolved["soh_name"], resolved["soh_fqn"]),
                    ):
                        soft_fail(nm, e)
                        offsets[nm]["fqn"] = fqn
                except (Exception, SystemExit):
                    soft_fail("oracle", e)

        found_any = any(v is not None for v in sources.values())
        if not found_any:
            item["ошибка"] = "; ".join(warnings) or "ни в одном источнике не найдено"
            print("# ошибка: {0}".format(item["ошибка"]), file=sys.stderr)
        else:
            try:
                payload_field = (
                    pair.get("payload_field")
                    or cfg.get("payload_field")
                    or "auto"
                )
                cmp_ = compare_sources(
                    sources,
                    payload_field=str(payload_field),
                    unwrap_names=unwrap_names,
                )
                item["сравнение"] = cmp_
                item["смещения"] = offsets
                item["oracle"] = oracle_meta
                if warnings:
                    item["предупреждения"] = warnings
                if cfg.get("show_values"):
                    item["значения"] = sources
                print("# итог: {0}".format(cmp_["итог"]), file=sys.stderr)
                if warnings:
                    print(
                        "# частично: {0}".format("; ".join(warnings)),
                        file=sys.stderr,
                    )
            except Exception as e:
                item["ошибка"] = str(e)
                item["смещения"] = offsets
                if warnings:
                    item["предупреждения"] = warnings
                print("# ошибка: {0}".format(e), file=sys.stderr)
                if cfg.get("debug"):
                    traceback.print_exc()

        results.append(item)

    if oracle_conn is not None:
        try:
            oracle_conn.close()
        except Exception:
            pass

    written = write_reports(
        results,
        output,
        meta={
            "конфиг": str(Path(args.config).resolve()),
            "левый_кластер": left.get("name"),
            "правый_кластер": right.get("name"),
            "oracle": bool(global_oracle),
        },
    )
    print("\n# отчёт:", file=sys.stderr)
    for w in written:
        print("#   {0}".format(w), file=sys.stderr)
    print(
        json.dumps(
            {
                "отчёт": written,
                "пар": len(results),
                "с_различиями": sum(
                    1
                    for r in results
                    if r.get("сравнение", {}).get("итог") == "есть различия"
                ),
                "ошибки": sum(1 for r in results if r.get("ошибка")),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
