import shutil
from pathlib import Path

class RollbackManager:
    def __init__(self, backup_root="out/.backup"):
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.snapshots = {}  # original_path -> backup_path

    def _safe_relpath(self, path: Path):
        """
        Returns a relative path safe for backup storage,
        even if path is already relative or outside cwd.
        """
        path = Path(path)
        try:
            return path.resolve().relative_to(Path.cwd().resolve())
        except Exception:
            # Fallback: flatten into backup dir using filename only
            return Path("external") / path.name

    def snapshot(self, path: Path):
        path = Path(path)
        if not path.exists():
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
            shutil.copy2(backup_path, orig_path)

    def clear(self):
        if self.backup_root.exists():
            shutil.rmtree(self.backup_root, ignore_errors=True)
        self.snapshots.clear()
