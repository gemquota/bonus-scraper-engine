import csv, datetime, json, random, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from requests.exceptions import HTTPError
import sys

import config, db, server
import network as net

RAW_DIR = Path("data/raw_responses")
TMP_DIR = Path("data")
DEBUG_DIR = Path("data/debug")

ERROR_MAP = [("MERCHANT", 201), ("Captcha", 202), ("gaierror", 102), ("Timeout", 104),
    ("Refused", 101), ("Connection", 103), ("403", 403)]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

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

def classify_error(exception):
    error_string = str(exception)
    if isinstance(exception, HTTPError):
        return exception.response.status_code
    for error_pattern, error_code in ERROR_MAP:
        if error_pattern in error_string:
            return error_code
    if "login" in error_string.lower():
        return 304
    if "None" in error_string:
        return 302
    return 301

def process_bonus(bonus, merchant_name, url, fingerprint, perceived_value, expiry):
    existing_records = db.execute("SELECT uid, mirrors FROM b WHERE fp=?", (fingerprint,))
    if existing_records:
        unique_id, mirrors = existing_records[0]
        if url not in str(mirrors):
            db.execute("UPDATE b SET mirrors=?, sl=CURRENT_TIMESTAMP WHERE uid=?", (f"{mirrors},{url}", unique_id))
        else:
            db.execute("UPDATE b SET sl=CURRENT_TIMESTAMP WHERE uid=?", (unique_id,))
        return unique_id, 0
        
    merchant_name_rows = db.execute("SELECT name, uid, mirrors FROM b WHERE mname=?", (merchant_name,))
    if merchant_name_rows:
        existing_names = [row[0] for row in merchant_name_rows if row[0]]
        matched_name = db.find_matching_name(bonus.get("name"), existing_names)
        if matched_name:
            matched_row = next((row for row in merchant_name_rows if row[0] == matched_name), None)
            if matched_row and url not in str(matched_row[2]):
                db.execute("UPDATE b SET mirrors=?, sl=CURRENT_TIMESTAMP WHERE uid=?", (f"{matched_row[2]},{url}", matched_row[1]))
            elif matched_row:
                db.execute("UPDATE b SET sl=CURRENT_TIMESTAMP WHERE uid=?", (matched_row[1],))
            return (matched_row[1] if matched_row else None), 0
            
    unique_id = f"{url}|{bonus.get('id')}"
    expiry_string = expiry.isoformat() if expiry else None
    db.execute(
        "REPLACE INTO b(uid, eid, u, v, pv, raw, exp, fp, mirrors, sl, mname, name) VALUES (?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,?,?)",
        (unique_id, bonus.get("id"), url, str(bonus.get("amount", 0)), perceived_value, json.dumps(bonus),
         expiry_string, fingerprint, url, merchant_name, bonus.get("name"))
    )
    return unique_id, 1

def try_scrape_url(scraper_session, url, username, password, record_raw, chunk_id):
    html_content = net.get_page(scraper_session, url)
    merchant_id, merchant_name = net.parse_merchant_info(html_content)
    db.execute("UPDATE t SET m=? WHERE u=?", (merchant_name, url))
    api_url = net.build_api_url(url)
    
    session_data = db.load_session(url, username)
    user_data = None
    if session_data:
        try:
            timestamp = datetime.datetime.fromisoformat(session_data["ts"]).replace(tzinfo=datetime.timezone.utc)
            if (datetime.datetime.now(datetime.timezone.utc) - timestamp).total_seconds() < 21600:
                scraper_session.cookies.update(session_data["ck"])
                user_data = session_data["data"]
        except Exception:
            pass
            
    if not user_data:
        user_data = net.login(scraper_session, api_url, username, password, merchant_id)
        db.save_session(url, username, scraper_session.cookies.get_dict(), user_data)
        
    try:
        sync_response = net.sync_user_data(scraper_session, api_url, merchant_id, user_data.get("token"), user_data.get("id"))
    except Exception:
        user_data = net.login(scraper_session, api_url, username, password, merchant_id)
        db.save_session(url, username, scraper_session.cookies.get_dict(), user_data)
        sync_response = net.sync_user_data(scraper_session, api_url, merchant_id, user_data.get("token"), user_data.get("id"))
        
    if record_raw:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        timestamp_string = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_url = url.replace("https://", "").replace("/", "_")
        (RAW_DIR / f"{timestamp_string}_{safe_url}.json").write_text(json.dumps(sync_response, indent=2))
        
    bonuses = sync_response.get("data", {}).get("bonus", []) + sync_response.get("data", {}).get("promotions", [])
    site_bonuses = 0
    site_new = 0
    
    csv_path = TMP_DIR / f"tmp_{chunk_id}.csv"
    
    for bonus in bonuses:
        normalized = {k.lower(): v for k, v in bonus.items()}
        if db.float_value(normalized.get("amount")) <= 0:
            continue
        site_bonuses += 1
        perceived_val = db.perceived_value(normalized)
        expiry = db.parse_expiry(str(normalized.get("name", "")) + str(normalized.get("claimcondition", "")))
        fingerprint = db.fingerprint_bonus(normalized)
        uid, is_new = process_bonus(normalized, merchant_name, url, fingerprint, perceived_val, expiry)
        site_new += is_new
        
        row_data = {k: normalized.get(k, normalized.get(k.upper(), "")) for k in db.HEADERS[:-2]}
        row_data["url"] = url
        row_data["mname"] = merchant_name
        row_data["perceived_value"] = perceived_val
        row_data["is_new"] = 1 if is_new else 0
        db.append_csv_row(row_data, str(csv_path))
        
    return True, html_content, site_bonuses, site_new

def worker(chunk_id, stats, stats_lock, total_tasks, pass_start, ip_score, record_raw, worker_count, tasks, proxy_pool, on_update):
    for task_idx, (url, username, password) in enumerate(tasks):
        if server.STOPPED:
            break
        while server.PAUSED and not server.STOPPED:
            time.sleep(0.5)
            
        with stats_lock["index"]:
            stats["index"] += 1
            current_index = stats["index"]
            
        db.execute("INSERT OR IGNORE INTO t(u) VALUES (?)", (url,))
        start_time = time.perf_counter()
        time.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        
        html_content = ""
        success = False
        error_code = 301
        exception = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(random.uniform(2.0, 4.0) * attempt)
                # Fresh session per URL — unique UA + browser fingerprint combo
                combo_idx = chunk_id * 1000 + task_idx * 3 + attempt
                browser_cfg = BROWSER_CONFIGS[combo_idx % len(BROWSER_CONFIGS)]
                scraper_session = net.create_session(browser_config=browser_cfg)
                scraper_session.headers.update({"User-Agent": USER_AGENTS[combo_idx % len(USER_AGENTS)]})
                scraper_session.timeout = config.TIMEOUT + (attempt * 10)

                success, html_content, site_bonuses, site_new = try_scrape_url(
                    scraper_session, url, username, password, record_raw, chunk_id
                )
                break
                
            except Exception as exc:
                exception = exc
                if attempt == max_retries - 1:
                    error_code = classify_error(exception)
                    db.execute("UPDATE t SET ts=CURRENT_TIMESTAMP, ec=? WHERE u=?", (error_code, url))
                    stats["failures"] += 1
                    
                    if error_code in (201, 202, 302):
                        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                        safe_url = url.replace("https://", "").replace("/", "_")
                        timestamp_string = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        if html_content:
                            (DEBUG_DIR / f"E{error_code}_{timestamp_string}_{safe_url}.html").write_text(html_content)
                            
                    db.log_event(f"E{error_code}", url, str(exception))
                else:
                    continue
                    
        if success:
            with stats_lock["stats"]:
                stats["total_bonuses"] += site_bonuses
                stats["successes"] += 1
                stats["new_bonuses"] += site_new
                
            db.execute("UPDATE t SET ts=CURRENT_TIMESTAMP, ec=200 WHERE u=?", (url,))
            
            if on_update:
                on_update({
                    "index": current_index,
                    "successes": stats["successes"],
                    "failures": stats["failures"],
                    "total_bonuses": stats["total_bonuses"],
                    "site_url": url,
                    "status_message": "DONE",
                    "site_bonuses_gt_zero": site_bonuses,
                    "N": total_tasks,
                    "elapsed": time.perf_counter() - start_time,
                    "ip_score": ip_score,
                    "site_new_bonuses": site_new,
                    "total_new_bonuses": stats["new_bonuses"],
                    "nw": worker_count
                })
        elif on_update:
            on_update({
                "index": current_index,
                "successes": stats["successes"],
                "failures": stats["failures"],
                "total_bonuses": stats["total_bonuses"],
                "site_url": url,
                "status_message": f"E{error_code}",
                "site_bonuses_gt_zero": 0,
                "N": total_tasks,
                "elapsed": time.perf_counter() - start_time,
                "ip_score": ip_score,
                "error_details": str(exception),
                "total_new_bonuses": stats["new_bonuses"],
                "nw": worker_count
            })

        pos_in_pass = current_index - pass_start
        if pos_in_pass % 50 == 0 or pos_in_pass == total_tasks:
            with stats_lock["stats"]:
                ok = stats["successes"]
                fail = stats["failures"]
                bonuses = stats["total_bonuses"]
                newb = stats["new_bonuses"]
            rate = (ok / current_index * 100) if current_index else 0
            pct = (pos_in_pass / total_tasks * 100) if total_tasks else 0
            print(f"[{current_index}/{pass_start + total_tasks}] {pct:.0f}% | OK:{ok}({rate:.1f}%) FAIL:{fail} BONUSES:{bonuses} NEW:{newb}", flush=True)

def run_scrape(on_update=None, on_launcher=None, on_completion=None):
    resume_mode = "-r" in sys.argv
    shuffle_mode = "-s" in sys.argv
    record_raw_responses = "-v" in sys.argv and sys.argv[sys.argv.index("-v") + 1] == "max" if "-v" in sys.argv else False
    
    url_list, account_list = config.parse_urls_and_accounts(shuffle_mode)
    if resume_mode:
        completed_urls = {row[0] for row in db.execute("SELECT u FROM t WHERE ts > date('now','-1 day') AND ec=200")}
        url_list = [url for url in url_list if url not in completed_urls]
        
    if not url_list or not account_list:
        server.IS_RUNNING = False
        return

    Path("data/last_scrape_start.txt").write_text(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        
    execution_stats = {"index": 0, "successes": 0, "failures": 0, "total_bonuses": 0, "new_bonuses": 0}
    thread_locks = {"index": threading.Lock(), "stats": threading.Lock()}
    ip_score, _ = net.check_ip_reputation(config.ABUSEIPDB_KEY)
    proxy_list = config.load_proxies()
    
    run_timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    final_csv_path = TMP_DIR / f"bonuses_{run_timestamp}.csv"
    db._init_csv(str(final_csv_path))

    def process_url_batch(current_url_list, account_index=0):
        username, password = account_list[account_index]
        task_list = [(url, username, password) for url in current_url_list]
        max_workers = config.config_parser.getint("SETTINGS", "workers", fallback=10)
        num_workers = min(max_workers, len(task_list))
        task_chunks = [task_list[i::num_workers] for i in range(num_workers)]
        pass_start = execution_stats["index"]
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            for i in range(num_workers):
                executor.submit(
                    worker, i, execution_stats, thread_locks, len(task_list), pass_start,
                    ip_score, record_raw_responses, num_workers, task_chunks[i], 
                    proxy_list, on_update
                )
                
        for i in range(num_workers):
            temp_file_path = TMP_DIR / f"tmp_{i}.csv"
            if temp_file_path.exists():
                with temp_file_path.open(newline="") as csv_file:
                    for csv_row in csv.DictReader(csv_file, fieldnames=db.HEADERS):
                        db.append_csv_row(csv_row, str(final_csv_path))
                temp_file_path.unlink()

    if on_launcher:
        max_configured_workers = config.config_parser.getint("SETTINGS", "workers", fallback=10)
        on_launcher(len(url_list), len(proxy_list), min(max_configured_workers, len(url_list)), shuffle_mode, ip_score)
        
    process_url_batch(url_list)

    retry_error_codes = (101, 102, 103, 104, 201, 202, 301, 302, 304, 403)
    placeholders = ",".join("?" for _ in url_list)
    failed_urls = [row[0] for row in db.execute(f"SELECT u FROM t WHERE u IN ({placeholders}) AND ec IN (?,?,?,?,?,?,?,?,?,?)", (*url_list, *retry_error_codes)) if row[0]]
    
    if failed_urls and len(account_list) > 1:
        for account_index in range(1, len(account_list)):
            if not failed_urls:
                break
            process_url_batch(failed_urls, account_index)
            failed_placeholders = ",".join("?" for _ in failed_urls)
            failed_urls = [row[0] for row in db.execute(f"SELECT u FROM t WHERE u IN ({failed_placeholders}) AND ec IN (?,?,?,?,?,?,?,?,?,?)", (*failed_urls, *retry_error_codes)) if row[0]]

    server.IS_RUNNING = False
    if on_completion:
        on_completion(execution_stats)
