from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.patterns.roles import SemanticRole

class ServiceToInjectableRule:
    def apply(self, analysis, patterns):
        changes = []
        for node_id, roles in patterns.roles_by_node.items():
            if SemanticRole.SERVICE in roles:
                changes.append(
                    Change(
                        before_id=node_id,
                        after_id="injectable_" + node_id,
                        source=ChangeSource.RULE,
                        reason="Service → @Injectable()"
                    )
                )
        return changes
