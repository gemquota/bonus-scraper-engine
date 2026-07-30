import configparser, random
from pathlib import Path
import urllib3
urllib3.disable_warnings()

config_parser = configparser.ConfigParser()
config_parser.read([str(Path("in/config.ini")), str(Path("in/config/config.ini"))])

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 8
MIN_DELAY = config_parser.getfloat("SETTINGS", "min_delay", fallback=1.0)
MAX_DELAY = config_parser.getfloat("SETTINGS", "max_delay", fallback=3.0)
ABUSEIPDB_KEY = config_parser.get("SETTINGS", "abuseipdb_key", fallback=None)
UI_USER = "admin"
DEFAULT_MAX_WITHDRAW = 3776.0

def load_proxies():
    proxy_path = Path("in/config/proxies.txt")
    if proxy_path.exists():
        return [line.strip() for line in proxy_path.read_text().splitlines() if line.strip()]
    return []

def parse_urls_and_accounts(shuffle=False):
    import db
    url_path = Path("in/config/urls.txt")
    urls = [line.strip() for line in url_path.read_text().splitlines() if line.strip()]
    
    if shuffle or random.random() < 0.1:
        random.shuffle(urls)
    else:
        scores = db.get_url_scores()
        urls.sort(key=lambda url_item: scores.get(url_item, 0), reverse=True)
        
    accounts = [(config_parser[section]["u"], config_parser[section]["p"]) for section in config_parser.sections() if section and section[0] == "U"]
    return urls, accounts

def normalize_url(url):
    for prefix in ["https://www.", "http://www.", "https://", "http://"]:
        if url.startswith(prefix):
            url = url[len(prefix):]
            break
    return url.split("/")[0].replace("-", " ")

def load_config_dict():
    return {section: dict(config_parser[section]) for section in config_parser.sections()}

def save_config_dict(data: dict):
    for section, keys in data.items():
        if section not in config_parser:
            config_parser[section] = {}
        for key, value in keys.items():
            config_parser[section][key] = str(value)
            
    config_path = Path("in/config/config.ini")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w") as config_file:
        config_parser.write(config_file)
