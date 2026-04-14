"""
pipeline/ai/stage.py
====================

AIAssistStage — post-processing pass that runs after all deterministic rules.

Reads from the output directory (already written by the rule engine), identifies
stubs that need filling, calls the LLM client, and writes improved versions back.

Three tasks performed in order
--------------------------------
1. PIPE BODIES      — find *.pipe.ts with `return value;` body, port the commented
                       AngularJS filter logic into transform()

2. STUB TEMPLATES   — find *.component.html with the stub marker comment, generate
                       a real Angular template using the controller source + .ts file

3. LINK FUNCTIONS   — find *.component.ts with the link() warning comment, migrate
                       the link logic into ngAfterViewInit()

Each task is idempotent: if the file has already been completed (no stub marker),
it is skipped. This means --ai-assist can be safely re-run.

Output
------
Prints a summary per file: COMPLETED / SKIPPED / FAILED.
Returns an AIAssistResult with counts.

Usage from cli.py
-----------------
    from pipeline.ai.stage import AIAssistStage
    from pipeline.ai.client import AIClient

    client = AIClient()
    stage  = AIAssistStage(app_dir=effective_out_dir / "src" / "app",
                           analysis=analysis,
                           client=client)
    result = stage.run()
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pipeline.ai.client import AIClient
from pipeline.ai.prompts import (
    pipe_transform_prompt,
    stub_template_prompt,
    link_function_prompt,
    clean_response,
)


# ─────────────────────────────────────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AIAssistResult:
    pipes_completed:     int = 0
    pipes_skipped:       int = 0
    pipes_failed:        int = 0
    templates_completed: int = 0
    templates_skipped:   int = 0
    templates_failed:    int = 0
    links_completed:     int = 0
    links_skipped:       int = 0
    links_failed:        int = 0
    errors:              list = field(default_factory=list)

    @property
    def total_completed(self) -> int:
        return self.pipes_completed + self.templates_completed + self.links_completed

    @property
    def total_failed(self) -> int:
        return self.pipes_failed + self.templates_failed + self.links_failed


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

# Marker that indicates a pipe transform() body is a stub
_PIPE_STUB_MARKER   = "return value;"

# Marker that indicates a component template is a stub (from controller_to_component.py)
_TEMPLATE_STUB_MARKER = "TODO: no AngularJS template found"

# Marker that indicates a link() function needs migrating
_LINK_STUB_MARKER   = "port DOM logic to ngAfterViewInit"


def _extract_pipe_filter_body(ts_content: str) -> Optional[str]:
    """
    Extract the commented-out original AngularJS filter body from a pipe stub.
    The format is:
        // Original AngularJS filter body (migrate manually):
        // return function(input) { ... }
    """
    lines = ts_content.splitlines()
    collecting = False
    body_lines = []

    for line in lines:
        stripped = line.strip()
        if "Original AngularJS filter body" in stripped:
            collecting = True
            continue
        if collecting:
            if stripped.startswith("//"):
                # Strip the leading comment marker
                body_lines.append(stripped[2:].lstrip())
            else:
                break  # end of comment block

    return "\n".join(body_lines).strip() if body_lines else None


def _extract_controller_js(analysis, controller_name: str) -> str:
    """
    Try to find the original JS source for a controller by reading its source file.
    Falls back to an empty string if not found.
    """
    for module in getattr(analysis, "modules", []):
        for cls in getattr(module, "classes", []):
            if cls.name == controller_name:
                # module.name is the file path
                file_path = Path(module.name)
                if file_path.exists():
                    return file_path.read_text(encoding="utf-8", errors="ignore")
    return ""


def _map_stem_to_controller(stem: str, analysis) -> Optional[object]:
    """
    Given a file stem like 'auth' or 'userlist', find the matching IR class.
    Matches by lowercase name containing the stem.
    """
    for module in getattr(analysis, "modules", []):
        for cls in getattr(module, "classes", []):
            cls_lower = cls.name.lower().replace("controller", "").replace("ctrl", "")
            stem_clean = stem.replace("component", "").rstrip(".")
            if stem_clean in cls_lower or cls_lower in stem_clean:
                return cls
    return None


def _extract_link_source(directive_name: str, analysis) -> str:
    """
    Try to extract the link() function source from the original JS file.
    Falls back to a descriptive placeholder if not found.
    """
    for d in getattr(analysis, "directives", []) or []:
        if d.name == directive_name and getattr(d, "has_link", False):
            file_path = Path(d.file)
            if file_path.exists():
                source = file_path.read_text(encoding="utf-8", errors="ignore")
                # Try to extract the link: function(...) { ... } block
                match = re.search(
                    r'link\s*:\s*function\s*\([^)]*\)\s*\{',
                    source
                )
                if match:
                    # Extract from match start, balance braces
                    start = match.start()
                    depth = 0
                    for i, ch in enumerate(source[start:]):
                        if ch == "{":
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                            if depth == 0:
                                return source[start: start + i + 1]
    return "// link() source not available — migrate DOM manipulation manually"


# ─────────────────────────────────────────────────────────────────────────────
# Stage
# ─────────────────────────────────────────────────────────────────────────────

class AIAssistStage:
    """
    Post-processing AI stage. Runs after all deterministic rules have written
    their output to app_dir.

    Parameters
    ----------
    app_dir  : Path to the generated src/app directory
    analysis : AnalysisResult from the engine (used to look up original source)
    client   : AIClient instance (handles provider selection + API calls)
    """

    def __init__(self, app_dir: Path, analysis, client: AIClient):
        self.app_dir  = Path(app_dir)
        self.analysis = analysis
        self.client   = client

    def run(self) -> AIAssistResult:
        result = AIAssistResult()

        print("\n========== AIAssistStage.run() ==========")

        if not self.client.available:
            print("[AIAssist] No API key — skipping all AI tasks.")
            print("========== AIAssistStage DONE ==========\n")
            return result

        if not self.app_dir.exists():
            print(f"[AIAssist] Output dir not found: {self.app_dir}")
            print("========== AIAssistStage DONE ==========\n")
            return result

        self._run_pipe_completion(result)
        self._run_template_completion(result)
        self._run_link_migration(result)
        self._run_q_defer_migration(result)
        self._run_type_inference(result)

        print(f"\n[AIAssist] Summary:")
        print(f"  Pipes:     {result.pipes_completed} completed, "
              f"{result.pipes_skipped} skipped, {result.pipes_failed} failed")
        print(f"  Templates: {result.templates_completed} completed, "
              f"{result.templates_skipped} skipped, {result.templates_failed} failed")
        print(f"  Links:     {result.links_completed} completed, "
              f"{result.links_skipped} skipped, {result.links_failed} failed")
        print(f"  Total completed: {result.total_completed}")
        print("========== AIAssistStage DONE ==========\n")

        return result

    # ── Task 1: Pipe body completion ──────────────────────────────────────

    def _run_pipe_completion(self, result: AIAssistResult):
        print("\n[AIAssist] Task 1: Pipe transform() completion")
        pipe_files = sorted(self.app_dir.glob("*.pipe.ts"))

        if not pipe_files:
            print("[AIAssist]   No pipe files found — skipping")
            return

        for pipe_file in pipe_files:
            content = pipe_file.read_text(encoding="utf-8")

            # Skip if already completed (no stub marker)
            if _PIPE_STUB_MARKER not in content:
                print(f"[AIAssist]   SKIPPED (already complete): {pipe_file.name}")
                result.pipes_skipped += 1
                continue

            # Extract metadata
            pipe_name   = _extract_class_name(content) or pipe_file.stem.replace(".", " ").title()
            filter_name = _extract_pipe_name(content) or pipe_file.stem.split(".")[0]
            js_body     = _extract_pipe_filter_body(content)

            if not js_body:
                print(f"[AIAssist]   SKIPPED (no JS body to port): {pipe_file.name}")
                result.pipes_skipped += 1
                continue

            print(f"[AIAssist]   Completing: {pipe_file.name}  (filter: {filter_name})")

            prompt   = pipe_transform_prompt(pipe_name, filter_name, js_body, content)
            response = self.client.complete(prompt)

            if response is None:
                print(f"[AIAssist]   FAILED: {pipe_file.name}")
                result.pipes_failed += 1
                result.errors.append(f"pipe:{pipe_file.name}:api_failed")
                continue

            cleaned = clean_response(response, "code")
            if not cleaned.strip():
                print(f"[AIAssist]   FAILED (empty response): {pipe_file.name}")
                result.pipes_failed += 1
                continue

            # Safety check: response must still look like a pipe
            if "@Pipe" not in cleaned or "transform(" not in cleaned:
                print(f"[AIAssist]   FAILED (response lost @Pipe structure): {pipe_file.name}")
                result.pipes_failed += 1
                result.errors.append(f"pipe:{pipe_file.name}:bad_response")
                continue

            pipe_file.write_text(cleaned, encoding="utf-8")
            print(f"[AIAssist]   COMPLETED: {pipe_file.name}")
            result.pipes_completed += 1

    # ── Task 2: Stub template completion ─────────────────────────────────

    def _run_template_completion(self, result: AIAssistResult):
        print("\n[AIAssist] Task 2: Stub template completion")
        html_files = sorted(self.app_dir.glob("*.component.html"))

        if not html_files:
            print("[AIAssist]   No component HTML files found — skipping")
            return

        for html_file in html_files:
            content = html_file.read_text(encoding="utf-8")

            # Skip if already completed (no stub marker)
            if _TEMPLATE_STUB_MARKER not in content:
                print(f"[AIAssist]   SKIPPED (has real content): {html_file.name}")
                result.templates_skipped += 1
                continue

            # Find the matching .component.ts
            ts_file = html_file.with_suffix(".ts")
            if not ts_file.exists():
                print(f"[AIAssist]   SKIPPED (no .ts file): {html_file.name}")
                result.templates_skipped += 1
                continue

            ts_content = ts_file.read_text(encoding="utf-8")
            component_name = _extract_class_name(ts_content) or html_file.stem.replace(".component", "")

            # Find matching IR class for this component
            stem = html_file.stem.replace(".component", "")
            cls  = _map_stem_to_controller(stem, self.analysis)

            controller_name = cls.name if cls else f"{stem}Controller"
            _raw_props    = (getattr(cls, "scope_reads", []) or []) + (getattr(cls, "scope_writes", []) or []) if cls else []
            _raw_methods  = getattr(cls, "scope_methods", []) or [] if cls else []
            # scope_reads/writes may be dicts {name, line} or plain strings — normalise
            scope_props   = list(dict.fromkeys(_extract_name(x) for x in _raw_props   if _extract_name(x)))
            scope_methods = list(dict.fromkeys(_extract_name(x) for x in _raw_methods if _extract_name(x)))
            controller_js   = _extract_controller_js(self.analysis, controller_name)

            print(f"[AIAssist]   Completing: {html_file.name}  "
                  f"(controller: {controller_name}, props: {scope_props[:4]}...)")

            prompt   = stub_template_prompt(
                component_name, controller_name, controller_js,
                ts_content, scope_props, scope_methods
            )
            response = self.client.complete(prompt)

            if response is None:
                print(f"[AIAssist]   FAILED: {html_file.name}")
                result.templates_failed += 1
                result.errors.append(f"template:{html_file.name}:api_failed")
                continue

            cleaned = clean_response(response, "html")
            if not cleaned.strip():
                print(f"[AIAssist]   FAILED (empty response): {html_file.name}")
                result.templates_failed += 1
                continue

            # Safety check: must be HTML-like (contains < character)
            if "<" not in cleaned:
                print(f"[AIAssist]   FAILED (response not HTML): {html_file.name}")
                result.templates_failed += 1
                result.errors.append(f"template:{html_file.name}:bad_response")
                continue

            # Prepend a migration comment so it's traceable
            final = (
                f"<!-- AI-assisted migration from AngularJS {controller_name} -->\n"
                f"<!-- Review carefully before production use -->\n"
                f"{cleaned}\n"
            )
            html_file.write_text(final, encoding="utf-8")
            print(f"[AIAssist]   COMPLETED: {html_file.name}")
            result.templates_completed += 1

    # ── Task 3: Link function migration ───────────────────────────────────

    def _run_link_migration(self, result: AIAssistResult):
        print("\n[AIAssist] Task 3: Link function → ngAfterViewInit() migration")
        ts_files = sorted(self.app_dir.glob("*.component.ts"))

        if not ts_files:
            print("[AIAssist]   No component TS files found — skipping")
            return

        for ts_file in ts_files:
            content = ts_file.read_text(encoding="utf-8")

            # Only process files with the link warning comment
            if _LINK_STUB_MARKER not in content:
                result.links_skipped += 1
                continue

            # Skip if already migrated (implements AfterViewInit already present)
            if "AfterViewInit" in content and "ngAfterViewInit" in content and "TODO" not in content:
                print(f"[AIAssist]   SKIPPED (already migrated): {ts_file.name}")
                result.links_skipped += 1
                continue

            component_name = _extract_class_name(content) or ts_file.stem
            # Map back to directive name
            stem = ts_file.stem.replace(".component", "")
            directive_name = _find_directive_name(stem, self.analysis)
            link_source    = _extract_link_source(directive_name, self.analysis)

            print(f"[AIAssist]   Migrating link(): {ts_file.name}  (directive: {directive_name})")

            prompt   = link_function_prompt(directive_name, component_name, link_source, content)
            response = self.client.complete(prompt)

            if response is None:
                print(f"[AIAssist]   FAILED: {ts_file.name}")
                result.links_failed += 1
                result.errors.append(f"link:{ts_file.name}:api_failed")
                continue

            cleaned = clean_response(response, "code")
            if not cleaned.strip():
                print(f"[AIAssist]   FAILED (empty response): {ts_file.name}")
                result.links_failed += 1
                continue

            # Safety check: must still look like an Angular component
            if "@Component" not in cleaned or "export class" not in cleaned:
                print(f"[AIAssist]   FAILED (lost @Component): {ts_file.name}")
                result.links_failed += 1
                result.errors.append(f"link:{ts_file.name}:bad_response")
                continue

            ts_file.write_text(cleaned, encoding="utf-8")
            print(f"[AIAssist]   COMPLETED: {ts_file.name}")
            result.links_completed += 1

    def _run_q_defer_migration(self, result: AIAssistResult):
        print("\n[AIAssist] Task 4: $q.defer() → Observable migration")

        ts_files = sorted(self.app_dir.glob("*.ts"))

        for ts_file in ts_files:
            content = ts_file.read_text(encoding="utf-8")

            if "$q.defer" not in content:
                continue

            print(f"[AIAssist]   Migrating $q.defer: {ts_file.name}")

            prompt = f"""
    Rewrite this Angular TypeScript code to replace AngularJS $q.defer() patterns
    with RxJS Observable equivalents.

    Rules:
    - Use new Observable(...)
    - Use observer.next / observer.error / observer.complete
    - Do not change unrelated code

    Code:
    {content}

    Output ONLY the rewritten TypeScript file.
    """

            response = self.client.complete(prompt)
            if not response:
                continue

            cleaned = clean_response(response)
            if "Observable" not in cleaned:
                continue

            ts_file.write_text(cleaned, encoding="utf-8")
            print(f"[AIAssist]   COMPLETED: {ts_file.name}")

    def _run_type_inference(self, result: AIAssistResult):
        print("\n[AIAssist] Task 5: Type inference for component properties")

        ts_files = sorted(self.app_dir.glob("*.component.ts"))

        for ts_file in ts_files:
            content = ts_file.read_text(encoding="utf-8")

            if "!: any;" not in content:
                continue

            print(f"[AIAssist]   Inferring types: {ts_file.name}")

            prompt = f"""
    Improve the TypeScript types in this Angular component.

    Rules:
    - Replace fields typed as `any`
    - Infer types from usage
    - Keep code structure unchanged
    - Do not modify decorators or methods

    Code:
    {content}

    Output ONLY the full improved TypeScript file.
    """

            response = self.client.complete(prompt)

            if response:
                cleaned = clean_response(response)

                if "export class" in cleaned:
                    ts_file.write_text(cleaned, encoding="utf-8")
                    print(f"[AIAssist]   COMPLETED: {ts_file.name}")
                    return

            # ---- fallback if AI unavailable ----

            print(f"[AIAssist]   fallback inference: {ts_file.name}")

            cleaned = content

            cleaned = cleaned.replace("!: any;", "!: unknown;")
            cleaned = cleaned.replace(": any;", ": unknown;")

            ts_file.write_text(cleaned, encoding="utf-8")
            print(f"[AIAssist]   COMPLETED: {ts_file.name}")


# ─────────────────────────────────────────────────────────────────────────────
# File-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_name(x) -> Optional[str]:
    """
    Normalise a scope entry to a plain string name.
    Handles: plain str, dict with 'name' key, objects with .name attribute.
    """
    if isinstance(x, str):
        return x or None
    if isinstance(x, dict):
        return x.get("name") or x.get("key") or None
    return getattr(x, "name", None) or None


def _extract_class_name(ts_content: str) -> Optional[str]:
    """Extract 'export class FooBar' from TypeScript content."""
    match = re.search(r"export\s+class\s+(\w+)", ts_content)
    return match.group(1) if match else None


def _extract_pipe_name(ts_content: str) -> Optional[str]:
    """Extract pipe name from @Pipe({ name: 'foo' })."""
    match = re.search(r"@Pipe\(\{[^}]*name\s*:\s*['\"]([^'\"]+)['\"]", ts_content)
    return match.group(1) if match else None


def _find_directive_name(stem: str, analysis) -> str:
    """Find original AngularJS directive name from file stem."""
    for d in getattr(analysis, "directives", []) or []:
        d_stem = re.sub(r"[^a-z0-9]", "", d.name.lower())
        if d_stem == stem or stem in d_stem or d_stem in stem:
            return d.name
    # Fallback: convert stem to camelCase
    return "".join(word.capitalize() for word in re.split(r"[-_]", stem))