# core/filesystem/adapter_local.py

from pathlib import Path

class LocalFilesystemAdapter:
    def list(self, path: Path):
        if not path.exists():
            return []

        if not path.is_dir():
            raise ValueError("Not a directory")

        return [p.name for p in path.iterdir()]

    def read(self, path: Path):
        if not path.exists():
            raise ValueError("File not found")

        if not path.is_file():
            raise ValueError("Not a file")

        return path.read_text(encoding="utf-8", errors="ignore")
