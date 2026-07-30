import datetime, difflib, hashlib, re
from math import log2, log10, pow


import config, db

TZ = datetime.timezone(datetime.timedelta(hours=10))

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
    r = db.execute("SELECT u, SUM(pv) FROM b GROUP BY u")
    return {row[0]: row[1] for row in r} if r else {}

def parse_expiry(text):
    if not text: return None
    for pat, fmt in [(r"\d{4}-\d{2}-\d{2}","%Y-%m-%d"),(r"\d{2}/\d{2}/\d{4}","%d/%m/%Y"),(r"\d{2}-\d{2}-\d{4}","%d-%m-%Y"),(r"\d{2}/\d{2}","%d/%m")]:
        m = re.search(pat, str(text))
        if m:
            try:
                s = m.group(0)
                if fmt=="%d/%m" and len(s)<=5: s = f"{s}/2026"
                return datetime.datetime.strptime(s, fmt).replace(tzinfo=TZ)
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
