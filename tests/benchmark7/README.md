# ngjs-legacy-directives (Benchmark 7)

Legacy AngularJS app using directives, transclusion, and scope inheritance.

## Covers
- Custom directives (restrict: E)
- Transclusion (ng-transclude)
- Isolated scope with @ bindings
- Implicit parent-scope access via transcluded content

## Expected Migration Risks
- Directive → Component rewrite
- Transclusion → content projection mapping
- Scope inheritance semantics loss
- Hidden coupling between parent and directive template

## Validation
- Unit test for transcluded content behavior
- Snapshot of directive features + parent state

## Failure Means
EVUA cannot safely migrate directives or reason about scope boundaries.
