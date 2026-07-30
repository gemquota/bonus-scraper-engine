"""
search.py - Full-Text Search CLI

Search bonuses using SQLite FTS5 full-text search.
"""

import db
import sys
import argparse
from rich.console import Console
from rich.table import Table


def search(query, min_pv=0):
    """
    Search bonuses using full-text search.

    Uses SQLite FTS5 for fast, relevant text matching.

    Args:
        query: FTS5 search query (supports AND, OR, NOT, phrases)
        min_pv: Minimum perceived value filter

    Returns:
        list: Tuples of (url, external_id, value, perceived_value, raw_json)
    """
    sql = """
    SELECT b.u, b.eid, b.v, b.pv, b.raw
    FROM b
    JOIN b_fts ON b.rowid = b_fts.rowid
    WHERE b_fts MATCH ? AND b.pv >= ?
    ORDER BY b.pv DESC
    """
    results = db.query(sql, (query, min_pv))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Global Bonus Search")
    parser.add_argument("query", help="Search query (FTS5 syntax)")
    parser.add_argument("--pv", type=float, default=0, help="Minimum Perceived Value")
    args = parser.parse_args()

    console = Console()
    results = search(args.query, args.pv)

    if not results:
        console.print("[red]No results found.[/]")
        sys.exit(0)

    table = Table(title=f"Search Results for: {args.query}")
    table.add_column("Site", style="cyan")
    table.add_column("ID", style="magenta")
    table.add_column("Value", style="green")
    table.add_column("PV", style="bold yellow")
    table.add_column("Details", style="dim")

    for url, external_id, value, perceived_value, raw in results:
        table.add_row(
            url,
            str(external_id),
            f"{value:.2f}",
            f"{perceived_value:.2f}",
            raw[:50] + "..."
        )

    console.print(table)
