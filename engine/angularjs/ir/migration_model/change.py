from dataclasses import dataclass
from .base import MigrationRecord

@dataclass
class Change(MigrationRecord):
    before_id: str      # IRNode ID
    after_id: str       # IRNode ID
