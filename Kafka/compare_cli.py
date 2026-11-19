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
from typing import Any, Dict, Optional, Tuple

from compare import compare_sources
from reader import read_from_cluster, try_parse
from report import write_reports
from schema_source import resolve_schema

try:
    from oracle_source import connect as oracle_connect
    from oracle_source import fetch_pair_rows, resolve_pair_oracle
except ImportError:
    oracle_connect = None  # type: ignore
    fetch_pair_rows = None  # type: ignore
    resolve_pair_oracle = None  # type: ignore


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

        try:
            if key is None and pair.get("left_offset") is None:
                raise SystemExit(
                    "У пары [{0}] нужен свой key (или left_offset/right_offset)".format(
                        name
                    )
                )

            sch_l = schema_for(left, left_topic)
            sch_r = schema_for(right, right_topic)

            def read_and_fix_schema(cluster, topic, sch, **kwargs):
                """
                Читаем сообщение, затем при наличии schema_catalog
                передекодируем строго по schema_id из Confluent-заголовка.
                Иначе subject-match часто даёт другую версию → пустой 610_5.
                """
                msg = read_from_cluster(
                    cluster, topic=topic, avro_schema=sch, **kwargs
                )
                sid = msg.get("schema_id")
                val = msg.get("value")
                if sid is None and isinstance(val, dict):
                    sid = val.get("_schema_id")
                catalog = cluster.get("schema_catalog")
                raw = msg.get("raw_value")

                def apply_schema(sch2, reason):
                    if raw is None:
                        return msg
                    print(
                        "# [{0}] decode with schema_id={1} ({2})".format(
                            cluster["name"], sid, reason
                        ),
                        file=sys.stderr,
                    )
                    data2 = try_parse(raw, avro_schema=sch2)
                    out = dict(msg)
                    out["value"] = data2
                    out["schema_id"] = sid
                    if isinstance(data2, dict) and data2.get("_error"):
                        out["decode_error"] = data2.get("_error")
                        print(
                            "# [{0}] decode still failing: {1}".format(
                                cluster["name"], data2.get("_error")
                            ),
                            file=sys.stderr,
                        )
                    else:
                        out["decode_error"] = None
                        if isinstance(data2, dict):
                            print(
                                "# [{0}] decode ok, keys={1}".format(
                                    cluster["name"],
                                    list(data2.keys())[:12],
                                ),
                                file=sys.stderr,
                            )
                    return out

                decode_failed = (
                    isinstance(val, dict)
                    and val.get("_binary")
                    and val.get("_error")
                )

                if catalog and sid is not None:
                    try:
                        sch2 = schema_for(cluster, topic, schema_id=int(sid))
                    except SystemExit as e:
                        print(
                            "# [{0}] нет схемы id={1} в catalog: {2}".format(
                                cluster["name"], sid, e
                            ),
                            file=sys.stderr,
                        )
                        if decode_failed:
                            # оставим ошибку decode + подсказку
                            bad = dict(val)
                            bad["_error"] = (
                                "{0}; в schema_catalog нет id={1} "
                                "(проверьте экспорт Registry)".format(
                                    val.get("_error"), sid
                                )
                            )
                            msg = dict(msg)
                            msg["value"] = bad
                            msg["decode_error"] = bad["_error"]
                        return msg
                    except Exception as e:
                        print(
                            "# [{0}] schema by id failed: {1}".format(
                                cluster["name"], e
                            ),
                            file=sys.stderr,
                        )
                        return msg
                    return apply_schema(
                        sch2,
                        "retry" if decode_failed else "prefer wire id",
                    )

                return msg

            read_kw_l = dict(
                offset=pair.get("left_offset"),
                from_end=left_from_end,
                partition=int(pair.get("left_partition") or 0),
                key=key,
                field=field,
                key_contains=bool(pair_key_contains),
                max_messages=max_messages,
            )
            read_kw_r = dict(
                offset=pair.get("right_offset"),
                from_end=right_from_end,
                partition=int(pair.get("right_partition") or 0),
                key=key,
                field=field,
                key_contains=bool(pair_key_contains),
                max_messages=max_messages,
            )
            msg_a = read_and_fix_schema(left, left_topic, sch_l, **read_kw_l)
            msg_b = read_and_fix_schema(right, right_topic, sch_r, **read_kw_r)

            sources = {
                left["name"]: msg_a["value"],
                right["name"]: msg_b["value"],
            }  # type: Dict[str, Any]
            unwrap_names = [left["name"], right["name"]]
            offsets = {
                left["name"]: {
                    "topic": left_topic,
                    "offset": msg_a["offset"],
                    "partition": msg_a["partition"],
                    "schema_id": msg_a.get("schema_id"),
                    "key": msg_a.get("key"),
                    "decode_error": msg_a.get("decode_error"),
                    "payload": (
                        list(msg_a["value"].keys())[:20]
                        if isinstance(msg_a.get("value"), dict)
                        else type(msg_a.get("value")).__name__
                    ),
                },
                right["name"]: {
                    "topic": right_topic,
                    "offset": msg_b["offset"],
                    "partition": msg_b["partition"],
                    "schema_id": msg_b.get("schema_id"),
                    "key": msg_b.get("key"),
                    "decode_error": msg_b.get("decode_error"),
                    "payload": (
                        list(msg_b["value"].keys())[:20]
                        if isinstance(msg_b.get("value"), dict)
                        else type(msg_b.get("value")).__name__
                    ),
                },
            }  # type: Dict[str, Any]
            oracle_meta = {}  # type: Dict[str, Any]

            pair_oracle = pair.get("oracle")
            if pair_oracle:
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
                sct_row, soh_row = fetch_pair_rows(conn, resolved, key)
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
                    print("# warning: нет строки в {0}".format(resolved["sct_fqn"]), file=sys.stderr)
                if soh_row is None:
                    print("# warning: нет строки в {0}".format(resolved["soh_fqn"]), file=sys.stderr)

            payload_field = (
                pair.get("payload_field") or cfg.get("payload_field") or "auto"
            )
            cmp_ = compare_sources(
                sources,
                payload_field=str(payload_field),
                unwrap_names=unwrap_names,
            )
            item["сравнение"] = cmp_
            item["смещения"] = offsets
            item["oracle"] = oracle_meta
            if cfg.get("show_values"):
                item["значения"] = sources
            print("# итог: {0}".format(cmp_["итог"]), file=sys.stderr)
        except Exception as e:
            item["ошибка"] = str(e)
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
