# core/user_store.py
# Phase 11 — Multi-User System
# Persistent user store with SHA-256 password hashing.

import json
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

USER_DIR   = Path("memory/users")
INDEX_FILE = USER_DIR / "index.json"

_DEFAULT_ADMIN = {"name": "admin", "password": "hermes2026", "role": "admin"}


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class UserStore:
    def __init__(self):
        USER_DIR.mkdir(parents=True, exist_ok=True)
        if not INDEX_FILE.exists():
            INDEX_FILE.write_text(json.dumps([]))
        # Seed default admin on first run
        if not self.get_by_name(_DEFAULT_ADMIN["name"]):
            self.create(
                _DEFAULT_ADMIN["name"],
                _DEFAULT_ADMIN["password"],
                _DEFAULT_ADMIN["role"],
            )

    # ── Public API ───────────────────────────────────────────────────────

    def create(self, name: str, password: str, role: str = "user") -> dict:
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        user = {
            "id":            user_id,
            "name":          name,
            "password_hash": _hash(password),
            "created_at":    datetime.utcnow().isoformat(),
            "role":          role,
            "sandbox_path":  "/documents",
        }
        self._save(user)
        self._update_index(user)
        # Create sandbox directory for new user
        sandbox = Path("sandboxes") / user_id / "documents"
        sandbox.mkdir(parents=True, exist_ok=True)
        return user

    def get(self, user_id: str) -> Optional[dict]:
        f = USER_DIR / f"{user_id}.json"
        return json.loads(f.read_text()) if f.exists() else None

    def get_by_name(self, name: str) -> Optional[dict]:
        for entry in self._load_index():
            if entry.get("name") == name:
                return self.get(entry["id"])
        return None

    def verify(self, name: str, password: str) -> Optional[dict]:
        user = self.get_by_name(name)
        if user and user["password_hash"] == _hash(password):
            return user
        return None

    def list_all(self) -> list:
        """Return all users with no password hashes."""
        result = []
        for entry in self._load_index():
            user = self.get(entry["id"])
            if user:
                result.append({k: v for k, v in user.items() if k != "password_hash"})
        return result

    def delete(self, user_id: str) -> bool:
        """Delete a user (cannot delete admin)."""
        user = self.get(user_id)
        if not user or user["role"] == "admin":
            return False
        f = USER_DIR / f"{user_id}.json"
        if f.exists():
            f.unlink()
        index = [e for e in self._load_index() if e["id"] != user_id]
        INDEX_FILE.write_text(json.dumps(index, indent=2))
        return True

    # ── Private helpers ──────────────────────────────────────────────────

    def _save(self, user: dict):
        (USER_DIR / f"{user['id']}.json").write_text(json.dumps(user, indent=2))

    def _load_index(self) -> list:
        return json.loads(INDEX_FILE.read_text()) if INDEX_FILE.exists() else []

    def _update_index(self, user: dict):
        index = [e for e in self._load_index() if e["id"] != user["id"]]
        index.append({"id": user["id"], "name": user["name"], "role": user["role"]})
        INDEX_FILE.write_text(json.dumps(index, indent=2))
