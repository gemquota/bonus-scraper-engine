import base64, json, re, time
from pathlib import Path
import cloudscraper, requests
import config

CACHE = Path("data/ip_health.json")

def create_session():
    s = cloudscraper.create_scraper()
    s.headers.update({"User-Agent": config.USER_AGENT})
    return s

def post_json(session, url, data):
    r = session.post(url, data=data, timeout=config.TIMEOUT)
    r.raise_for_status()
    return r.json()

def _parklogic_redirect(session, html):
    if "<title>Redirecting" not in html or "parklogic" not in html: return None
    m = re.search(r'"(ey[A-Za-z0-9+/=]{50,})"', html)
    if not m: return None
    p = json.loads(base64.b64decode(m.group(1)))
    p["parameters"].update({"adBlockingDetected":0,"timezoneBrowser":"Australia/Sydney","webdriver":0,"gpu":None})
    r = session.post("https://router.parklogic.com/", data=json.dumps(p), timeout=config.TIMEOUT)
    return r.text if r.text[:4]=="http" else None

def get_page(session, url):
    r = session.get(url, timeout=config.TIMEOUT)
    r.raise_for_status()
    rd = _parklogic_redirect(session, r.text)
    if rd: r = session.get(rd, timeout=config.TIMEOUT)
    return r.text

def _extract_var(html, name):
    s = html.index(f"var {name} = ") + len(f"var {name} = ")
    return html[s:html.index(";",s)].strip('" ')

def parse_merchant_info(html):
    return _extract_var(html, "MERCHANTID"), _extract_var(html, "MERCHANTNAME")

def build_api_url(url):
    return f"{url.rstrip('/')}/api/v1/index.php"

def login(session, url, username, password, merchant_id):
    return post_json(session, url, {"module":"/users/login","mobile":username,"password":password,
        "merchantId":merchant_id,"domainId":"0","accessId":"","accessToken":"","walletIsAdmin":""}).get("data",{})

def sync_user_data(session, url, merchant_id, access_token, access_id):
    return post_json(session, url, {"module":"/users/syncData","merchantId":merchant_id,
        "accessToken":access_token,"accessId":access_id,"domainId":"0","walletIsAdmin":""})

def check_ip_reputation(api_key):
    if CACHE.exists():
        c = json.loads(CACHE.read_text())
        if time.time() - c["ts"] < 3600: return c["score"], c["ip"]
    if not api_key or api_key=="YOUR_KEY_HERE": return 0, "Unknown"
    try:
        r = requests.get("https://api.abuseipdb.com/api/v2/check",
            headers={"Accept":"application/json","Key":api_key}, params={"maxAgeInDays":"90"}, timeout=10)
        d = r.json()["data"]
        CACHE.write_text(json.dumps({"ts":time.time(),"score":d["abuseConfidenceScore"],"ip":d["ipAddress"]}))
        return d["abuseConfidenceScore"], d["ipAddress"]
    except: return -1, "Error"
