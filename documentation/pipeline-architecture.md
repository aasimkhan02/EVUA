# EVUA Pipeline Architecture

## Overview

The `pipeline/` module is the execution backbone of EVUA.  
It orchestrates the full legacy modernization lifecycle — from raw repository input to validated Angular output and structured migration reports.

The pipeline is stage-driven and strictly layered:
Repository
    ↓
Ingestion
    ↓
Analysis
    ↓
Pattern Detection
    ↓
Transformation
    ↓
Risk Assessment
    ↓
Validation
    ↓
Reporting


Each stage:

- Has a clearly defined interface  
- Produces a structured result object  
- Does not depend on implementation details of other stages  
- Can be extended independently  

---

# 1. Ingestion

## Purpose

Convert a filesystem repository into structured source inputs for analysis.

## Responsibilities

- Traverse project directory  
- Identify relevant source files  
- Classify file types (JS, HTML, TS, etc.)  
- Normalize file metadata  
- Package sources for downstream analysis  

## Output

Structured ingestion result containing:

- Source objects  
- File type classification  
- Content access handles  

Ingestion performs **no semantic reasoning** — it only prepares input for analysis.

---

# 2. Analysis

## Purpose

Extract structured knowledge from source files.

This stage converts raw source code into structured IR-backed data.

## Responsibilities

- Parse JavaScript / TypeScript  
- Parse AngularJS templates (HTML)  
- Identify:
  - Controllers  
  - Services  
  - Directives  
  - HTTP calls  
  - `$watch` usage  
  - Scope writes  
  - `$compile` usage  
  - Template bindings  
- Build intermediate representation (IR)  
- Capture behavioral metadata  

## Output

`AnalysisResult` containing:

- `modules`  
- `classes`  
- `directives`  
- `http_calls`  
- `watches`  
- `templates`  
- `raw_templates`  

This stage focuses on **what exists** in the codebase.

It does **not yet reason about migration semantics**.

---

# 3. Pattern Detection

## Purpose

Convert raw analysis findings into semantic migration roles.

Raw AST facts are elevated into meaningful migration abstractions.

## Core Concept

AST facts → Semantic Roles


## Examples of Roles

- `CONTROLLER`
- `SERVICE`
- `DIRECTIVE`
- `HTTP_CALL`
- `SHALLOW_WATCH`
- `TEMPLATE_BINDING`
- `EVENT_HANDLER`
- `COMPILE_USAGE`

## Responsibilities

- Map analysis findings to semantic roles  
- Assign confidence scores  
- Normalize detection outputs  

## Output

`PatternResult`:

- `roles_by_node`  
- `confidence_by_node`  

Pattern detection isolates framework-specific complexity and converts it into migration-ready semantics.

---

# 4. Transformation

## Purpose

Generate a fully functional Angular project from AngularJS input.

This stage executes deterministic migration rules.

## Core Mechanism

- Rule-based system  
- Each rule implements `apply(analysis, patterns)`  
- Produces structured `Change` objects  
- Writes files idempotently  

---

## Major Transformation Rules

### ControllerToComponent

- Converts AngularJS controllers → Angular components  
- Generates `.component.ts`  
- Migrates template  
- Updates Angular routing  

---

### ServiceToInjectable

- Converts AngularJS services/factories → Angular `@Injectable`  
- Generates `.service.ts`  

---

### HttpToHttpClient

- Converts `$http` → `HttpClient`  
- Adds `HttpClientModule`  
- Generates service/component methods  
- Handles `$q.defer` with manual stubs  

---

### SimpleWatchToRxjs

- Converts shallow `$watch` → `BehaviorSubject`  
- Injects RxJS imports  
- Adds reactive properties  

---

### TemplateMigrator

- Rewrites `ng-*` attributes to Angular syntax  
- Converts filters to pipes  
- Flags unsupported patterns with TODO comments  

---

### Angular Project Scaffold

Generates full Angular workspace:

- `angular.json`  
- `package.json`  
- `tsconfig` files  
- `app.module.ts`  
- Routing module  

Ensures idempotency.

---

## Output

`TransformationResult`:

- `changes` (list of `Change` objects)  
- `new_ir_nodes` (optional)  

This stage transforms **structure**, not just syntax.

---

# 5. Risk Assessment

## Purpose

Evaluate migration safety and behavioral complexity.

Risk is assessed **after transformation** to reflect actual generated output.

---

## Risk Levels

- `SAFE`
- `RISKY`
- `MANUAL`

---

## Signals Evaluated

### Structural Signals

- Directive presence  
- Complex template bindings  

### Behavioral Signals

- Deep `$watch`  
- `$compile` usage  
- Nested scope inheritance  
- Heavy `$scope` mutation  

### Async Signals

- `$q.defer`  
- Promise chains  

---

## Key Rules

- `DirectiveRiskRule` → Always `MANUAL`  
- `WatcherRiskRule` → Deep behavior → `MANUAL`  
- `TemplateBindingRiskRule` → Complex binding → `RISKY`  
- `ServiceRiskRule` → Baseline `SAFE`  

---

## Output

`RiskResult`:

- `risk_by_change_id`  
- `reason_by_change_id`  

Risk classification is **change-granular**, not file-granular.

---

# 6. Validation

## Purpose

Verify migration correctness through runtime checks.

- Risk = static reasoning  
- Validation = runtime verification  

---

## Validation Mechanisms

### TestRunner

- Runs `ng test` for generated Angular workspace  
- Falls back to `npm test`  
- Handles timeout  
- Captures output  

---

### SnapshotComparator

- Compares before/after component state snapshots  
- Detects behavioral mismatches  
- Ensures state equivalence  

---

### LintRunner (Extensible Placeholder)

Designed for:

- ESLint integration  
- TypeScript compiler validation  

---

## Output

`ValidationResult`:

- `passed`  
- `checks`  
- `failures`  

Validation provides execution-grounded confirmation of migration quality.

---

# 7. Reporting

## Purpose

Aggregate and present migration results in structured formats.

---

## Inputs

- `AnalysisResult`  
- `PatternResult`  
- `TransformationResult`  
- `RiskResult`  
- `AIResult` (optional)  
- `ValidationResult`  

---

## Reporting Outputs

### JSON Report

- Machine-readable  
- Lists controllers, changes, risk per change  
- Includes validation results  
- API-ready  

---

### Markdown Report

- Human-readable  
- Summarizes:
  - Controllers detected  
  - Proposed changes  
  - Risk level per change  
  - Validation summary  
  - Run instructions  

---

## Metrics

Computed summary:

- Percent auto-converted  
- Risky changes count  
- Manual changes count  
- Test pass rate  

---

## Output

`ReportingResult`:

- `metrics`  
- `reports` (format → content)  

---

# Core Data Contracts

Each stage communicates through structured result objects:

| Stage           | Result Object              |
|----------------|---------------------------|
| Analysis       | `AnalysisResult`          |
| Patterns       | `PatternResult`           |
| Transformation | `TransformationResult`    |
| Risk           | `RiskResult`              |
| Validation     | `ValidationResult`        |
| Reporting      | `ReportingResult`         |

This ensures strict pipeline boundaries.

---

# Architectural Principles

## 1. Layered Isolation

Each stage:

- Has a base abstract class  
- Produces typed output  
- Is independently extensible  

---

## 2. Deterministic First

All core migrations are rule-based and reproducible.

---

## 3. Semantic Abstraction

Transformation operates on semantic roles, not raw AST.

---

## 4. Post-Transformation Risk

Risk reflects actual generated output.

---

## 5. Runtime Validation

Migration success is validated by tests and state comparison.

---

## 6. Multi-Format Reporting

Supports both developer UX and machine API integration.

---

# End-to-End Lifecycle

Raw AngularJS Repository
        ↓
Ingestion
        ↓
Structured Analysis
        ↓
Semantic Pattern Classification
        ↓
Deterministic Angular Generation
        ↓
Risk Classification
        ↓
Runtime Validation
        ↓
Structured Report + Metrics


---

# Extensibility Model

The pipeline supports extension at every layer:

| Layer          | Extendable By               |
|---------------|----------------------------|
| Ingestion     | New file classifiers        |
| Analysis      | New language analyzers      |
| Patterns      | New semantic roles          |
| Transformation| New migration rules         |
| Risk          | New heuristics              |
| Validation    | New runtime checks          |
| Reporting     | New output formats          |

---

# Summary

The `pipeline/` module implements a full modernization engine with:

- Structured static analysis  
- Semantic role abstraction  
- Deterministic transformation  
- Behavioral risk classification  
- Runtime validation  
- Structured reporting and metrics  

It is a layered, extensible migration system designed for scalable legacy-to-modern framework upgrades.