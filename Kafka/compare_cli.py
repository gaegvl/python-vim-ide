#!/usr/bin/env python3
"""
Сравнение многих пар топиков между двумя кластерами Kafka.

  python compare_cli.py --config compare.json

В JSON:
  clusters.left / clusters.right — только подключения + schema_topic/schema_catalog
  pairs[] — пары топиков для сравнения
  output — путь к отчёту (.html + .json)
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Dict, Tuple

from compare import compare_messages
from reader import read_from_cluster
from report import write_reports
from schema_source import resolve_schema


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if "clusters" not in cfg or "left" not in cfg["clusters"] or "right" not in cfg["clusters"]:
        raise SystemExit("В конфиге нужны clusters.left и clusters.right")
    if not cfg.get("pairs") or not isinstance(cfg["pairs"], list):
        raise SystemExit("В конфиге нужен непустой массив pairs")
    return cfg


def main() -> int:
    p = argparse.ArgumentParser(description="Пакетное сравнение пар топиков двух Kafka")
    p.add_argument("--config", "-c", required=True, help="JSON с кластерами и pairs")
    args = p.parse_args()

    cfg = load_config(args.config)
    left = dict(cfg["clusters"]["left"])
    right = dict(cfg["clusters"]["right"])
    left.setdefault("name", "левый")
    right.setdefault("name", "правый")

    global_key = cfg.get("key")
    key_contains = bool(cfg.get("key_contains", True))
    max_messages = int(cfg.get("max_messages") or 500_000)
    global_from_end = cfg.get("from_end")
    output = cfg.get("output") or "compare_report.html"

    schema_cache = {}  # type: Dict[Tuple[str, str], object]

    def schema_for(cluster: dict, topic: str):
        # schema_key можно переопределить на пару через cluster copy
        cache_key = (cluster["name"], topic, cluster.get("schema_key"), cluster.get("schema_catalog"), cluster.get("schema_topic"))
        if cache_key not in schema_cache:
            print(f"# схема {cluster['name']} / {topic}", file=sys.stderr)
            c = dict(cluster)
            # для поиска схемы по умолчанию key = имя топика данных
            if not c.get("schema_key"):
                c["schema_key"] = topic
            schema_cache[cache_key] = resolve_schema(c, topic)
        return schema_cache[cache_key]

    results = []
    for i, pair in enumerate(cfg["pairs"], 1):
        name = pair.get("name") or f"Пара {i}"
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

        key = pair.get("key", global_key)
        # key_field не обязателен: поиск по Kafka key. null/нет поля = не используем
        field = pair.get("key_field", pair.get("field"))
        if field is None or field == "" or str(field).lower() == "none":
            field = ""
        left_from_end = pair.get("left_from_end", pair.get("from_end", global_from_end))
        right_from_end = pair.get("right_from_end", pair.get("from_end", global_from_end))

        print(f"\n# === [{i}/{len(cfg['pairs'])}] {name} ===", file=sys.stderr)
        print(f"# {left_topic}  vs  {right_topic}", file=sys.stderr)

        item = {
            "название": name,
            "левый_топик": left_topic,
            "правый_топик": right_topic,
            "ключ": key,
        }

        try:
            if key is None and pair.get("left_offset") is None:
                raise SystemExit("Нужен key (глобальный или в паре) либо left_offset/right_offset")

            sch_l = schema_for(left, left_topic)
            sch_r = schema_for(right, right_topic)

            msg_a = read_from_cluster(
                left,
                topic=left_topic,
                offset=pair.get("left_offset"),
                from_end=left_from_end,
                partition=int(pair.get("left_partition") or 0),
                key=key,
                field=field,
                key_contains=key_contains,
                max_messages=max_messages,
                avro_schema=sch_l,
            )
            msg_b = read_from_cluster(
                right,
                topic=right_topic,
                offset=pair.get("right_offset"),
                from_end=right_from_end,
                partition=int(pair.get("right_partition") or 0),
                key=key,
                field=field,
                key_contains=key_contains,
                max_messages=max_messages,
                avro_schema=sch_r,
            )

            payload_field = (
                pair.get("payload_field")
                or cfg.get("payload_field")
                or "auto"
            )
            cmp_ = compare_messages(
                msg_a["value"],
                msg_b["value"],
                name_a=left["name"],
                name_b=right["name"],
                payload_field=str(payload_field),
            )
            item["сравнение"] = cmp_
            item["смещения"] = {
                "левый": {
                    "offset": msg_a["offset"],
                    "partition": msg_a["partition"],
                    "schema_id": msg_a.get("schema_id"),
                    "key": msg_a.get("key"),
                },
                "правый": {
                    "offset": msg_b["offset"],
                    "partition": msg_b["partition"],
                    "schema_id": msg_b.get("schema_id"),
                    "key": msg_b.get("key"),
                },
            }
            if cfg.get("show_values"):
                item["значения"] = {"левый": msg_a["value"], "правый": msg_b["value"]}
            print(f"# итог: {cmp_['итог']}", file=sys.stderr)
        except Exception as e:
            item["ошибка"] = str(e)
            print(f"# ошибка: {e}", file=sys.stderr)
            if cfg.get("debug"):
                traceback.print_exc()

        results.append(item)

    written = write_reports(
        results,
        output,
        meta={
            "конфиг": str(Path(args.config).resolve()),
            "левый_кластер": left.get("name"),
            "правый_кластер": right.get("name"),
            "ключ": global_key,
        },
    )
    print("\n# отчёт:", file=sys.stderr)
    for w in written:
        print(f"#   {w}", file=sys.stderr)
    # краткая сводка в stdout
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
