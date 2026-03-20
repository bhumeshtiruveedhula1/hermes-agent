# core/filesystem/change_detector.py

from pathlib import Path
from datetime import datetime


class FolderChangeDetector:
    """
    Detects new files in a sandbox folder since last check.
    Stateless — caller passes in last_seen set.
    """

    @staticmethod
    def detect(physical_path: Path, known_files: set) -> dict:
        try:
            current_files = set(f.name for f in physical_path.iterdir() if f.is_file())
        except Exception as e:
            return {"error": str(e), "new_files": [], "all_files": []}

        new_files = sorted(current_files - known_files)

        return {
            "all_files": sorted(current_files),
            "new_files": new_files,
            "checked_at": datetime.utcnow().isoformat()
        }