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

        report = {
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
                    "output_path": c.reason.split("written to ")[-1] if "written to" in c.reason else None,
                    "risk": str(risk_by_change.get(c.id)),
                    "risk_reason": reason_by_change.get(c.id, ""),
                }
                for c in transformation.changes
            ],
        }

        if validation:
            report["validation"] = validation

        return json.dumps(report, indent=2)
