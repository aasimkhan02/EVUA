from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TimelineEvent(BaseModel):
    timestamp: datetime
    stage: str  # ingestion | analysis | patterns | transformation | risk | validation | reporting | decision
    message: str
    detail: Optional[dict] = None
    level: str = "info"  # info | warning | error


class FileChange(BaseModel):
    path: str
    status: str  # NEW | MODIFIED
    risk_level: str = "SAFE"  # SAFE | RISKY | MANUAL
    reason: str = ""
    decision: str = "pending"  # pending | accepted | reverted


class SessionOut(BaseModel):
    id: str
    user_id: str
    benchmark_id: str
    benchmark_name: str
    status: str  # running | completed | failed
    created_at: datetime
    file_count: int = 0
    risk_summary: Optional[dict] = None


class SessionDetail(SessionOut):
    timeline: List[TimelineEvent] = []
    files: List[FileChange] = []


class FileDiff(BaseModel):
    file_path: str
    before_content: str
    after_content: str
    unified_diff: str
    is_new: bool
    risk_level: str = "SAFE"
    reason: str = ""
    decision: str = "pending"
