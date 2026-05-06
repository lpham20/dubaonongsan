from __future__ import annotations

import argparse
import statistics
import time
from urllib.request import Request, urlopen


DEFAULT_PATHS = [
    "/",
    "/api/v1/content/news?limit=24",
    "/api/v1/content/guides?limit=12",
    "/api/v1/analytics/ticker-prices?crop=sau_rieng&limit=60",
    "/api/v1/analytics/ticker-prices?crop=ca_phe&limit=60",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit basic production response times.")
    parser.add_argument("base_url", help="Base URL, for example https://example.com")
    parser.add_argument("--threshold-ms", type=float, default=2000)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    failures = []
    for path in DEFAULT_PATHS:
        url = f"{base_url}{path}"
        timings = []
        sizes = []
        for _ in range(args.runs):
            started = time.perf_counter()
            request = Request(url, headers={"User-Agent": "dubaonongsan-performance-audit/1.0"})
            with urlopen(request, timeout=15) as response:
                body = response.read()
                status = response.status
            elapsed_ms = (time.perf_counter() - started) * 1000
            timings.append(elapsed_ms)
            sizes.append(len(body))
            if status >= 400:
                failures.append(f"{path}: HTTP {status}")
        avg_ms = statistics.mean(timings)
        max_ms = max(timings)
        avg_kb = statistics.mean(sizes) / 1024
        print(f"{path:58s} avg={avg_ms:7.1f}ms max={max_ms:7.1f}ms size={avg_kb:7.1f}KB")
        if max_ms > args.threshold_ms:
            failures.append(f"{path}: max {max_ms:.1f}ms > {args.threshold_ms:.1f}ms")

    if failures:
        print("\nFAILED")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("\nPASSED")


if __name__ == "__main__":
    main()
