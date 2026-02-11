from dataclasses import dataclass
from typing import List
from ir.code_model.module import Module
from ir.dependency_model.graph import DependencyGraph
from ir.template_model.template import Template
from ir.behavior_model.base import Behavior


@dataclass
class AnalysisResult:
    modules: List[Module]
    dependencies: DependencyGraph
    templates: List[Template]
    behaviors: List[Behavior]
