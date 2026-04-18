"""
pipeline/validation/base.py
============================

Abstract base for every validation stage.

The `validate()` method must return a ValidationResult.  Since
ValidationResult now carries a `coverage_report` dict, concrete stages
that run after the Angular project is written should populate it via
CoverageAnalyzer.  Stages that run in dry-run mode should leave it as
the default empty dict.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..analysis.result import AnalysisResult
from ..transformation.result import TransformationResult
from ..ai.result import AIResult
from .result import ValidationResult


class ValidationStage(ABC):

    @abstractmethod
    def validate(
        self,
        analysis: AnalysisResult,
        transformation: TransformationResult,
        ai: AIResult | None,
    ) -> ValidationResult:
        """
        Run all validation checks and return a ValidationResult.

        Implementations should:
        1. Run each check independently — never short-circuit on first failure.
        2. Populate `checks` dict for every check attempted.
        3. Run CoverageAnalyzer if files have been written to disk, and store
           the result in `coverage_report`.
        4. Never raise — catch exceptions per-check and record them as
           failures.
        """