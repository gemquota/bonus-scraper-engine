import csv, datetime, difflib, hashlib, pickle, re, sqlite3
from contextlib import contextmanager
from math import log2, log10, pow
from pathlib import Path

import config

TZ = datetime.timezone(datetime.timedelta(hours=10))
DB_PATH = "data/base.db"
_csv_cache: dict = {}
_cache: dict[str, sqlite3.Connection] = {}

HEADERS = ["url","mname","id","name","transactiontype","bonusfixed","amount","minwithdraw",
    "maxwithdraw","rollover","balance","claimconfig","claimcondition","bonus","bonusrandom",
    "reset","mintopup","maxtopup","referlink","perceived_value","is_new"]

def get_connection():
    if DB_PATH not in _cache:
        _cache[DB_PATH] = sqlite3.connect(DB_PATH, check_same_thread=False)
    return _cache[DB_PATH]

@contextmanager
def cursor_context():
    conn = get_connection(); cursor = conn.cursor()
    try:
        yield cursor; conn.commit()
    except Exception: conn.rollback(); raise
    finally: cursor.close()

def execute(query, params=()):
    with cursor_context() as c:
        c.execute(query, params)
        return c.fetchall()

def initialize_database():
    schema = """
    CREATE TABLE IF NOT EXISTS t(u TEXT PRIMARY KEY, m, p, g, a INT DEFAULT 1, ts DATETIME, ec INTEGER);
    CREATE TABLE IF NOT EXISTS b(uid TEXT PRIMARY KEY, eid, u, v REAL, pv REAL, w REAL, c REAL, t, raw, h, exp DATETIME, fp TEXT, mirrors TEXT, s1 DATETIME DEFAULT CURRENT_TIMESTAMP, sl DATETIME, mname, name);
    CREATE TABLE IF NOT EXISTS s(uid, u, ck BLOB, data BLOB, ua, ip, ok INT DEFAULT 1, ts DATETIME DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(uid, u));
    CREATE TABLE IF NOT EXISTS m(rid, ts DATETIME DEFAULT CURRENT_TIMESTAMP, dur REAL, cnt INT, new INT, spv REAL, err INT);
    CREATE TABLE IF NOT EXISTS l(id INTEGER PRIMARY KEY, ts DATETIME DEFAULT CURRENT_TIMESTAMP, lvl, src, msg);
    CREATE VIRTUAL TABLE IF NOT EXISTS b_fts USING fts5(uid UNINDEXED, eid, u, raw, content='b', content_rowid='rowid');
    CREATE TRIGGER IF NOT EXISTS b_ai AFTER INSERT ON b BEGIN INSERT INTO b_fts(rowid, uid, eid, u, raw) VALUES (new.rowid, new.uid, new.eid, new.u, new.raw); END;
    CREATE TRIGGER IF NOT EXISTS b_ad AFTER DELETE ON b BEGIN INSERT INTO b_fts(b_fts, rowid, uid, eid, u, raw) VALUES ('delete', old.rowid, old.uid, old.eid, old.u, old.raw); END;
    CREATE TRIGGER IF NOT EXISTS b_au AFTER UPDATE ON b BEGIN INSERT INTO b_fts(b_fts, rowid, uid, eid, u, raw) VALUES ('delete', old.rowid, old.uid, old.eid, old.u, old.raw); INSERT INTO b_fts(rowid, uid, eid, u, raw) VALUES (new.rowid, new.uid, new.eid, new.u, new.raw); END;
    """
    with cursor_context() as c: c.executescript(schema)

def load_session(url, uid):
    r = execute("SELECT ck, data, ts FROM s WHERE uid=? AND u=?", (uid, url))
    if not r: return None
    return {"ck": pickle.loads(r[0][0]), "data": pickle.loads(r[0][1]), "ts": r[0][2]}

def save_session(url, uid, cookies, data):
    execute("REPLACE INTO s(uid, u, ck, data, ts) VALUES (?,?,?,?,CURRENT_TIMESTAMP)", (uid, url, pickle.dumps(cookies), pickle.dumps(data)))

def _init_csv(path):
    p = Path(path)
    if p.exists(): return
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f: csv.DictWriter(f, HEADERS).writeheader()

def append_csv_row(row, path="data/bonuses.csv"):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", newline="") as f: csv.DictWriter(f, fieldnames=list(row.keys())).writerow(row)

def log_event(level, source, message):
    execute("INSERT INTO l(lvl, src, msg) VALUES (?,?,?)", (level, source, message))

def search(query, min_pv=0):
    return execute("SELECT b.u, b.eid, b.v, b.pv, b.raw FROM b JOIN b_fts ON b.rowid=b_fts.rowid WHERE b_fts MATCH ? AND b.pv>=? ORDER BY b.pv DESC", (query, min_pv))

# --- Bonus filter utilities (merged from filter.py) ---

def _clean(name):
    if not name: return ""
    return " ".join(re.sub(r"<[^>]+>", "", name).strip().lower().split())

def is_fuzzy_match(a, b, threshold=0.85):
    if not a or not b: return not a and not b
    ca, cb = _clean(a), _clean(b)
    if not ca or not cb: return not ca and not cb
    return (difflib.SequenceMatcher(None, ca, cb).ratio() >= threshold
        and re.findall(r"\d+", ca) == re.findall(r"\d+", cb)
        and re.findall(r"\b(i{1,3}|iv|v|vi{1,3}|ix|x)\b", ca) == re.findall(r"\b(i{1,3}|iv|v|vi{1,3}|ix|x)\b", cb))

def find_matching_name(name, existing_names, threshold=0.85):
    for c in existing_names:
        if is_fuzzy_match(name, c, threshold): return c
    return None

def float_value(value):
    try: return float(value)
    except (TypeError, ValueError): return 0.0

def fingerprint_bonus(bonus):
    raw = f"{bonus.get('name')}|{bonus.get('amount')}|{bonus.get('rollover')}|{bonus.get('minwithdraw')}|{bonus.get('maxwithdraw')}"
    return hashlib.sha256(raw.encode()).hexdigest()

def get_url_scores():
    r = execute("SELECT u, SUM(pv) FROM b GROUP BY u")
    return {row[0]: row[1] for row in r} if r else {}

def parse_expiry(text):
    if not text: return None
    for pat, fmt in [(r"\d{4}-\d{2}-\d{2}","%Y-%m-%d"),(r"\d{2}/\d{2}/\d{4}","%d/%m/%Y"),(r"\d{2}-\d{2}-\d{4}","%d-%m-%Y"),(r"\d{2}/\d{2}","%d/%m")]:
        m = re.search(pat, str(text))
        if not m: continue
        try:
            s = m.group(0)
            if fmt=="%d/%m" and len(s)<=5: s = f"{s}/2026"
            return datetime.datetime.strptime(s, "%d/%m/%Y" if "/" in s else fmt).replace(tzinfo=TZ)
        except ValueError: continue
    return None

def perceived_value(bonus):
    amount = float_value(bonus.get("amount"))
    if amount <= 0: return 0.0
    max_w = float_value(bonus.get("maxwithdraw")) or config.DEFAULT_MAX_WITHDRAW
    min_w = float_value(bonus.get("minwithdraw"))
    roll = float_value(bonus.get("rollover"))
    num = 10.0 * log2((max_w + 1)) * (1.0 + 0.2 * log10(amount + 1))
    div = max(1.0, max(min_w, amount * roll)) / amount
    return max(0.0, num / pow(max(1.0, div), 1.25) / (1.0 + roll / 20.0))
