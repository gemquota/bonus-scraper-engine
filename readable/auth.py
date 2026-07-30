"""
auth.py - User Authentication

Handles login to target sites via their REST API.
"""

import network


def login(session, api_url, phone_number, password, merchant_id):
    """
    Authenticate a user with a site's API.

    Args:
        session: HTTP session object from network.create_session()
        api_url: The API endpoint URL (e.g., https://example.com/api/v1/index.php)
        phone_number: User's mobile/phone number (used as username)
        password: User's password
        merchant_id: The site's merchant identifier (extracted from HTML)

    Returns:
        dict: User data containing:
            - 'token': Access token for subsequent API calls
            - 'id': User's access ID
            - Other user profile data

    Example:
        >>> session = network.create_session()
        >>> user_data = login(session, "https://site.com/api/v1/index.php",
        ...                   "61400000000", "password123", "12345")
        >>> print(user_data['token'])
        'abc123...'
    """
    payload = {
        "module": "/users/login",
        "mobile": phone_number,
        "password": password,
        "merchantId": merchant_id,
        "domainId": "0",
        "accessId": "",
        "accessToken": "",
        "walletIsAdmin": ""
    }

    response = network.post(session, api_url, payload)
    return response.get('data', {})
