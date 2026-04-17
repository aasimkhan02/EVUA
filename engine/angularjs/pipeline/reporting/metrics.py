from dataclasses import dataclass
from pipeline.risk.levels import RiskLevel


@dataclass
class Metrics:
    percent_auto_converted: float
    risky_changes: int
    manual_changes: int
    test_pass_rate: float

    @staticmethod
    def from_run(transformation, risk_result, validation):
        """
        risk_result: RiskResult dataclass with .risk_by_change_id dict
        validation:  dict with keys 'tests_passed', 'snapshot_passed', 'failures'
        """
        from pipeline.risk.result import RiskResult as _RiskResult

        # Accept both RiskResult dataclass and legacy (risk_by_change, reason) tuple
        if isinstance(risk_result, _RiskResult):
            risk_by_change = risk_result.risk_by_change_id
        elif isinstance(risk_result, tuple):
            risk_by_change = risk_result[0]
        else:
            risk_by_change = {}

        total = len(transformation.changes)
        if total == 0:
            return Metrics(
                percent_auto_converted=0.0,
                risky_changes=0,
                manual_changes=0,
                test_pass_rate=1.0 if (validation or {}).get("tests_passed") else 0.0,
            )

        risky = 0
        manual = 0
        for _cid, risk in risk_by_change.items():
            # Compare directly to enum values — no fragile string matching
            if risk == RiskLevel.RISKY:
                risky += 1
            elif risk == RiskLevel.MANUAL:
                manual += 1

        auto = total - manual
        percent_auto = (auto / total) * 100.0
        test_pass_rate = 1.0 if (validation or {}).get("tests_passed") else 0.0

        return Metrics(
            percent_auto_converted=round(percent_auto, 2),
            risky_changes=risky,
            manual_changes=manual,
            test_pass_rate=test_pass_rate,
        )