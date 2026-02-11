from dataclasses import dataclass

@dataclass
class Metrics:
    percent_auto_converted: float
    risky_changes: int
    manual_changes: int
    test_pass_rate: float
