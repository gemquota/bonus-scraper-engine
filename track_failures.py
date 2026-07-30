"""Track URL failures and auto-remove URLs after 5 failures."""
import db
from pathlib import Path

URLS_PATH = Path("in/config/urls.txt")
OLD_URLS_PATH = Path("in/config/oldurls.txt")
MAX_FAILURES = 5

def record_failure(url):
    """Increment failure count for a URL. If it hits MAX_FAILURES, move to oldurls.txt."""
    row = db.execute("SELECT a FROM t WHERE u=?", (url,))
    count = (row[0][0] if row else 0) + 1
    db.execute("INSERT OR IGNORE INTO t(u) VALUES (?)", (url,))
    db.execute("UPDATE t SET a=?, ts=CURRENT_TIMESTAMP WHERE u=?", (count, url))

    if count >= MAX_FAILURES:
        _move_to_oldurls(url)
        db.log_event("BANNED", url, f"Moved to oldurls.txt after {count} failures")
        print(f"  \U0001f5d1\ufe0f Moved {url} to oldurls.txt after {count} failures", flush=True)
    else:
        print(f"  \u26a0\ufe0f {url} failed ({count}/{MAX_FAILURES})", flush=True)
    return count

def record_success(url):
    """Reset failure count to 0 on success."""
    db.execute("INSERT OR IGNORE INTO t(u) VALUES (?)", (url,))
    db.execute("UPDATE t SET a=0 WHERE u=?", (url,))

def _move_to_oldurls(url):
    """Move a URL from urls.txt to oldurls.txt."""
    if not URLS_PATH.exists():
        return False
    lines = URLS_PATH.read_text().splitlines()
    filtered = [l for l in lines if l.strip() != url]
    if len(filtered) != len(lines):
        URLS_PATH.write_text("\n".join(filtered) + ("\n" if filtered else ""))
        # Append to oldurls.txt
        old_lines = OLD_URLS_PATH.read_text().splitlines() if OLD_URLS_PATH.exists() else []
        if url not in old_lines:
            old_lines.append(url)
            OLD_URLS_PATH.write_text("\n".join(old_lines) + "\n")
        return True
    return False

def get_failure_counts():
    """Return dict of {url: failure_count} for all URLs with a > 0."""
    rows = db.execute("SELECT u, a FROM t WHERE a > 0 ORDER BY a DESC")
    return {row[0]: row[1] for row in rows}

def list_banned_urls():
    """Return list of URLs that have been moved to oldurls.txt."""
    if not OLD_URLS_PATH.exists():
        return []
    return [line.strip() for line in OLD_URLS_PATH.read_text().splitlines() if line.strip()]
