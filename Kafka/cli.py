#!/usr/bin/env python3
"""
Чтение из одной Kafka (простой CLI, без compare-конфига).

Примеры:
  python cli.py --cluster A --topic T --key UUID --from-end 50000
  python cli.py --cluster A --topic T --offset 175440 --meta
"""
from __future__ import annotations

import argparse
import json
import sys

from conf import CLUSTERS
from reader import read_from_cluster


def main() -> int:
    p = argparse.ArgumentParser(description="Чтение из одной Kafka")
    p.add_argument("--cluster", default="A", choices=sorted(CLUSTERS))
    p.add_argument("--topic", required=True)
    p.add_argument("--offset", type=int, default=None)
    p.add_argument("--from-end", type=int, default=None)
    p.add_argument("--partition", type=int, default=0)
    p.add_argument("--key", default=None)
    p.add_argument(
        "--key-contains",
        action="store_true",
        help="Искать вхождение --key в Kafka key (не точное равенство)",
    )
    p.add_argument("--field", default="task_id")
    p.add_argument("--max-messages", type=int, default=500_000)
    p.add_argument("--meta", action="store_true", help="Печатать topic/offset/key/value")
    p.add_argument("--raw", action="store_true", help="Только value, без indent")
    args = p.parse_args()

    if args.key is None and args.offset is None:
        raise SystemExit("Укажите --key и/или --offset")

    cluster = CLUSTERS[args.cluster]
    result = read_from_cluster(
        cluster,
        topic=args.topic,
        offset=args.offset,
        from_end=args.from_end,
        partition=args.partition,
        key=args.key,
        field=args.field,
        key_contains=args.key_contains,
        max_messages=args.max_messages,
        with_meta=True,
    )

    if args.meta:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        value = result.get("value", result)
        if args.raw:
            print(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str))
        else:
            print(json.dumps(value, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
