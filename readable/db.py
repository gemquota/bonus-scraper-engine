"""
db.py - Database Layer

SQLite database connection and schema management.
"""

import sqlite3

# Database file path
DATABASE_PATH = 'data/base.db'


def connect():
    """
    Create a connection to the SQLite database.

    Returns:
        sqlite3.Connection: Database connection object
    """
    return sqlite3.connect(DATABASE_PATH)


def init():
    """
    Initialize database schema.

    Creates all required tables if they don't exist:
    - t: Sites/targets table
    - b: Bonuses table
    - s: Sessions table (cached logins)
    - m: Metrics table (run statistics)
    - l: Logs table (error logs)
    - b_fts: Full-text search index on bonuses
    """
    with connect() as conn:
        conn.executescript("""
            -- Sites/Targets table
            CREATE TABLE IF NOT EXISTS t(
                u TEXT PRIMARY KEY,      -- URL
                m TEXT,                  -- Merchant name
                p TEXT,                  -- Platform (unused)
                g TEXT,                  -- Group (unused)
                a INT DEFAULT 1,         -- Active flag
                ts DATETIME              -- Last seen timestamp
            );

            -- Bonuses table
            CREATE TABLE IF NOT EXISTS b(
                uid TEXT PRIMARY KEY,    -- Unique ID (url|bonus_id)
                eid TEXT,                -- External/API bonus ID
                u TEXT,                  -- Site URL
                v REAL,                  -- Value/amount
                pv REAL,                 -- Perceived value score
                w REAL,                  -- (unused)
                c REAL,                  -- (unused)
                t TEXT,                  -- (unused)
                raw TEXT,                -- Raw JSON data
                h TEXT,                  -- (unused)
                exp DATETIME,            -- Expiry date
                fp TEXT,                 -- Fingerprint hash
                mirrors TEXT,            -- Comma-separated mirror URLs
                s1 DATETIME DEFAULT CURRENT_TIMESTAMP,  -- First seen
                sl DATETIME,             -- Last seen
                mname TEXT,              -- Merchant name
                name TEXT                -- Bonus name
            );

            -- Sessions table (cached logins)
            CREATE TABLE IF NOT EXISTS s(
                uid TEXT,                -- Phone number (user ID)
                u TEXT,                  -- Site URL
                ck BLOB,                 -- Pickled cookies
                data BLOB,               -- Pickled user data
                ua TEXT,                 -- User agent
                ip TEXT,                 -- IP address
                ok INT DEFAULT 1,        -- Valid flag
                ts DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(uid, u)
            );

            -- Metrics table (run statistics)
            CREATE TABLE IF NOT EXISTS m(
                rid TEXT,                -- Run ID
                ts DATETIME DEFAULT CURRENT_TIMESTAMP,
                dur REAL,                -- Duration
                cnt INT,                 -- Count
                new INT,                 -- New items found
                spv REAL,                -- Sum of perceived values
                err INT                  -- Error count
            );

            -- Logs table
            CREATE TABLE IF NOT EXISTS l(
                id INTEGER PRIMARY KEY,
                ts DATETIME DEFAULT CURRENT_TIMESTAMP,
                lvl TEXT,                -- Level (E301, E201, etc.)
                src TEXT,                -- Source URL
                msg TEXT                 -- Error message
            );

            -- Full-text search virtual table for bonuses
            CREATE VIRTUAL TABLE IF NOT EXISTS b_fts USING fts5(
                uid UNINDEXED,
                eid,
                u,
                raw,
                content='b',
                content_rowid='rowid'
            );

            -- Trigger: Insert into FTS after bonus insert
            CREATE TRIGGER IF NOT EXISTS b_ai AFTER INSERT ON b BEGIN
                INSERT INTO b_fts(rowid, uid, eid, u, raw)
                VALUES (new.rowid, new.uid, new.eid, new.u, new.raw);
            END;

            -- Trigger: Remove from FTS after bonus delete
            CREATE TRIGGER IF NOT EXISTS b_ad AFTER DELETE ON b BEGIN
                INSERT INTO b_fts(b_fts, rowid, uid, eid, u, raw)
                VALUES('delete', old.rowid, old.uid, old.eid, old.u, old.raw);
            END;

            -- Trigger: Update FTS after bonus update
            CREATE TRIGGER IF NOT EXISTS b_au AFTER UPDATE ON b BEGIN
                INSERT INTO b_fts(b_fts, rowid, uid, eid, u, raw)
                VALUES('delete', old.rowid, old.uid, old.eid, old.u, old.raw);
                INSERT INTO b_fts(rowid, uid, eid, u, raw)
                VALUES (new.rowid, new.uid, new.eid, new.u, new.raw);
            END;
        """)


def query(sql, args=()):
    """
    Execute a SQL query and return results.

    Handles both SELECT and INSERT/UPDATE/DELETE queries.

    Args:
        sql: SQL query string with ? placeholders
        args: Tuple of query parameters

    Returns:
        list: Query results (empty for non-SELECT queries)

    Example:
        >>> query("SELECT * FROM b WHERE pv > ?", (10,))
        [(row1...), (row2...), ...]

        >>> query("INSERT INTO l(lvl, src, msg) VALUES(?, ?, ?)",
        ...       ("E301", "https://example.com", "Error message"))
        []
    """
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(sql, args)
    conn.commit()
    results = cursor.fetchall()
    conn.close()
    return results


# Aliases for backward compatibility with obfuscated code
C = connect
I = init
Q = query
