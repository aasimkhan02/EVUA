from pathlib import Path
import subprocess
import sys

ENGINE_ROOT = Path(__file__).resolve().parents[1]  # engine/

def run_pipeline_on_repo(repo_path: Path):
    """
    Runs EVUA CLI in batch mode from engine root so reports are written.
    """
    cmd = [sys.executable, "cli.py", str(repo_path), "--batch"]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=ENGINE_ROOT,   # 🔥 critical fix
    )

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }
