import json
from pathlib import Path

def load_expected(benchmark_dir: Path):
    expected = json.loads((benchmark_dir / "expected.json").read_text(encoding="utf-8"))
    expected_risk = json.loads((benchmark_dir / "expected_risk.json").read_text(encoding="utf-8"))
    expected_changes = json.loads((benchmark_dir / "expected_changes.json").read_text(encoding="utf-8"))

    return {
        "surface": expected["supported_constructs"],
        "auto_modernized": expected["auto_modernized"],
        "manual_required": expected["manual_required"],
        "blocked": expected["blocked"],
        "notes": expected.get("notes", []),

        "expected_risk": expected_risk,              # SAFE/RISKY/MANUAL labels
        "expected_changes": expected_changes,        # files + thresholds
    }
