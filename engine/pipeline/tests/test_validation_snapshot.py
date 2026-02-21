import json
from pipeline.validation.comparators.snapshot import SnapshotComparator


def test_snapshot_comparator_pass(tmp_path):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"

    before.write_text(json.dumps({"UserComponent": {"x": 1}}))
    after.write_text(json.dumps({"UserComponent": {"x": 1}}))

    ok, failures = SnapshotComparator().compare(str(before), str(after))
    assert ok is True
    assert failures == []


def test_snapshot_comparator_mismatch(tmp_path):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"

    before.write_text(json.dumps({"UserComponent": {"x": 1}}))
    after.write_text(json.dumps({"UserComponent": {"x": 2}}))

    ok, failures = SnapshotComparator().compare(str(before), str(after))
    assert ok is False
    assert "State mismatch" in failures[0]


def test_snapshot_comparator_missing_component(tmp_path):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"

    before.write_text(json.dumps({"UserComponent": {"x": 1}}))
    after.write_text(json.dumps({}))

    ok, failures = SnapshotComparator().compare(str(before), str(after))
    assert ok is False
    assert "Missing component snapshot" in failures[0]


def test_snapshot_comparator_invalid_json(tmp_path):
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"

    before.write_text("{bad json")
    after.write_text("{}")

    ok, failures = SnapshotComparator().compare(str(before), str(after))
    assert ok is False
    assert "Snapshot comparison failed" in failures[0]
