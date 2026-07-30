"""
api.py - API Endpoint Functions

Constructs API URLs and fetches data from target sites.
"""

import network


def get_api_url(site_url):
    """
    Construct the API endpoint URL from a site's base URL.

    All target sites use the same API structure at /api/v1/index.php

    Args:
        site_url: Base URL of the site (e.g., "https://example.com")

    Returns:
        str: Full API endpoint URL

    Example:
        >>> get_api_url("https://example.com")
        'https://example.com/api/v1/index.php'
        >>> get_api_url("https://example.com/")
        'https://example.com/api/v1/index.php'
    """
    return f"{site_url.rstrip('/')}/api/v1/index.php"


def fetch_data(session, api_url, merchant_id, access_token, access_id):
    """
    Fetch user data including bonuses and promotions from the API.

    This calls the /users/syncData endpoint which returns the user's
    complete data including available bonuses and promotions.

    Args:
        session: HTTP session object
        api_url: API endpoint URL from get_api_url()
        merchant_id: Site's merchant ID
        access_token: Authentication token from login
        access_id: User's ID from login

    Returns:
        dict: API response containing:
            - 'status': 'SUCCESS' or error
            - 'data': {
                'bonus': [...],       # List of bonus offers
                'promotions': [...],  # List of promotions
                ...                   # Other user data
            }
    """
    payload = {
        "module": "/users/syncData",
        "merchantId": merchant_id,
        "accessToken": access_token,
        "accessId": access_id,
        "domainId": "0",
        "walletIsAdmin": ""
    }

    return network.post(session, api_url, payload)
