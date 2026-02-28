from pipeline.patterns.base import PatternDetector
from pipeline.patterns.roles import SemanticRole
from pipeline.patterns.confidence import Confidence


class ServiceDetector(PatternDetector):
    """
    Detects AngularJS services, factories, and provider classes.

    Matches class names ending with:
      - Service / Svc   → Angular @Injectable()
      - Factory         → Angular @Injectable() (factory pattern maps cleanly)
      - Provider        → Angular @Injectable() with useFactory pattern

    Also detects standalone directive classes that js.py registered as
    RawController (some codebases use class-style directives).
    """

    _SERVICE_SUFFIXES  = ("service", "svc")
    _FACTORY_SUFFIXES  = ("factory",)
    _PROVIDER_SUFFIXES = ("provider",)

    def extract(self, analysis):
        matches = []

        for m in analysis.modules:
            for c in m.classes:
                name_lower = c.name.lower()

                if any(name_lower.endswith(s) for s in self._SERVICE_SUFFIXES):
                    matches.append((
                        c,
                        SemanticRole.SERVICE,
                        Confidence(0.95, f"Service detected: {c.name}")
                    ))

                elif any(name_lower.endswith(s) for s in self._FACTORY_SUFFIXES):
                    matches.append((
                        c,
                        SemanticRole.SERVICE,
                        Confidence(0.90, f"Factory detected (maps to @Injectable): {c.name}")
                    ))

                elif any(name_lower.endswith(s) for s in self._PROVIDER_SUFFIXES):
                    matches.append((
                        c,
                        SemanticRole.SERVICE,
                        Confidence(0.85, f"Provider detected (maps to @Injectable): {c.name}")
                    ))

        return matches