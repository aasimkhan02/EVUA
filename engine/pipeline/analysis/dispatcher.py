from .analyzers.js import JSAnalyzer
from .analyzers.html import HTMLAnalyzer
from .analyzers.py import PyAnalyzer
from .analyzers.java import JavaAnalyzer
from ..ingestion.classifier import FileType
from .builder import IRBuilder
from .result import AnalysisResult


class AnalyzerDispatcher:

    def get_analyzer(self, file_type: FileType):
        return {
            FileType.JS:   JSAnalyzer(),
            FileType.HTML: HTMLAnalyzer(),
            FileType.PY:   PyAnalyzer(),
            FileType.JAVA: JavaAnalyzer(),
        }.get(file_type)

    def _filter_raw_modules(self, raw_modules):
        return [m for m in raw_modules if hasattr(m, "name") and hasattr(m, "file")]

    def _filter_raw_templates(self, raw_templates):
        return [t for t in raw_templates if hasattr(t, "bindings") and hasattr(t, "directives")]

    def _filter_raw_edges(self, raw_edges):
        return [
            e for e in raw_edges
            if hasattr(e, "source_id") and hasattr(e, "target_id") and hasattr(e, "type")
        ]

    def _filter_raw_directives(self, raw_directives):
        return [
            d for d in raw_directives
            if hasattr(d, "has_compile") or hasattr(d, "has_link") or hasattr(d, "transclude")
        ]

    def dispatch(self, files_by_type):
        raw_modules    = []
        raw_templates  = []
        raw_edges      = []
        raw_directives = []
        raw_http_calls = []
        raw_routes     = []

        for ftype, paths in files_by_type.items():
            analyzer = self.get_analyzer(ftype)
            if not analyzer:
                continue

            result = analyzer.analyze(paths)

            # JSAnalyzer returns 6-tuple (adds raw_routes); others return 5-tuple
            if len(result) == 6:
                rm, rt, re, rd, rh, rr = result
                raw_routes.extend(rr)
            else:
                rm, rt, re, rd, rh = result

            raw_modules.extend(rm)
            raw_templates.extend(rt)
            raw_edges.extend(re)
            raw_directives.extend(rd)
            raw_http_calls.extend(rh)

        # Sanitize
        raw_modules    = self._filter_raw_modules(raw_modules)
        raw_edges      = self._filter_raw_edges(raw_edges)
        raw_directives = self._filter_raw_directives(raw_directives)

        # Preserve raw_templates before IRBuilder strips raw_html
        preserved_raw_templates = list(raw_templates)
        ir_ready_templates      = self._filter_raw_templates(raw_templates)

        builder = IRBuilder()
        modules, dependencies, templates, behaviors = builder.build(
            (raw_modules, ir_ready_templates, raw_edges, raw_directives, raw_http_calls)
        )

        return AnalysisResult(
            modules=modules,
            dependencies=dependencies,
            templates=templates,
            behaviors=behaviors,
            http_calls=raw_http_calls,
            directives=raw_directives,
            raw_templates=preserved_raw_templates,
            routes=raw_routes,
        )