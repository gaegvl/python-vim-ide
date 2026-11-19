#!/usr/bin/env python3
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
    p.add_argument("--field", default="task_id")
    p.add_argument("--max-messages", type=int, default=500_000)
    p.add_argument("--meta", action="store_true")
    p.add_argument("--raw", action="store_true")
    args = p.parse_args()

    cluster = CLUSTERS[args.cluster]
    # bootstrap берётся из cluster["bootstrap"] внутри read_from_cluster → prepare_ssl_files/build_ssl_conf

    result = read_from_cluster(
        cluster,
        topic=args.topic,
        offset=args.offset,
        from_end=args.from_end,
        partition=args.partition,
        key=args.key,
        field=args.field,
        max_messages=args.max_messages,
        with_meta=args.meta or True,
    )

    payload = result if args.meta else result.get("value", result)
    if args.raw and not args.meta:
        v = result.get("value", result)
        print(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
    else:
        print(json.dumps(payload if args.meta else result["value"], ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
