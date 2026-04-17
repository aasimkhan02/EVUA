from dataclasses import dataclass, field
from typing import Dict, List
from pathlib import Path
from .classifier import FileType

@dataclass
class IngestionResult:
    files_by_type: Dict[FileType, List[Path]] = field(default_factory=dict)
    root_path: str = ""
