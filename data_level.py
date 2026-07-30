"""
Data level enforcement for Bonus Scraper Pro.

Maps subscription tiers to export capabilities:
  Basic (Standard):   CSV export, core fields only
  Advanced (Pro):     CSV + JSON, perceived value scoring, filtered export
  Expert (Elite):     All formats, raw data, full-text search, custom fields

Usage:
    from data_level import get_data_level, export_bonuses
    export_bonuses(bonuses, output_dir)
"""
import csv, json, os, sqlite3
from pathlib import Path

CORE_FIELDS = [
    "url", "mname", "name", "amount", "perceived_value",
    "minwithdraw", "maxwithdraw", "rollover", "expiry"
]

ADVANCED_FIELDS = CORE_FIELDS + [
    "transactiontype", "bonusfixed", "bonus", "bonusrandom",
    "claimconfig", "claimcondition", "balance", "referlink"
]

EXPERT_FIELDS = ADVANCED_FIELDS + [
    "mintopup", "maxtopup", "reset", "is_new",
    "raw_json", "fingerprint", "mirrors"
]

LEVELS = {"basic": 0, "advanced": 1, "expert": 2}

def get_data_level():
    """Return current data level from env var or license file."""
    level = os.environ.get("SCRAPER_DATA_LEVEL", "basic")
    # Fallback: check license file
    if level == "basic":
        lic_path = Path("data/license_active.json")
        if lic_path.exists():
            try:
                lic = json.loads(lic_path.read_text())
                level = lic.get("data_level", "basic")
            except: pass
    return level if level in LEVELS else "basic"

def level_code():
    return LEVELS.get(get_data_level(), 0)

def can_export_json():
    return level_code() >= 1  # Advanced+

def has_value_scoring():
    return level_code() >= 1  # Advanced+

def can_raw_access():
    return level_code() >= 2  # Expert

def can_fulltext_search():
    return level_code() >= 2  # Expert

def can_custom_fields():
    return level_code() >= 2  # Expert

def get_export_fields():
    level = get_data_level()
    if level == "expert":
        return EXPERT_FIELDS
    elif level == "advanced":
        return ADVANCED_FIELDS
    return CORE_FIELDS

def filter_bonus_row(row, level=None):
    """Filter a bonus dict to only include fields for the current tier."""
    if level is None:
        level = get_data_level()
    allowed = get_export_fields()
    return {k: v for k, v in row.items() if k in allowed}

def export_csv(bonuses, output_path, level=None):
    """Export bonuses to CSV, filtered by tier level."""
    if level is None:
        level = get_data_level()
    fields = get_export_fields()
    filtered = [filter_bonus_row(b, level) for b in bonuses]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(filtered)
    print(f"  📄 CSV exported ({level}): {path} ({len(filtered)} rows)", flush=True)

def export_json(bonuses, output_path, level=None):
    """Export bonuses to JSON. Requires Advanced+ tier."""
    if level is None:
        level = get_data_level()
    if level_code() < 1:
        print(f"  ⚠️  JSON export requires Advanced tier or higher", flush=True)
        return False

    filtered = [filter_bonus_row(b, level) for b in bonuses]
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(filtered, indent=2, default=str))
    print(f"  📊 JSON exported ({level}): {path} ({len(filtered)} rows)", flush=True)
    return True

def export_expert(bonuses, output_path, level=None):
    """Export raw/full data. Requires Expert tier."""
    if level is None:
        level = get_data_level()
    if level_code() < 2:
        print(f"  ⚠️  Full data export requires Expert tier", flush=True)
        return False

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bonuses, indent=2, default=str))
    print(f"  🔬 Expert export: {path} ({len(bonuses)} rows)", flush=True)
    return True

def export_all(bonuses, output_dir="data", prefix="bonuses"):
    """Run full export pipeline based on current tier level."""
    level = get_data_level()
    timestamp = __import__('time').strftime('%Y%m%d_%H%M%S')

    # Always export CSV (all tiers)
    csv_path = Path(output_dir) / f"{prefix}_{timestamp}.csv"
    export_csv(bonuses, csv_path, level)

    # JSON for Advanced+
    if level_code() >= 1:
        json_path = Path(output_dir) / f"{prefix}_{timestamp}.json"
        export_json(bonuses, json_path, level)

    # Expert full export
    if level_code() >= 2:
        expert_path = Path(output_dir) / f"{prefix}_{timestamp}_full.json"
        export_expert(bonuses, expert_path, level)

    return csv_path

def db_search(query, min_pv=0):
    """Full-text search on bonus database. Expert tier only."""
    if level_code() < 2:
        return {"error": "Full-text search requires Elite tier"}
    import db
    results = db.search(query, min_pv)
    return results


if __name__ == "__main__":
    print(f"Data level: {get_data_level()} ({level_code()})")
    print(f"  JSON export:  {'✓' if can_export_json() else '✕'}")
    print(f"  Value scoring: {'✓' if has_value_scoring() else '✕'}")
    print(f"  Raw access:   {'✓' if can_raw_access() else '✕'}")
    print(f"  FTS search:   {'✓' if can_fulltext_search() else '✕'}")
    print(f"  Fields: {len(get_export_fields())}")
