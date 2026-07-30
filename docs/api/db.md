# db.py

## Module Overview

- **File:** `db.py`
- **Functions:** 18
- **Classes:** 0
- **Imports:** 5

### Dependencies
- `import csv`
- `import datetime`
- `import difflib`
- `import hashlib`
- `import pickle`
- `import re`
- `import sqlite3`
- `from contextlib import contextmanager`
- `from math import log2`
- `from math import log10`
- `from math import pow`
- `from pathlib import Path`
- `import config`

### Function Reference

| Function | Line | Signature |
|----------|------|-----------|
| get_connection | 17 | `get_connection()` |
| cursor_context | 23 | `cursor_context()` |
| execute | 30 | `execute(query, params=())` |
| initialize_database | 35 | `initialize_database()` |
| load_session | 49 | `load_session(url, uid)` |
| save_session | 54 | `save_session(url, uid, cookies, data)` |
| _init_csv | 57 | `_init_csv(path)` |
| append_csv_row | 63 | `append_csv_row(row, path='data/bonuses.csv')` |
| log_event | 68 | `log_event(level, source, message)` |
| search | 71 | `search(query, min_pv=0)` |
| _clean | 76 | `_clean(name)` |
| is_fuzzy_match | 80 | `is_fuzzy_match(a, b, threshold=0.85)` |
| find_matching_name | 88 | `find_matching_name(name, existing_names, threshold=0.85)` |
| float_value | 93 | `float_value(value)` |
| fingerprint_bonus | 97 | `fingerprint_bonus(bonus)` |
| get_url_scores | 101 | `get_url_scores()` |
| parse_expiry | 105 | `parse_expiry(text)` |
| perceived_value | 117 | `perceived_value(bonus)` |

### Function Details

#### `get_connection()`

**Location:** `db.py:17`

- **Branches:** 1
- **Calls:** 1
- **Returns:** 1
- **Body lines:** 4

#### `cursor_context()`

**Location:** `db.py:23`

- **Branches:** 0
- **Calls:** 5
- **Returns:** 0
- **Body lines:** 6

#### `execute()`

**Location:** `db.py:30`

- **Branches:** 0
- **Calls:** 3
- **Returns:** 1
- **Body lines:** 4

#### `initialize_database()`

**Location:** `db.py:35`

- **Branches:** 0
- **Calls:** 2
- **Returns:** 0
- **Body lines:** 13

#### `load_session()`

**Location:** `db.py:49`

- **Branches:** 1
- **Calls:** 3
- **Returns:** 2
- **Body lines:** 4

#### `save_session()`

**Location:** `db.py:54`

- **Branches:** 0
- **Calls:** 3
- **Returns:** 0
- **Body lines:** 2

#### `_init_csv()`

**Location:** `db.py:57`

- **Branches:** 1
- **Calls:** 6
- **Returns:** 1
- **Body lines:** 5

#### `append_csv_row()`

**Location:** `db.py:63`

- **Branches:** 0
- **Calls:** 7
- **Returns:** 0
- **Body lines:** 4

#### `log_event()`

**Location:** `db.py:68`

- **Branches:** 0
- **Calls:** 1
- **Returns:** 0
- **Body lines:** 2

#### `search()`

**Location:** `db.py:71`

- **Branches:** 0
- **Calls:** 1
- **Returns:** 1
- **Body lines:** 2

#### `_clean()`

**Location:** `db.py:76`

- **Branches:** 1
- **Calls:** 5
- **Returns:** 2
- **Body lines:** 3

#### `is_fuzzy_match()`

**Location:** `db.py:80`

- **Branches:** 2
- **Calls:** 8
- **Returns:** 3
- **Body lines:** 7

#### `find_matching_name()`

**Location:** `db.py:88`

- **Branches:** 1
- **Calls:** 1
- **Returns:** 2
- **Body lines:** 4

#### `float_value()`

**Location:** `db.py:93`

- **Branches:** 0
- **Calls:** 1
- **Returns:** 2
- **Body lines:** 3

#### `fingerprint_bonus()`

**Location:** `db.py:97`

- **Branches:** 0
- **Calls:** 8
- **Returns:** 1
- **Body lines:** 3

#### `get_url_scores()`

**Location:** `db.py:101`

- **Branches:** 1
- **Calls:** 1
- **Returns:** 1
- **Body lines:** 3

#### `parse_expiry()`

**Location:** `db.py:105`

- **Branches:** 4
- **Calls:** 6
- **Returns:** 3
- **Body lines:** 11

#### `perceived_value()`

**Location:** `db.py:117`

- **Branches:** 1
- **Calls:** 15
- **Returns:** 2
- **Body lines:** 9
