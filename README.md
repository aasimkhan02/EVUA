🚀 EVUA — Automated Legacy Upgrade Engine

AngularJS (1.x) → Modern Angular (v15+)

EVUA is an automated modernization engine that migrates legacy AngularJS (1.x) codebases to modern Angular.
It converts most application logic automatically, flags risky or ambiguous cases for manual review, and measures accuracy using a benchmark harness.

🎯 Goal: 80–90% automated migration for real-world AngularJS projects.

✨ What EVUA Does (Today)

EVUA runs a full end-to-end pipeline on a legacy repo:

Ingestion → Analysis → Pattern Detection → Transformation → Risk Assessment → Validation → Reporting → Benchmarking

✅ Currently Supported (Working)

Controllers → Angular Components

Services / Factories → Angular Injectable Services

$http → HttpClient

Simple $scope.$watch → RxJS (BehaviorSubject)

Angular workspace scaffold (out/angular-app)

Risk classification: SAFE / RISKY / MANUAL

JSON + Markdown reports (.evua_report.json, .evua_report.md)

Benchmark harness with measurable accuracy metrics

⚠️ In Progress (Active Work)

HTML template generation (.component.html)

Routing module generation (app-routing.module.ts)

Directive detection + manual-risk classification

Naming normalization (ConfigFactory → configfactory.service.ts)

More complete risk rules (deep watches, complex bindings)

📊 Current Accuracy (Benchmarks)

On internal AngularJS benchmarks:

Auto coverage: ~100%

Manual recall: ~100% (directives pending)

File accuracy: ~33% – 60% (missing HTML + routing files)

Validation: currently failing (no real tests wired yet)

Interpretation:
EVUA correctly migrates what should be migrated, but is still improving how complete the generated Angular project is.

📈 Project status: ~75% complete (MVP stage)

🧠 How It Works (Architecture)
engine/
  ingestion/        # reads legacy repo
  analysis/         # builds IR (controllers, services, http, watchers)
  patterns/         # detects AngularJS patterns
  transforms/       # migration rules (controller → component, etc.)
  risk/             # SAFE / RISKY / MANUAL classification
  reporting/        # JSON + Markdown reports
  cli.py            # entrypoint

evaluation/
  harness.py        # runs benchmarks
  metrics.py        # accuracy metrics
  schemas.py        # report schemas
  reporters.py      # benchmark output

benchmarks/
  angularjs/        # test repos + expected outputs

EVUA converts legacy code into an Intermediate Representation (IR).
All transformations and risk decisions operate on this IR, making the engine extensible to other tech stacks later.

▶️ Usage
Run EVUA on a project
python engine/cli.py path/to/angularjs-repo

Outputs:

Migrated Angular workspace: out/angular-app/

Report: .evua_report.json, .evua_report.md

Run benchmarks + accuracy evaluation
python -m evaluation.harness

Outputs:

Per-benchmark metrics

Reports in /reports

🧪 Metrics Explained
Metric	Meaning
auto_coverage	% of expected components/services auto-migrated
manual_recall	% of expected manual cases correctly flagged
file_accuracy	% of expected Angular files generated
validation	Whether tests/snapshots passed

These metrics make progress measurable and prevent regressions.

🛠️ Roadmap
Short-Term (MVP Completion)

 Generate .component.html files

 Always generate app-routing.module.ts

 Directive detection + manual-risk flag

 Naming normalization

 Improve file accuracy to 85%+

Mid-Term

 $routeProvider → Angular Router

 Filters → Pipes

 Template binding rewrite

 Deep $scope.$watch handling

 Buildable Angular output (ng build)

Long-Term (EVUA Vision)

EVUA is designed to support multi-stack modernization:

AngularJS → Angular

Python 2 → Python 3

Java 8 → Java 17

CommonJS → ES Modules

.NET Framework → modern .NET

AngularJS is the proving ground.

🤝 Contributing

Good first issues:

Add new pattern detectors (directives, filters)

Add new transformation rules

Improve Angular file generation

Add new benchmarks

Improve risk heuristics

Improve template conversion

PRs welcome.

📌 TL;DR

EVUA already migrates most AngularJS logic automatically

The pipeline is stable and benchmarked

Accuracy is measurable

Remaining work is mainly Angular scaffolding + directives

This is a real modernization engine, not a demo script