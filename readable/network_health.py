"""
network_health.py - IP Reputation Checking

Checks IP health/reputation using the AbuseIPDB API.
"""

import requests
import time
import os
import json

# Cache file path with 1-hour TTL
HEALTH_CACHE = 'data/ip_health.json'


def check_ip_health(api_key):
    """
    Check the current IP's abuse confidence score via AbuseIPDB.

    Results are cached for 1 hour to avoid rate limiting.

    Args:
        api_key: AbuseIPDB API key (optional)

    Returns:
        tuple: (score, ip_address)
            - score: Abuse confidence score (0-100, 0=clean, 100=malicious)
                    -1 if error, 0 if no API key
            - ip_address: The detected IP address
    """
    # Check cache first (1 hour TTL)
    if os.path.exists(HEALTH_CACHE):
        with open(HEALTH_CACHE, 'r') as f:
            cache = json.load(f)
            if time.time() - cache['ts'] < 3600:  # 1 hour
                return cache['score'], cache['ip']

    # No API key = skip check
    if not api_key or api_key == 'YOUR_KEY_HERE':
        return 0, "Unknown"

    try:
        # Query AbuseIPDB
        url = 'https://api.abuseipdb.com/api/v2/check'
        headers = {
            'Accept': 'application/json',
            'Key': api_key
        }
        params = {'maxAgeInDays': '90'}

        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        score = data['data']['abuseConfidenceScore']
        ip = data['data']['ipAddress']

        # Save to cache
        with open(HEALTH_CACHE, 'w') as f:
            json.dump({'ts': time.time(), 'score': score, 'ip': ip}, f)

        return score, ip

    except Exception:
        return -1, "Error"


def get_health_status(score):
    """
    Get emoji and color for an IP health score.

    Args:
        score: Abuse confidence score (0-100, -1 for error)

    Returns:
        tuple: (emoji, rich_color_name)
    """
    if score == -1:
        return "⚪", "white"        # Error/Unknown
    if score == 0:
        return "🟢", "bright_green"  # Clean
    if score < 25:
        return "🟡", "yellow"        # Low risk
    if score < 75:
        return "🟠", "orange3"       # Medium risk
    return "🔴", "bright_red"        # High risk
