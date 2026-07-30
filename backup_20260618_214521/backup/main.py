import csv, datetime, json, random, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from requests.exceptions import HTTPError

import config, db, network as net, ui

RAW_DIR = Path("data/raw_responses")
TMP_DIR = Path("data")
DEBUG_DIR = Path("data/debug")

ERROR_MAP = [("MERCHANT", 201), ("Captcha", 202), ("gaierror", 102), ("Timeout", 104),
    ("Refused", 101), ("Connection", 103), ("403", 403)]

def classify_error(exc):
    s = str(exc)
    if isinstance(exc, HTTPError): return exc.response.status_code
    for pattern, code in ERROR_MAP:
        if pattern in s: return code
    if "login" in s.lower(): return 304
    if "None" in s: return 302
    return 301

def process_bonus(bonus, merchant_name, url, fingerprint, perceived_value, expiry):
    existing = db.execute("SELECT uid, mirrors FROM b WHERE fp=?", (fingerprint,))
    if existing:
        uid, mirrors = existing[0]
        if url not in str(mirrors):
            db.execute("UPDATE b SET mirrors=?, sl=CURRENT_TIMESTAMP WHERE uid=?", (f"{mirrors},{url}", uid))
        return uid, 0
    name_rows = db.execute("SELECT name, uid, mirrors FROM b WHERE mname=?", (merchant_name,))
    if name_rows:
        existing_names = [row[0] for row in name_rows if row[0]]
        matched = db.find_matching_name(bonus.get("name"), existing_names)
        if matched:
            row = next((r for r in name_rows if r[0] == matched), None)
            if row and url not in str(row[2]):
                db.execute("UPDATE b SET mirrors=?, sl=CURRENT_TIMESTAMP WHERE uid=?", (f"{row[2]},{url}", row[1]))
            return (row[1] if row else None), 0
    uid = f"{url}|{bonus.get('id')}"
    db.execute("REPLACE INTO b(uid, eid, u, v, pv, raw, exp, fp, mirrors, sl, mname, name) VALUES (?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,?,?)",
        (uid, bonus.get("id"), url, str(bonus.get("amount", 0)), perceived_value, json.dumps(bonus),
         expiry.isoformat() if expiry else None, fingerprint, url, merchant_name, bonus.get("name")))
    return uid, 1

def worker(chunk_id, stats, stats_lock, total_tasks, ip_score, record_raw, worker_count, tasks):
    session = net.create_session()
    for url, username, password in tasks:
        if ui.STOPPED: break
        while ui.PAUSED and not ui.STOPPED: time.sleep(0.5)
        with stats_lock["index"]: stats["index"] += 1; idx = stats["index"]
        db.execute("INSERT OR IGNORE INTO t(u) VALUES (?)", (url,))
        start = time.perf_counter()
        time.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
        html = ""
        try:
            html = net.get_page(session, url)
            merchant_id, merchant_name = net.parse_merchant_info(html)
            db.execute("UPDATE t SET m=? WHERE u=?", (merchant_name, url))
            api_url = net.build_api_url(url)
            sd = db.load_session(url, username)
            user_data = None
            if sd:
                try:
                    ts = datetime.datetime.fromisoformat(sd["ts"]).replace(tzinfo=datetime.timezone.utc)
                    if (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds() < 21600:
                        session.cookies.update(sd["ck"]); user_data = sd["data"]
                except: pass
            if not user_data:
                user_data = net.login(session, api_url, username, password, merchant_id)
                db.save_session(url, username, session.cookies, user_data)
            try:
                sync = net.sync_user_data(session, api_url, merchant_id, user_data.get("token"), user_data.get("id"))
            except:
                user_data = net.login(session, api_url, username, password, merchant_id)
                db.save_session(url, username, session.cookies, user_data)
                sync = net.sync_user_data(session, api_url, merchant_id, user_data.get("token"), user_data.get("id"))
            if record_raw:
                RAW_DIR.mkdir(parents=True, exist_ok=True)
                (RAW_DIR / f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{url.replace('https://','').replace('/','_')}.json").write_text(json.dumps(sync, indent=2))
            bonuses = sync.get("data",{}).get("bonus",[]) + sync.get("data",{}).get("promotions",[])
            site_b = site_new = 0
            for b in bonuses:
                n = {k.lower(): v for k, v in b.items()}
                if db.float_value(n.get("amount")) <= 0: continue
                site_b += 1
                pv = db.perceived_value(n); exp = db.parse_expiry(str(n.get("name","")) + str(n.get("claimcondition","")))
                fp = db.fingerprint_bonus(n)
                uid, is_new = process_bonus(n, merchant_name, url, fp, pv, exp)
                site_new += is_new
                db.append_csv_row({k: n.get(k, n.get(k.upper(), "")) for k in db.HEADERS[:-2]} | {"url":url,"mname":merchant_name,"perceived_value":pv,"is_new":1 if is_new else 0},
                    f"data/tmp_{chunk_id}.csv")
            with stats_lock["stats"]: stats["total_bonuses"] += site_b; stats["successes"] += 1; stats["new_bonuses"] += site_new
            db.execute("UPDATE t SET ts=CURRENT_TIMESTAMP, ec=200 WHERE u=?", (url,))
            ui.update_display({"index": idx, "successes": stats["successes"], "total_bonuses": stats["total_bonuses"],
                "site_url": url, "status_message": "\u2705", "site_bonuses_gt_zero": site_b, "N": total_tasks,
                "elapsed": time.perf_counter()-start, "ip_score": ip_score, "site_new_bonuses": site_new,
                "total_new_bonuses": stats["new_bonuses"], "nw": worker_count})
        except Exception as exc:
            ec = classify_error(exc)
            db.execute("UPDATE t SET ts=CURRENT_TIMESTAMP, ec=? WHERE u=?", (ec, url))
            stats["failures"] += 1
            if ec in (201, 202, 302):
                DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                safe = url.replace("https://","").replace("/","_")
                (DEBUG_DIR / f"E{ec}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe}.html").write_text(html) if html else None
            db.log_event(f"E{ec}", url, str(exc))
            ui.update_display({"index": idx, "successes": stats["successes"], "failures": stats["failures"],
                "total_bonuses": stats["total_bonuses"], "site_url": url, "status_message": f"E{ec}",
                "site_bonuses_gt_zero": 0, "N": total_tasks, "elapsed": time.perf_counter()-start,
                "ip_score": ip_score, "error_details": str(exc), "total_new_bonuses": stats["new_bonuses"], "nw": worker_count})

def run_scrape():
    resume = "-r" in sys.argv; shuffle = "-s" in sys.argv; record_raw = "-v" in sys.argv and sys.argv[sys.argv.index("-v")+1] == "max" if "-v" in sys.argv else False
    urls, accounts = config.parse_urls_and_accounts(shuffle)
    if resume:
        done = {r[0] for r in db.execute("SELECT u FROM t WHERE ts > date('now','-1 day') AND ec=200")}
        urls = [u for u in urls if u not in done]
    stats = {"index": 0, "successes": 0, "failures": 0, "total_bonuses": 0, "new_bonuses": 0}
    locks = {"index": threading.Lock(), "stats": threading.Lock()}
    ip_score, _ = net.check_ip_reputation(config.ABUSEIPDB_KEY)
    proxies = config.load_proxies()
    for aidx, (username, password) in enumerate(accounts):
        if not urls or ui.STOPPED: break
        tasks = [(u, username, password) for u in urls]
        nw = min(10 if proxies else 1, len(tasks))
        ui.print_launcher(len(tasks), len(proxies), nw, shuffle, ip_score)
        ui.START_TIME = time.time()
        chunks = [tasks[i::nw] for i in range(nw)]
        with ThreadPoolExecutor(max_workers=nw) as ex:
            for i in range(nw): ex.submit(worker, i, stats, locks, len(tasks), ip_score, record_raw, nw, chunks[i])
        for i in range(nw):
            p = TMP_DIR / f"tmp_{i}.csv"
            if p.exists():
                with p.open(newline="") as f:
                    for row in csv.DictReader(f, fieldnames=db.HEADERS): db.append_csv_row(row)
                p.unlink()
        if aidx < len(accounts) - 1:
            ph = ",".join("?" for _ in urls)
            urls = [r[0] for r in db.execute(f"SELECT u FROM t WHERE u IN ({ph}) AND ec IN (?,?,?,?)", (*urls, 304, 202, 302, 403)) if r[0]]
    ui.IS_RUNNING = False
    ui.print_completion(stats)

def main():
    Path("data").mkdir(parents=True, exist_ok=True)
    db.initialize_database()
    try: db.execute("ALTER TABLE t ADD COLUMN ec INTEGER")
    except: pass
    if "-h" in sys.argv: print("Usage: python main.py [-v min|med|max] [-r] [-s]"); sys.exit(0)
    if "-v" in sys.argv:
        i = sys.argv.index("-v")
        if i+1 < len(sys.argv) and sys.argv[i+1] in ("med","max"): pass
    ui.IS_RUNNING = True
    threading.Thread(target=run_scrape, daemon=True).start()
    ui.start_server()

if __name__ == "__main__":
    try: main()
    except Exception as exc:
        db.log_event("FATAL", "500", str(exc))
        print(f"FATAL: {exc}", file=sys.stderr)
