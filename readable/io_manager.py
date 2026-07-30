"""
io_manager.py - I/O Operations

Handles session caching, CSV file operations, and error logging.
"""

import db
import csv
import pickle
import datetime


def load_session(phone_number, site_url):
    """
    Load cached session data (cookies + user data) from database.

    Sessions are cached to avoid re-authenticating on every request.
    Cached sessions have a 6-hour TTL.

    Args:
        phone_number: User identifier (phone number)
        site_url: Site URL

    Returns:
        dict: Session data with keys:
            - 'ck': Cookies (deserialized)
            - 'data': User data from login (deserialized)
            - 'ts': Timestamp string
        Returns None if no cached session found
    """
    result = db.query(
        "SELECT ck, data, ts FROM s WHERE uid=? AND u=?",
        (phone_number, site_url)
    )

    if result:
        return {
            'ck': pickle.loads(result[0][0]),    # Deserialize cookies
            'data': pickle.loads(result[0][1]),  # Deserialize user data
            'ts': result[0][2]                   # Timestamp
        }
    return None


def save_session(phone_number, site_url, cookies, user_data):
    """
    Cache session data to database for reuse.

    Args:
        phone_number: User identifier (phone number)
        site_url: Site URL
        cookies: Session cookies to cache
        user_data: User data from login response
    """
    db.query(
        "REPLACE INTO s(uid, u, ck, data, ts) VALUES(?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (phone_number, site_url, pickle.dumps(cookies), pickle.dumps(user_data))
    )


def csv_init(headers, path='data/bonuses.csv'):
    """
    Initialize a CSV file with headers.

    Creates a new file (overwrites if exists) and writes the header row.

    Args:
        headers: List of column headers
        path: Output file path
    """
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, headers)
        writer.writeheader()


def csv_append(headers, row, path='data/bonuses.csv'):
    """
    Append a row to an existing CSV file.

    Args:
        headers: List of column headers (must match initialization)
        row: Dictionary of row data
        path: Output file path
    """
    with open(path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, headers)
        writer.writerow(row)


def log_error(level, source, message):
    """
    Log an error to the database.

    Args:
        level: Error level/code (e.g., "E301", "E201")
        source: Source URL or identifier
        message: Error message/details
    """
    db.query(
        "INSERT INTO l(lvl, src, msg) VALUES(?, ?, ?)",
        (level, source, message)
    )


# Aliases for backward compatibility with obfuscated code
L = load_session
S = save_session
CSV_INIT = csv_init
CSV_APPEND = csv_append
ERR = log_error
