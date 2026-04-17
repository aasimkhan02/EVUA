import shutil
from pathlib import Path

class RollbackManager:
    def __init__(self, backup_root="out/.backup"):
        self.backup_root = Path(backup_root).resolve()
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.snapshots = {}  # original_path -> backup_path

    def _is_in_backup_dir(self, path: Path) -> bool:
        try:
            path = path.resolve()
            return self.backup_root in path.parents
        except Exception:
            return False

    def _safe_relpath(self, path: Path):
        """
        Returns a safe relative path for backup storage.
        """
        path = Path(path).resolve()
        try:
            return path.relative_to(Path.cwd().resolve())
        except Exception:
            parts = [p.replace(":", "") for p in path.parts if p not in ("/", "\\")]
            return Path("external") / Path(*parts[-4:])

    def snapshot(self, path: Path):
        path = Path(path)
        if not path.exists():
            return

        # Do not snapshot backup directory contents (prevents infinite nesting)
        if self._is_in_backup_dir(path):
            return

        rel = self._safe_relpath(path)
        backup_path = self.backup_root / rel

        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_path)

        self.snapshots[str(path.resolve())] = str(backup_path.resolve())

    def rollback(self):
        for orig, backup in self.snapshots.items():
            orig_path = Path(orig)
            backup_path = Path(backup)

            orig_path.parent.mkdir(parents=True, exist_ok=True)
            if backup_path.exists():
                shutil.copy2(backup_path, orig_path)

    def clear(self):
        if self.backup_root.exists():
            shutil.rmtree(self.backup_root, ignore_errors=True)
        self.snapshots.clear()
