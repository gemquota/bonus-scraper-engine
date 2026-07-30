import sys, threading, json, time
from pathlib import Path
import sqlite3

import db, server, scraper, terminal, validate_license

def main():
    Path("data").mkdir(parents=True, exist_ok=True)
    db.initialize_database()
    
    try:
        db.execute("ALTER TABLE t ADD COLUMN ec INTEGER")
    except sqlite3.OperationalError:
        pass
        
    if "-h" in sys.argv:
        print("Usage: python main.py [-v min|med|max] [-r] [-s]")
        sys.exit(0)

    # Validate license — determines scrape schedule and data level
    license_data = validate_license.validate_license()
    tier_name = license_data.get("tier_name", "Free Trial")
    scrape_today = license_data.get("scrape_today", False)

    if not scrape_today:
        today = time.strftime('%A')
        scrape_days = license_data.get("scrape_days", ["Monday"])
        days_str = ", ".join(scrape_days)
        print(f"  ⏭️  {tier_name} — skipping scrape ({today} not in schedule: {days_str})", flush=True)
        print(f"     Starting server for dashboard access only.", flush=True)
        server.IS_RUNNING = False
        server.start_server()
        return

    print(f"  ✅ {tier_name} — scrape day: {time.strftime('%A')}", flush=True)

    # Expose data level for export modules via env var
    data_level = license_data.get("data_level", "basic")
    import os as _os
    _os.environ["SCRAPER_DATA_LEVEL"] = data_level
    if data_level == "basic":
        print(f"  📄 Data: Standard (CSV only, core fields)", flush=True)
    elif data_level == "advanced":
        print(f"  📊 Data: Advanced (CSV + JSON, value scoring)", flush=True)
    elif data_level == "expert":
        print(f"  🔬 Data: Expert (all formats, raw access, search)", flush=True)

    # Write active license for export modules
    license_path = Path("data") / "license_active.json"
    license_path.write_text(json.dumps(license_data, indent=2, default=str))

    server.IS_RUNNING = True
    
    callbacks = {
        "on_update": terminal.update_display,
        "on_launcher": terminal.print_launcher,
        "on_completion": terminal.print_completion
    }
    
    threading.Thread(target=scraper.run_scrape, kwargs=callbacks, daemon=True).start()
    server.start_server()

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        db.log_event("FATAL", "500", str(exc))
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
