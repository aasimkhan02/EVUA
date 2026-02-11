class MarkdownReporter:
    def render(self, analysis, patterns, transformation, risk, validation=None):
        risk_by_change, reason_by_change = risk

        id_to_name = {}
        id_to_file = {}

        for m in analysis.modules:
            for c in m.classes:
                id_to_name[c.id] = c.name
                id_to_file[c.id] = m.name

        lines = ["# EVUA Migration Report\n"]

        lines.append("## Controllers Detected")
        for cid in patterns.roles_by_node.keys():
            name = id_to_name.get(cid, "unknown")
            file = id_to_file.get(cid, "unknown")
            lines.append(f"- **{name}** (`{file}`)")

        lines.append("\n## Proposed Changes")
        for c in transformation.changes:
            name = id_to_name.get(c.before_id, "unknown")
            file = id_to_file.get(c.before_id, "unknown")
            risk_level = risk_by_change.get(c.id)
            reason = reason_by_change.get(c.id, "")
            out_path = c.reason.split("written to ")[-1] if "written to" in c.reason else "N/A"

            lines.append(
                f"- **{name}** (`{file}`) → Angular Component  \n"
                f"  Output: `{out_path}`  \n"
                f"  Risk: **{risk_level}** — {reason}"
            )

        if validation:
            lines.append("\n## Validation")
            lines.append(f"- Tests passed: **{validation.get('tests_passed')}**")
            for f in validation.get("failures", []):
                lines.append(f"  - ❌ {f}")

        return "\n".join(lines)
