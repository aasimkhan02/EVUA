import json
from pathlib import Path

class SnapshotComparator:
    """
    Compares before/after snapshots of component state.
    Expects JSON like:
    {
      "UserComponent": { "users": [...], "query": "" },
      "AdminComponent": { "isAdmin": true }
    }
    """

    def compare(self, before_path: str, after_path: str):
        try:
            before = json.loads(Path(before_path).read_text(encoding="utf-8"))
            after = json.loads(Path(after_path).read_text(encoding="utf-8"))

            failures = []

            for component, before_state in before.items():
                after_state = after.get(component)
                if after_state is None:
                    failures.append(f"Missing component snapshot after migration: {component}")
                    continue

                if before_state != after_state:
                    failures.append(f"State mismatch in {component}")

            passed = len(failures) == 0
            return passed, failures

        except Exception as e:
            return False, [f"Snapshot comparison failed: {e}"]
