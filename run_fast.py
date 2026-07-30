"""Fast scraper: single pass, no multi-account retries, exports DB to CSV."""
import csv, json, sqlite3, sys, threading, time, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from requests.exceptions import HTTPError

sys.path.insert(0, str(Path(__file__).parent))
import config, db, server
import track_failures
import network as net, validate_license

ERROR_MAP = [("MERCHANT", 201), ("Captcha", 202), ("gaierror", 102), ("Timeout", 104),
    ("Refused", 101), ("Connection", 103), ("403", 403)]

# 50 unique user agents — one per parallel worker.
# Covers Chrome/Firefox/Edge/Safari across Windows, macOS, Linux.
USER_AGENTS = [
    # Chrome / Windows (10)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.122 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.129 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.185 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.216 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.199 Safari/537.36",
    # Chrome / macOS (5)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.122 Safari/537.36",
    # Chrome / Linux (5)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox / Windows (5)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    # Firefox / macOS (5)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4; rv:128.0) Gecko/20100101 Firefox/128.0",
    # Firefox / Linux (5)
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    # Safari / macOS (5)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    # Edge / Windows (5)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.122 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    # Opera (5)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/111.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 OPR/110.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/111.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/111.0.0.0",
]

def classify_error(exception):
    error_string = str(exception)
    if isinstance(exception, HTTPError):
        return exception.response.status_code
    for pattern, code in ERROR_MAP:
        if pattern in error_string:
            return code
    if "login" in error_string.lower(): return 304
    return 301

# Vary cloudscraper browser fingerprints across workers for extra identity diversity.
BROWSER_CONFIGS = [
    {"browser": "chrome",  "platform": "windows", "desktop": True},
    {"browser": "chrome",  "platform": "darwin",  "desktop": True},
    {"browser": "chrome",  "platform": "linux",   "desktop": True},
    {"browser": "firefox", "platform": "windows", "desktop": True},
    {"browser": "firefox", "platform": "darwin",  "desktop": True},
    {"browser": "firefox", "platform": "linux",   "desktop": True},
    {"browser": "chrome",  "platform": "windows", "desktop": True, "mobile": False},
    {"browser": "chrome",  "platform": "darwin",  "desktop": True, "mobile": False},
    {"browser": "firefox", "platform": "windows", "desktop": True, "mobile": False},
    {"browser": "chrome",  "platform": "linux",   "desktop": True, "mobile": False},
]


def process_bonus(bonus, merchant_name, url, fingerprint, perceived_value, expiry):
    existing = db.execute("SELECT uid, mirrors FROM b WHERE fp=?", (fingerprint,))
    if existing:
        uid, mirrors = existing[0]
        if url not in str(mirrors):
            db.execute("UPDATE b SET mirrors=?, sl=CURRENT_TIMESTAMP WHERE uid=?", (f"{mirrors},{url}", uid))
        return uid, 0
    unique_id = f"{url}|{bonus.get('id')}"
    expiry_str = expiry.isoformat() if expiry else None
    db.execute(
        "REPLACE INTO b(uid, eid, u, v, pv, raw, exp, fp, mirrors, sl, mname, name) VALUES (?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,?,?)",
        (unique_id, bonus.get("id"), url, str(bonus.get("amount", 0)), perceived_value,
         json.dumps(bonus), expiry_str, fingerprint, url, merchant_name, bonus.get("name")))
    return unique_id, 1

def try_scrape(scraper_session, url, username, password):
    html_content = net.get_page(scraper_session, url)
    if not html_content or len(html_content) < 100:
        raise ValueError("Page too short or empty")
    merchant_id, merchant_name = net.parse_merchant_info(html_content)
    db.execute("UPDATE t SET m=? WHERE u=?", (merchant_name, url))
    api_url = net.build_api_url(url)

    session_data = db.load_session(url, username)
    user_data = None
    if session_data:
        try:
            ts = session_data["ts"]
            if ts:
                import datetime as dt
                timestamp = dt.datetime.fromisoformat(ts).replace(tzinfo=dt.timezone.utc)
                if (dt.datetime.now(dt.timezone.utc) - timestamp).total_seconds() < 21600:
                    scraper_session.cookies.update(session_data["ck"])
                    user_data = session_data["data"]
        except: pass

    if not user_data:
        user_data = net.login(scraper_session, api_url, username, password, merchant_id)
        db.save_session(url, username, scraper_session.cookies.get_dict(), user_data)

    try:
        sync_response = net.sync_user_data(scraper_session, api_url, merchant_id, user_data.get("token"), user_data.get("id"))
    except:
        user_data = net.login(scraper_session, api_url, username, password, merchant_id)
        db.save_session(url, username, scraper_session.cookies.get_dict(), user_data)
        sync_response = net.sync_user_data(scraper_session, api_url, merchant_id, user_data.get("token"), user_data.get("id"))

    bonuses = sync_response.get("data", {}).get("bonus", []) + sync_response.get("data", {}).get("promotions", [])
    new_count = 0
    for bonus in bonuses:
        normalized = {k.lower(): v for k, v in bonus.items()}
        if db.float_value(normalized.get("amount")) <= 0:
            continue
        perceived_val = db.perceived_value(normalized)
        expiry = db.parse_expiry(str(normalized.get("name", "")) + str(normalized.get("claimcondition", "")))
        fingerprint = db.fingerprint_bonus(normalized)
        _, is_new = process_bonus(normalized, merchant_name, url, fingerprint, perceived_val, expiry)
        new_count += is_new

    db.execute("UPDATE t SET ts=CURRENT_TIMESTAMP, ec=200 WHERE u=?", (url,))
    track_failures.record_success(url)
    return True, len(bonuses), new_count


def worker(worker_id, tasks, stats, lock, total):
    """Scrape a chunk of URLs with a pinned UA and browser fingerprint."""
    import random

    # Each of the 50 workers gets its own unique user agent
    browser_cfg = BROWSER_CONFIGS[worker_id % len(BROWSER_CONFIGS)]
    ua = USER_AGENTS[worker_id % len(USER_AGENTS)]

    scraper_session = net.create_session(browser_config=browser_cfg)
    scraper_session.headers.update({"User-Agent": ua})

    for idx, (url, username, password) in enumerate(tasks):
        with lock:
            stats["processed"] += 1
            current = stats["processed"]

        db.execute("INSERT OR IGNORE INTO t(u) VALUES (?)", (url,))
        time.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

        success = False
        bonus_count = 0
        new_count = 0
        error_code = 301

        for attempt in range(3):
            try:
                if attempt > 0:
                    # On retry, rotate UA and browser fingerprint
                    new_id = worker_id + attempt
                    browser_cfg = BROWSER_CONFIGS[new_id % len(BROWSER_CONFIGS)]
                    ua = USER_AGENTS[new_id % len(USER_AGENTS)]
                    scraper_session = net.create_session(browser_config=browser_cfg)
                    scraper_session.headers.update({"User-Agent": ua})
                    time.sleep(2 ** attempt * 2)
                success, bonus_count, new_count = try_scrape(scraper_session, url, username, password)
                break
            except Exception as exc:
                if attempt == 2:
                    error_code = classify_error(exc)
                    db.execute("UPDATE t SET ts=CURRENT_TIMESTAMP, ec=? WHERE u=?", (error_code, url))
                    track_failures.record_failure(url)

        with lock:
            if success:
                stats["successes"] += 1
                stats["bonuses"] += bonus_count
                stats["new"] += new_count
            else:
                stats["failures"] += 1

            if current % 50 == 0 or current == total:
                pct = current / total * 100
                rate = stats["successes"] / current * 100 if current > 0 else 0
                print(f"[{current}/{total}] {pct:.0f}% | OK:{stats['successes']}({rate:.1f}%) FAIL:{stats['failures']} BONUSES:{stats['bonuses']} NEW:{stats['new']}", flush=True)


def export_db_to_csv():
    conn = sqlite3.connect('data/base.db')
    c = conn.cursor()
    HEADERS = ['url','mname','id','name','transactiontype','bonusfixed','amount','minwithdraw','maxwithdraw','rollover','balance','claimconfig','claimcondition','bonus','bonusrandom','reset','mintopup','maxtopup','referlink','perceived_value','is_new']
    c.execute('SELECT uid, eid, u, v, pv, raw, exp, fp, mirrors, s1, sl, mname, name FROM b')
    rows = c.fetchall()
    with open('data/Dayne_Bonuses.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for row in rows:
            uid, eid, u, v, pv, raw_json, exp, fp, mirrors, s1, sl, mname, name = row
            try: bonus = json.loads(raw_json) if raw_json else {}
            except: bonus = {}
            n = {k.lower(): val for k, val in bonus.items()} if bonus else {}
            writer.writerow({'url': u, 'mname': mname or '', 'id': eid or '', 'name': name or '',
                'transactiontype': n.get('transactiontype', ''), 'bonusfixed': n.get('bonusfixed', ''),
                'amount': v if v else n.get('amount', ''), 'minwithdraw': n.get('minwithdraw', ''),
                'maxwithdraw': n.get('maxwithdraw', ''), 'rollover': n.get('rollover', ''),
                'balance': n.get('balance', ''), 'claimconfig': n.get('claimconfig', ''),
                'claimcondition': n.get('claimcondition', ''), 'bonus': n.get('bonus', ''),
                'bonusrandom': n.get('bonusrandom', ''), 'reset': n.get('reset', ''),
                'mintopup': n.get('mintopup', ''), 'maxtopup': n.get('maxtopup', ''),
                'referlink': n.get('referlink', ''), 'perceived_value': pv if pv else '',
                'is_new': 1 if sl and sl == s1 else 0})
    print(f"\nExported {len(rows)} bonuses to data/Dayne_Bonuses.csv")


def main():
    Path("data").mkdir(parents=True, exist_ok=True)
    db.initialize_database()
    try: db.execute("ALTER TABLE t ADD COLUMN ec INTEGER")
    except: pass
    import os
    # Path already imported at top level
    lic = {"data_level": "basic"}
    os.environ["SCRAPER_DATA_LEVEL"] = lic.get("data_level", "basic")
    Path("data/license_active.json").write_text(__import__("json").dumps(lic, indent=2, default=str))

    import server as srv
    srv.STOPPED = False
    srv.PAUSED = False

    url_list, account_list = config.parse_urls_and_accounts(shuffle=True)
    # Skip URLs with ec=200 in last 24h
    from datetime import datetime, timezone, timedelta
    completed = {r[0] for r in db.execute("SELECT u FROM t WHERE ts > date('now','-1 day') AND ec=200")}
    url_list = [u for u in url_list if u not in completed]

    workers = min(config.config_parser.getint("SETTINGS", "workers", fallback=6), len(url_list))
    print(f"URLs to scrape: {len(url_list)} (skipped {len(completed)} recently successful)")
    print(f"Accounts: {len(account_list)}, Workers: {workers}")

    if not url_list:
        print("Nothing to scrape!")
        export_db_to_csv()
        return

    # Distribute accounts round-robin so each task uses a different account
    tasks = [(url, account_list[i % len(account_list)][0], account_list[i % len(account_list)][1]) for i, url in enumerate(url_list)]
    chunks = [tasks[i::workers] for i in range(workers)]

    stats = {"processed": 0, "successes": 0, "failures": 0, "bonuses": 0, "new": 0}
    lock = threading.Lock()
    total = len(tasks)

    start = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for i, chunk in enumerate(chunks):
            executor.submit(worker, i, chunk, stats, lock, total)

    elapsed = time.time() - start
    print(f"\nCompleted in {elapsed/60:.1f} minutes")
    print(f"Processed: {stats['processed']}, Success: {stats['successes']}, Failed: {stats['failures']}")
    print(f"Bonuses found: {stats['bonuses']}, New: {stats['new']}")

    # Export DB to CSV
    export_db_to_csv()


if __name__ == "__main__":
    main()
