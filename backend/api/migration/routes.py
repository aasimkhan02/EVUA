from fastapi import APIRouter, UploadFile, File
from services.migration_service import run_folder_migration
from api.sessions.store import create_session

router = APIRouter(prefix="/migration", tags=["migration"])


@router.post("/upload")
async def migrate_project(file: UploadFile = File(...)):

    print("\n=== MIGRATION REQUEST RECEIVED ===")
    print("Uploaded filename:", file.filename)

    try:

        print("\nRunning EVUA migration pipeline...")
        result = run_folder_migration(file)

        print("Migration result:", result)

        job_id = result["job_id"]
        files_analyzed = result["stats"]["filesAnalyzed"]

        print("\nCreating session record...")

        # Using dummy benchmark for custom uploads
        session = create_session(
            benchmark_id="custom",
            benchmark_name="Custom Migration",
            status="completed",
            file_count=files_analyzed,
            job_id=job_id
        )

        print("Session created:", session)

        return {
            "session": session,
            "migration": result
        }

    except Exception as e:

        print("\n=== MIGRATION ERROR ===")
        print("Error:", str(e))
        raise