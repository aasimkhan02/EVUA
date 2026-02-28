import hashlib
import shutil
import uuid
from pathlib import Path

from orchestration.progress_tracker import ProgressTracker


class PipelineRunner:
    def __init__(self, pipeline_fn, out_root="out"):
        """
        pipeline_fn: callable that runs the full pipeline and returns (validation_passed: bool)
                     MUST accept out_root kwarg: pipeline_fn(out_root=Path)
        """
        self.pipeline_fn = pipeline_fn
        self.out_root = Path(out_root)
        self.final_root = self.out_root / "angular-app"
        self.progress = ProgressTracker(self.out_root / "progress.json")

    def _hash(self, path: Path):
        if not path.exists():
            return None
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()

    def run(self):
        run_id = uuid.uuid4().hex[:8]
        tmp_root = self.out_root / f".tmp_{run_id}"
        tmp_root.mkdir(parents=True, exist_ok=True)

        # Snapshot final output state for progress diffing
        files_before = []
        before_hashes = {}
        if self.final_root.exists():
            files_before = sorted([p for p in self.final_root.rglob("*") if p.is_file()])
            before_hashes = {str(p): self._hash(p) for p in files_before}

        validation_passed = False
        try:
            validation_passed = self.pipeline_fn(out_root=tmp_root)
        except Exception as e:
            print("Pipeline crashed:", e)
            validation_passed = False

        if validation_passed:
            if self.final_root.exists():
                shutil.rmtree(self.final_root)
            shutil.move(str(tmp_root), str(self.final_root))
            print("Committed output atomically")
        else:
            shutil.rmtree(tmp_root, ignore_errors=True)
            print("Validation failed -> temp workspace discarded")

        # Progress tracking (only on final output)
        if self.final_root.exists():
            files_after = sorted([p for p in self.final_root.rglob("*") if p.is_file()])
        else:
            files_after = []

        for p in files_after:
            old_hash = before_hashes.get(str(p))
            new_hash = self._hash(p)

            if old_hash is None:
                self.progress.record(p, "created")
            elif old_hash == new_hash:
                self.progress.record(p, "unchanged")
            else:
                self.progress.record(p, "updated")

        removed = set(before_hashes.keys()) - set(str(p) for p in files_after)
        for p in removed:
            self.progress.record(p, "removed")

        self.progress.save()
        return validation_passed