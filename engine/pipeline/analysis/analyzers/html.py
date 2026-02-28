from pathlib import Path
from typing import List
import re
from .base import Analyzer


class RawTemplate:
    def __init__(
        self,
        controller: str | None,
        loops: list[str],
        conditionals: list[str],
        events: list[str],
        file: str,
        raw_html: str = "",
    ):
        self.controller   = controller
        self.loops        = loops
        self.conditionals = conditionals
        self.events       = events
        self.file         = file
        self.raw_html     = raw_html   # full source text for template_migrator

        # IRBuilder compatibility
        self.bindings   = []
        self.directives = []


class HTMLAnalyzer(Analyzer):
    NG_CONTROLLER_REGEX = re.compile(r'ng-controller\s*=\s*["\'](\w+)["\']')
    NG_REPEAT_REGEX     = re.compile(r'ng-repeat\s*=\s*["\']([^"\']+)["\']')
    NG_IF_REGEX         = re.compile(r'ng-if\s*=\s*["\']([^"\']+)["\']')
    NG_CLICK_REGEX      = re.compile(r'ng-click\s*=\s*["\']([^"\']+)["\']')

    def analyze(self, paths: List[Path]):
        raw_templates = []

        for path in paths:
            text = path.read_text(encoding="utf-8", errors="ignore")

            controllers = self.NG_CONTROLLER_REGEX.findall(text)
            loops       = self.NG_REPEAT_REGEX.findall(text)
            conditionals = self.NG_IF_REGEX.findall(text)
            events      = self.NG_CLICK_REGEX.findall(text)

            controller = controllers[0] if controllers else None

            raw_templates.append(
                RawTemplate(
                    controller=controller,
                    loops=loops,
                    conditionals=conditionals,
                    events=events,
                    file=str(path),
                    raw_html=text,       # pass full source for text-rewriting
                )
            )

        return [], raw_templates, [], [], []