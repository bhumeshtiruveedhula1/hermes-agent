# core/hermes_db.py — Phase 17: Persistent Memory & User Intelligence
# SQLite memory store for Hermes — sessions, messages, memory entries, skills,
# user profile.
#
# Architecture learnings from NousResearch/hermes-agent hermes_state.py:
#   - WAL mode for concurrent FastAPI readers + sync thread writers
#   - FTS5 via SQL triggers for zero-maintenance full-text search
#   - BEGIN IMMEDIATE + jitter retry for write contention under concurrent load
#   - Declarative schema: SCHEMA_SQL is the single source of truth
#   - Thread-local connections so every thread gets its own SQLite handle
#
# Hermes-specific adaptations:
#   - Per-user isolation (user_id on every table)
#   - messages store "text" (not tool_calls/reasoning) — chat-focused
#   - memory_entries + skills + user_profile tables for Phase 17 systems
#   - Singleton via get_db() — same instance reused across the process

import json
import random
import sqlite3
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path("memory/hermes.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Schema SQL — CREATE IF NOT EXISTS for every table + index.
# FTS5 virtual table is created SEPARATELY in _init_schema() because
# CREATE VIRTUAL TABLE ... IF NOT EXISTS is not reliably atomic in
# executescript() on all SQLite versions.
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER NOT NULL,
    applied_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id            TEXT    PRIMARY KEY,
    user_id       TEXT    NOT NULL DEFAULT 'user_1',
    title         TEXT    NOT NULL DEFAULT 'New Mission',
    summary       TEXT    NOT NULL DEFAULT '',
    tools_used    TEXT    NOT NULL DEFAULT '[]',   -- JSON array
    pinned        INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL,
    parent_id     TEXT,                            -- compression lineage
    message_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id         TEXT    PRIMARY KEY,
    session_id TEXT    NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id    TEXT    NOT NULL DEFAULT 'user_1',
    role       TEXT    NOT NULL,                   -- 'user'|'hermes'|'system'
    content    TEXT    NOT NULL,
    tools      TEXT    NOT NULL DEFAULT '[]',      -- JSON array of tool names
    ts         TEXT    NOT NULL,
    is_summary INTEGER NOT NULL DEFAULT 0          -- 1 = compression summary
);

CREATE TABLE IF NOT EXISTS memory_entries (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL DEFAULT 'user_1',
    content    TEXT NOT NULL,
    category   TEXT NOT NULL DEFAULT 'general',   -- preference|fact|correction
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    description     TEXT NOT NULL,
    trigger_phrases TEXT NOT NULL DEFAULT '[]',   -- JSON array
    steps_json      TEXT NOT NULL DEFAULT '[]',   -- JSON array of plan steps
    use_count       INTEGER NOT NULL DEFAULT 0,
    last_used       TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_profile (
    user_id    TEXT PRIMARY KEY,
    profile_md TEXT NOT NULL DEFAULT '',
    soul_md    TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_user    ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user    ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_user      ON memory_entries(user_id);
"""

# FTS5 triggers — auto-maintain the full-text index on messages.
# Using triggers (NousResearch pattern) so we never need to call
# an explicit INSERT into messages_fts manually.
FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    tools,
    session_id UNINDEXED,
    user_id    UNINDEXED
);

CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content, tools, session_id, user_id)
    VALUES (
        new.rowid,
        COALESCE(new.content, ''),
        COALESCE(new.tools, '[]'),
        new.session_id,
        new.user_id
    );
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.rowid;
    INSERT INTO messages_fts(rowid, content, tools, session_id, user_id)
    VALUES (
        new.rowid,
        COALESCE(new.content, ''),
        COALESCE(new.tools, '[]'),
        new.session_id,
        new.user_id
    );
END;
"""

# Write-contention tuning (from NousResearch pattern)
_WRITE_MAX_RETRIES  = 10
_WRITE_RETRY_MIN_S  = 0.020   # 20ms
_WRITE_RETRY_MAX_S  = 0.120   # 120ms

_singleton_lock: threading.Lock = threading.Lock()


class HermesDB:
    """
    Thread-safe SQLite store for Hermes.

    Design principles (derived from NousResearch SessionDB study):
    - WAL mode: concurrent readers never block each other. Writers are
      serialised via BEGIN IMMEDIATE + jitter retry to avoid convoy effects.
    - Thread-local connections: SQLite connections are NOT thread-safe for
      parallel writes, so each thread gets its own handle via threading.local().
    - All writes go through _execute_write() which handles BEGIN IMMEDIATE,
      commit, rollback, and retry automatically.
    - get_db() returns a global singleton so the same schema is reused
      across the entire FastAPI process.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._write_count = 0
        self._init_schema()

    # ── Connection management ─────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        """Thread-local connection. Creates one if this thread has none."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=1.0,          # Short — we handle retries ourselves
                isolation_level=None, # We manage transactions explicitly
            )
            conn.row_factory = sqlite3.Row
            # WAL mode: allow concurrent reads during writes.
            # Falls back to DELETE journal if WAL not supported (network FS).
            try:
                conn.execute("PRAGMA journal_mode=WAL")
            except sqlite3.OperationalError:
                conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA synchronous=NORMAL")   # safe with WAL
            self._local.conn = conn
        return self._local.conn

    def _execute_write(self, fn) -> object:
        """
        Execute fn(conn) inside BEGIN IMMEDIATE with jitter retry.
        BEGIN IMMEDIATE acquires the WAL write lock at transaction start,
        surfacing contention immediately so we can retry with random jitter
        instead of sitting in SQLite's internal busy handler.
        """
        last_err = None
        for attempt in range(_WRITE_MAX_RETRIES):
            conn = self._conn()
            try:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    result = fn(conn)
                    conn.commit()
                except BaseException:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    raise
                # Periodic WAL checkpoint — keep WAL file from growing
                self._write_count += 1
                if self._write_count % 50 == 0:
                    self._try_checkpoint()
                return result
            except sqlite3.OperationalError as exc:
                msg = str(exc).lower()
                if "locked" in msg or "busy" in msg:
                    last_err = exc
                    if attempt < _WRITE_MAX_RETRIES - 1:
                        time.sleep(random.uniform(_WRITE_RETRY_MIN_S, _WRITE_RETRY_MAX_S))
                    continue
                raise
        raise last_err or sqlite3.OperationalError("database is locked after max retries")

    def _try_checkpoint(self):
        """Best-effort passive WAL checkpoint. Never raises."""
        try:
            self._conn().execute("PRAGMA wal_checkpoint(PASSIVE)")
        except Exception:
            pass

    def _init_schema(self):
        """Create all tables on first run. Safe to call multiple times."""
        conn = self._conn()
        conn.executescript(SCHEMA_SQL)

        # FTS5 virtual table + triggers — separate from executescript
        # because CREATE VIRTUAL TABLE IF NOT EXISTS behaves differently
        # in executescript vs individual execute() calls on older SQLite.
        try:
            conn.execute("SELECT * FROM messages_fts LIMIT 0")
        except sqlite3.OperationalError:
            # Table doesn't exist yet — create it
            conn.executescript(FTS_SQL)

        # Schema version bookkeeping
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO schema_version VALUES (?, ?)",
                (SCHEMA_VERSION, datetime.utcnow().isoformat())
            )
            conn.commit()

    # ── Sessions ──────────────────────────────────────────────────────

    def create_session(self, user_id: str = "user_1") -> dict:
        now = datetime.utcnow().isoformat()
        sid = f"sess_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        def _do(conn):
            conn.execute(
                """INSERT INTO sessions
                   (id, user_id, title, summary, tools_used, pinned,
                    created_at, updated_at, message_count)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (sid, user_id, "New Mission", "", "[]", 0, now, now, 0)
            )
        self._execute_write(_do)
        return self.get_session(sid) or {}

    def get_session(self, session_id: str) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT * FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        if not row:
            return None
        return self._session_to_dict(row)

    def list_sessions(self, user_id: str = "user_1", search: str = "") -> list:
        if search:
            # FTS across messages content
            try:
                rows = self._conn().execute("""
                    SELECT DISTINCT s.* FROM sessions s
                    JOIN messages m ON m.session_id = s.id
                    JOIN messages_fts f ON f.rowid = m.rowid
                    WHERE s.user_id = ? AND messages_fts MATCH ?
                    ORDER BY s.pinned DESC, s.updated_at DESC
                    LIMIT 100
                """, (user_id, search)).fetchall()
            except sqlite3.OperationalError:
                rows = []
            if not rows:
                # Fallback: title/summary LIKE search
                rows = self._conn().execute("""
                    SELECT * FROM sessions
                    WHERE user_id=? AND (title LIKE ? OR summary LIKE ?)
                    ORDER BY pinned DESC, updated_at DESC LIMIT 100
                """, (user_id, f"%{search}%", f"%{search}%")).fetchall()
        else:
            rows = self._conn().execute("""
                SELECT * FROM sessions WHERE user_id=?
                ORDER BY pinned DESC, updated_at DESC LIMIT 200
            """, (user_id,)).fetchall()

        # Return lightweight index rows (no message bodies) for perf
        result = []
        for r in rows:
            d = dict(r)
            d["tools_used"] = json.loads(d.get("tools_used", "[]"))
            result.append(d)
        return result

    def update_session(self, session_id: str, **kwargs):
        """Update arbitrary session fields. Allowed: title, summary, tools_used, pinned."""
        _ALLOWED = {"title", "summary", "tools_used", "pinned"}
        updates = {k: v for k, v in kwargs.items() if k in _ALLOWED}
        if not updates:
            return
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k}=?" for k in updates)

        def _do(conn):
            conn.execute(
                f"UPDATE sessions SET {set_clause} WHERE id=?",
                (*updates.values(), session_id)
            )
        self._execute_write(_do)

    def delete_session(self, session_id: str):
        def _do(conn):
            conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        self._execute_write(_do)

    def pin_session(self, session_id: str, pinned: bool):
        self.update_session(session_id, pinned=1 if pinned else 0)

    # ── Messages ──────────────────────────────────────────────────────

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tools: list = None,
        user_id: str = "user_1",
        is_summary: bool = False,
    ) -> dict:
        now        = datetime.utcnow().isoformat()
        mid        = uuid.uuid4().hex
        tools_json = json.dumps(tools or [])

        def _do(conn):
            conn.execute(
                """INSERT INTO messages
                   (id, session_id, user_id, role, content, tools, ts, is_summary)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (mid, session_id, user_id, role, content, tools_json, now,
                 1 if is_summary else 0)
            )
            # Update session counters atomically with the message insert
            conn.execute(
                "UPDATE sessions SET message_count=message_count+1, updated_at=? WHERE id=?",
                (now, session_id)
            )
        self._execute_write(_do)

        # Update tools_used list on session (outside transaction — non-critical)
        if tools:
            self._update_tools_used(session_id, tools)

        return {
            "id": mid, "role": role, "content": content,
            "text": content,        # alias for backward compat with conv_store shape
            "tools": tools or [], "ts": now
        }

    def get_messages(self, session_id: str) -> list:
        rows = self._conn().execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY ts ASC",
            (session_id,)
        ).fetchall()
        return [self._msg_to_dict(r) for r in rows]

    def search_messages(
        self,
        query: str,
        user_id: str = "user_1",
        limit: int = 10,
    ) -> list:
        """FTS5 full-text search across all messages for this user."""
        try:
            rows = self._conn().execute("""
                SELECT m.id, m.session_id, m.role, m.content, m.ts,
                       s.title as session_title, s.updated_at as session_date
                FROM messages m
                JOIN messages_fts f ON f.rowid = m.rowid
                JOIN sessions s ON s.id = m.session_id
                WHERE messages_fts MATCH ? AND m.user_id = ?
                ORDER BY rank LIMIT ?
            """, (query, user_id, limit)).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.OperationalError:
            # FTS not available — plain LIKE fallback
            rows = self._conn().execute("""
                SELECT m.id, m.session_id, m.role, m.content, m.ts,
                       s.title as session_title, s.updated_at as session_date
                FROM messages m
                JOIN sessions s ON s.id = m.session_id
                WHERE m.user_id=? AND m.content LIKE ?
                ORDER BY m.ts DESC LIMIT ?
            """, (user_id, f"%{query}%", limit)).fetchall()
            return [dict(r) for r in rows]

    # ── Memory Entries ────────────────────────────────────────────────

    def add_memory(
        self,
        content: str,
        user_id: str = "user_1",
        category: str = "general",
    ) -> dict:
        now = datetime.utcnow().isoformat()
        mid = uuid.uuid4().hex[:8]

        # Dedup check — don't store the exact same fact twice
        existing = self._conn().execute(
            "SELECT id FROM memory_entries WHERE user_id=? AND content=?",
            (user_id, content)
        ).fetchone()
        if existing:
            return {"id": existing["id"], "duplicate": True, "content": content}

        def _do(conn):
            conn.execute(
                """INSERT INTO memory_entries
                   (id, user_id, content, category, created_at, updated_at)
                   VALUES (?,?,?,?,?,?)""",
                (mid, user_id, content, category, now, now)
            )
        self._execute_write(_do)
        return {"id": mid, "content": content, "category": category, "ts": now}

    def get_memory(self, user_id: str = "user_1") -> list:
        rows = self._conn().execute(
            "SELECT * FROM memory_entries WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_memory(self, entry_id: str):
        def _do(conn):
            conn.execute("DELETE FROM memory_entries WHERE id=?", (entry_id,))
        self._execute_write(_do)

    # ── Skills ────────────────────────────────────────────────────────

    def save_skill(
        self,
        name: str,
        description: str,
        steps: list,
        trigger_phrases: list = None,
    ) -> dict:
        now   = datetime.utcnow().isoformat()
        sid   = uuid.uuid4().hex[:8]
        steps_json    = json.dumps(steps or [])
        triggers_json = json.dumps(trigger_phrases or [])

        def _do(conn):
            existing = conn.execute(
                "SELECT id FROM skills WHERE name=?", (name,)
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE skills SET description=?, steps_json=?,
                       trigger_phrases=?, updated_at=? WHERE name=?""",
                    (description, steps_json, triggers_json, now, name)
                )
            else:
                conn.execute(
                    """INSERT INTO skills
                       (id, name, description, trigger_phrases, steps_json,
                        use_count, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (sid, name, description, triggers_json, steps_json, 0, now, now)
                )
        self._execute_write(_do)
        return self.get_skill(name) or {}

    def get_skill(self, name: str) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT * FROM skills WHERE name=?", (name,)
        ).fetchone()
        if not row:
            return None
        return self._skill_to_dict(dict(row))

    def list_skills(self) -> list:
        rows = self._conn().execute(
            "SELECT * FROM skills ORDER BY use_count DESC"
        ).fetchall()
        return [self._skill_to_dict(dict(r)) for r in rows]

    def increment_skill_use(self, name: str):
        def _do(conn):
            conn.execute(
                "UPDATE skills SET use_count=use_count+1, last_used=? WHERE name=?",
                (datetime.utcnow().isoformat(), name)
            )
        self._execute_write(_do)

    def delete_skill(self, name: str):
        def _do(conn):
            conn.execute("DELETE FROM skills WHERE name=?", (name,))
        self._execute_write(_do)

    # ── User Profile ──────────────────────────────────────────────────

    def get_profile(self, user_id: str = "user_1") -> dict:
        row = self._conn().execute(
            "SELECT * FROM user_profile WHERE user_id=?", (user_id,)
        ).fetchone()
        if not row:
            return {"user_id": user_id, "profile_md": "", "soul_md": "", "updated_at": ""}
        return dict(row)

    def update_profile(
        self,
        user_id: str = "user_1",
        profile_md: str = None,
        soul_md: str = None,
    ):
        now     = datetime.utcnow().isoformat()
        current = self.get_profile(user_id)
        new_profile = profile_md if profile_md is not None else current["profile_md"]
        new_soul    = soul_md    if soul_md    is not None else current["soul_md"]

        def _do(conn):
            conn.execute(
                """INSERT INTO user_profile (user_id, profile_md, soul_md, updated_at)
                   VALUES (?,?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET
                     profile_md=excluded.profile_md,
                     soul_md=excluded.soul_md,
                     updated_at=excluded.updated_at""",
                (user_id, new_profile, new_soul, now)
            )
        self._execute_write(_do)

    # ── Internal helpers ──────────────────────────────────────────────

    def _update_tools_used(self, session_id: str, new_tools: list):
        """Merge new tool names into the session's tools_used JSON array."""
        if not new_tools:
            return
        row = self._conn().execute(
            "SELECT tools_used FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        if not row:
            return
        existing = set(json.loads(row["tools_used"] or "[]"))
        existing.update(t for t in new_tools if t)

        def _do(conn):
            conn.execute(
                "UPDATE sessions SET tools_used=? WHERE id=?",
                (json.dumps(sorted(existing)), session_id)
            )
        self._execute_write(_do)

    def _session_to_dict(self, row) -> dict:
        d = dict(row)
        d["tools_used"] = json.loads(d.get("tools_used", "[]"))
        # NOTE: messages are NOT included here for list performance.
        # Call get_messages(id) separately when full history is needed.
        return d

    def _msg_to_dict(self, row) -> dict:
        d = dict(row)
        d["tools"] = json.loads(d.get("tools", "[]"))
        # Both "text" and "content" are the same — support both call-sites
        d["text"] = d.get("content", "")
        return d

    def _skill_to_dict(self, d: dict) -> dict:
        d["steps"]           = json.loads(d.get("steps_json", "[]"))
        d["trigger_phrases"] = json.loads(d.get("trigger_phrases", "[]"))
        return d


# ── Module-level singleton ────────────────────────────────────────────────────

_db: Optional["HermesDB"] = None


def get_db() -> "HermesDB":
    """Return the global HermesDB singleton (thread-safe, lazy init)."""
    global _db
    if _db is None:
        with _singleton_lock:
            if _db is None:
                _db = HermesDB()
                print(f"[HERMES DB] SQLite initialized at {DB_PATH}")
    return _db
