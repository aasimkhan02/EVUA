import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Depends
from sqlmodel import Session
from app.api import deps
from app.core.database import get_session
from app.models.database_models import User, Project, Job, JobStatus
from app.services.engine_runner import run_engine
from app.services.migration_persistor import persist_migration_results

router = APIRouter()
ROOT_DIR = Path(__file__).resolve().parents[3]


def _resolve_angular_report_path(project_name: str, fmt: str) -> Path:
    report_file = ".evua_report.json" if fmt == "json" else ".evua_report.md"
    reports_root = ROOT_DIR / "engine" / "angularjs" / "reports"

    direct = reports_root / project_name / report_file
    if direct.exists():
        return direct

    extracted = reports_root / f"extracted_{project_name}" / report_file
    if extracted.exists():
        return extracted

    # Fallback: pick newest matching report directory for this project key.
    candidates = []
    if reports_root.exists():
        for candidate_dir in reports_root.iterdir():
            if not candidate_dir.is_dir():
                continue
            name = candidate_dir.name.lower()
            key = project_name.lower()
            if key in name or name in key:
                candidate_file = candidate_dir / report_file
                if candidate_file.exists():
                    candidates.append(candidate_file)
        if not candidates:
            for candidate_file in reports_root.glob(f"**/{report_file}"):
                candidates.append(candidate_file)

    if candidates:
        return max(candidates, key=lambda p: p.stat().st_mtime)
    return direct


@router.post("/migrate")
async def migrate_project(
    engine: str         = Form(...),
    strategy: str       = Form(...),
    project_id: int      = Form(...), # Changed from project_name to project_id
    output_path: str    = Form(...),
    file: UploadFile    = File(...),
    # Angular-specific
    target_version: str = Form(default="17"),
    # PHP-specific
    source_version: str = Form(default="5.6"),
    command: str        = Form(default="migrate"),
    # Auth & DB Dependencies
    current_user: User   = Depends(deps.get_current_user),
    session: Session     = Depends(get_session),
):
    """
    Unified migration endpoint.
    Routes to the Angular or PHP engine and persists results to the database.
    """
    # 1. Verify Project
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")

    # 2. Create Job in DB
    job = Job(
        project_id=project_id,
        status=JobStatus.RUNNING,
        source_version=source_version if engine == "php" else "AngularJS",
        target_version=target_version,
        started_at=datetime.utcnow()
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # 3. Run Engine
    try:
        result = await run_engine(
            engine=engine,
            strategy=strategy,
            project_name=project.name, # Use project name from DB for fs paths
            target_version=target_version,
            output_path=output_path,
            file=file,
            source_version=source_version,
            command=command,
        )
        
        success = result.get("success", False)
        report_path_str = result.get("report_path")
        report_path = Path(report_path_str) if report_path_str else None
        
        # 4. Persist Results
        persist_migration_results(
            session=session,
            job_id=job.id,
            engine=engine,
            report_path=report_path,
            logs=result.get("log", []),
            success=success
        )
        
        return {
            "status": "success" if success else "failed",
            "job_id": job.id,
            "result": result
        }
        
    except Exception as e:
        job.status = JobStatus.FAILED
        job.completed_at = datetime.utcnow()
        session.add(job)
        session.commit()
        raise HTTPException(status_code=500, detail=f"Migration engine failed: {str(e)}")


@router.get("/report")
async def get_report(
    engine: str = Query(..., description="angular or php"),
    project_name: str = Query(..., description="Project name used for migration"),
    format: str = Query("json", description="json or md"),
):
    engine_key = engine.lower()
    fmt = format.lower()
    if fmt not in {"json", "md"}:
        raise HTTPException(status_code=400, detail="format must be 'json' or 'md'")

    if engine_key in {"angular", "angularjs"}:
        report_path = _resolve_angular_report_path(project_name, fmt)
    elif engine_key == "php":
        # Current PHP flow keeps JSON in .evua and markdown in reports/php.
        report_path = (
            ROOT_DIR / ".evua" / "analyze-report.json"
            if fmt == "json"
            else ROOT_DIR / "reports" / "php" / "evua_report.md"
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported engine")

    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Report not found at {report_path}",
        )

    if fmt == "json":
        try:
            return {
                "engine": engine_key,
                "project_name": project_name,
                "format": fmt,
                "path": str(report_path.relative_to(ROOT_DIR)),
                "content": json.loads(report_path.read_text(encoding="utf-8")),
            }
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail=f"Invalid JSON report: {exc}") from exc

    return {
        "engine": engine_key,
        "project_name": project_name,
        "format": fmt,
        "path": str(report_path.relative_to(ROOT_DIR)),
        "content": report_path.read_text(encoding="utf-8", errors="replace"),
    }
