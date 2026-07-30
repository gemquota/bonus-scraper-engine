import argparse, sys
from rich.console import Console
from rich.table import Table
import db

def search(query, min_pv=0):
    return db.execute("SELECT b.u, b.eid, b.v, b.pv, b.raw FROM b JOIN b_fts ON b.rowid=b_fts.rowid WHERE b_fts MATCH ? AND b.pv>=? ORDER BY b.pv DESC", (query, min_pv))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query"); parser.add_argument("--pv", type=float, default=0)
    args = parser.parse_args()
    c = Console(); r = search(args.query, args.pv)
    if not r: c.print("[red]No results.[/]"); sys.exit(0)
    t = Table(title=f"Results: {args.query}")
    t.add_column("Site"); t.add_column("ID"); t.add_column("Value"); t.add_column("PV"); t.add_column("Details")
    for u, eid, v, pv, raw in r: t.add_row(u, str(eid), f"{v:.2f}", f"{pv:.2f}", str(raw)[:50]+"...")
    c.print(t)
