# ngjs-mini-dashboard (Benchmark 8)

Large-ish AngularJS mini-dashboard with routing, shared state, filters, and mixed anti-patterns.

## Covers
- ngRoute routing + views
- Multiple controllers
- Shared service state across routes
- Filters in templates
- Watchers + two-way binding + service coupling anti-patterns

## Expected Migration Risks
- Router migration (ngRoute → Angular Router)
- Shared mutable service state
- Watchers on service data
- Filter → pipe conversion
- Cross-view state preservation

## Validation
- Integration test for shared state across routes
- Snapshot of routes + state + anti-pattern topology

## Failure Means
EVUA cannot handle real-world AngularJS dashboards or complex migration graphs.
