"""
orchestration/stage_controller.py

Controls which pipeline stages are enabled and in what order they run.
Useful for partial runs (e.g. analysis-only, skip validation in CI).
"""

from dataclasses import dataclass, field
from typing import List


STAGES = [
    "ingestion",
    "analysis",
    "patterns",
    "transformation",
    "risk",
    "validation",
    "reporting",
]


@dataclass
class StageController:
    """
    Controls which pipeline stages are active.

    Usage:
        ctrl = StageController.all()          # run everything
        ctrl = StageController.until("risk")  # stop before validation
        ctrl = StageController(skip={"validation", "reporting"})
    """
    skip: set = field(default_factory=set)

    @classmethod
    def all(cls) -> "StageController":
        """Enable every stage."""
        return cls(skip=set())

    @classmethod
    def until(cls, last_stage: str) -> "StageController":
        """Enable stages up to and including last_stage, skip the rest."""
        if last_stage not in STAGES:
            raise ValueError(f"Unknown stage '{last_stage}'. Valid: {STAGES}")
        cutoff = STAGES.index(last_stage)
        return cls(skip=set(STAGES[cutoff + 1:]))

    @classmethod
    def only(cls, *stages: str) -> "StageController":
        """Enable only the named stages, skip everything else."""
        for s in stages:
            if s not in STAGES:
                raise ValueError(f"Unknown stage '{s}'. Valid: {STAGES}")
        return cls(skip=set(STAGES) - set(stages))

    def is_enabled(self, stage: str) -> bool:
        return stage not in self.skip

    def enabled_stages(self) -> List[str]:
        return [s for s in STAGES if s not in self.skip]

    def __repr__(self):
        enabled = self.enabled_stages()
        return f"StageController(enabled={enabled})"