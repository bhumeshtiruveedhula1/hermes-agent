# core/memory.py

import json
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_DIR = BASE_DIR / "memory"
SESSION_FILE = MEMORY_DIR / "session.json"
PREFS_FILE = MEMORY_DIR / "preferences.json"
DB_FILE = MEMORY_DIR / "hermes.db"

MAX_SESSION_MESSAGES = 20


class MemoryManager:
    def __init__(self):
        MEMORY_DIR.mkdir(exist_ok=True)
        self._init_files()
        self._init_db()

    # ---------- Initialization ----------
    def _init_files(self):
        if not SESSION_FILE.exists():
            SESSION_FILE.write_text("[]", encoding="utf-8")

        if not PREFS_FILE.exists():
            PREFS_FILE.write_text(json.dumps({
                "writing_style": "structured, concise",
                "coding_style": "clean, minimal",
                "verbosity": "medium"
            }, indent=2), encoding="utf-8")

    def _init_db(self):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    content TEXT,
                    timestamp TEXT
                )
            """)
            conn.commit()

    # ---------- Session Memory ----------
    def load_session(self):
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))

    def add_session_message(self, role: str, content: str):
        session = self.load_session()
        session.append({"role": role, "content": content})
        session = session[-MAX_SESSION_MESSAGES:]
        SESSION_FILE.write_text(json.dumps(session, indent=2), encoding="utf-8")

    def clear_session(self):
        SESSION_FILE.write_text("[]", encoding="utf-8")

    # ---------- Preferences ----------
    def load_preferences(self):
        try:
            content = PREFS_FILE.read_text(encoding="utf-8").strip()
            if not content:
                raise ValueError("Empty preferences file")
            return json.loads(content)
        except Exception:
            default_prefs = {
            "writing_style": "structured, concise",
            "coding_style": "clean, minimal",
            "verbosity": "medium"
            }
            PREFS_FILE.write_text(
                json.dumps(default_prefs, indent=2),
                encoding="utf-8"
                )
            return default_prefs


    def update_preference(self, key: str, value: str):
        prefs = self.load_preferences()
        prefs[key] = value
        PREFS_FILE.write_text(json.dumps(prefs, indent=2), encoding="utf-8")

    # ---------- Long-Term Memory ----------
    def store_long_term(self, memory_type: str, content: str):
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "INSERT INTO memories (type, content, timestamp) VALUES (?, ?, ?)",
                (memory_type, content, datetime.utcnow().isoformat())
            )
            conn.commit()

    def fetch_recent_memories(self, memory_type: str = None, limit: int = 5):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            if memory_type:
                cursor.execute(
                    "SELECT content FROM memories WHERE type=? ORDER BY id DESC LIMIT ?",
                    (memory_type, limit)
                )
            else:
                cursor.execute(
                    "SELECT content FROM memories ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
            return [row[0] for row in cursor.fetchall()]
