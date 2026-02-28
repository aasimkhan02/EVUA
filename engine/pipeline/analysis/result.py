from dataclasses import dataclass, field
from typing import List, Any
from ir.code_model.module import Module
from ir.dependency_model.graph import DependencyGraph
from ir.template_model.template import Template
from ir.behavior_model.base import Behavior


@dataclass
class AnalysisResult:
    modules:       List[Module]
    dependencies:  DependencyGraph
    templates:     List[Template]   # IR Template objects
    behaviors:     List[Behavior]
    http_calls:    List[Any]        # RawHttpCall — untyped for IR-agnostic access
    directives:    List[Any] = field(default_factory=list)   # RawDirective objects
    raw_templates: List[Any] = field(default_factory=list)   # RawTemplate objects (with raw_html)
    routes:        List[Any] = field(default_factory=list)   # RawRoute objects