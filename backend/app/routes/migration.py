import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Depends
from sqlmodel import Session
from app.api import deps
from app.core.database import get_session
from app.models.database_models import User, Project, Job, JobStatus
from app.models.schemas import JobOut
from app.services.engine_runner import run_engine
from app.services.migration_persistor import persist_migration_results
from typing import List

router = APIRouter()
ROOT_DIR = Path(__file__).resolve().parents[3]


def _resolve_angular_report_path(project_name: str, fmt: str) -> Path:
    report_file = ".evua_report.json" if fmt == "json" else ".evua_report.md"
    reports_root = ROOT_DIR / "engine" / "angularjs" / "reports"

    extracted = reports_root / f"extracted_{project_name}" / report_file
    if extracted.exists():
        return extracted

    direct = reports_root / project_name / report_file
    if direct.exists():
        return direct

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
    project_name: str    = Form(...), # Changed back to project_name for UI compatibility
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
    # 0. Engine/File validation — check the archive contains files for the chosen engine
    import zipfile, tempfile, shutil as _shutil
    _allowed = {"angular": [".js", ".ts"], "php": [".php"]}
    _ext_required = _allowed.get(engine.lower())
    if _ext_required:
        # Peek inside the zip without running the full engine
        try:
            _zip_bytes = await file.read()
            await file.seek(0)   # FastAPI UploadFile.seek() is a coroutine
            import io as _io
            with zipfile.ZipFile(_io.BytesIO(_zip_bytes)) as _zf:
                _names = [n.lower() for n in _zf.namelist()]
            # Count files matching the engine
            _matched = sum(1 for n in _names if any(n.endswith(ext) for ext in _ext_required))
            # Count files belonging to the OTHER engine (e.g. .php when engine=angular)
            _other_exts = [".php"] if engine.lower() in ("angular", "angularjs") else [".js", ".ts"]
            _other = sum(1 for n in _names if any(n.endswith(ext) for ext in _other_exts))
            if _matched == 0 and _other > 0:
                _other_label = "PHP" if engine.lower() in ("angular", "angularjs") else "JavaScript/TypeScript"
                _chosen_label = "AngularJS" if engine.lower() in ("angular", "angularjs") else "PHP"
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Engine mismatch: you selected the {_chosen_label} engine, but the uploaded "
                        f"archive contains {_other} {_other_label} file(s) and no "
                        f"{', '.join(_ext_required)} files. "
                        f"Please select the correct engine for your project."
                    )
                )
        except zipfile.BadZipFile:
            pass  # Non-zip uploads — let engine_runner handle validation

    # 1. Verify/Create Project
    from sqlmodel import select
    project = session.exec(
        select(Project)
        .where(Project.name == project_name)
        .where(Project.user_id == current_user.id)
    ).first()

    if not project:
        project = Project(
            name=project_name,
            user_id=current_user.id,
            tech_stack=engine,
            description=f"Auto-created during {engine} migration"
        )
        session.add(project)
        session.commit()
        session.refresh(project)

    # 2. Create Job in DB
    job = Job(
        project_id=project.id,
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
        out_dir = ROOT_DIR / "temp_uploads" / f"php_out_{project_name}"
        report_path = out_dir / "evua_report.json"
        if not report_path.exists():
            report_path = ROOT_DIR / ".evua" / "analyze-report.json" if fmt == "json" else ROOT_DIR / "reports" / "php" / "evua_report.md"
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


@router.get("/file")
async def get_file_content(
    path: str = Query(..., description="Absolute path to the file"),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Read file contents from the local filesystem to display in the Workspace diff editor.
    """
    try:
        target = Path(path)
        if not target.is_absolute():
            target = ROOT_DIR / target
        target = target.resolve()
        
        # Fallback for Angular: pipeline_runner renames .tmp_ to angular-app
        if not target.exists() and ".tmp_" in str(target) and "angular-app" in str(target):
            import re
            fixed_path = re.sub(r"\.tmp_[a-f0-9]+", "angular-app", str(target))
            alt_target = Path(fixed_path).resolve()
            if alt_target.exists():
                target = alt_target

        # Fallback for PHP: if looking in php_out but it doesn't exist, use the extracted source
        if not target.exists() and "php_out_" in str(target):
            import re
            # Extract project name from php_out_{project_name}
            match = re.search(r"php_out_([^/\\]+)", str(target))
            if match:
                project_name = match.group(1)
                fixed_path = re.sub(rf"php_out_{project_name}", rf"extracted_{project_name}/{project_name}", str(target))
                alt_target = Path(fixed_path).resolve()
                if alt_target.exists():
                    target = alt_target
        
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail="File not found on server")
        content = target.read_text(encoding="utf-8", errors="replace")
        return {"path": str(target), "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/jobs", response_model=List[JobOut])
async def get_jobs(
    current_user: User = Depends(deps.get_current_user),
    session: Session = Depends(get_session),
):
    """
    Get migration history for the current user.
    """
    from sqlmodel import select
    
    # We join Job with Project to get the project_name for the history list
    statement = (
        select(Job, Project.name)
        .join(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Job.created_at.desc())
    )
    
    results = session.exec(statement).all()
    
    # Map the results to JobOut objects
    jobs = []
    for job, project_name in results:
        job_dict = job.dict()
        job_dict["project_name"] = project_name
        jobs.append(JobOut(**job_dict))
        
    return jobs

@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: int,
    current_user: User = Depends(deps.get_current_user),
    session: Session = Depends(get_session),
):
    """
    Delete a specific migration job and its associated data.
    """
    from sqlmodel import select, delete
    from app.models.database_models import Report, FileTracking, JobLog, Validation, AIDecision
    
    # Ensure job belongs to the current user
    statement = select(Job).join(Project).where(
        Job.id == job_id, 
        Project.user_id == current_user.id
    )
    job = session.exec(statement).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Delete related dependencies explicitly to ensure clean cleanup
    for model in [Report, AIDecision, FileTracking, JobLog, Validation]:
        session.exec(delete(model).where(model.job_id == job.id))
        
    # Delete the job itself
    session.delete(job)
    session.commit()
    
    return None
