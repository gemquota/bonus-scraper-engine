"""
License validation for Bonus Scraper Pro.
Validates your subscription tier and enforces scrape schedule.

Tiers:
  Trial:   Free first month (Monday scrape)
  Starter: $47/mo  — Monday scrape
  Pro:     $97/mo  — Monday + Thursday + Saturday
  Elite:   $197/mo — Daily scrapes

Usage:
    export SCRAPER_LICENSE_KEY="SCRPR-XXXX-XXXX-XXXX"
    python3 validate_license.py

The scraper will only run full scrapes on your tier's scheduled days.
On non-scrape days, validation still works but the scraper should
skip the main scrape cycle (or only update metadata).
"""

import json, os, sys, time
from pathlib import Path

CACHE_FILE = Path(__file__).parent / "data" / "license.json"
CACHE_TTL = 3600  # 1 hour

TIER_SCHEDULES = {
    'trial':   ['Monday'],
    'tier1':   ['Monday'],
    'tier2':   ['Thursday', 'Saturday', 'Monday'],
    'tier3':   ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
}

TIER_NAMES = {
    'trial':   'Free Trial',
    'tier1':   'Starter',
    'tier2':   'Pro',
    'tier3':   'Elite',
}

def get_today():
    return time.strftime('%A')  # e.g. 'Monday'

def get_license_key():
    key = os.environ.get("SCRAPER_LICENSE_KEY", "")
    if key:
        return key
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text()).get("key", "")
        except:
            pass
    return ""

def validate_license(force=False):
    from datetime import datetime  # noqa: needed for cache age check

    server_url = os.environ.get("LICENSE_SERVER_URL", "http://localhost:3000")
    license_key = get_license_key()
    today = get_today()
    
    defaults = {
        "valid": False,
        "tier": "trial",
        "tier_name": "Free Trial",
        "scrape_days": ["Monday"],
        "data_level": "basic",
        "scrape_today": today == "Monday",
        "error": "No license key configured",
    }
    
    # Check cache
    if not force and CACHE_FILE.exists():
        try:
            cached = json.loads(CACHE_FILE.read_text())
            if cached.get("valid") and cached.get("validatedAt"):
                age = time.time() - datetime.fromisoformat(cached["validatedAt"]).timestamp()
                if age < CACHE_TTL:
                    return cached
        except:
            pass
    
    if not license_key:
        print(f"  ⚠️  No license key. Free trial mode (Monday scrapes only).", flush=True)
        print(f"     Set SCRAPER_LICENSE_KEY or subscribe at the subscription portal.", flush=True)
        _write_cache(defaults)
        return defaults
    
    # Validate against server
    try:
        import requests
        r = requests.post(f"{server_url}/api/license/validate",
            json={"license_key": license_key},
            timeout=10)
        data = r.json()
    except Exception as e:
        print(f"  ⚠️  License server unreachable ({e}). Using cached mode.", flush=True)
        if CACHE_FILE.exists():
            cached = json.loads(CACHE_FILE.read_text())
            if cached.get("valid"):
                return cached
        return defaults
    
    if data.get("valid"):
        tier = data.get("tier", "trial")
        tier_name = data.get("tier_name", "Unknown")
        scrape_days = data.get("scrape_days", ["Monday"])
        data_level = data.get("data_level", "basic")
        scrape_today = today in scrape_days
        
        if scrape_today:
            print(f"  ✅ {tier_name} — scraping today ({today})", flush=True)
        else:
            days_str = ", ".join(scrape_days)
            print(f"  ℹ️  {tier_name} — no scrape today ({today}). Your days: {days_str}", flush=True)
        
        result = {
            "valid": True,
            "tier": tier,
            "tier_name": tier_name,
            "scrape_days": scrape_days,
            "data_level": data_level,
            "scrape_today": scrape_today,
            "features": data.get("features", {}),
            "customer_email": data.get("customer_email", ""),
            "validatedAt": datetime.utcnow().isoformat(),
            "expires_at": data.get("expires_at"),
        }
        _write_cache({**result, "key": license_key})
        return result
    else:
        print(f"  ❌ {data.get('error', 'License invalid')}", flush=True)
        return {**defaults, "error": data.get("error", "Invalid license")}

def _write_cache(data):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, indent=2, default=str))

if __name__ == "__main__":
    from datetime import datetime  # noqa
    force = "--force" in sys.argv
    result = validate_license(force)
    print(json.dumps(result, indent=2, default=str))
    
    if result.get("scrape_today"):
        print(f"\n  → Scrape today: {get_today()} ✓")
    else:
        print(f"\n  → No scrape scheduled for {get_today()}")
    
    sys.exit(0 if result.get("valid") else 1)
