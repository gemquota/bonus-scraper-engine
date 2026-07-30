# Golf Scraper — Full Architecture Reference

## Module Dependency Graph

```
main.py  ──→  scraper.py  ──→  db.py  ──→  config.py
                │              │
                ├── network.py  └── (circular via local import)
                │
                ├── terminal.py ──→ config.py
                │                 └── server.py (HTTP POST)
                │
                └── server.py (flags)

server.py ──→ config.py
terminal.py ──→ config.py
```

## Data Flow

1. `main.py` starts `server.py` (blocking) and `scraper.run_scrape()` (daemon thread)
2. `run_scrape()` loads URLs, iterates accounts, spawns worker threads
3. Each `worker()` fetches page → parses merchant → logs in → syncs data → processes bonuses
4. Bonuses are fingerprinted, matched against existing records, stored in SQLite + CSV
5. `terminal.update_display()` prints progress to console + POSTs to server
6. `server.py` broadcasts updates to all connected WebSocket clients

## Key Design Decisions

- **Threading:** Scraper runs on daemon thread, server on main (blocks for Ctrl+C)
- **Auth:** Optional HTTP Basic Auth (enabled by setting `ui_pass` in config.ini)
- **DB:** Single SQLite file with FTS5 full-text search on bonus data
- **Sessions:** Pickle-serialized cookies for re-login avoidance (6hr TTL)
- **Frontend:** Fully inline React via Babel standalone — no build step
- **Color:** Red→yellow→green gradient for rates, spectral gradient for yield