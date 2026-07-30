"""
error_definitions.py - Error Code Definitions

Defines error codes and their descriptions for the scraper.
"""

import http.client

# Custom error codes and their definitions
ERROR_DEFINITIONS = {
    # --- Network Errors (1xx) ---
    101: {
        "brief": "Server Offline",
        "verbose": "The server for the website is not responding. The domain resolves, but the host is unreachable."
    },
    102: {
        "brief": "DNS Error",
        "verbose": "The domain name could not be resolved. Check DNS settings or if the domain has expired."
    },
    103: {
        "brief": "Connection Error",
        "verbose": "A generic connection error occurred. Likely a transient network issue."
    },
    104: {
        "brief": "Timeout",
        "verbose": "The request timed out. The server is too slow or the network connection is poor."
    },
    105: {
        "brief": "HTTP Protocol Error",
        "verbose": "A generic HTTP protocol violation occurred."
    },
    106: {
        "brief": "Request Error",
        "verbose": "An error occurred while constructing or sending the request."
    },

    # --- Parsing Errors (2xx) ---
    201: {
        "brief": "ID/Name Not Found",
        "verbose": "The scraper could not find the merchant ID or name. The site layout has likely changed."
    },
    202: {
        "brief": "Captcha Detected",
        "verbose": "Access blocked by a captcha or bot protection system. Manual intervention required."
    },

    # --- Scraper Logic Errors (3xx) ---
    301: {
        "brief": "Unexpected Error",
        "verbose": "An unhandled exception occurred during processing. Check logs/snapshots."
    },
    302: {
        "brief": "No Response",
        "verbose": "The server returned an empty response or NoneType where data was expected."
    },
    303: {
        "brief": "Not Modified",
        "verbose": "Content has not changed since the last request."
    },
    304: {
        "brief": "Login Failed",
        "verbose": "Authentication failed. Check credentials or session expiration."
    },
    305: {
        "brief": "No Login Response",
        "verbose": "The login request completed but returned no data."
    },
    306: {
        "brief": "No Bonus Response",
        "verbose": "The bonus data endpoint returned an empty or invalid response."
    }
}

# Dynamically add standard HTTP error codes (400-599)
for code, phrase in http.client.responses.items():
    if code >= 400:
        ERROR_DEFINITIONS[code] = {
            "brief": phrase,
            "verbose": f"The server returned HTTP {code} ({phrase}). This is a standard web server error."
        }


def get_error_info(code):
    """
    Get error information for a given error code.

    Args:
        code: Error code (int)

    Returns:
        dict: Dictionary with 'brief' and 'verbose' descriptions
    """
    return ERROR_DEFINITIONS.get(code, {
        "brief": f"Error {code}",
        "verbose": "An undefined error occurred."
    })
