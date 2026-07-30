"""
main.py - Main Entry Point

Multi-threaded scraper that authenticates with target sites,
fetches bonus data, and processes/stores results.
"""

import network
import parser
import auth
import api
import models
import io_manager
import config
import filter as f
import db
import ui
import network_health
import web_server

import json
import time
import random
import csv
import datetime
import threading
import concurrent.futures
import os
import sys
import requests


def process_bonus_deduplication(bonus, merchant_name, site_url, fingerprint, perceived_value, expiry):
    """
    Handle deduplication logic for a bonus.

    Deduplication uses two strategies:
    1. Exact fingerprint match - identical bonuses across sites
    2. Fuzzy name match - similar bonus names within same merchant

    If a duplicate is found, the site is added to the 'mirrors' field.
    Otherwise, a new bonus record is created.

    Args:
        bonus: Normalized bonus dictionary
        merchant_name: Name of the merchant
        site_url: URL of the current site
        fingerprint: SHA256 fingerprint of the bonus
        perceived_value: Calculated perceived value score
        expiry: Expiry datetime or None

    Returns:
        str: Existing UID if merged with duplicate, None if new bonus
    """
    # Strategy 1: Exact Fingerprint Match
    existing = db.query("SELECT uid, mirrors FROM b WHERE fp=?", (fingerprint,))
    if existing:
        uid, mirrors = existing[0]
        if site_url not in str(mirrors):
            new_mirrors = f"{mirrors},{site_url}"
            db.query("UPDATE b SET mirrors=?, sl=CURRENT_TIMESTAMP WHERE uid=?",
                     (new_mirrors, uid))
        return uid

    # Strategy 2: Fuzzy Name Match (within same merchant)
    existing_bonuses = db.query(
        "SELECT name, uid, mirrors FROM b WHERE mname=?",
        (merchant_name,)
    )
    existing_names = [row[0] for row in existing_bonuses if row[0]]

    fuzzy_match_name = f.is_fuzzy_duplicate(bonus.get('name'), existing_names)

    if fuzzy_match_name:
        # Find the matching record
        match_record = next(
            (row for row in existing_bonuses if row[0] == fuzzy_match_name),
            None
        )
        if match_record:
            uid, mirrors = match_record[1], match_record[2]
            if site_url not in str(mirrors):
                new_mirrors = f"{mirrors},{site_url}"
                db.query("UPDATE b SET mirrors=?, sl=CURRENT_TIMESTAMP WHERE uid=?",
                         (new_mirrors, uid))
            return uid

    # Strategy 3: No Match - Insert New Bonus
    uid = f"{site_url}|{bonus.get('id')}"
    expiry_str = expiry.isoformat() if expiry else None

    db.query(
        """REPLACE INTO b(uid, eid, u, v, pv, raw, exp, fp, mirrors, sl, mname, name)
           VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)""",
        (uid, bonus.get('id'), site_url, bonus.get('amount', 0), perceived_value,
         json.dumps(bonus), expiry_str, fingerprint, site_url, merchant_name,
         bonus.get('name'))
    )
    return None


def worker(tasks, worker_id, stats, locks, total_count, ip_score, save_raw):
    """
    Worker function that processes a list of scraping tasks.

    Each task is a (url, phone, password) tuple. The worker:
    1. Fetches the site HTML
    2. Extracts merchant details
    3. Logs in (or uses cached session)
    4. Fetches bonus data
    5. Processes and stores each bonus

    Args:
        tasks: List of (url, phone, password) tuples
        worker_id: Unique ID for this worker thread
        stats: Shared statistics dictionary
        locks: Dictionary of threading locks
        total_count: Total number of tasks across all workers
        ip_score: IP health score from AbuseIPDB
        save_raw: Whether to save raw API responses
    """
    session = network.create_session()
    tmp_path = f'data/tmp_{worker_id}.csv'
    io_manager.csv_init(models.CSV_HEADERS, tmp_path)

    # Australia/Brisbane timezone
    tz = datetime.timezone(datetime.timedelta(hours=10))

    for url, phone, password in tasks:
        # Update progress index
        with locks['idx']:
            stats['idx'] += 1
            current_idx = stats['idx']

        start_time = time.perf_counter()

        # Random delay between requests
        time.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

        try:
            # === Step 1: Fetch site HTML and extract merchant details ===
            html = network.get(session, url)
            merchant_id, merchant_name = parser.get_merchant_details(html)
            api_url = api.get_api_url(url)

            # Record site in database
            db.query("INSERT OR IGNORE INTO t(u, m) VALUES(?, ?)", (url, merchant_name))

            # === Step 2: Login (or use cached session) ===
            cached = io_manager.load_session(phone, url)
            user_data = None

            if cached:
                try:
                    timestamp = datetime.datetime.fromisoformat(cached['ts'])
                    timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
                    age_seconds = (datetime.datetime.now(datetime.timezone.utc) - timestamp).total_seconds()

                    # Use cache if less than 6 hours old
                    if age_seconds < 21600:
                        session.cookies.update(cached['ck'])
                        user_data = cached['data']
                except Exception:
                    pass

            if not user_data:
                user_data = auth.login(session, api_url, phone, password, merchant_id)
                io_manager.save_session(phone, url, session.cookies, user_data)

            # === Step 3: Fetch bonus data ===
            try:
                response = api.fetch_data(session, api_url, merchant_id,
                                          user_data.get('token'), user_data.get('id'))
            except Exception:
                # Session might be stale - re-login and retry
                user_data = auth.login(session, api_url, phone, password, merchant_id)
                io_manager.save_session(phone, url, session.cookies, user_data)
                response = api.fetch_data(session, api_url, merchant_id,
                                          user_data.get('token'), user_data.get('id'))

            # Save raw response if requested
            if save_raw:
                try:
                    os.makedirs('data/raw_responses', exist_ok=True)
                    timestamp_slug = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    url_slug = url.replace('https://', '').replace('/', '_')
                    with open(f'data/raw_responses/{timestamp_slug}_{url_slug}.json', 'w',
                              encoding='utf-8') as f_raw:
                        json.dump(response, f_raw, indent=2)
                except Exception:
                    pass

            # === Step 4: Process bonuses ===
            data = response.get('data', {})
            bonuses = data.get('bonus', []) + data.get('promotions', [])
            site_bonus_count = len(bonuses)
            has_expiring = False

            for bonus in bonuses:
                # Normalize keys to lowercase
                normalized = models.normalize_bonus(bonus)

                # Calculate metrics
                perceived_value = f.calculate_perceived_value(normalized)
                expiry = f.extract_expiry(
                    str(normalized.get('name', '')) + str(normalized.get('claimcondition', ''))
                )
                fingerprint = f.generate_fingerprint(normalized)

                # Check if expiring within 48 hours
                if expiry:
                    time_until_expiry = (expiry - datetime.datetime.now(tz)).total_seconds()
                    if time_until_expiry < 172800:  # 48 hours
                        has_expiring = True

                # Deduplicate and store
                process_bonus_deduplication(
                    normalized, merchant_name, url, fingerprint, perceived_value, expiry
                )

                # Write to CSV
                row = models.create_row(normalized, url, merchant_name, perceived_value, 1)
                io_manager.csv_append(models.CSV_HEADERS, row, tmp_path)

            # Update statistics
            with locks['stats']:
                stats['tot'] += site_bonus_count
                stats['suc'] += 1
                current_total = stats['tot']
                current_successes = stats['suc']

            elapsed = time.perf_counter() - start_time

            # Update UI
            ui.update({
                'index': current_idx,
                'successes': current_successes,
                'failures': stats['fail'],
                'total_bonuses': current_total,
                'site_url': url,
                'status_message': '✅',
                'site_bonuses_gt_zero': site_bonus_count,
                'N': total_count,
                'elapsed': elapsed,
                'is_expiring': has_expiring,
                'ip_score': ip_score
            })

        except Exception as e:
            # === Error handling ===
            with locks['stats']:
                stats['fail'] += 1
                current_failures = stats['fail']

            elapsed = time.perf_counter() - start_time
            error_string = str(e)

            # Map exception to error code
            if isinstance(e, requests.exceptions.HTTPError):
                error_code = e.response.status_code
                error_string = f"HTTP {error_code}"
            elif "get_merchant_details" in error_string or "Missing MERCHANT" in error_string:
                error_code = 201  # ID/Name Not Found
            elif "Captcha" in error_string or "bot" in error_string.lower():
                error_code = 202  # Captcha Detected
            elif "Failed to resolve" in error_string or "gaierror" in error_string:
                error_code = 102  # DNS Error
            elif "ReadTimeout" in error_string or "Timeout" in error_string:
                error_code = 104  # Timeout
            elif "ConnectionRefused" in error_string:
                error_code = 101  # Server Offline
            elif "ConnectionError" in error_string:
                error_code = 103  # Connection Error
            elif "403" in error_string or "Cloudflare" in error_string:
                error_code = 403  # Forbidden
            elif "login" in error_string.lower():
                error_code = 304  # Login Failed
            elif "NoneType" in error_string:
                error_code = 302  # No Response
            else:
                error_code = 301  # Unexpected Error

            # Save debug snapshot for certain errors
            if error_code in [201, 202, 302, 303]:
                try:
                    os.makedirs('data/debug', exist_ok=True)
                    timestamp_slug = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    url_slug = url.replace('https://', '').replace('/', '_')
                    with open(f'data/debug/E{error_code}_{timestamp_slug}_{url_slug}.html',
                              'w', encoding='utf-8') as f_debug:
                        f_debug.write(html if 'html' in locals() else "No HTML captured")
                except Exception:
                    pass

            # Log error to database
            io_manager.log_error(f"E{error_code}", url, error_string)

            # Update UI with error
            ui.update({
                'index': current_idx,
                'successes': stats['suc'],
                'failures': current_failures,
                'total_bonuses': stats['tot'],
                'site_url': url,
                'status_message': f'E{error_code}',
                'site_bonuses_gt_zero': 0,
                'N': total_count,
                'elapsed': elapsed,
                'ip_score': ip_score,
                'error_details': error_string
            })


def main():
    """Main entry point for the scraper."""

    # Handle help flag
    if "-h" in sys.argv or "--help" in sys.argv:
        print("Usage: python main.py [OPTIONS]")
        print()
        print("Options:")
        print("  -v, --verbose [LEVEL]  Set verbosity level: min, med, max (default: min).")
        print("                         If flag is used without level, defaults to med.")
        print("  -r, --raw              Save full raw API responses to data/raw_responses/.")
        print("  -s, --shuffle          Force random execution order (overrides priority).")
        print("  -h, --help             Show this help message and exit.")
        print()
        print("Utilities:")
        print("  search.py              Global bonus search engine.")
        print("  discover.py            URL discovery crawler (finds NEW sites).")
        sys.exit(0)

    # Parse verbosity level
    ui.VERBOSITY = "min"
    if "-v" in sys.argv:
        idx = sys.argv.index("-v")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1] in ["min", "med", "max"]:
            ui.VERBOSITY = sys.argv[idx + 1]
        else:
            ui.VERBOSITY = "med"
    elif "--verbose" in sys.argv:
        idx = sys.argv.index("--verbose")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1] in ["min", "med", "max"]:
            ui.VERBOSITY = sys.argv[idx + 1]
        else:
            ui.VERBOSITY = "med"

    # Initialize database
    db.init()
    io_manager.csv_init(models.CSV_HEADERS)

    # Start web dashboard server
    threading.Thread(target=web_server.start_server, daemon=True).start()

    # Parse flags
    save_raw = "--raw" in sys.argv or "-r" in sys.argv
    shuffle_mode = "--shuffle" in sys.argv or "-s" in sys.argv

    try:
        # Load URLs and credentials
        urls, credentials = config.parse(force_shuffle=shuffle_mode)

        # Create task list: all combinations of URLs and credentials
        all_tasks = [
            (url, phone, password)
            for phone, password in credentials
            for url in urls
        ]
        total_count = len(all_tasks)

        # Initialize shared state
        stats = {'idx': 0, 'suc': 0, 'fail': 0, 'tot': 0}
        locks = {
            'idx': threading.Lock(),
            'stats': threading.Lock()
        }

        # Check IP health
        ip_score, _ = network_health.check_ip_health(config.ABUSEIPDB_KEY)

        # Determine number of workers (use proxies if available)
        proxies = config.get_proxies()
        num_workers = 10 if proxies else 1
        num_workers = min(num_workers, total_count)

        # Distribute tasks across workers
        chunks = [all_tasks[i::num_workers] for i in range(num_workers)]

        # Run workers in thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(worker, chunks[i], i, stats, locks, total_count, ip_score, save_raw)
                for i in range(num_workers)
            ]
            concurrent.futures.wait(futures)

        # Merge temporary CSV files into main output
        for i in range(num_workers):
            tmp_path = f'data/tmp_{i}.csv'
            if os.path.exists(tmp_path):
                with open(tmp_path, 'r') as f_in:
                    reader = csv.DictReader(f_in)
                    for row in reader:
                        io_manager.csv_append(models.CSV_HEADERS, row)
                os.remove(tmp_path)

    except Exception as e:
        io_manager.log_error("FATAL", "500", str(e))


if __name__ == "__main__":
    main()
