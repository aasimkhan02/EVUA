# ngjs-crud-simple (Benchmark 2)

Simple AngularJS CRUD app with controller + service + DI + ng-repeat.

## Covers
- Service detection and DI wiring
- Controller ↔ service dependency graph
- ng-repeat template loops
- Event bindings (ng-click, ng-submit)
- Stateful mutations

## Expected Migration Risks
- Service to provider migration
- Two-way binding removal (ng-model)
- List rendering conversion
- Change detection semantics

## Validation
- Jasmine tests for CRUD operations
- JSON snapshots for semantic state validation

## Failure Means
EVUA cannot correctly lift services, map DI, or preserve list semantics.
