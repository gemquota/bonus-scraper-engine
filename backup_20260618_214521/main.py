import sys, threading
from pathlib import Path

import db, server, scraper

def main():
    Path("data").mkdir(parents=True, exist_ok=True)
    db.initialize_database()
    try: db.execute("ALTER TABLE t ADD COLUMN ec INTEGER")
    except: pass
    if "-h" in sys.argv: print("Usage: python main.py [-v min|med|max] [-r] [-s]"); sys.exit(0)
    server.IS_RUNNING = True
    threading.Thread(target=scraper.run_scrape, daemon=True).start()
    server.start_server()

if __name__ == "__main__":
    try: main()
    except Exception as exc:
        db.log_event("FATAL", "500", str(exc))
        print(f"FATAL: {exc}", file=sys.stderr)
