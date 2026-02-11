from pathlib import Path
from typing import List

class FileScanner:
    IGNORE_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__"}

    def scan(self, root: str) -> List[Path]:
        root_path = Path(root)

        files: List[Path] = []
        for p in root_path.rglob("*"):
            if not p.is_file():
                continue

            # skip ignored directories
            if any(part in self.IGNORE_DIRS for part in p.parts):
                continue

            files.append(p)

        return files
