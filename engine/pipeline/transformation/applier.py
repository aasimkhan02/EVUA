class RuleApplier:
    def __init__(self, rules):
        self.rules = rules

    def apply_all(self, analysis, patterns):
        changes = []
        for rule in self.rules:
            changes.extend(rule.apply(analysis, patterns))
        return changes
