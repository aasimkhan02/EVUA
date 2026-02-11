# ngjs-async-http (Benchmark 6)

AngularJS app with $http + $q async chains and UI side effects.

## Covers
- $http usage
- $q promise chains
- then/catch/finally flows
- UI loading + error state side effects
- Async service abstraction

## Expected Migration Risks
- $http → HttpClient conversion
- $q → native Promise / async/await
- Digest-cycle timing changes
- Error propagation semantics
- Side effects ordering

## Validation
- Async unit tests with mocked service
- Snapshot of async flow topology + component state

## Failure Means
EVUA cannot correctly lift async flows or preserve side-effect ordering.
