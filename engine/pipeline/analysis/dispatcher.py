from .analyzers.js import JSAnalyzer
from .analyzers.html import HTMLAnalyzer
from .analyzers.py import PyAnalyzer
from .analyzers.java import JavaAnalyzer
from ..ingestion.classifier import FileType

class AnalyzerDispatcher:

    def get_analyzer(self, file_type: FileType):
        return {
            FileType.JS: JSAnalyzer(),
            FileType.HTML: HTMLAnalyzer(),
            FileType.PY: PyAnalyzer(),
            FileType.JAVA: JavaAnalyzer(),
        }.get(file_type)
