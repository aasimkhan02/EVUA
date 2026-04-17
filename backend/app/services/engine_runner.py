import os
import sys
import shutil
import zipfile
import subprocess
import asyncio
from pathlib import Path

# ── Resolve paths ──────────────────────────────────────────────────────────────
# Project layout:
#   <root>/
#     engine/
#       angularjs/cli.py
#       php/cli.py
#     backend/
#       app/services/engine_runner.py  ← this file
_THIS_DIR    = Path(__file__).resolve().parent   # .../backend/app/services
_BACKEND     = _THIS_DIR.parent.parent           # .../backend
_ROOT        = _BACKEND.parent                   # project root
_ENGINE_ROOT = _ROOT / "engine"


def _cli_path(engine: str) -> Path:
    engine_key = engine.lower()
    if engine_key == "angular":
        engine_key = "angularjs"
    return _ENGINE_ROOT / engine_key / "cli.py"


def _find_project_root(extract_dir: Path, engine: str) -> Path:
    """
    After extracting an archive, the real project folder may be one level deeper.
    Use file extensions appropriate for the requested engine.
    """
    ext_map = {
        "angular": "*.js",
        "angularjs": "*.js",
        "php": "*.php",
    }
    pattern = ext_map.get(engine.lower())
    if not pattern:
        return extract_dir

    for candidate in [extract_dir, *sorted(extract_dir.iterdir())]:
        if candidate.is_dir():
            if list(candidate.rglob(pattern)):
                return candidate
    return extract_dir          # fallback: trust what was given


# ── Public dispatcher ─────────────────────────────────────────────────────────

async def run_engine(
    engine: str,
    strategy: str,
    project_name: str,
    target_version: str,
    output_path: str,
    file,                        # FastAPI UploadFile
    # PHP-specific (ignored for Angular)
    source_version: str = "5.6",
    command: str = "migrate",
) -> dict:
    """
    Route to the correct engine runner based on the `engine` field.
    """
    if engine.lower() == "php":
        return await run_php_engine(
            strategy=strategy,
            project_name=project_name,
            source_version=source_version,
            target_version=target_version,
            output_path=output_path,
            command=command,
            file=file,
        )
    # Default → Angular
    return await run_angular_engine(
        strategy=strategy,
        project_name=project_name,
        target_version=target_version,
        output_path=output_path,
        file=file,
    )


# ── Angular engine ────────────────────────────────────────────────────────────

async def run_angular_engine(
    strategy: str,
    project_name: str,
    target_version: str,
    output_path: str,
    file,
) -> dict:
    engine = "angular"
    # ── 1. Save & extract archive ─────────────────────────────────────────────
    upload_dir = _ROOT / "temp_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    archive_path = upload_dir / file.filename
    content = await file.read()
    archive_path.write_bytes(content)

    extract_dir = upload_dir / f"extracted_{project_name}"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    if archive_path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_dir)
        except zipfile.BadZipFile as e:
            return _error_result(engine, strategy, project_name, f"Bad zip file: {e}")
    else:
        shutil.copy(archive_path, extract_dir / archive_path.name)

    project_folder = _find_project_root(extract_dir, engine)
    cli_path = _cli_path(engine)

    # ── 2. Build the Angular CLI command ─────────────────────────────────────
    cmd = [
        sys.executable,
        str(cli_path),
        str(project_folder),
        "--skip-tsc",
    ]
    if strategy.lower() in ("dry-run", "dry_run", "preview"):
        cmd.append("--dry-run")
    elif strategy.lower() == "diff":
        cmd.append("--diff")

    # ── 3. Run subprocess ─────────────────────────────────────────────────────
    log_lines: list[str] = []
    indicators: list[str] = []
    return_code: int = -1

    print(f"\n[EVUA] ▶  Angular engine")
    print(f"[EVUA]    strategy : {strategy}")
    print(f"[EVUA]    project  : {project_name}")
    print(f"[EVUA]    folder   : {project_folder}")
    print(f"[EVUA]    command  : {' '.join(cmd)}\n")

    try:
        engine_dir = str(cli_path.parent)   # engine/<engine_name>/ — where pipeline/ and orchestration/ live

        def _run_subprocess():
            """Blocking subprocess call — runs inside a thread executor."""
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,   # merge stderr → stdout
                cwd=engine_dir,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            lines = []
            for line in iter(proc.stdout.readline, ""):
                line = line.rstrip()
                lines.append(line)
                print(f"[EVUA]  {line}")
            proc.stdout.close()
            proc.wait()
            return lines, proc.returncode

        loop = asyncio.get_event_loop()
        log_lines, return_code = await loop.run_in_executor(None, _run_subprocess)

        # Pick out key indicator lines
        for line in log_lines:
            lo = line.lower()
            if any(kw in lo for kw in (
                "migration summary",
                "files scanned",
                "classes found",
                "routes migrated",
                "changes proposed",
                "generated files",
                "risk:",
                "next steps",
                "validate",
                "reports",
                "error",
                "warning",
                "traceback",
            )):
                indicators.append(line)

    except FileNotFoundError:
        msg = f"cli.py not found at {cli_path}. Check project structure."
        print(f"[EVUA] ✗  {msg}")
        return _error_result(engine, strategy, project_name, msg)

    except Exception as exc:
        import traceback as _tb
        tb = _tb.format_exc()
        msg = f"Subprocess error ({type(exc).__name__}): {exc}\n{tb}"
        print(f"[EVUA] ✗  {msg}")
        return _error_result(engine, strategy, project_name, msg)

    # ── 5. Determine success ──────────────────────────────────────────────────
    success = return_code == 0

    print(f"\n[EVUA] {'✓' if success else '✗'}  Engine exited with code {return_code}\n")

    return {
        "engine":       engine,
        "strategy":     strategy,
        "project":      project_name,
        "success":      success,
        "return_code":  return_code,
        "indicators":   indicators,
        "log":          log_lines,
        "message":      "Migration complete" if success else "Migration failed — see log for details",
    }


# ── PHP engine ────────────────────────────────────────────────────────────────

async def run_php_engine(
    strategy: str,
    project_name: str,
    source_version: str,
    target_version: str,
    output_path: str,
    command: str,
    file,
) -> dict:
    engine = "php"

    # ── 1. Save & extract archive ─────────────────────────────────────────────
    upload_dir = _ROOT / "temp_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    archive_path = upload_dir / file.filename
    content = await file.read()
    archive_path.write_bytes(content)

    extract_dir = upload_dir / f"extracted_{project_name}"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    if archive_path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_dir)
        except zipfile.BadZipFile as e:
            return _error_result(engine, strategy, project_name, f"Bad zip file: {e}")
    else:
        shutil.copy(archive_path, extract_dir / archive_path.name)

    project_folder = _find_project_root(extract_dir, engine)

    # Resolve output directory — always an absolute path
    out_dir = (
        Path(output_path).resolve()
        if output_path and output_path != "./out"
        else _ROOT / "temp_uploads" / f"php_out_{project_name}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── 2. Build the PHP CLI command ──────────────────────────────────────────
    # The PHP CLI is invoked as a module from the project root so that relative
    # imports inside engine/php/ resolve correctly.
    #
    # python -m engine.php.cli [--verbose] <command> [options]
    #
    # Commands and their required flags:
    #   migrate  --source-version X --target-version Y --path <dir> --output <dir>
    #   analyze  --path <dir> --target-version Y [--source-version X] [--output <file>]
    #   report   --job-id <id> --format json
    #   rules    --list --php-version Y

    cmd_base = [sys.executable, "-m", "engine.php.cli"]

    if strategy.lower() in ("dry-run", "dry_run"):
        dry_run_flag = ["--dry-run"]
    else:
        dry_run_flag = []

    cmd_verb = command.lower()

    if cmd_verb == "migrate":
        cmd = cmd_base + [
            "migrate",
            "--source-version", source_version,
            "--target-version", target_version,
            "--path",           str(project_folder),
            "--output",         str(out_dir),
        ] + dry_run_flag

    elif cmd_verb == "analyze":
        analyze_report = str(out_dir / "analyze-report.json")
        cmd = cmd_base + [
            "analyze",
            "--path",           str(project_folder),
            "--target-version", target_version,
            "--source-version", source_version,
            "--output",         analyze_report,
        ]

    elif cmd_verb == "rules":
        cmd = cmd_base + [
            "rules",
            "--list",
            "--php-version", target_version,
        ]

    else:
        # 'report' requires a job-id we don't have at this stage — not yet supported via UI
        return _error_result(
            engine, strategy, project_name,
            f"Command '{command}' is not yet supported via the web UI. "
            "Use 'migrate' or 'analyze'."
        )

    # ── 3. Run subprocess (cwd = project root so module imports work) ─────────
    log_lines: list[str] = []
    indicators: list[str] = []
    return_code: int = -1

    print(f"\n[EVUA] ▶  PHP engine")
    print(f"[EVUA]    command  : {cmd_verb}")
    print(f"[EVUA]    strategy : {strategy}")
    print(f"[EVUA]    project  : {project_name}")
    print(f"[EVUA]    src ver  : {source_version}")
    print(f"[EVUA]    tgt ver  : {target_version}")
    print(f"[EVUA]    folder   : {project_folder}")
    print(f"[EVUA]    output   : {out_dir}")
    print(f"[EVUA]    cmd      : {' '.join(cmd)}\n")

    try:
        def _run_subprocess():
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(_ROOT),          # run from project root — enables `engine.php.cli`
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            lines = []
            for line in iter(proc.stdout.readline, ""):
                line = line.rstrip()
                lines.append(line)
                print(f"[EVUA/PHP]  {line}")
            proc.stdout.close()
            proc.wait()
            return lines, proc.returncode

        loop = asyncio.get_event_loop()
        log_lines, return_code = await loop.run_in_executor(None, _run_subprocess)

        # Pick out key indicator lines for the UI summary
        for line in log_lines:
            lo = line.lower()
            if any(kw in lo for kw in (
                "migration complete",
                "analysis complete",
                "report generated",
                "files scanned",
                "job_id",
                "report=",
                "deprecated",
                "breaking",
                "manual review",
                "error",
                "warning",
                "traceback",
                "php",
            )):
                indicators.append(line)

    except FileNotFoundError:
        msg = "Python module engine.php.cli not found. Ensure engine/php/__init__.py exists and the venv is active."
        print(f"[EVUA] ✗  {msg}")
        return _error_result(engine, strategy, project_name, msg)

    except Exception as exc:
        import traceback as _tb
        tb = _tb.format_exc()
        msg = f"PHP subprocess error ({type(exc).__name__}): {exc}\n{tb}"
        print(f"[EVUA] ✗  {msg}")
        return _error_result(engine, strategy, project_name, msg)

    # ── 4. Determine success ──────────────────────────────────────────────────
    # PHP CLI exits 0 (success), 1 (manual review needed), 2 (failures)
    # We consider 0 and 1 as non-fatal; 2+ or negative = failure
    success = return_code in (0, 1)

    print(f"\n[EVUA] {'✓' if success else '✗'}  PHP engine exited with code {return_code}\n")

    return {
        "engine":         engine,
        "command":        cmd_verb,
        "strategy":       strategy,
        "project":        project_name,
        "source_version": source_version,
        "target_version": target_version,
        "success":        success,
        "return_code":    return_code,
        "indicators":     indicators,
        "log":            log_lines,
        "message":        (
            f"PHP {cmd_verb} complete (exit {return_code})" if success
            else f"PHP {cmd_verb} failed — see log for details (exit {return_code})"
        ),
    }


def _error_result(engine, strategy, project, msg):
    return {
        "engine":      engine,
        "strategy":    strategy,
        "project":     project,
        "success":     False,
        "return_code": -1,
        "indicators":  [f"ERROR: {msg}"],
        "log":         [msg],
        "message":     msg,
    }