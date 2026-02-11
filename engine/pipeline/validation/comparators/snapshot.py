import json
from pathlib import Path

class SnapshotComparator:
    """
    Compares before/after snapshots of key outputs.
    For demo: compare JSON files produced by the app (e.g., ./snapshots/output.json)
    """

    def compare(self, before_path: str, after_path: str):
        try:
            before = json.loads(Path(before_path).read_text(encoding="utf-8"))
            after = json.loads(Path(after_path).read_text(encoding="utf-8"))

            if before == after:
                return True, []
            else:
                return False, ["Snapshot mismatch detected"]
        except Exception as e:
            return False, [f"Snapshot comparison failed: {e}"]
