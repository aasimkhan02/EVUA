from __future__ import annotations

from dataclasses import dataclass

from .models.migration_models import PHPVersion


_ORDER = {
    PHPVersion.PHP_5_6: 0,
    PHPVersion.PHP_7_0: 1,
    PHPVersion.PHP_7_4: 2,
    PHPVersion.PHP_8_0: 3,
    PHPVersion.PHP_8_1: 4,
    PHPVersion.PHP_8_2: 5,
    PHPVersion.PHP_8_3: 6,
}


@dataclass
class MigrationStep:
    from_version: PHPVersion
    to_version: PHPVersion
    label: str


def detect_migration_path(source_version: PHPVersion, target_version: PHPVersion) -> list[MigrationStep]:
    if _ORDER[source_version] >= _ORDER[target_version]:
        return []

    ordered = sorted(_ORDER, key=lambda v: _ORDER[v])
    src_idx = ordered.index(source_version)
    tgt_idx = ordered.index(target_version)

    steps: list[MigrationStep] = []
    for idx in range(src_idx, tgt_idx):
        step = MigrationStep(
            from_version=ordered[idx],
            to_version=ordered[idx + 1],
            label=f"{ordered[idx].value}->{ordered[idx + 1].value}",
        )
        steps.append(step)
    return steps


def estimate_effort_hours(total_issues: int, ai_items: int) -> float:
    base = total_issues * 0.03
    ai_weight = ai_items * 0.12
    return round(base + ai_weight, 2)
