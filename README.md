# 🚀 EVUA — Automated Legacy Upgrade Engine  
**AngularJS (1.x) → Modern Angular (v15+)**

EVUA is an automated modernization engine that migrates legacy AngularJS (1.x) codebases to modern Angular.  
It converts most application logic automatically, flags risky or ambiguous cases for manual review, and measures accuracy using a benchmark harness.

**🎯 Goal:** 80–90% automated migration for real-world AngularJS projects.

---

## ✨ What EVUA Does

EVUA runs a full end-to-end pipeline on a legacy repo:

> **Ingestion → Analysis → Pattern Detection → Transformation → Risk Assessment → Validation → Reporting → Benchmarking**

---

## ✅ Working Features

| Feature | Status |
|--------|--------|
| Controllers → Angular Components | ✅ |
| Services / Factories → Angular Injectable Services | ✅ |
| `$http` → `HttpClient` | ✅ |
| Simple `$scope.$watch` → RxJS (`BehaviorSubject`) | ✅ |
| Angular workspace scaffold | ✅ |
| JSON + Markdown reports | ✅ |
| Benchmark harness | ✅ |
| Risk classification (SAFE / RISKY / MANUAL) | ✅ |

---

## ⚠️ In Progress

| Feature | Status |
|--------|--------|
| HTML template generation (`.component.html`) | 🚧 |
| Routing module generation (`app-routing.module.ts`) | 🚧 |
| Directive detection | 🚧 |
| Directive auto-migration | ⏳ |
| Naming normalization | 🚧 |
| Deep watcher handling | ⏳ |
| Complex template binding migration | ⏳ |

---

## 📊 Current Accuracy (Benchmarks)

| Metric | Current Result |
|--------|----------------|
| Auto coverage | ~100% |
| Manual recall | ~100% (directives pending) |
| File accuracy | ~33% – 60% |
| Validation | ❌ (no real tests yet) |

**Interpretation:**  
EVUA migrates the right things, but does not yet generate all required Angular files.

**📈 Project status:** ~75% complete (MVP)

---

## 🧠 Architecture Overview

```
engine/
├── .gitignore
├── cli.py
├── package-lock.json
├── __init__.py
│
├── benchmarks/
│   └── angularjs/
│       ├── bench-02-multi-service/
│       ├── bench-03-directive-hazard/
│       ├── bench-04-nested-scope/
│       ├── bench-05-mixed-realistic/
│       └── evua-benchmark-01/
│
├── evaluation/
│   ├── config.py
│   ├── harness.py
│   ├── metrics.py
│   ├── reporters.py
│   ├── runners.py
│   └── schemas.py
│
├── ir/
│   ├── behavior_model/
│   ├── code_model/
│   ├── dependency_model/
│   ├── migration_model/
│   ├── template_model/
│   └── tests/
│
├── orchestration/
│   ├── pipeline_runner.py
│   ├── progress_tracker.py
│   ├── rollback_manager.py
│   ├── stage_controller.py
│   └── __init__.py
│
├── out/
│   └── angular-app/          # Generated Angular workspace output
│
├── pipeline/
│   ├── ai/
│   │   └── adapters/
│   │       └── openai.py
│   │
│   ├── analysis/
│   │   └── analyzers/
│   │       ├── html.py
│   │       ├── js.py
│   │       └── py.py
│   │
│   ├── ingestion/
│   ├── patterns/
│   │   └── detectors/angularjs/
│   │       ├── controller_detector.py
│   │       ├── http_detector.py
│   │       ├── service_detector.py
│   │       ├── simple_watch_detector.py
│   │       └── template_binding_detector.py
│   │
│   ├── reporting/
│   │   └── reporters/
│   │       ├── json_reporter.py
│   │       └── markdown_reporter.py
│   │
│   ├── risk/
│   │   └── rules/angularjs/
│   │       ├── template_binding_risk.py
│   │       └── watcher_risk.py
│   │
│   ├── transformation/
│   │   └── rules/angularjs/
│   │       ├── controller_to_component.py
│   │       ├── http_to_httpclient.py
│   │       ├── service_to_injectable.py
│   │       └── simple_watch_to_rxjs.py
│   │
│   ├── validation/
│   │   └── runners/
│   │       ├── lint.py
│   │       └── tests.py
│   │
│   └── tests/
│
└── reports/
```

## ▶️ Usage

### Run migration

```bash
python engine/cli.py path/to/angularjs-repo
```

## Outputs:

Migrated Angular app: out/angular-app/
Report: .evua_report.json, .evua_report.md

## Run benchmarks
```bash
python -m evaluation.harness
```

## Outputs:

Metrics per benchmark
Reports in /reports

## 🧪 Metrics Explained

| Metric        | Meaning |
|---------------|---------|
| auto_coverage | % of expected components/services auto-migrated |
| manual_recall | % of expected manual cases correctly flagged |
| file_accuracy | % of expected Angular files generated |
| validation    | Snapshot/test validation result |

---

## 🛠️ Roadmap

### MVP Completion

- [ ] Generate `.component.html` files  
- [ ] Always generate `app-routing.module.ts`  
- [ ] Directive detection + manual-risk flag  
- [ ] Naming normalization  
- [ ] File accuracy ≥ 85%  

### Next Phase

- [ ] `$routeProvider` → Angular Router  
- [ ] Filters → Pipes  
- [ ] Template binding rewrite  
- [ ] Deep `$scope.$watch` handling  
- [ ] `ng build` passes on output  

---

## 🤝 Contributing

Good first contributions:

- Add AngularJS detectors (directives, filters)  
- Add transformation rules  
- Improve Angular file generation  
- Add benchmarks  
- Improve risk heuristics  

PRs welcome.

---

## 📌 TL;DR

- EVUA already migrates most AngularJS logic automatically  
- The pipeline is real and benchmarked  
- Accuracy is measurable  
- Remaining work is mostly Angular scaffolding + directives  
- This is a real modernization engine, not a toy script  
