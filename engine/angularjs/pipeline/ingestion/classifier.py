from enum import Enum
from pathlib import Path

class FileType(str, Enum):
    JS = "js"
    TS = "ts"
    HTML = "html"
    PY = "py"
    JAVA = "java"
    OTHER = "other"

class FileClassifier:

    def classify(self, path: Path) -> FileType:
        ext = path.suffix.lower()
        return {
            ".js": FileType.JS,
            ".ts": FileType.TS,
            ".html": FileType.HTML,
            ".py": FileType.PY,
            ".java": FileType.JAVA,
        }.get(ext, FileType.OTHER)
