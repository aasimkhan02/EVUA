# ngjs-medium-multi (Benchmark 3)

Medium-complexity AngularJS app with multiple controllers and shared services.

## Covers
- Multiple controllers in one module
- Service + factory usage
- DI graph across files
- Template conditionals (ng-if)
- Event handlers (ng-click)
- Form state (ng-model)

## Expected Migration Risks
- Service ↔ factory normalization
- Cross-controller service coupling
- ng-if → structural directive conversion
- Form state migration (ng-model removal)

## Validation
- Unit tests for both controllers
- Snapshot-based state validation

## Failure Means
EVUA cannot correctly build cross-file semantic graphs or preserve shared state.
