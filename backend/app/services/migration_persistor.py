import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlmodel import Session, select

from app.models.database_models import Job, Report, FileTracking, Validation, JobLog, JobStatus, FileStatus

def persist_migration_results(
    session: Session,
    job_id: int,
    engine: str,
    report_path: Optional[Path],
    logs: List[str],
    success: bool
):
    """
    Core function to persist migration job results into the database.
    """
    # 1. Update Job Status
    job = session.get(Job, job_id)
    if not job:
        return
    
    job.status = JobStatus.COMPLETED if success else JobStatus.FAILED
    job.completed_at = datetime.utcnow()
    session.add(job)
    
    # 2. Save Logs (normalized)
    for line in logs:
        log_entry = JobLog(
            job_id=job_id,
            level="INFO" if "error" not in line.lower() else "ERROR",
            message=line
        )
        session.add(log_entry)
    
    # 3. Parse Report if exists
    if report_path and report_path.exists():
        try:
            report_data = json.loads(report_path.read_text(encoding="utf-8"))
            
            # 3a. Save Report
            db_report = Report(
                job_id=job_id,
                report_json=report_data,
                success_rate=report_data.get("validation", {}).get("test_run", {}).get("spec_percent", 0.0) if engine == "angular" else 0.0,
                errors_count=report_data.get("metadata", {}).get("total_issues", 0) if engine == "php" else 0,
            )
            session.add(db_report)
            
            # 3b. Save File Tracking
            if engine == "angular":
                _persist_angular_files(session, job_id, report_data)
                _persist_angular_validation(session, job_id, report_data)
            elif engine == "php":
                _persist_php_files(session, job_id, report_data)
                
        except Exception as e:
            print(f"Error persisting report results: {e}")
            session.add(JobLog(job_id=job_id, level="ERROR", message=f"Database Persistence Error: {e}"))
            
    session.commit()

def _persist_angular_files(session: Session, job_id: int, data: Dict[Any, Any]):
    changes = data.get("changes", [])
    for change in changes:
        status = FileStatus.CONVERTED if change.get("output_path") or "written to" in change.get("reason", "").lower() else FileStatus.SKIPPED
        if change.get("risk") == "RiskLevel.MANUAL":
            status = FileStatus.FAILED # Needs manual review
            
        file_track = FileTracking(
            job_id=job_id,
            file_path=change.get("source_file") or change.get("after_id") or "unknown",
            status=status,
            changes_summary=change.get("reason"),
            diff=None # In future, we could store actual diff here
        )
        session.add(file_track)

def _persist_angular_validation(session: Session, job_id: int, data: Dict[Any, Any]):
    val = data.get("validation", {})
    db_val = Validation(
        job_id=job_id,
        test_passed=val.get("tests_passed", False),
        tsc_passed=val.get("tsc_passed", False),
        lint_passed=False, # Angular report doesn't explicitly have this yet
        coverage_percent=val.get("coverage_report", {}).get("percent", 0.0)
    )
    session.add(db_val)

def _persist_php_files(session: Session, job_id: int, data: Dict[Any, Any]):
    files = data.get("files", [])
    for f in files:
        issues = f.get("manual_review", [])
        status = FileStatus.CONVERTED if not issues else FileStatus.FAILED
        
        file_track = FileTracking(
            job_id=job_id,
            file_path=f.get("path"),
            status=status,
            changes_summary=f"Issues: {len(issues)}" if issues else "All automated",
            diff=None
        )
        session.add(file_track)
