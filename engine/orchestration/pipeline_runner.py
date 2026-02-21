import hashlib
from pathlib import Path

from orchestration.progress_tracker import ProgressTracker
from orchestration.rollback_manager import RollbackManager


class PipelineRunner:
    def __init__(self, pipeline_fn, out_root="out"):
        """
        pipeline_fn: callable that runs the full pipeline and returns (validation_passed: bool)
        """
        self.pipeline_fn = pipeline_fn
        self.out_root = Path(out_root)
        self.progress = ProgressTracker(self.out_root / "progress.json")
        self.rollback = RollbackManager(self.out_root / ".backup")

    def _hash(self, path: Path):
        if not path.exists():
            return None
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()

    def run(self):
        # Determinism: stable, sorted traversal
        files_before = sorted([p for p in self.out_root.rglob("*") if p.is_file()])
        before_hashes = {str(p): self._hash(p) for p in files_before}

        # Snapshot files before run (for rollback)
        for p in files_before:
            self.rollback.snapshot(p)

        validation_passed = False
        try:
            validation_passed = self.pipeline_fn()
        except Exception as e:
            print("Pipeline crashed:", e)
            validation_passed = False

        # Determinism + idempotency: stable traversal, compare hashes
        files_after = sorted([p for p in self.out_root.rglob("*") if p.is_file()])

        for p in files_after:
            old_hash = before_hashes.get(str(p))
            new_hash = self._hash(p)

            if old_hash is None:
                self.progress.record(p, "created")
            elif old_hash == new_hash:
                self.progress.record(p, "unchanged")
            else:
                self.progress.record(p, "updated")

        # Record files that existed before but were removed
        removed = set(before_hashes.keys()) - set(str(p) for p in files_after)
        for p in removed:
            self.progress.record(p, "removed")

        # Safe rollback on failure
        if not validation_passed:
            print("Validation failed -> rolling back generated files")
            self.rollback.rollback()
            for p in files_after:
                self.progress.record(p, "rolled_back")
        else:
            self.rollback.clear()

        self.progress.save()
        return validation_passed
