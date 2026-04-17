from pathlib import Path

def coverage_ratio(found, expected):
    if not expected:
        return 1.0
    # Convert paths to just filenames for comparison if needed
    found_normalized = [Path(f).name if isinstance(f, str) else f for f in found]
    expected_normalized = [Path(e).name if isinstance(e, str) else e for e in expected]
    
    # Debug output
    print(f"  [DEBUG] coverage_ratio - found: {found_normalized}")
    print(f"  [DEBUG] coverage_ratio - expected: {expected_normalized}")
    print(f"  [DEBUG] coverage_ratio - intersection: {set(found_normalized) & set(expected_normalized)}")
    
    return len(set(found_normalized) & set(expected_normalized)) / len(expected)


def precision_recall(found, expected):
    found = set(found)
    expected = set(expected)

    tp = len(found & expected)
    fp = len(found - expected)
    fn = len(expected - found)

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return precision, recall


def compute_metrics(actual, expected):
    """
    actual = {
      "risk": { "SAFE": [...], "RISKY": [...], "MANUAL": [...] },
      "generated_files": [...],
      "auto_modernized": [...],
      "manual_required": [...],
      "validation_passed": bool
    }
    expected = output of load_expected()
    """

    metrics = {}

    # Auto-modernization coverage
    metrics["auto_coverage"] = coverage_ratio(
        actual.get("auto_modernized", []),
        expected.get("auto_modernized", [])
    )

    # Manual detection recall
    metrics["manual_recall"] = coverage_ratio(
        actual.get("manual_required", []),
        expected.get("manual_required", [])
    )

    # Risk precision/recall
    metrics["risk"] = {}
    for level in ["SAFE", "RISKY", "MANUAL"]:
        p, r = precision_recall(
            actual["risk"].get(level, []),
            expected["expected_risk"].get(level, [])
        )
        metrics["risk"][level] = {"precision": p, "recall": r}

    # File generation accuracy - with better path handling
    generated_files = actual.get("generated_files", [])
    expected_files = expected["expected_changes"].get("generated_files", [])
    
    print(f"\n  [DEBUG] File accuracy check:")
    print(f"    generated_files: {generated_files}")
    print(f"    expected_files: {expected_files}")
    
    # Extract just filenames for comparison
    generated_filenames = [Path(f).name for f in generated_files if f]
    expected_filenames = [Path(f).name for f in expected_files if f]
    
    print(f"    generated_filenames: {generated_filenames}")
    print(f"    expected_filenames: {expected_filenames}")
    
    if expected_filenames:
        metrics["file_accuracy"] = coverage_ratio(generated_filenames, expected_filenames)
    else:
        metrics["file_accuracy"] = 1.0 if not generated_filenames else 0.0

    # Threshold checks (optional CI gates)
    min_auto = expected["expected_changes"].get("min_auto_coverage", 0.0)
    max_manual_ratio = expected["expected_changes"].get("expected_manual_ratio", 1.0)
    expected_validation = expected["expected_changes"].get("expected_validation", None)

    metrics["meets_min_auto_coverage"] = metrics["auto_coverage"] >= min_auto

    total = len(actual.get("auto_modernized", [])) + len(actual.get("manual_required", []))
    manual_ratio = (len(actual.get("manual_required", [])) / max(total, 1))

    metrics["meets_manual_ratio"] = manual_ratio <= max_manual_ratio

    metrics["validation_expected"] = expected_validation
    metrics["validation_passed"] = actual.get("validation_passed", False)

    return metrics