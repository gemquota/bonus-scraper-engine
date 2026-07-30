"""
network.py - HTTP Client with Cloudflare Bypass

Provides HTTP GET and POST functions using cloudscraper to bypass
Cloudflare protection. Also handles parklogic.com JavaScript redirects.
"""

import requests
import config
import cloudscraper
import re
import base64
import json


def create_session():
    """
    Creates a new cloudscraper session with a custom User-Agent.

    Returns:
        cloudscraper session object configured for Cloudflare bypass
    """
    session = cloudscraper.create_scraper()
    session.headers.update({'User-Agent': config.USER_AGENT})
    return session


def _resolve_parklogic(session, html):
    """
    Handle parklogic.com JavaScript redirect pages.

    Some sites use parklogic.com for domain parking/redirects that require
    JavaScript execution. This function extracts the redirect URL by:
    1. Finding the base64-encoded payload in the HTML
    2. POSTing it to router.parklogic.com
    3. Getting the actual redirect URL from the response

    Args:
        session: HTTP session object
        html: HTML content that may contain a parklogic redirect

    Returns:
        str: The redirect URL if found, None otherwise
    """
    # Check if this is a parklogic redirect page
    if '<title>Redirecting...</title>' not in html:
        return None
    if 'router.parklogic.com' not in html:
        return None

    # Find the base64-encoded JSON payload (starts with 'ey' = '{"')
    match = re.search(r'"(ey[A-Za-z0-9+/=]{50,})"', html)
    if not match:
        return None

    try:
        # Decode the payload
        payload = json.loads(base64.b64decode(match.group(1)))

        # Add required parameters that the JS normally sets
        payload['parameters']['adBlockingDetected'] = False
        payload['parameters']['timezoneBrowser'] = 'Australia/Sydney'
        payload['parameters']['webdriver'] = False
        payload['parameters']['gpu'] = None

        # POST to parklogic router to get the redirect URL
        response = session.post(
            'https://router.parklogic.com/',
            data=json.dumps(payload),
            timeout=config.TIMEOUT
        )

        # Response should be the redirect URL
        if response.text.startswith('http'):
            return response.text.strip()

    except Exception:
        pass

    return None


def get(session, url):
    """
    Perform a GET request with Cloudflare bypass and parklogic redirect handling.

    Args:
        session: HTTP session from create_session()
        url: URL to fetch

    Returns:
        str: HTML content of the page

    Raises:
        requests.HTTPError: If the request fails
    """
    response = session.get(url, timeout=config.TIMEOUT)
    response.raise_for_status()

    html = response.text

    # Check for parklogic redirect and follow it
    redirect_url = _resolve_parklogic(session, html)
    if redirect_url:
        response = session.get(redirect_url, timeout=config.TIMEOUT)
        response.raise_for_status()
        return response.text

    return html


def post(session, url, data):
    """
    Perform a POST request and return JSON response.

    Args:
        session: HTTP session from create_session()
        url: URL to post to
        data: Dictionary of POST data

    Returns:
        dict: JSON response from server

    Raises:
        requests.HTTPError: If the request fails
    """
    response = session.post(url, data=data, timeout=config.TIMEOUT)
    response.raise_for_status()
    return response.json()


# Aliases for backward compatibility with obfuscated code
S = create_session
G = get
P = post
