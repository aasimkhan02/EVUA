from pathlib import Path
from typing import List


class FileScanner:
    IGNORE_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__"}

    def scan(self, root: str) -> List[Path]:
        root_path = Path(root)

        # ✅ Fail fast on invalid root
        if not root_path.exists():
            raise FileNotFoundError(f"Ingestion root does not exist: {root_path}")

        if not root_path.is_dir():
            raise NotADirectoryError(f"Ingestion root is not a directory: {root_path}")

        files: List[Path] = []

        for p in root_path.rglob("*"):
            if not p.is_file():
                continue

            # skip ignored directories
            if any(part in self.IGNORE_DIRS for part in p.parts):
                continue

            files.append(p)

        return files
