from datetime import datetime
from enum import Enum
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, Column, JSON
from sqlalchemy import Index

# --- Enums ---

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class FileStatus(str, Enum):
    CONVERTED = "converted"
    FAILED = "failed"
    SKIPPED = "skipped"

# --- Models ---

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    projects: List["Project"] = Relationship(back_populates="user")

class Project(SQLModel, table=True):
    __tablename__ = "projects"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    tech_stack: str  # AngularJS, PHP, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="projects")
    jobs: List["Job"] = Relationship(back_populates="project")

class Job(SQLModel, table=True):
    __tablename__ = "jobs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    status: JobStatus = Field(default=JobStatus.PENDING, index=True)
    source_version: Optional[str] = None
    target_version: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    project: Project = Relationship(back_populates="jobs")
    report: Optional["Report"] = Relationship(back_populates="job")
    file_tracks: List["FileTracking"] = Relationship(back_populates="job")
    logs: List["JobLog"] = Relationship(back_populates="job")
    validations: List["Validation"] = Relationship(back_populates="job")

class Report(SQLModel, table=True):
    __tablename__ = "reports"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True, unique=True)
    success_rate: float = 0.0
    errors_count: int = 0
    warnings_count: int = 0
    report_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    diff_summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    job: Job = Relationship(back_populates="report")

class FileTracking(SQLModel, table=True):
    __tablename__ = "file_tracking"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    file_path: str = Field(index=True)
    status: FileStatus = Field(default=FileStatus.SKIPPED)
    changes_summary: Optional[str] = None
    diff: Optional[str] = None  # User requested diff by default
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    job: Job = Relationship(back_populates="file_tracks")

class AIDecision(SQLModel, table=True):
    __tablename__ = "ai_decisions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    file_id: Optional[int] = Field(default=None, foreign_key="file_tracking.id", index=True)
    prompt: str
    model_used: str
    output: str
    user_override: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Validation(SQLModel, table=True):
    __tablename__ = "validations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    test_passed: bool = False
    tsc_passed: bool = False
    lint_passed: bool = False
    coverage_percent: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    job: Job = Relationship(back_populates="validations")

class JobLog(SQLModel, table=True):
    __tablename__ = "job_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    level: str = "INFO" # INFO, WARNING, ERROR, DEBUG
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    job: Job = Relationship(back_populates="logs")
