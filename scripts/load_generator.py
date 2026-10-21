#!/usr/bin/env python3
"""Generate synthetic HTTP traffic for the hospital cloud autoscaling baseline."""

from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class LoadStep:
    seconds: int
    concurrency: int
    iterations: int


PROFILES = {
    "normal": [LoadStep(120, 1, 10_000)],
    "high": [LoadStep(180, 8, 75_000)],
    "spike": [LoadStep(60, 1, 10_000), LoadStep(120, 12, 100_000), LoadStep(60, 1, 10_000)],
    "decreasing": [LoadStep(60, 12, 100_000), LoadStep(60, 6, 75_000), LoadStep(60, 2, 25_000)],
}


def request_loop(url: str, stop_at: float, iterations: int, counters: dict[str, int], lock: threading.Lock) -> None:
    while time.monotonic() < stop_at:
        try:
            with urllib.request.urlopen(f"{url}/work?iterations={iterations}", timeout=10) as response:
                response.read()
            with lock:
                counters["success"] += 1
        except (urllib.error.URLError, TimeoutError, OSError):
            with lock:
                counters["errors"] += 1


def run_step(url: str, step: LoadStep, counters: dict[str, int], lock: threading.Lock) -> None:
    stop_at = time.monotonic() + step.seconds
    workers = [
        threading.Thread(target=request_loop, args=(url, stop_at, step.iterations, counters, lock), daemon=True)
        for _ in range(step.concurrency)
    ]
    for worker in workers:
        worker.start()
    while time.monotonic() < stop_at:
        time.sleep(5)
        with lock:
            snapshot = dict(counters)
        print(json.dumps({"step_seconds": step.seconds, "concurrency": step.concurrency, **snapshot}), flush=True)
    for worker in workers:
        worker.join(timeout=15)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8001", help="Base URL of patient-service")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="spike")
    args = parser.parse_args()

    counters = {"success": 0, "errors": 0}
    lock = threading.Lock()
    print(json.dumps({"profile": args.profile, "url": args.url}), flush=True)
    for step in PROFILES[args.profile]:
        run_step(args.url.rstrip("/"), step, counters, lock)
    print(json.dumps({"complete": True, **counters}), flush=True)


if __name__ == "__main__":
    main()
