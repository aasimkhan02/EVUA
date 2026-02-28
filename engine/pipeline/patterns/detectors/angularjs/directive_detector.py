from pipeline.patterns.base import PatternDetector
from pipeline.patterns.roles import SemanticRole
from pipeline.patterns.confidence import Confidence


class DirectiveDetector(PatternDetector):
    """
    Detects AngularJS directives in the analysis result.

    js.py already parses .directive() calls and populates analysis.directives
    (raw_directives forwarded through AnalysisResult). This detector surfaces
    them into the pattern layer so DirectiveRiskRule can assess them.

    Each directive is identified by its RawDirective.id and flagged with:
      - SemanticRole.DIRECTIVE            always
      - SemanticRole.COMPILE_USAGE        if has_compile
      - SemanticRole.TEMPLATE_BINDING     if has_link or transclude (complex DOM)
    """

    def extract(self, analysis):
        matches = []

        directives = getattr(analysis, "directives", []) or []

        for d in directives:
            # Base role — every directive requires manual Angular migration
            matches.append((
                d,
                SemanticRole.DIRECTIVE,
                Confidence(1.0, f"AngularJS directive detected: {d.name}")
            ))

            # Compile usage — hardest migration, requires complete rewrite
            if getattr(d, "has_compile", False):
                matches.append((
                    d,
                    SemanticRole.COMPILE_USAGE,
                    Confidence(1.0, "Directive uses $compile — DOM manipulation must be rewritten")
                ))

            # Link function or transclusion — complex lifecycle coupling
            if getattr(d, "has_link", False) or getattr(d, "transclude", False):
                matches.append((
                    d,
                    SemanticRole.TEMPLATE_BINDING,
                    Confidence(0.9, "Directive has link/transclude — non-trivial DOM coupling")
                ))

        return matches