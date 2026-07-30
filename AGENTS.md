# Golf Bonuses Scraper

## Conservative Scraping

This scraper must be **gentle** to avoid IP bans.

- **Workers**: Set via `workers` in `in/config/config.ini` (currently 6).
- **Delays**: `min_delay = 3.0`, `max_delay = 6.0` — random sleep between requests.
- **Exponential backoff**: On retry, wait `2^attempt * 2` seconds (attempt 1 = 4s, attempt 2 = 8s).
- **No proxies** — direct connection only (VPN handled externally).

## Session Identity

- Each worker gets its own unique user agent from the 50-entry `USER_AGENTS` list (Chrome, Firefox, Safari, Edge, Opera across Windows/macOS/Linux).
- `cloudscraper` browser fingerprints are also varied per worker.

## Failure Tracking

- **5/5 failures**: When a URL reaches 5 consecutive failures, it is moved from `in/config/urls.txt` to `in/config/oldurls.txt`.
- **Success resets counter**: If a URL succeeds at any time, its failure count resets to 0/5.
- The failure counter (`a` column in table `t`) tracks consecutive failures. A success sets it to 0.
