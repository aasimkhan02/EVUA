from __future__ import annotations

import logging
from pathlib import Path

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from .config import load_config
from .pipeline.orchestrator import CLIOrchestrator
from .report_generator import write_report
from .rule_engine.live_rules import fetch_live_rules

console = Console()


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


@click.group()
@click.option("--config", "config_path", default=None, help="Path to .evua.yml")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx: click.Context, config_path: str | None, verbose: bool) -> None:
    _configure_logging(verbose)
    config = load_config(config_path)
    ctx.obj = {"config": config, "orchestrator": CLIOrchestrator(config)}


@cli.command()
@click.option("--source-version", required=True, type=click.Choice(["5.6", "7.0", "7.4", "8.0", "8.1", "8.2", "8.3"]))
@click.option("--target-version", required=True, type=click.Choice(["7.0", "7.4", "8.0", "8.1", "8.2", "8.3"]))
@click.option("--path", "scan_path", required=True, type=click.Path(exists=True, file_okay=True, dir_okay=True))
@click.option("--output", "output_path", required=True, type=click.Path())
@click.option("--format", "fmt", default="json", type=click.Choice(["json", "html", "markdown"]))
@click.option("--dry-run", is_flag=True, help="Analyze and plan changes without modifying files")
@click.pass_context
def migrate(ctx: click.Context, source_version: str, target_version: str, scan_path: str, output_path: str, fmt: str, dry_run: bool) -> None:
    orchestrator: CLIOrchestrator = ctx.obj["orchestrator"]

    progress_updates: list[tuple[int, int, str]] = []

    def cb(done: int, total: int, file_path: str) -> None:
        progress_updates.append((done, total, file_path))

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Migrating files", total=100)
        job_id, report, _ = orchestrator.analyze_or_migrate(
            path=scan_path,
            source_version=source_version,
            target_version=target_version,
            dry_run=dry_run,
            do_migrate=True,
            progress_cb=cb,
        )
        if progress_updates:
            done, total, _ = progress_updates[-1]
            progress.update(task, completed=int((done / max(total, 1)) * 100))
        else:
            progress.update(task, completed=100)

    out = write_report(report, output_path, fmt)
    console.print(f"[green]Migration complete[/green] job_id={job_id} report={out}")

    failed = report.ai_handoff_summary.get("failed", 0)
    manual = report.summary.manual_review_items
    if failed > 0:
        raise SystemExit(2)
    if manual > 0:
        raise SystemExit(1)
    raise SystemExit(0)


@cli.command()
@click.option("--path", "scan_path", required=True, type=click.Path(exists=True, file_okay=True, dir_okay=True))
@click.option("--target-version", required=True, type=click.Choice(["7.0", "7.4", "8.0", "8.1", "8.2", "8.3"]))
@click.option("--source-version", default="5.6", type=click.Choice(["5.6", "7.0", "7.4", "8.0", "8.1", "8.2", "8.3"]))
@click.option("--output", "output_path", default=".evua/analyze-report.json", type=click.Path())
@click.pass_context
def analyze(ctx: click.Context, scan_path: str, target_version: str, source_version: str, output_path: str) -> None:
    orchestrator: CLIOrchestrator = ctx.obj["orchestrator"]
    job_id, report, _ = orchestrator.analyze_or_migrate(
        path=scan_path,
        source_version=source_version,
        target_version=target_version,
        dry_run=True,
        do_migrate=False,
    )
    out = write_report(report, output_path, "json")
    console.print(f"[cyan]Analysis complete[/cyan] job_id={job_id} report={out}")

    if report.summary.manual_review_items > 0:
        raise SystemExit(1)
    raise SystemExit(0)


@cli.command()
@click.option("--job-id", required=True)
@click.option("--format", "fmt", required=True, type=click.Choice(["json", "html", "markdown"]))
@click.option("--output", "output_path", required=False, type=click.Path())
@click.pass_context
def report(ctx: click.Context, job_id: str, fmt: str, output_path: str | None) -> None:
    orchestrator: CLIOrchestrator = ctx.obj["orchestrator"]
    loaded_report = orchestrator.load_job_report(job_id)
    if not output_path:
        ext = "md" if fmt == "markdown" else fmt
        output_path = str(Path(".evua/reports") / f"{job_id}.{ext}")
    out = write_report(loaded_report, output_path, fmt)
    console.print(f"[green]Report generated[/green] {out}")


@cli.command()
@click.option("--list", "list_rules", is_flag=True, help="List available rules for a PHP version")
@click.option("--php-version", default="8.0", type=click.Choice(["8.0", "8.1", "8.2", "8.3"]))
@click.pass_context
def rules(ctx: click.Context, list_rules: bool, php_version: str) -> None:
    if not list_rules:
        console.print("Use --list to display rules")
        raise SystemExit(0)

    cfg = ctx.obj["config"]
    data = fetch_live_rules(php_version, cfg.rules.cache_dir)
    counts = {
        "deprecated": len([r for r in data["raw_items"] if r.get("category") == "deprecated"]),
        "breaking_change": len([r for r in data["raw_items"] if r.get("category") == "breaking_change"]),
        "new_feature": len([r for r in data["raw_items"] if r.get("category") == "new_feature"]),
    }

    console.print(f"[bold]PHP {php_version} Live Rules[/bold]")
    console.print(f"Deprecated items: {counts['deprecated']}")
    console.print(f"Breaking changes: {counts['breaking_change']}")
    console.print(f"New features: {counts['new_feature']}")
    console.print(f"Known deprecated function mappings: {len(data['deprecated_functions'])}")


if __name__ == "__main__":
    cli()
