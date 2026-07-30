"""Benchmarking suite for the golf scraper engine.

Measures performance of core operations to track regression over time.

Usage:
    python -m tests.benchmark              # full suite
    python -m tests.benchmark --quick       # fast subset
    python -m tests.benchmark --json        # machine-readable output
"""
import argparse, json, time, statistics, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db, config, scraper, network as net

WARMUP = 3
RUNS = 10 if "--quick" not in sys.argv else 3

results = {}

def bench(name, fn, *args, runs=RUNS, warmup=WARMUP, **kwargs):
    # Warmup
    for _ in range(warmup):
        fn(*args, **kwargs)
    # Timed runs
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn(*args, **kwargs)
        times.append(time.perf_counter() - t0)
    avg = statistics.mean(times)
    med = statistics.median(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0
    results[name] = {"avg_ms": round(avg*1000, 3), "med_ms": round(med*1000, 3), "stdev_ms": round(stdev*1000, 3), "runs": runs}
    return results[name]

# ── BENCHMARKS ──

def bm_db_basics():
    db.execute("INSERT INTO t(u) VALUES (?)", ("https://bench-test.com",))
    db.execute("SELECT * FROM t WHERE u=?", ("https://bench-test.com",))
    db.execute("DELETE FROM t WHERE u=?", ("https://bench-test.com",))

def bm_filter_math():
    b = {"amount": "100", "maxwithdraw": "500", "minwithdraw": "50",
         "rollover": "30", "name": "Welcome Bonus 100%", "claimcondition": "2025-12-31"}
    db.perceived_value(b)
    db.fingerprint_bonus(b)
    db.parse_expiry("2025-12-31")
    db.float_value("123.45")

def bm_fuzzy_match():
    db.is_fuzzy_match("Welcome Bonus 100%", "Welcome Bonus 100%")
    db.is_fuzzy_match("First Deposit Match", "First Deposit 200% Match")

def bm_classify_error():
    for msg in ["MERCHANT not found", "Captcha blocked", "Timeout occurred",
                "Connection Refused", "Connection problem", "403 Forbidden",
                "login required", "None value", "random error"]:
        scraper.classify_error(ValueError(msg))

def bm_normalize_url():
    for url in ["https://www.example.com/path", "https://my-site.com",
                "http://www.test.com/a/b", "https://example.com"]:
        config.normalize_url(url)

# ── RUNNER ──

if __name__ == "__main__":
    bench("db_basics", bm_db_basics)
    bench("filter_math", bm_filter_math)
    bench("fuzzy_match", bm_fuzzy_match)
    bench("classify_error", bm_classify_error)
    bench("normalize_url", bm_normalize_url)

    use_json = "--json" in sys.argv
    if use_json:
        print(json.dumps(results, indent=2))
    else:
        print()
        print("╔════════════════════════════════════════════════════════╗")
        print("║           BENCHMARK RESULTS (avg over runs)          ║")
        print("╠════════════════════════════════════════════════════════╣")
        print(f"║  {'Benchmark':<24} {'avg (ms)':>10} {'med (ms)':>10} ║")
        print(f"║  {'─'*24} {'─'*10} {'─'*10} ║")
        for name, r in sorted(results.items()):
            bar = "█" * max(1, int(r["avg_ms"] * 2))
            print(f"║  {name:<24} {r['avg_ms']:>10.3f} {r['med_ms']:>10.3f}  {bar:<25}║")
        print(f"║  {'─'*24} {'─'*10} {'─'*10} ║")
        total = sum(r["avg_ms"] for r in results.values())
        print(f"║  {'TOTAL (all benchmarks)':<24} {total:>10.3f} {'':>10} ║")
        print("╚════════════════════════════════════════════════════════╝")
        print(f"  Runs per benchmark: {RUNS}  |  Warmup: {WARMUP}")
