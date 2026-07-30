"""
deduplication.py - Fuzzy String Matching

Provides fuzzy matching functions for bonus name deduplication.
"""

import difflib
import re


def clean_name(name):
    """
    Normalize a bonus name for comparison.

    - Removes HTML tags
    - Collapses whitespace
    - Converts to lowercase

    Args:
        name: Raw bonus name string

    Returns:
        str: Normalized name
    """
    if not name:
        return ""

    # Remove HTML tags
    name = re.sub(r'<[^>]+>', '', name)

    # Normalize whitespace (collapse multiple spaces to single)
    name = ' '.join(name.split())

    return name.lower()


def extract_numbers(text):
    """
    Extract all numbers from a string.

    Args:
        text: Input string

    Returns:
        list: List of number strings found

    Example:
        >>> extract_numbers("Bonus 123 Level 45")
        ['123', '45']
    """
    return re.findall(r'\d+', text)


def extract_roman_numerals(text):
    """
    Extract roman numerals (I-X) that appear as separate words.

    Args:
        text: Input string (should be lowercase)

    Returns:
        list: List of roman numeral strings found

    Example:
        >>> extract_roman_numerals("level ii bonus")
        ['ii']
    """
    return re.findall(r'\b(i{1,3}|iv|v|vi{1,3}|ix|x)\b', text)


def calculate_similarity(s1, s2):
    """
    Calculate similarity ratio between two strings.

    Uses difflib.SequenceMatcher for fuzzy string comparison.

    Args:
        s1: First string
        s2: Second string

    Returns:
        float: Similarity ratio (0.0 to 1.0)
    """
    return difflib.SequenceMatcher(None, clean_name(s1), clean_name(s2)).ratio()


def is_fuzzy_match(s1, s2, threshold=0.85):
    """
    Check if two strings are fuzzy matches.

    Two strings are considered a match if:
    1. Their similarity ratio >= threshold (default 85%)
    2. They don't have conflicting numbers (e.g., "Bonus 1" vs "Bonus 2")
    3. They don't have conflicting roman numerals (e.g., "Level I" vs "Level II")

    Args:
        s1: First string
        s2: Second string
        threshold: Minimum similarity ratio (default 0.85)

    Returns:
        bool: True if strings are a fuzzy match

    Examples:
        >>> is_fuzzy_match("Free Spin Bonus", "Free Spins Bonus")
        True
        >>> is_fuzzy_match("Bonus Level 1", "Bonus Level 2")
        False
        >>> is_fuzzy_match("Daily Reward I", "Daily Reward II")
        False
    """
    c1 = clean_name(s1)
    c2 = clean_name(s2)

    # Handle empty strings
    if not c1 and not c2:
        return True
    if not c1 or not c2:
        return False

    # Check similarity threshold
    ratio = difflib.SequenceMatcher(None, c1, c2).ratio()
    if ratio < threshold:
        return False

    # Check for conflicting numbers
    numbers1 = extract_numbers(c1)
    numbers2 = extract_numbers(c2)
    if numbers1 != numbers2:
        # If BOTH have numbers and they differ, not a match
        if numbers1 and numbers2:
            return False

    # Check for conflicting roman numerals
    roman1 = extract_roman_numerals(c1)
    roman2 = extract_roman_numerals(c2)
    if roman1 != roman2:
        # If BOTH have roman numerals and they differ, not a match
        if roman1 and roman2:
            return False

    return True
