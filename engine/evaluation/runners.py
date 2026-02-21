from pathlib import Path
import subprocess
import sys

ENGINE_ROOT = Path(__file__).resolve().parents[1]  # engine/

def run_pipeline_on_repo(repo_path: Path):
    """
    Runs EVUA CLI in batch mode from engine root so reports are written.
    """
    # Use absolute path to ensure we're running the right cli.py
    cli_path = ENGINE_ROOT / "cli.py"
    
    cmd = [sys.executable, str(cli_path), str(repo_path), "--batch"]
    
    print(f"\n[HARNESS DEBUG] Running command: {' '.join(cmd)}")
    print(f"[HARNESS DEBUG] Working directory: {ENGINE_ROOT}")
    print(f"[HARNESS DEBUG] CLI.py exists: {cli_path.exists()}")
    print(f"[HARNESS DEBUG] Repo path: {repo_path}")
    print(f"[HARNESS DEBUG] Repo exists: {repo_path.exists()}")
    
    # Clear any existing report to avoid reading stale data
    report_path = repo_path / ".evua_report.json"
    if report_path.exists():
        report_path.unlink()
        print(f"[HARNESS DEBUG] Deleted existing report: {report_path}")

    print(f"[HARNESS DEBUG] Running subprocess...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=ENGINE_ROOT,
    )
    
    print(f"[HARNESS DEBUG] Return code: {result.returncode}")
    print(f"[HARNESS DEBUG] stdout length: {len(result.stdout)}")
    print(f"[HARNESS DEBUG] stderr length: {len(result.stderr)}")
    
    # Print first 500 chars of stdout to see our debug messages
    if result.stdout:
        print(f"\n[HARNESS DEBUG] CLI STDOUT (first 500 chars):")
        print(result.stdout[:500])
    
    if result.stderr:
        print(f"\n[HARNESS DEBUG] CLI STDERR (first 500 chars):")
        print(result.stderr[:500])

    # Verify the report was written
    if report_path.exists():
        print(f"[HARNESS DEBUG] Report written successfully: {report_path}")
        print(f"[HARNESS DEBUG] Report size: {report_path.stat().st_size} bytes")
    else:
        print(f"[HARNESS DEBUG] ERROR: Report not written to {report_path}")
        print(f"[HARNESS DEBUG] Full stdout: {result.stdout[-1000:]}")
        print(f"[HARNESS DEBUG] Full stderr: {result.stderr[-1000:]}")

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }