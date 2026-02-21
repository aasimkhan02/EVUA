# EVUA Benchmark — evua-benchmark-01

## What this tests

A realistic AngularJS application covering every migration pattern your pipeline handles:

| Pattern | Location | Expected outcome |
|---------|----------|-----------------|
| `UserController` + shallow `$watch` | `src/app.js` | Auto-migrated → `user.component.ts` + BehaviorSubject |
| `ProductController` + deep `$watch` + `$q.defer` | `src/app.js` | MANUAL — flagged, not auto-migrated |
| `AuthService` | `src/app.js` | Auto-migrated → `authservice.service.ts` |
| `$http.get /api/users` | `UserController` | `load_get()` injected into user component |
| `$http.get /api/products` | `ProductController` | `load_get()` injected into product component |
| `$http.post /api/checkout` | `ProductController` | `load_post()` injected |
| `$http.post /api/login` | `AuthService` | Migrated via HttpToHttpClientRule |
| ng-repeat, ng-if, ng-click | `src/index.html` | Detected by HTMLAnalyzer |

## Directory layout

```
evua-benchmark-01/
  repo/
    src/
      app.js          ← AngularJS source (the input)
      index.html      ← HTML templates
    snapshots/
      before.json     ← initial component state
      after.json      ← expected state post-migration (same for initial state)
  expected.json         ← auto_modernized / manual_required ground truth
  expected_risk.json    ← SAFE / RISKY / MANUAL classification ground truth
  expected_changes.json ← generated files list + CI gate thresholds
```

## Expected evaluation scores (perfect run)

| Metric | Expected |
|--------|----------|
| `auto_coverage` | ≥ 0.66 (2/3 nodes auto-migrated) |
| `manual_recall` | 1.00 (ProductController flagged) |
| `file_accuracy` | ≥ 0.80 (most files generated) |
| `risk.MANUAL precision` | 1.00 |
| `risk.SAFE precision` | 1.00 |
| `meets_min_auto_coverage` | ✅ |
| `meets_manual_ratio` | ✅ |

## How to run

```bash
# From engine/ root:
python cli.py benchmarks/angularjs/evua-benchmark-01/repo

# Or via evaluation harness (runs all benchmarks):
python -m evaluation.harness
```

## Notes

- `expected_validation: false` because `ng test` requires Node/Angular CLI installed.
  The snapshot comparison is the real validation signal in eval environments.
- Risk IDs in `expected_risk.json` use controller/service **names** not UUIDs,
  because UUIDs are generated at runtime. The metrics compare sets of names via
  the `before_name` field in the report.