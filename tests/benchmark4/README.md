# ngjs-watchers-heavy (Benchmark 4)

AngularJS app with heavy $scope mutation and multiple $watch listeners.

## Covers
- Shallow and deep $watch
- Nested object mutation
- Watchers mutating other scope fields
- Digest-cycle-dependent behavior

## Expected Migration Risks
- $watch → computed/effect translation
- Deep watch semantics loss
- Hidden coupling via mutation inside watchers
- Infinite-loop risks post-migration

## Validation
- Jasmine tests asserting watcher-driven behavior
- Snapshot of watcher topology + component state

## Failure Means
EVUA cannot model AngularJS reactivity or preserve watcher semantics.
