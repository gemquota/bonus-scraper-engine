"""Re-scrape oldurls.txt with 1 slow worker to confirm they're really dead."""
import sys, threading, time, random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config, db
import network as net
from run_fast import USER_AGENTS, BROWSER_CONFIGS, try_scrape, classify_error

OLD_URLS = Path("in/config/oldurls.txt")

def log(msg):
    print(msg, flush=True)

def worker(tasks, stats, lock):
    browser_cfg = BROWSER_CONFIGS[0]
    ua = USER_AGENTS[0]
    session = net.create_session(browser_config=browser_cfg)
    session.headers.update({"User-Agent": ua})

    for idx, (url, username, password) in enumerate(tasks):
        db.execute("INSERT OR IGNORE INTO t(u) VALUES (?)", (url,))
        time.sleep(random.uniform(5.0, 10.0))

        success = False
        for attempt in range(2):
            try:
                if attempt > 0:
                    session = net.create_session(browser_config=BROWSER_CONFIGS[attempt])
                    session.headers.update({"User-Agent": USER_AGENTS[attempt]})
                    time.sleep(2 ** attempt * 3)
                success, bc, nc = try_scrape(session, url, username, password)
                break
            except Exception as exc:
                if attempt == 1:
                    ec = classify_error(exc)
                    db.execute("UPDATE t SET ts=CURRENT_TIMESTAMP, ec=? WHERE u=?", (ec, url))
                    with lock:
                        stats["failures"] += 1

        with lock:
            if success:
                stats["successes"] += 1
                log(f"  ✅ {url} — ALIVE! bonuses={bc} new={nc}")
            else:
                stats["processed"] += 1
            s = stats
            done = s["processed"] + s["successes"]
            if done % 25 == 0:
                log(f"[{done}/{s['total']}] OK:{s['successes']} FAIL:{s['failures']}")

def main():
    if not OLD_URLS.exists():
        log("No oldurls.txt found")
        return

    urls = [l.strip() for l in OLD_URLS.read_text().splitlines() if l.strip()]
    _, accounts = config.parse_urls_and_accounts()
    if not accounts:
        log("No accounts")
        return

    tasks = [(url, accounts[i % len(accounts)][0], accounts[i % len(accounts)][1]) for i, url in enumerate(urls)]
    stats = {"processed": 0, "successes": 0, "failures": 0, "total": len(tasks)}
    lock = threading.Lock()

    log(f"Re-checking {len(tasks)} oldurls with 1 worker (5-10s delay)...")
    with ThreadPoolExecutor(max_workers=1) as ex:
        ex.submit(worker, tasks, stats, lock)

    log(f"\nDone. OK:{stats['successes']} FAIL:{stats['failures']} of {stats['total']}")

if __name__ == "__main__":
    main()
