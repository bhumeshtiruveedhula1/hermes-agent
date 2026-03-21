# core/conversation_store.py
# Persistent conversation/mission storage

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional

CONV_DIR = Path("memory/conversations")
INDEX_FILE = CONV_DIR / "index.json"


class ConversationStore:
    def __init__(self):
        CONV_DIR.mkdir(parents=True, exist_ok=True)
        if not INDEX_FILE.exists():
            INDEX_FILE.write_text(json.dumps([]))

    def create(self) -> dict:
        conv_id = f"conv_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        conv = {
            "id": conv_id,
            "title": "New Mission",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "messages": [],
            "tools_used": [],
            "summary": "",
            "pinned": False,
        }
        self._save_conv(conv)
        self._update_index(conv)
        return conv

    def get(self, conv_id: str) -> Optional[dict]:
        conv_file = CONV_DIR / f"{conv_id}.json"
        if not conv_file.exists():
            return None
        return json.loads(conv_file.read_text())

    def add_message(self, conv_id: str, role: str, text: str, tools: list = None) -> dict:
        conv = self.get(conv_id)
        if not conv:
            return {}

        conv["messages"].append({
            "role": role,
            "text": text,
            "ts": datetime.utcnow().isoformat(),
            "tools": tools or []
        })

        # Track unique tools used
        for t in (tools or []):
            if t and t not in conv["tools_used"]:
                conv["tools_used"].append(t)

        conv["updated_at"] = datetime.utcnow().isoformat()
        self._save_conv(conv)
        self._update_index(conv)
        return conv

    def update_title(self, conv_id: str, title: str):
        conv = self.get(conv_id)
        if conv:
            conv["title"] = title
            conv["updated_at"] = datetime.utcnow().isoformat()
            self._save_conv(conv)
            self._update_index(conv)

    def update_summary(self, conv_id: str, summary: str):
        conv = self.get(conv_id)
        if conv:
            conv["summary"] = summary
            self._save_conv(conv)
            self._update_index(conv)

    def pin(self, conv_id: str, pinned: bool):
        conv = self.get(conv_id)
        if conv:
            conv["pinned"] = pinned
            self._save_conv(conv)
            self._update_index(conv)

    def delete(self, conv_id: str):
        conv_file = CONV_DIR / f"{conv_id}.json"
        if conv_file.exists():
            conv_file.unlink()
        index = self._load_index()
        index = [c for c in index if c["id"] != conv_id]
        INDEX_FILE.write_text(json.dumps(index, indent=2))

    def list_all(self, search: str = "") -> list:
        index = self._load_index()
        # Sort: pinned first, then by updated_at desc
        index.sort(key=lambda x: (not x.get("pinned", False), x.get("updated_at", "")), reverse=True)
        if search:
            search_lower = search.lower()
            index = [
                c for c in index
                if search_lower in c.get("title", "").lower()
                or search_lower in c.get("summary", "").lower()
                or any(search_lower in t for t in c.get("tools_used", []))
            ]
        return index

    def _save_conv(self, conv: dict):
        conv_file = CONV_DIR / f"{conv['id']}.json"
        conv_file.write_text(json.dumps(conv, indent=2))

    def _load_index(self) -> list:
        if not INDEX_FILE.exists():
            return []
        return json.loads(INDEX_FILE.read_text())

    def _update_index(self, conv: dict):
        index = self._load_index()
        entry = {
            "id": conv["id"],
            "title": conv["title"],
            "summary": conv["summary"],
            "tools_used": conv["tools_used"],
            "pinned": conv["pinned"],
            "created_at": conv["created_at"],
            "updated_at": conv["updated_at"],
            "message_count": len(conv["messages"]),
        }
        index = [c for c in index if c["id"] != conv["id"]]
        index.append(entry)
        INDEX_FILE.write_text(json.dumps(index, indent=2))