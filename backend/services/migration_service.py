import zipfile
import os
import subprocess
import uuid
import json
from pathlib import Path

ENGINE_PATH = r"C:\Users\moidin\Desktop\Projects\EVUA\engine"

UPLOAD_DIR = "uploads"
WORKSPACE = "workspace"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(WORKSPACE, exist_ok=True)


def count_files(root):
    total = 0
    for _, _, files in os.walk(root):
        total += len(files)
    return total


def generate_stats(project_path, diff_text):

    files_analyzed = count_files(project_path)

    changed_files = set()
    rules_applied = 0

    for line in diff_text.splitlines():

        if line.startswith("diff --git"):
            parts = line.split(" ")
            if len(parts) > 2:
                changed_files.add(parts[2])

        if line.startswith("+") or line.startswith("-"):
            rules_applied += 1

    return {
        "filesAnalyzed": files_analyzed,
        "filesChanged": len(changed_files),
        "rulesApplied": rules_applied
    }


def generate_markdown_report(stats, job_id):

    return f"""
# EVUA Migration Report

## Migration Job
{job_id}

## Summary

| Metric | Value |
|------|------|
| Files Analyzed | {stats['filesAnalyzed']} |
| Files Changed | {stats['filesChanged']} |
| Transformation Operations | {stats['rulesApplied']} |

## Notes

Generated automatically by EVUA migration engine.
""".strip()


def zip_directory(source_dir, output_zip):

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                path = os.path.join(root, file)
                arcname = os.path.relpath(path, source_dir)
                zipf.write(path, arcname)


def run_folder_migration(file):

    job_id = str(uuid.uuid4())
    job_dir = Path(WORKSPACE) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # detect if upload is zip or folder file
    if file.filename.endswith(".zip"):

        zip_path = Path(UPLOAD_DIR) / file.filename

        with open(zip_path, "wb") as f:
            f.write(file.file.read())

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(job_dir)

    else:
        # folder upload
        relative_path = Path(file.filename)
        target_path = job_dir / relative_path

        target_path.parent.mkdir(parents=True, exist_ok=True)

        with open(target_path, "wb") as f:
            f.write(file.file.read())

    # run EVUA engine
    cmd = [
        "python",
        "cli.py",
        str(job_dir),
        "--diff"
    ]

    result = subprocess.run(
        cmd,
        cwd=ENGINE_PATH,
        capture_output=True,
        text=True
    )

    diff_output = result.stdout

    stats = generate_stats(job_dir, diff_output)

    stats_file = job_dir / "migration_stats.json"
    report_file = job_dir / "migration_report.md"
    diff_file = job_dir / "diff.txt"
    zip_file = job_dir / "migrated_project.zip"

    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)

    with open(report_file, "w") as f:
        f.write(generate_markdown_report(stats, job_id))

    with open(diff_file, "w") as f:
        f.write(diff_output)

    zip_directory(job_dir, zip_file)

    return {
        "job_id": job_id,
        "stats": stats,
        "outputs": {
            "report": str(report_file),
            "stats": str(stats_file),
            "diff": str(diff_file),
            "zip": str(zip_file)
        }
    }