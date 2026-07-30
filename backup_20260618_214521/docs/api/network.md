# network.py

## Module Overview

- **File:** `network.py`
- **Functions:** 10
- **Classes:** 0
- **Imports:** 4

### Dependencies
- `import base64`
- `import json`
- `import re`
- `import time`
- `from pathlib import Path`
- `import cloudscraper`
- `import requests`
- `import config`

### Function Reference

| Function | Line | Signature |
|----------|------|-----------|
| create_session | 8 | `create_session()` |
| post_json | 13 | `post_json(session, url, data)` |
| _parklogic_redirect | 18 | `_parklogic_redirect(session, html)` |
| get_page | 27 | `get_page(session, url)` |
| _extract_var | 34 | `_extract_var(html, name)` |
| parse_merchant_info | 38 | `parse_merchant_info(html)` |
| build_api_url | 41 | `build_api_url(url)` |
| login | 44 | `login(session, url, username, password, merchant_id)` |
| sync_user_data | 48 | `sync_user_data(session, url, merchant_id, access_token, access_id)` |
| check_ip_reputation | 52 | `check_ip_reputation(api_key)` |

### Function Details

#### `create_session()`

**Location:** `network.py:8`

- **Branches:** 0
- **Calls:** 2
- **Returns:** 1
- **Body lines:** 4

#### `post_json()`

**Location:** `network.py:13`

- **Branches:** 0
- **Calls:** 3
- **Returns:** 1
- **Body lines:** 4

#### `_parklogic_redirect()`

**Location:** `network.py:18`

- **Branches:** 3
- **Calls:** 7
- **Returns:** 3
- **Body lines:** 8

#### `get_page()`

**Location:** `network.py:27`

- **Branches:** 1
- **Calls:** 4
- **Returns:** 1
- **Body lines:** 6

#### `_extract_var()`

**Location:** `network.py:34`

- **Branches:** 0
- **Calls:** 4
- **Returns:** 1
- **Body lines:** 3

#### `parse_merchant_info()`

**Location:** `network.py:38`

- **Branches:** 0
- **Calls:** 2
- **Returns:** 1
- **Body lines:** 2

#### `build_api_url()`

**Location:** `network.py:41`

- **Branches:** 0
- **Calls:** 1
- **Returns:** 1
- **Body lines:** 2

#### `login()`

**Location:** `network.py:44`

- **Branches:** 0
- **Calls:** 2
- **Returns:** 1
- **Body lines:** 3

#### `sync_user_data()`

**Location:** `network.py:48`

- **Branches:** 0
- **Calls:** 1
- **Returns:** 1
- **Body lines:** 3

#### `check_ip_reputation()`

**Location:** `network.py:52`

- **Branches:** 3
- **Calls:** 9
- **Returns:** 4
- **Body lines:** 12
