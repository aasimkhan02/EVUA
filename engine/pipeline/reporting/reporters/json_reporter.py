import json

class JSONReporter:
    def render(self, analysis, patterns, transformation, risk, validation=None):
        risk_by_change, reason_by_change = risk

        id_to_name = {}
        id_to_file = {}

        for m in analysis.modules:
            for c in m.classes:
                id_to_name[c.id] = c.name
                id_to_file[c.id] = m.name

        def extract_output_path(reason: str):
            if not reason:
                return None
            if "written to " in reason:
                return reason.split("written to ")[-1]
            if "wired into Angular app at " in reason:
                return reason.split("wired into Angular app at ")[-1]
            if "files:" in reason:
                return reason.split("files:")[-1].strip()
            return None

        report = {
            "angular_workspace": "out/angular-app",
            "controllers": [
                {
                    "id": cid,
                    "name": id_to_name.get(cid, "unknown"),
                    "file": id_to_file.get(cid, "unknown"),
                }
                for cid in patterns.roles_by_node.keys()
            ],
            "changes": [
                {
                    "before_id": c.before_id,
                    "before_name": id_to_name.get(c.before_id, "unknown"),
                    "source_file": id_to_file.get(c.before_id, "unknown"),
                    "after_id": c.after_id,
                    "reason": c.reason,
                    "output_path": extract_output_path(c.reason),
                    "risk": str(risk_by_change.get(c.id)),
                    "risk_reason": reason_by_change.get(c.id, ""),
                    "build_passed": validation.get("tests_passed") if validation else None,
                    "snapshot_passed": validation.get("snapshot_passed") if validation else None,
                }
                for c in transformation.changes
            ],
            "validation": validation or {},
        }

        return json.dumps(report, indent=2)
