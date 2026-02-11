import json
from pathlib import Path
from datetime import datetime

class ProgressTracker:
    def __init__(self, log_path="out/progress.json"):
        self.log_path = Path(log_path)
        self.entries = []

    def record(self, path: str, action: str, info: str = ""):
        self.entries.append({
            "path": str(path),
            "action": action,  # created | updated | unchanged | rolled_back | skipped
            "info": info,
            "timestamp": datetime.utcnow().isoformat()
        })

    def save(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2)
