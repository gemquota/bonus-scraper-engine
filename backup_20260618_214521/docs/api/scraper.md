# scraper.py

## Module Overview

- **File:** `scraper.py`
- **Functions:** 4
- **Classes:** 0
- **Imports:** 7

### Dependencies
- `import csv`
- `import datetime`
- `import json`
- `import random`
- `import threading`
- `import time`
- `from concurrent.futures import ThreadPoolExecutor`
- `from pathlib import Path`
- `from requests.exceptions import HTTPError`
- `import sys`
- `import config`
- `import db`
- `import terminal`
- `import server`
- `import network as net`

### Function Reference

| Function | Line | Signature |
|----------|------|-----------|
| classify_error | 18 | `classify_error(exc)` |
| process_bonus | 27 | `process_bonus(bonus, merchant_name, url, fingerprint, perceived_value, expiry)` |
| worker | 49 | `worker(chunk_id, stats, stats_lock, total_tasks, ip_score, record_raw, worker_count, tasks)` |
| run_scrape | 116 | `run_scrape()` |

### Function Details

#### `classify_error()`

**Location:** `scraper.py:18`

- **Branches:** 4
- **Calls:** 3
- **Returns:** 5
- **Body lines:** 8

#### `process_bonus()`

**Location:** `scraper.py:27`

- **Branches:** 7
- **Calls:** 17
- **Returns:** 3
- **Body lines:** 21

#### `worker()`

**Location:** `scraper.py:49`

- **Branches:** 9
- **Calls:** 69
- **Returns:** 0
- **Body lines:** 66

#### `run_scrape()`

**Location:** `scraper.py:116`

- **Branches:** 6
- **Calls:** 29
- **Returns:** 0
- **Body lines:** 31
