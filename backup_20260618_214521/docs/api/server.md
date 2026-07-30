# server.py

## Module Overview

- **File:** `server.py`
- **Functions:** 2
- **Classes:** 2
- **Imports:** 8

### Dependencies
- `import json`
- `from pathlib import Path`
- `from fastapi import FastAPI`
- `from fastapi import WebSocket`
- `from fastapi import WebSocketDisconnect`
- `from fastapi import Depends`
- `from fastapi import HTTPException`
- `from fastapi import status`
- `from fastapi.responses import HTMLResponse`
- `from fastapi.security import HTTPBasic`
- `from fastapi.security import HTTPBasicCredentials`
- `import uvicorn`
- `from pydantic import BaseModel`
- `from pydantic import Field`
- `import config`

### Function Reference

| Function | Line | Signature |
|----------|------|-----------|
| verify_auth | 39 | `verify_auth(credentials: HTTPBasicCredentials | None=Depends(security))` |
| start_server | 97 | `start_server()` |

### Function Details

#### `verify_auth()`

**Location:** `server.py:39`

**Docstring:** Optional auth — skip if no UI_PASS configured, else validate.

- **Branches:** 2
- **Calls:** 3
- **Returns:** 2
- **Body lines:** 8

#### `start_server()`

**Location:** `server.py:97`

- **Branches:** 0
- **Calls:** 1
- **Returns:** 0
- **Body lines:** 2
