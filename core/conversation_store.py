# core/conversation_store.py
# Persistent conversation/mission storage — Phase 11: per-user namespacing

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Base directory — user namespaced paths live under this
CONV_BASE = Path("memory/conversations")

# ── Legacy flat path (user_1 backward compat) ────────────────────────
# Old installs stored everything in memory/conversations/ flat.
# New installs use memory/conversations/{user_id}/.
# We keep reading the old flat index for user_1 migration.

def _conv_dir(user_id: str = "user_1") -> Path:
    """Return the per-user conversation directory."""
    return CONV_BASE / user_id

def _index_file(user_id: str = "user_1") -> Path:
    return _conv_dir(user_id) / "index.json"


class ConversationStore:
    def __init__(self):
        # Ensure base dir exists
        CONV_BASE.mkdir(parents=True, exist_ok=True)
        # Migrate existing flat conversations to user_1 namespace
        self._migrate_legacy()

    def _migrate_legacy(self):
        """
        One-time migration: move flat memory/conversations/*.json files
        into memory/conversations/user_1/.
        Safe to call multiple times — skips if already migrated.
        """
        legacy_index = CONV_BASE / "index.json"
        target_dir   = _conv_dir("user_1")
        if not legacy_index.exists():
            return  # nothing to migrate

        target_dir.mkdir(parents=True, exist_ok=True)
        target_index = _index_file("user_1")
        if target_index.exists():
            return  # already migrated

        # Copy index
        target_index.write_text(legacy_index.read_text())

        # Copy individual conversation files
        for f in CONV_BASE.glob("conv_*.json"):
            dest = target_dir / f.name
            if not dest.exists():
                dest.write_text(f.read_text())

    def _ensure_user_dir(self, user_id: str):
        d = _conv_dir(user_id)
        d.mkdir(parents=True, exist_ok=True)
        idx = _index_file(user_id)
        if not idx.exists():
            idx.write_text(json.dumps([]))

    # ── Public API (all methods accept user_id, default "user_1") ────────

    def create(self, user_id: str = "user_1") -> dict:
        self._ensure_user_dir(user_id)
        conv_id = f"conv_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        conv = {
            "id":         conv_id,
            "title":      "New Mission",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "messages":   [],
            "tools_used": [],
            "summary":    "",
            "pinned":     False,
            "user_id":    user_id,
        }
        self._save_conv(conv, user_id)
        self._update_index(conv, user_id)
        return conv

    def get(self, conv_id: str, user_id: str = "user_1") -> Optional[dict]:
        conv_file = _conv_dir(user_id) / f"{conv_id}.json"
        if not conv_file.exists():
            return None
        return json.loads(conv_file.read_text())

    def add_message(self, conv_id: str, role: str, text: str,
                    tools: list = None, user_id: str = "user_1") -> dict:
        conv = self.get(conv_id, user_id)
        if not conv:
            return {}

        conv["messages"].append({
            "role": role, "text": text,
            "ts": datetime.utcnow().isoformat(),
            "tools": tools or []
        })
        for t in (tools or []):
            if t and t not in conv["tools_used"]:
                conv["tools_used"].append(t)

        conv["updated_at"] = datetime.utcnow().isoformat()
        self._save_conv(conv, user_id)
        self._update_index(conv, user_id)
        return conv

    def update_title(self, conv_id: str, title: str, user_id: str = "user_1"):
        conv = self.get(conv_id, user_id)
        if conv:
            conv["title"]      = title
            conv["updated_at"] = datetime.utcnow().isoformat()
            self._save_conv(conv, user_id)
            self._update_index(conv, user_id)

    def update_summary(self, conv_id: str, summary: str, user_id: str = "user_1"):
        conv = self.get(conv_id, user_id)
        if conv:
            conv["summary"] = summary
            self._save_conv(conv, user_id)
            self._update_index(conv, user_id)

    def pin(self, conv_id: str, pinned: bool, user_id: str = "user_1"):
        conv = self.get(conv_id, user_id)
        if conv:
            conv["pinned"] = pinned
            self._save_conv(conv, user_id)
            self._update_index(conv, user_id)

    def delete(self, conv_id: str, user_id: str = "user_1"):
        conv_file = _conv_dir(user_id) / f"{conv_id}.json"
        if conv_file.exists():
            conv_file.unlink()
        index = [c for c in self._load_index(user_id) if c["id"] != conv_id]
        _index_file(user_id).write_text(json.dumps(index, indent=2))

    def list_all(self, search: str = "", user_id: str = "user_1") -> list:
        self._ensure_user_dir(user_id)
        index = self._load_index(user_id)
        index.sort(key=lambda x: (not x.get("pinned", False), x.get("updated_at", "")), reverse=True)
        if search:
            s = search.lower()
            index = [
                c for c in index
                if s in c.get("title", "").lower()
                or s in c.get("summary", "").lower()
                or any(s in t for t in c.get("tools_used", []))
            ]
        return index

    # ── Private ──────────────────────────────────────────────────────────

    def _save_conv(self, conv: dict, user_id: str = "user_1"):
        (_conv_dir(user_id) / f"{conv['id']}.json").write_text(json.dumps(conv, indent=2))

    def _load_index(self, user_id: str = "user_1") -> list:
        f = _index_file(user_id)
        return json.loads(f.read_text()) if f.exists() else []

    def _update_index(self, conv: dict, user_id: str = "user_1"):
        index = [c for c in self._load_index(user_id) if c["id"] != conv["id"]]
        index.append({
            "id":            conv["id"],
            "title":         conv["title"],
            "summary":       conv["summary"],
            "tools_used":    conv["tools_used"],
            "pinned":        conv["pinned"],
            "created_at":    conv["created_at"],
            "updated_at":    conv["updated_at"],
            "message_count": len(conv["messages"]),
        })
        _index_file(user_id).write_text(json.dumps(index, indent=2))