import pytest
import uuid

from ir.migration_model.base import MigrationRecord, ChangeSource
from ir.migration_model.change import Change
from ir.migration_model.confidence import ConfidenceScore
from ir.migration_model.decision import MigrationDecision, DecisionType
from ir.migration_model.snapshot import MigrationSnapshot
from ir.code_model.base import IRNode


# ----------------------------
# ChangeSource
# ----------------------------

def test_change_source_values():
    assert ChangeSource.RULE.value == "rule"
    assert ChangeSource.AI.value == "ai"
    assert ChangeSource.HUMAN.value == "human"


def test_change_source_invalid():
    with pytest.raises(ValueError):
        ChangeSource("bot")


# ----------------------------
# MigrationRecord
# ----------------------------

def test_migration_record_is_irnode():
    r = MigrationRecord(source=ChangeSource.RULE, reason="test")
    assert isinstance(r, IRNode)
    uuid.UUID(r.id)


def test_migration_record_fields():
    r = MigrationRecord(source=ChangeSource.AI, reason="ambiguous")
    assert r.source == ChangeSource.AI
    assert r.reason == "ambiguous"


# ----------------------------
# Change
# ----------------------------

def test_change_creation():
    c = Change(
        source=ChangeSource.RULE,
        reason="ng-controller -> component",
        before_id="old123",
        after_id="new456"
    )

    assert c.before_id == "old123"
    assert c.after_id == "new456"
    assert c.source == ChangeSource.RULE
    assert c.reason == "ng-controller -> component"


def test_change_is_migration_record():
    c = Change(
        source=ChangeSource.HUMAN,
        reason="manual fix",
        before_id="a",
        after_id="b"
    )
    assert isinstance(c, MigrationRecord)


# ----------------------------
# ConfidenceScore
# ----------------------------

def test_confidence_score_basic():
    cs = ConfidenceScore(value=0.75, explanation="rules matched perfectly")
    assert cs.value == 0.75
    assert cs.explanation == "rules matched perfectly"


def test_confidence_score_boundaries():
    ConfidenceScore(value=0.0, explanation="no confidence")
    ConfidenceScore(value=1.0, explanation="full confidence")


def test_confidence_score_out_of_range_allowed_but_flagged():
    cs = ConfidenceScore(value=1.5, explanation="bad model")
    assert cs.value == 1.5


# ----------------------------
# MigrationDecision
# ----------------------------

def test_migration_decision_approve():
    d = MigrationDecision(change_id="c1", decision=DecisionType.APPROVE)
    assert d.change_id == "c1"
    assert d.decision == DecisionType.APPROVE
    assert d.edited_after_id is None
    assert d.comment is None


def test_migration_decision_edit():
    d = MigrationDecision(
        change_id="c2",
        decision=DecisionType.EDIT,
        edited_after_id="new789",
        comment="fixed naming"
    )
    assert d.decision == DecisionType.EDIT
    assert d.edited_after_id == "new789"
    assert d.comment == "fixed naming"


def test_decision_type_invalid():
    with pytest.raises(ValueError):
        DecisionType("maybe")


# ----------------------------
# MigrationSnapshot
# ----------------------------

def test_migration_snapshot_defaults():
    snap = MigrationSnapshot()
    assert snap.changes == []
    assert snap.decision is None
    assert snap.confidence is None


def test_migration_snapshot_changes_isolated():
    s1 = MigrationSnapshot()
    s2 = MigrationSnapshot()

    s1.changes.append(
        Change(source=ChangeSource.RULE, reason="x", before_id="a", after_id="b")
    )
    assert s2.changes == []


def test_migration_snapshot_full():
    change = Change(source=ChangeSource.RULE, reason="x", before_id="a", after_id="b")
    decision = MigrationDecision(change_id="c1", decision=DecisionType.APPROVE)
    confidence = ConfidenceScore(value=0.9, explanation="safe")

    snap = MigrationSnapshot(
        changes=[change],
        decision=decision,
        confidence=confidence
    )

    assert snap.changes == [change]
    assert snap.decision == decision
    assert snap.confidence == confidence
