import json
from pipeline.risk.result import RiskResult


class JSONReporter:
    def _to_json_safe(self, obj):
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, list):
            return [self._to_json_safe(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self._to_json_safe(v) for k, v in obj.items()}
        if hasattr(obj, "__dict__"):
            return {k: self._to_json_safe(v) for k, v in obj.__dict__.items()}
        return str(obj)

    def render(self, analysis, patterns, transformation, risk, validation=None):
        # risk is a RiskResult dataclass — not a tuple
        if isinstance(risk, RiskResult):
            risk_by_change    = risk.risk_by_change_id
            reason_by_change  = risk.reason_by_change_id
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
                    "before_id":      c.before_id,
                    "before_name":    id_to_name.get(c.before_id, "unknown"),
                    "source_file":    id_to_file.get(c.before_id, "unknown"),
                    "after_id":       c.after_id,
                    "reason":         c.reason,
                    "output_path":    extract_output_path(c.reason),
                    "risk":           str(risk_by_change.get(c.id, "unknown")),
                    "risk_reason":    reason_by_change.get(c.id, ""),
                    "build_passed":   validation.get("tests_passed")    if validation else None,
                    "snapshot_passed":validation.get("snapshot_passed") if validation else None,
                }
                for c in transformation.changes
            ],
            "validation": validation or {},
        }

        return json.dumps(self._to_json_safe(report), indent=2)