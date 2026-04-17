from fastapi import APIRouter, UploadFile, File, Form
from app.services.engine_runner import run_engine

router = APIRouter()


@router.post("/migrate")
async def migrate_project(
    engine: str         = Form(...),
    strategy: str       = Form(...),
    project_name: str   = Form(...),
    output_path: str    = Form(...),
    file: UploadFile    = File(...),
    # Angular-specific
    target_version: str = Form(default="17"),
    # PHP-specific
    source_version: str = Form(default="5.6"),
    command: str        = Form(default="migrate"),
):
    """
    Unified migration endpoint.
    Routes to the Angular or PHP engine depending on the `engine` field.
    Supported engines: angular, php
    """
    result = await run_engine(
        engine=engine,
        strategy=strategy,
        project_name=project_name,
        target_version=target_version,
        output_path=output_path,
        file=file,
        source_version=source_version,
        command=command,
    )

    status = "success" if result.get("success") else "failed"
    return {"status": status, "result": result}