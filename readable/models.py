"""
models.py - Data Models

Defines CSV headers and data transformation functions for bonus data.
"""

# CSV column headers for bonus data export
CSV_HEADERS = [
    "url",              # Site URL
    "mname",            # Merchant name
    "id",               # Bonus ID
    "name",             # Bonus name/title
    "transactiontype",  # Type of transaction
    "bonusfixed",       # Fixed bonus amount
    "amount",           # Main bonus amount
    "minwithdraw",      # Minimum withdrawal amount
    "maxwithdraw",      # Maximum withdrawal amount
    "rollover",         # Wagering requirement multiplier
    "balance",          # Current balance
    "claimconfig",      # Claim configuration
    "claimcondition",   # Conditions to claim
    "bonus",            # Bonus details
    "bonusrandom",      # Random bonus flag
    "reset",            # Reset conditions
    "mintopup",         # Minimum top-up amount
    "maxtopup",         # Maximum top-up amount
    "referlink",        # Referral link
    "perceived_value",  # Calculated value score
    "is_new"            # Whether this is a new bonus (1=new, 0=existing)
]


def normalize_bonus(bonus_dict):
    """
    Normalize bonus data by converting all keys to lowercase.

    The API sometimes returns keys in UPPERCASE, sometimes lowercase.
    This normalizes them for consistent access.

    Args:
        bonus_dict: Raw bonus dictionary from API

    Returns:
        dict: Same data with all keys lowercase

    Example:
        >>> normalize_bonus({'AMOUNT': 100, 'Name': 'Free Spin'})
        {'amount': 100, 'name': 'Free Spin'}
    """
    return {key.lower(): value for key, value in bonus_dict.items()}


def create_row(bonus, site_url, merchant_name, perceived_value, is_new):
    """
    Create a CSV row dictionary from bonus data.

    Handles both lowercase and UPPERCASE field names from API by
    checking both variants.

    Args:
        bonus: Normalized bonus dictionary
        site_url: URL of the site
        merchant_name: Name of the merchant
        perceived_value: Calculated perceived value score
        is_new: 1 if new bonus, 0 if existing

    Returns:
        dict: Row data matching CSV_HEADERS structure
    """
    row = {}

    # Copy all standard fields, checking both cases
    for key in CSV_HEADERS[:-2]:  # Exclude perceived_value and is_new
        row[key] = bonus.get(key, bonus.get(key.upper(), ''))

    # Override with provided values
    row['url'] = site_url
    row['mname'] = merchant_name
    row['perceived_value'] = perceived_value
    row['is_new'] = is_new

    return row


# Aliases for backward compatibility with obfuscated code
H = CSV_HEADERS
norm = normalize_bonus
row = create_row
