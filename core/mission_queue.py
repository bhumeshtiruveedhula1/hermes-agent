# core/mission_queue.py — Phase 15: Persistent Mission Queue
# File-backed JSON queue — survives server restarts.
# Per-user queues supported via user_id filter.

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

QUEUE_FILE = Path("memory/mission_queue.json")


class MissionQueue:
    """
    Thread-safe (single-process) file-backed mission queue.

    Statuses:  queued → running → done | failed
    Priority:  higher int = higher priority (default 0)
    """

    def __init__(self):
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not QUEUE_FILE.exists():
            QUEUE_FILE.write_text("[]")

    # ── Write ops ────────────────────────────────────────────────────────

    def enqueue(
        self,
        prompt: str,
        user_id: str,
        conv_id: str,
        priority: int = 0,
    ) -> dict:
        mission = {
            "id":         str(uuid.uuid4())[:8],
            "prompt":     prompt,
            "user_id":    user_id,
            "conv_id":    conv_id,
            "priority":   priority,
            "status":     "queued",
            "created_at": _now(),
            "started_at": None,
            "done_at":    None,
            "result":     None,
        }
        queue = self._load()
        queue.append(mission)
        self._save(queue)
        return mission

    def set_status(self, mission_id: str, status: str, result: str = None):
        queue = self._load()
        for m in queue:
            if m["id"] == mission_id:
                m["status"] = status
                if status == "running":
                    m["started_at"] = _now()
                if status in ("done", "failed"):
                    m["done_at"] = _now()
                if result is not None:
                    m["result"] = result[:500]
                break
        self._save(queue)

    def delete(self, mission_id: str):
        queue = self._load()
        queue = [m for m in queue if m["id"] != mission_id]
        self._save(queue)

    def clear_done(self):
        """Remove all done/failed missions."""
        queue = self._load()
        queue = [m for m in queue if m["status"] not in ("done", "failed")]
        self._save(queue)

    # ── Read ops ─────────────────────────────────────────────────────────

    def get_next(self) -> Optional[dict]:
        """Return highest-priority queued mission, or None."""
        queue  = self._load()
        queued = [m for m in queue if m["status"] == "queued"]
        if not queued:
            return None
        queued.sort(key=lambda x: (-x["priority"], x["created_at"]))
        return queued[0]

    def list_all(self, user_id: str = None) -> list:
        queue = self._load()
        if user_id:
            queue = [m for m in queue if m["user_id"] == user_id]
        return sorted(queue, key=lambda x: x["created_at"], reverse=True)

    def get(self, mission_id: str) -> Optional[dict]:
        for m in self._load():
            if m["id"] == mission_id:
                return m
        return None

    # ── Private ──────────────────────────────────────────────────────────

    def _load(self) -> list:
        try:
            return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save(self, queue: list):
        QUEUE_FILE.write_text(
            json.dumps(queue, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
