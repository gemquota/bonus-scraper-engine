"""Standalone CLI scraper — outputs CSV to stdout, no server.
Enforces license schedule and data tier."""
import csv, sys, os, threading, time
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"

import db, scraper, config, validate_license, server

# Validate license first
license_data = validate_license.validate_license()
tier_name = license_data.get("tier_name", "Free Trial")
scrape_today = license_data.get("scrape_today", False)
data_level = license_data.get("data_level", "basic")

if not scrape_today:
    today = time.strftime('%A')
    scrape_days = license_data.get("scrape_days", ["Monday"])
    days_str = ", ".join(scrape_days)
    print(f"⏭️  {tier_name} — skipping scrape ({today} not in schedule: {days_str})", file=sys.stderr)
    sys.exit(0)

# Set data level for export modules
os.environ["SCRAPER_DATA_LEVEL"] = data_level

# Write active license for export modules
Path("data").mkdir(parents=True, exist_ok=True)
Path("data/license_active.json").write_text(
    __import__('json').dumps(license_data, indent=2, default=str)
)

# Monkey-patch terminal callbacks to be silent
def noop(*a, **kw): pass

db.initialize_database()
server.STOPPED = False
server.PAUSED = False
server.IS_RUNNING = True

# Run scraper with silent callbacks
scraper.run_scrape(
    on_update=noop,
    on_launcher=noop,
    on_completion=lambda s: print(f"\nDone: {s['successes']} sites, {s['total_bonuses']} bonuses, {s['new_bonuses']} new", file=sys.stderr)
)

# Find latest CSV
csv_files = sorted(Path("data").glob("bonuses_*.csv"))
if csv_files:
    latest = csv_files[-1]
    print(f"\n--- CSV: {latest} ---", file=sys.stderr)
    sys.stdout.write(latest.read_text())
