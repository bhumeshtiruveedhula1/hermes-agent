# core/db_migration.py — Phase 17: JSON → SQLite Migration
# One-time, idempotent migration that reads all existing JSON conversation
# files from memory/conversations/{user_id}/ and imports them into hermes.db.
#
# Design decisions:
#   - IDEMPOTENT: safe to run multiple times; already-migrated sessions are
#     detected via get_session() and skipped.
#   - NON-DESTRUCTIVE: original JSON files are NOT deleted. conv_store.py
#     continues to write to JSON during the transition period (Phase 17
#     uses dual-write: both stores receive messages).
#   - REPORTS: prints a clear summary so the user knows what happened.
#
# Run manually or call migrate_json_to_sqlite() from application startup.
# After Phase 17 is fully stable, conv_store.py writes can be deprecated.

import json
from pathlib import Path
from datetime import datetime


def migrate_json_to_sqlite():
    """
    Import all JSON conversation files into hermes.db.

    Scans memory/conversations/{user_id}/conv_*.json and inserts sessions
    + messages. Sessions that already exist in SQLite are skipped.

    Returns:
        dict with keys: migrated, skipped, errors
    """
    from core.hermes_db import get_db
    db = get_db()

    conv_root = Path("memory/conversations")
    if not conv_root.exists():
        print("[MIGRATION] No JSON conversations directory found — nothing to migrate")
        return {"migrated": 0, "skipped": 0, "errors": 0}

    migrated = 0
    skipped  = 0
    errors   = 0

    for user_dir in sorted(conv_root.iterdir()):
        if not user_dir.is_dir():
            continue
        user_id = user_dir.name

        conv_files = sorted(user_dir.glob("conv_*.json"))
        if not conv_files:
            continue

        print(f"[MIGRATION] Processing {len(conv_files)} conversations for {user_id}")

        for conv_file in conv_files:
            try:
                data = json.loads(conv_file.read_text(encoding="utf-8"))
                conv_id = data.get("id") or conv_file.stem

                # ── Skip if already in SQLite ──────────────────────────
                if db.get_session(conv_id):
                    skipped += 1
                    continue

                # ── Insert session row directly (bypass create_session
                #    so we preserve original IDs and timestamps) ─────────
                conn = db._conn()
                conn.execute("""
                    INSERT OR IGNORE INTO sessions
                    (id, user_id, title, summary, tools_used, pinned,
                     created_at, updated_at, message_count)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    conv_id,
                    data.get("user_id", user_id),
                    data.get("title", "Imported Mission"),
                    data.get("summary", ""),
                    json.dumps(data.get("tools_used", [])),
                    1 if data.get("pinned") else 0,
                    data.get("created_at", datetime.utcnow().isoformat()),
                    data.get("updated_at", datetime.utcnow().isoformat()),
                    len(data.get("messages", [])),
                ))
                conn.commit()

                # ── Import messages ────────────────────────────────────
                for msg in data.get("messages", []):
                    content = msg.get("text", msg.get("content", ""))
                    if not content:
                        continue
                    db.add_message(
                        session_id=conv_id,
                        role=msg.get("role", "user"),
                        content=content,
                        tools=msg.get("tools", []),
                        user_id=data.get("user_id", user_id),
                    )

                migrated += 1

            except Exception as exc:
                errors += 1
                print(f"[MIGRATION] Error migrating {conv_file.name}: {exc}")

    print(
        f"[MIGRATION] Complete — "
        f"{migrated} migrated, {skipped} already existed, {errors} errors"
    )
    return {"migrated": migrated, "skipped": skipped, "errors": errors}


if __name__ == "__main__":
    migrate_json_to_sqlite()
