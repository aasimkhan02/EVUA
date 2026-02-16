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
            FileType.JS: JSAnalyzer(),
            FileType.HTML: HTMLAnalyzer(),
            FileType.PY: PyAnalyzer(),
            FileType.JAVA: JavaAnalyzer(),
        }.get(file_type)

    def dispatch(self, files_by_type):
        raw_modules = []
        raw_templates = []
        raw_edges = []
        raw_directives = []
        raw_http_calls = []

        for ftype, paths in files_by_type.items():
            analyzer = self.get_analyzer(ftype)
            if not analyzer:
                continue

            # UPDATED: unpack 5 values (was 4)
            rm, rt, re, rd, rh = analyzer.analyze(paths)
            raw_modules.extend(rm)
            raw_templates.extend(rt)
            raw_edges.extend(re)
            raw_directives.extend(rd)
            raw_http_calls.extend(rh)

        builder = IRBuilder()
        modules, dependencies, templates, behaviors = builder.build(
            (raw_modules, raw_templates, raw_edges, raw_directives, raw_http_calls)
        )

        return AnalysisResult(
            modules=modules,
            dependencies=dependencies,
            templates=templates,
            behaviors=behaviors,
            http_calls=raw_http_calls,
        )
