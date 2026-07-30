"""
config.py - Configuration Management

Loads settings from config.ini and provides URL/credential parsing.
"""

from urllib3 import disable_warnings
import configparser
import random
import os

# Disable SSL warnings (sites often have certificate issues)
disable_warnings()

# Load configuration file
_config = configparser.ConfigParser()
_config.read('in/config.ini')

# HTTP User-Agent string (mimics Chrome browser)
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Request timeout in seconds
TIMEOUT = 15

# Verbosity level (0 = minimal output)
VERBOSITY = 0

# Delay between requests (seconds) - randomized between min and max
MIN_DELAY = _config.getint('SETTINGS', 'min_delay', fallback=1)
MAX_DELAY = _config.getint('SETTINGS', 'max_delay', fallback=3)

# AbuseIPDB API key for IP health checking (optional)
ABUSEIPDB_KEY = _config.get('SETTINGS', 'abuseipdb_key', fallback=None)


def get_proxies():
    """
    Load proxy list from file if it exists.

    Proxies should be listed one per line in in/proxies.txt

    Returns:
        list: List of proxy strings, empty if file doesn't exist
    """
    proxy_path = 'in/proxies.txt'
    if os.path.exists(proxy_path):
        with open(proxy_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return []


def parse(force_shuffle=False):
    """
    Parse URLs and credentials from config files.

    URLs are loaded from in/urls.txt
    Credentials are loaded from config.ini sections [U1], [U2], etc.

    By default, URLs are sorted by historical perceived value (best sites first).
    10% of the time, or when force_shuffle=True, URLs are randomized for exploration.

    Args:
        force_shuffle: If True, randomize URL order instead of sorting by priority

    Returns:
        tuple: (
            list of URLs,
            list of (phone_number, password) credential tuples
        )

    Example:
        >>> urls, credentials = parse()
        >>> print(urls[0])
        'https://example.com'
        >>> print(credentials[0])
        ('61400000000', 'password123')
    """
    # Import here to avoid circular dependency
    import filter as f

    # Load URLs from file
    with open('in/urls.txt', 'r') as file:
        urls = [line.strip() for line in file if line.strip()]

    # 10% chance to shuffle for exploration, or if forced
    if force_shuffle or random.random() < 0.1:
        random.shuffle(urls)
    else:
        # Sort by historical perceived value (high value sites first)
        priority = f.get_url_priority()
        urls.sort(key=lambda x: priority.get(x, 0), reverse=True)

    # Load credentials from config sections starting with 'U'
    # e.g., [U1] with 'u' (phone) and 'p' (password) keys
    credentials = []
    for section in _config.sections():
        if section.startswith('U'):
            phone = _config[section]['u']
            password = _config[section]['p']
            credentials.append((phone, password))

    return urls, credentials


# Aliases for backward compatibility
UA = USER_AGENT
TO = TIMEOUT
V = VERBOSITY
C = _config
IP_KEY = ABUSEIPDB_KEY
