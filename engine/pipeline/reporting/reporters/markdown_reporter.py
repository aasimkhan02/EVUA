from pipeline.risk.result import RiskResult


class MarkdownReporter:
    def render(self, analysis, patterns, transformation, risk, validation=None):
        # risk is a RiskResult dataclass — not a tuple
        if isinstance(risk, RiskResult):
            risk_by_change   = risk.risk_by_change_id
            reason_by_change = risk.reason_by_change_id
        else:
            # Graceful fallback for legacy callers passing (dict, dict) tuple
            risk_by_change, reason_by_change = risk

        id_to_name = {}
        id_to_file = {}
        for m in analysis.modules:
            for c in m.classes:
                id_to_name[c.id] = c.name
                id_to_file[c.id] = m.name   # Module.name holds the file path

        def extract_output_path(reason: str):
            if not reason:
                return "N/A"
            if "written to " in reason:
                return reason.split("written to ")[-1]
            if "wired into Angular app at " in reason:
                return reason.split("wired into Angular app at ")[-1]
            if "files:" in reason:
                return reason.split("files:")[-1].strip()
            return "N/A"

        lines = ["# EVUA Migration Report\n"]

        lines.append("## Controllers Detected")
        for cid in patterns.roles_by_node.keys():
            name = id_to_name.get(cid, "unknown")
            file = id_to_file.get(cid, "unknown")
            lines.append(f"- **{name}** (`{file}`)")

        lines.append("\n## Proposed Changes")
        for c in transformation.changes:
            name       = id_to_name.get(c.before_id, "unknown")
            file       = id_to_file.get(c.before_id, "unknown")
            risk_level = risk_by_change.get(c.id, "unknown")
            reason     = reason_by_change.get(c.id, "")
            out_path   = extract_output_path(c.reason)

            build    = validation.get("tests_passed")    if validation else None
            snapshot = validation.get("snapshot_passed") if validation else None

            lines.append(
                f"- **{name}** (`{file}`) → Angular Component  \n"
                f"  Output: `{out_path}`  \n"
                f"  Risk: **{risk_level}** — {reason}  \n"
                f"  Build: **{build}**, Snapshot: **{snapshot}**"
            )

        if validation:
            lines.append("\n## Validation Summary")
            lines.append(f"- Tests passed: **{validation.get('tests_passed')}**")
            lines.append(f"- Snapshot passed: **{validation.get('snapshot_passed')}**")
            for f in validation.get("failures", []):
                lines.append(f"  - ❌ {f}")

        lines.append("\n## Run the migrated Angular app")
        lines.append("```bash")
        lines.append("cd out/angular-app")
        lines.append("npm install")
        lines.append("ng serve")
        lines.append("```")

        return "\n".join(lines)