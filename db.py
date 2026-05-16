import os
import psycopg2
from psycopg2.extras import RealDictCursor


class DB:
    def __init__(self):
        self.dsn = os.getenv("DATABASE_URL")
        if not self.dsn:
            host = os.getenv("DB_HOST", "db")
            port = int(os.getenv("DB_PORT", 5432))
            user = os.getenv("DB_USER", "rfid")
            password = os.getenv("DB_PASSWORD", "rfidpassword")
            database = os.getenv("DB_NAME", "rfid")
            self.dsn = f"host={host} port={port} user={user} password={password} dbname={database}"

    def connect(self):
        return _ConnectionWrapper(psycopg2.connect(self.dsn))


class _ConnectionWrapper:
    """Wraps psycopg2 connection so .cursor(dictionary=True) keeps working
    like the old mysql-connector API used across the codebase."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self, dictionary: bool = False):
        if dictionary:
            return _CursorWrapper(self._conn.cursor(cursor_factory=RealDictCursor))
        return _CursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


class _CursorWrapper:
    """Translates MySQL-style %s placeholders into psycopg2 (already %s) and
    exposes lastrowid via RETURNING when needed."""

    def __init__(self, cur):
        self._cur = cur
        self._last_returning = None

    def execute(self, query, params=None):
        # psycopg2 already uses %s, so most queries pass through unchanged.
        return self._cur.execute(query, params)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def close(self):
        return self._cur.close()

    @property
    def lastrowid(self):
        # psycopg2 doesn't have lastrowid; callers that need the id should use RETURNING.
        # Kept for API compatibility — returns None.
        return None

    @property
    def rowcount(self):
        return self._cur.rowcount

    def __getattr__(self, name):
        return getattr(self._cur, name)

    def __iter__(self):
        return iter(self._cur)
