#!/usr/bin/env python3
"""Continuously generate changing traffic against real UCI-backed admission endpoints."""
from __future__ import annotations

import argparse
import csv
import random
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


def load_ids(path: Path, limit: int) -> list[int]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        ids = list(range(1, min(limit, sum(1 for _ in rows)) + 1))
    if not ids:
        raise ValueError(f"No admission IDs found in {path}")
    return ids[:limit]


def request_loop(base_url: str, ids: list[int], stop_at: float, counters: dict[str, int], lock: threading.Lock, cpu_work_percent: int) -> None:
    paths = ["/patients/{id}", "/patients?limit=25", "/readyz"]
    while time.monotonic() < stop_at:
        path = (f"/work?iterations={random.choice([100000, 150000, 200000, 250000])}" if random.randrange(100) < cpu_work_percent else random.choice(paths).format(id=random.choice(ids)))
        try:
            with urllib.request.urlopen(f"{base_url}{path}", timeout=8) as response:
                response.read()
            with lock:
                counters["success"] += 1
        except (urllib.error.URLError, TimeoutError, OSError):
            with lock:
                counters["errors"] += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8001")
    parser.add_argument("--dataset", type=Path, default=Path("data/uci/diabetic_data_features.csv"))
    parser.add_argument("--minutes", type=float, default=30)
    parser.add_argument("--min-concurrency", type=int, default=1)
    parser.add_argument("--max-concurrency", type=int, default=12)
    parser.add_argument("--step-seconds", type=int, default=20)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--cpu-work-percent", type=int, default=25, help="Share of requests sent to the CPU workload endpoint")
    args = parser.parse_args()
    if args.min_concurrency < 1 or args.max_concurrency < args.min_concurrency:
        raise SystemExit("Concurrency bounds are invalid")
    if not 0 <= args.cpu_work_percent <= 100:
        raise SystemExit("cpu-work-percent must be between 0 and 100")
    if args.seed is not None:
        random.seed(args.seed)
    ids = load_ids(args.dataset, 10000)
    base_url = args.url.rstrip("/")
    stop_at = time.monotonic() + args.minutes * 60
    counters = {"success": 0, "errors": 0}
    lock = threading.Lock()
    current = args.min_concurrency
    direction = 1
    print(f"Using {len(ids)} real UCI admission IDs; traffic changes every {args.step_seconds}s", flush=True)
    while time.monotonic() < stop_at:
        step_end = min(stop_at, time.monotonic() + args.step_seconds)
        workers = [threading.Thread(target=request_loop, args=(base_url, ids, step_end, counters, lock, args.cpu_work_percent), daemon=True) for _ in range(current)]
        for worker in workers:
            worker.start()
        while time.monotonic() < step_end:
            time.sleep(5)
            with lock:
                snapshot = dict(counters)
            print({"concurrency": current, **snapshot}, flush=True)
        for worker in workers:
            worker.join(timeout=3)
        if current >= args.max_concurrency:
            direction = -1
        elif current <= args.min_concurrency:
            direction = 1
        current += direction * random.choice([1, 1, 2])
        current = max(args.min_concurrency, min(args.max_concurrency, current))
    print({"complete": True, **counters}, flush=True)


if __name__ == "__main__":
    main()
