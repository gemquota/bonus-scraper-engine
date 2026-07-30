"""
filter.py - Filtering & Calculations

Provides bonus value calculations, fingerprinting, expiry extraction,
and URL priority functions.
"""

import re
import datetime
import hashlib
from math import pow, log2, log10

import db
from deduplication import is_fuzzy_match


def is_fuzzy_duplicate(new_name, existing_names, threshold=0.85):
    """
    Check if a bonus name is a fuzzy duplicate of any existing name.

    Args:
        new_name: The new bonus name to check
        existing_names: List of existing bonus names
        threshold: Similarity threshold (0.0-1.0, default 0.85)

    Returns:
        str: The matching existing name if found, None otherwise
    """
    for name in existing_names:
        if is_fuzzy_match(new_name, name, threshold):
            return name
    return None


def generate_fingerprint(bonus):
    """
    Generate a SHA256 fingerprint hash for a bonus.

    The fingerprint is based on key bonus attributes to identify
    duplicate bonuses across different sites.

    Args:
        bonus: Normalized bonus dictionary

    Returns:
        str: SHA256 hex digest

    Example:
        >>> bonus = {'name': 'Free Spin', 'amount': 100, 'rollover': 5,
        ...          'minwithdraw': 50, 'maxwithdraw': 500}
        >>> generate_fingerprint(bonus)
        'a1b2c3d4...'
    """
    # Create a string from key attributes
    fingerprint_string = (
        f"{bonus.get('name')}|"
        f"{bonus.get('amount')}|"
        f"{bonus.get('rollover')}|"
        f"{bonus.get('minwithdraw')}|"
        f"{bonus.get('maxwithdraw')}"
    )
    return hashlib.sha256(fingerprint_string.encode()).hexdigest()


def get_url_priority():
    """
    Get URL priority scores based on historical perceived value.

    URLs with higher total perceived value from past runs are
    prioritized in future runs.

    Returns:
        dict: Mapping of URL -> total perceived value score
    """
    try:
        results = db.query("SELECT u, SUM(pv) FROM b GROUP BY u")
        return {row[0]: row[1] for row in results}
    except Exception:
        return {}


def extract_expiry(text):
    """
    Extract expiry date from bonus text.

    Supports multiple date formats:
    - YYYY-MM-DD (e.g., 2024-12-31)
    - DD/MM/YYYY (e.g., 31/12/2024)
    - DD-MM-YYYY (e.g., 31-12-2024)
    - DD/MM (e.g., 31/12 - assumes current year)

    Args:
        text: Text that may contain an expiry date

    Returns:
        datetime: Parsed expiry date with Australia/Brisbane timezone,
                  or None if no date found
    """
    if not text:
        return None

    text = str(text)

    # Timezone: Australia/Brisbane (UTC+10)
    tz = datetime.timezone(datetime.timedelta(hours=10))

    # Date patterns to try
    patterns = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
        r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
        r'\d{2}/\d{2}',        # DD/MM (short)
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group()
            try:
                # YYYY-MM-DD format
                if '-' in date_str and len(date_str) == 10 and date_str[4] == '-':
                    return datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)

                # DD/MM/YYYY format
                if '/' in date_str and len(date_str) == 10:
                    return datetime.datetime.strptime(date_str, "%d/%m/%Y").replace(tzinfo=tz)

                # DD/MM format (assume current year, or next year if past)
                if '/' in date_str and len(date_str) == 5:
                    return datetime.datetime.strptime(date_str + "/2026", "%d/%m/%Y").replace(tzinfo=tz)

                # DD-MM-YYYY format
                if '-' in date_str and len(date_str) == 10:
                    return datetime.datetime.strptime(date_str, "%d-%m-%Y").replace(tzinfo=tz)

            except ValueError:
                pass

    return None


def calculate_perceived_value(bonus):
    """
    Calculate a "perceived value" score for a bonus.

    This formula evaluates how valuable a bonus is based on:
    - Bonus amount (higher = better)
    - Maximum withdrawal limit (higher = better)
    - Minimum withdrawal requirement (lower = better)
    - Rollover/wagering requirement (lower = better)

    Formula breakdown:
    - Numerator rewards high max_withdraw and bonus amount
    - Denominator penalizes high wagering requirements

    The formula is:
        PV = (10 * log2(max_withdraw + 1) * (1 + 0.2 * log10(amount + 1))) /
             (hurdle_ratio^1.25 * (1 + rollover/20))

    Where hurdle_ratio = max(1, max(min_withdraw, amount * rollover) / amount)

    Args:
        bonus: Normalized bonus dictionary with keys:
            - amount: Bonus amount
            - maxwithdraw: Maximum withdrawal limit
            - minwithdraw: Minimum withdrawal requirement
            - rollover: Wagering multiplier

    Returns:
        float: Perceived value score (0 if amount is 0 or negative)

    Example:
        >>> bonus = {'amount': 100, 'maxwithdraw': 500,
        ...          'minwithdraw': 50, 'rollover': 5}
        >>> calculate_perceived_value(bonus)
        42.5
    """
    amount = float(bonus.get('amount', 0))

    # No value if amount is zero or negative
    if amount <= 0:
        return 0

    max_withdraw = float(bonus.get('maxwithdraw', 0))
    min_withdraw = float(bonus.get('minwithdraw', 0))
    rollover = float(bonus.get('rollover', 0))

    # Use default max_withdraw if not specified
    # 3776 is approximately the median observed value
    if max_withdraw <= 0:
        max_withdraw = 3776

    # === NUMERATOR ===
    # Benefit from high withdrawal limits and bonus amount
    # log2(max_withdraw + 1) scales the max withdrawal benefit logarithmically
    # (1 + 0.2 * log10(amount + 1)) gives additional bonus for larger amounts
    withdrawal_benefit = log2(max_withdraw + 1)
    amount_multiplier = 1 + 0.2 * log10(amount + 1)
    numerator = 10 * withdrawal_benefit * amount_multiplier

    # === DENOMINATOR ===
    # Penalty for high wagering requirements

    # Calculate total wagering requirement
    wagering_requirement = amount * rollover

    # The "hurdle" is whichever is harder to achieve:
    # - Minimum withdrawal threshold, OR
    # - Total wagering requirement
    hurdle = max(min_withdraw, wagering_requirement)

    # Ratio of hurdle to bonus amount (minimum 1 to avoid division issues)
    hurdle_ratio = max(1, hurdle / amount)

    # Exponential penalty for high hurdles (^1.25 makes big hurdles worse)
    # Linear penalty for rollover (1 + rollover/20)
    denominator = pow(hurdle_ratio, 1.25) * (1 + rollover / 20)

    # Calculate final perceived value (never negative)
    return max(0, numerator / denominator)


# Aliases for backward compatibility with obfuscated code
gen_fp = generate_fingerprint
calc = calculate_perceived_value
