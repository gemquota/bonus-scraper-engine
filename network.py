import base64, json, re, time
from pathlib import Path
import cloudscraper, requests
import config

CACHE_PATH = Path("data/ip_health.json")

DEFAULT_BROWSER = {'browser': 'chrome', 'platform': 'windows', 'desktop': True}

def create_session(proxy=None, browser_config=None):
    if browser_config is None:
        browser_config = DEFAULT_BROWSER
    scraper_session = cloudscraper.create_scraper(browser=browser_config)
    scraper_session.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    })
    if proxy:
        scraper_session.proxies = {"http": proxy, "https": proxy}
    return scraper_session

def post_json(session, url, data):
    response = session.post(url, data=data, timeout=getattr(session, "timeout", None) or config.TIMEOUT)
    response.raise_for_status()
    return response.json()

def _parklogic_redirect(session, html):
    if "<title>Redirecting" not in html or "parklogic" not in html:
        return None

    match = re.search(r'"(ey[A-Za-z0-9+/=]{50,})"', html)
    if not match:
        return None

    payload = json.loads(base64.b64decode(match.group(1)))
    payload["parameters"].update({"adBlockingDetected": 0, "timezoneBrowser": "Australia/Sydney", "webdriver": 0, "gpu": None})

    response = session.post("https://router.parklogic.com/", data=json.dumps(payload), timeout=getattr(session, "timeout", None) or config.TIMEOUT)
    if response.text[:4] == "http":
        return response.text
    return None

def get_page(session, url):
    timeout = getattr(session, "timeout", None) or config.TIMEOUT
    response = session.get(url, timeout=timeout)
    response.raise_for_status()

    redirect_url = _parklogic_redirect(session, response.text)
    if redirect_url:
        response = session.get(redirect_url, timeout=timeout)

    return response.text

def _extract_var(html, name):
    marker = f"var {name} = "
    idx = html.find(marker)
    if idx == -1:
        return None
    start_index = idx + len(marker)
    end_index = html.find(";", start_index)
    if end_index == -1:
        return None
    return html[start_index:end_index].strip('" ')

def parse_merchant_info(html):
    mid = _extract_var(html, "MERCHANTID")
    mname = _extract_var(html, "MERCHANTNAME")
    if not mid:
        raise ValueError("MERCHANTID not found in page")
    return mid, mname

def build_api_url(url):
    return f"{url.rstrip('/')}/api/v1/index.php"

def login(session, url, username, password, merchant_id):
    payload = {
        "module": "/users/login",
        "mobile": username,
        "password": password,
        "merchantId": merchant_id,
        "domainId": "0",
        "accessId": "",
        "accessToken": "",
        "walletIsAdmin": ""
    }
    return post_json(session, url, payload).get("data", {})

def sync_user_data(session, url, merchant_id, access_token, access_id):
    payload = {
        "module": "/users/syncData",
        "merchantId": merchant_id,
        "accessToken": access_token,
        "accessId": access_id,
        "domainId": "0",
        "walletIsAdmin": ""
    }
    return post_json(session, url, payload)

def check_ip_reputation(api_key):
    if CACHE_PATH.exists():
        cache_data = json.loads(CACHE_PATH.read_text())
        if time.time() - cache_data["ts"] < 3600:
            return cache_data["score"], cache_data["ip"]

    if not api_key or api_key == "YOUR_KEY_HERE":
        return 0, "Unknown"

    try:
        response = requests.get(
            "https://api.abuseipdb.com/api/v2/check",
            headers={"Accept": "application/json", "Key": api_key},
            params={"maxAgeInDays": "90"},
            timeout=10
        )
        api_data = response.json()["data"]

        CACHE_PATH.write_text(json.dumps({
            "ts": time.time(),
            "score": api_data["abuseConfidenceScore"],
            "ip": api_data["ipAddress"]
        }))

        return api_data["abuseConfidenceScore"], api_data["ipAddress"]
    except Exception:
        return -1, "Error"
