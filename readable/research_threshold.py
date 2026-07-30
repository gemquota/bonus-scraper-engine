"""
research_threshold.py - Similarity Threshold Research Tool

Analyzes existing bonus data to help tune fuzzy matching thresholds.
"""

import sqlite3
import json
from itertools import combinations
from deduplication import calculate_similarity


def main():
    """
    Analyze bonus names for similarity to tune deduplication threshold.

    Groups bonuses by (merchant, amount, rollover, minwithdraw, maxwithdraw)
    and calculates pairwise similarity within each group. Prints pairs
    with similarity > 0.85 to help identify potential duplicates.
    """
    conn = sqlite3.connect('data/base.db')
    cursor = conn.cursor()

    # Join bonuses with sites to get merchant name
    query = """
    SELECT t.m, b.raw
    FROM b
    JOIN t ON b.u = t.u
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    # Group by key attributes (same merchant + same bonus terms)
    groups = {}
    for merchant, raw_json in rows:
        if not raw_json:
            continue

        data = json.loads(raw_json)
        name = data.get('name') or data.get('NAME') or ""
        amount = data.get('amount') or data.get('AMOUNT') or 0
        rollover = data.get('rollover') or data.get('ROLLOVER') or 0
        min_withdraw = data.get('minwithdraw') or data.get('MINWITHDRAW') or 0
        max_withdraw = data.get('maxwithdraw') or data.get('MAXWITHDRAW') or 0

        key = (merchant, amount, rollover, min_withdraw, max_withdraw)
        if key not in groups:
            groups[key] = set()
        groups[key].add(name)

    conn.close()

    # Print header
    print(f"{'Sim':<5} | {'Merchant':<15} | {'Name 1':<30} | {'Name 2':<30}")
    print("-" * 85)

    # Find similar pairs within each group
    for key, names in groups.items():
        if len(names) < 2:
            continue

        name_list = list(names)
        for name1, name2 in combinations(name_list, 2):
            similarity = calculate_similarity(name1, name2)
            if similarity > 0.85:
                merchant = str(key[0])[:15]
                print(f"{similarity:.3f} | {merchant:<15} | {str(name1)[:30]:<30} | {str(name2)[:30]:<30}")


if __name__ == "__main__":
    main()
