from dataclasses import dataclass

@dataclass
class Metrics:
    percent_auto_converted: float
    risky_changes: int
    manual_changes: int
    test_pass_rate: float

    @staticmethod
    def from_run(transformation, risk_by_change, validation):
        total = len(transformation.changes)
        if total == 0:
            return Metrics(0.0, 0, 0, 1.0 if validation.get("tests_passed") else 0.0)

        risky = 0
        manual = 0
        for cid, risk in risk_by_change.items():
            if str(risk).endswith("RISKY"):
                risky += 1
            if str(risk).endswith("MANUAL"):
                manual += 1

        auto = total - manual
        percent_auto = (auto / total) * 100.0
        test_pass_rate = 1.0 if validation.get("tests_passed") else 0.0

        return Metrics(
            percent_auto_converted=round(percent_auto, 2),
            risky_changes=risky,
            manual_changes=manual,
            test_pass_rate=test_pass_rate
        )
