import configparser, random
from pathlib import Path
import urllib3; urllib3.disable_warnings()

_cfg = configparser.ConfigParser()
_cfg.read([str(Path("in/config.ini")), str(Path("in/config/config.ini"))])

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 15
MIN_DELAY = _cfg.getfloat("SETTINGS", "min_delay", fallback=1.0)
MAX_DELAY = _cfg.getfloat("SETTINGS", "max_delay", fallback=3.0)
ABUSEIPDB_KEY = _cfg.get("SETTINGS", "abuseipdb_key", fallback=None)
UI_USER = "admin"
DEFAULT_MAX_WITHDRAW = 3776.0

def load_proxies():
    p = Path("in/config/proxies.txt")
    return [x.strip() for x in p.read_text().splitlines() if x.strip()] if p.exists() else []

def parse_urls_and_accounts(shuffle=False):
    import db
    p = Path("in/config/urls.txt")
    u = [l.strip() for l in p.read_text().splitlines() if l.strip()]
    if shuffle or random.random() < 0.1: random.shuffle(u)
    else:
        s = db.get_url_scores()
        u.sort(key=lambda x: s.get(x, 0), reverse=True)
    a = [(_cfg[s]["u"], _cfg[s]["p"]) for s in _cfg.sections() if s and s[0] == "U"]
    return u, a

def normalize_url(url):
    for p in ["https://www.","http://www.","https://","http://"]:
        if url.startswith(p): url = url[len(p):]; break
    return url.split("/")[0].replace("-", " ")

def load_config_dict():
    return {s: dict(_cfg[s]) for s in _cfg.sections()}

def save_config_dict(data: dict):
    for section, keys in data.items():
        if section not in _cfg: _cfg[section] = {}
        for k, v in keys.items(): _cfg[section][k] = str(v)
    p = Path("in/config/config.ini")
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f: _cfg.write(f)
