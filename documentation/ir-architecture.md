# EVUA IR Architecture

The IR (Intermediate Representation) module is the semantic backbone of EVUA.  
It models **structure, runtime behavior, dependencies, templates, and migration governance** in a unified graph-based system.

EVUA is not a codemod tool.  
It is a **semantic migration engine**.

---

# 1. Architectural Philosophy

EVUA separates concerns into five distinct IR layers:

| Layer | Purpose |
|-------|----------|
| `code_model` | Static program structure |
| `behavior` | Runtime semantics |
| `dependency_model` | Directed relationships between nodes |
| `template_model` | UI/template semantics |
| `migration_model` | Migration tracking & governance |

Together they form a **semantic graph** of the application.

---

# 2. Core Design Principles

## 2.1 UUID-Based Identity

All nodes inherit from `IRNode` and provide:

- Unique ID
- Source location
- Metadata storage

This enables:

- Cross-referencing
- Diff tracking
- Auditability
- LLM trace explanations
- Deterministic graph linking

---

## 2.2 Separation of Structure and Behavior

- `code_model` = static structure (**what exists**)
- `behavior` = runtime meaning (**what it does**)

This prevents naive syntax-only transformations.

---

## 2.3 Graph-Oriented Architecture

Everything is linkable via IDs:

- Behavior references `Symbol.id`
- Dependencies connect any `IRNode`
- Templates reference symbols and directives
- Migration changes reference before/after IDs

The entire system is designed to evolve into a **semantic dependency graph engine**.

---

# 3. IR Layer Breakdown

---

## 3.1 `code_model` — Structural IR

Represents static code structure.

### Core Nodes

- `Module` → file-level container  
- `Class` → component/class definition  
- `Function` → method or function  
- `Symbol` → variable/field/parameter  
- `IRNode` → base class (UUID + location)

### Purpose

Provides:

- Component structure
- Symbol graph
- Entry points for transformation
- Static program topology

This is the structural backbone of EVUA.

---

## 3.2 `behavior` — Runtime Semantics

Models what happens at runtime.

### Core Nodes

| Node | Meaning |
|------|---------|
| `RuntimeBinding` | Data flow between symbols |
| `LifecycleHook` | Init / Update / Destroy phases |
| `Observer` | Watchers / reactive triggers |
| `SideEffect` | State mutation |
| `Behavior` | Base abstraction |

### Why This Exists

Enables semantic migrations such as:

- AngularJS → Angular 16  
- Vue 2 → Vue 3  
- React class components → Hooks  

Without this layer, migration would only transform syntax — not behavior.

---

## 3.3 `dependency_model` — Relationship Graph

Defines relationships between IR nodes.

### Dependency Types

- `IMPORT`
- `CALL`
- `INJECT`
- `EXTENDS`
- `IMPLEMENTS`
- `TEMPLATE_BINDING`

### Components

- `DependencyEdge`
- `DependencyGraph`

### Purpose

Enables:

- Call graph construction
- Dependency injection validation
- Circular dependency detection
- Impact analysis
- Safe refactoring ordering
- Dead code detection

This is the structural connectivity layer.

---

## 3.4 `template_model` — UI Semantics

Represents template-level behavior.

### Core Nodes

| Node | Purpose |
|------|---------|
| `Template` | Root template container |
| `Binding` | Read / Write / Two-way binding |
| `Directive` | Loop / Conditional / Event |
| `TemplateNode` | Base template node |

### Why This Matters

AngularJS migration heavily depends on:

- Two-way bindings
- `ng-repeat` → `*ngFor`
- `ng-if` → `*ngIf`
- `ng-click` → `(click)`

This layer enables rule-based, semantic template transformation.

---

## 3.5 `migration_model` — Governance & Audit

Tracks how migrations occur.

### Core Concepts

| Model | Purpose |
|--------|---------|
| `Change` | Before/after node mapping |
| `MigrationRecord` | Source of change (`RULE` / `AI` / `HUMAN`) |
| `ConfidenceScore` | Risk scoring |
| `MigrationDecision` | Approve / Edit / Reject |
| `MigrationSnapshot` | Persisted migration artifact |

### Why This Is Critical

Enables:

- AI-assisted upgrades
- Risk-aware automation
- Human-in-the-loop review
- Compliance auditing
- Rollback checkpoints

This transforms EVUA into a **governed migration platform**.

---

# 4. System Flow

The system operates as follows:

1. Parse code → build `code_model`
2. Extract runtime semantics → attach `behavior`
3. Build relationship graph → `dependency_model`
4. Parse templates → build `template_model`
5. Apply transformation rules / AI → produce `migration_model`
6. Score confidence
7. Allow human review and decisions

The result is a **semantic transformation pipeline**.

---

# 5. Current State vs Future Direction

## Current State

- Semantic tagging system
- Directed dependency graph
- Migration change tracking
- Template semantics abstraction
- UUID-linked IR ecosystem

## Planned Evolution

- Full behavior execution graph
- Advanced graph algorithms (SCC, topological sort)
- Expression-level AST for templates
- Call graph depth analysis
- Versioned migration timelines
- Reactive dependency modeling

The architecture is prepared to evolve into a **complete semantic execution graph engine**.

---

# 6. Mental Model for Contributors

Think of EVUA IR as:

Structure → What exists
Behavior → What it does
Dependency → How it's connected
Template → How UI binds to state
Migration → How it changes


This is not a compiler.  
This is not a codemod.  

This is a **semantic migration engine**.

---

# 7. Contributor Guidelines

When adding new IR features:

1. All nodes must inherit from `IRNode`
2. Use UUID linking — never direct object references
3. Prefer Enums over raw strings
4. Keep structure and behavior separate
5. Think in graph terms, not tree terms
6. Always consider migration traceability

If your addition cannot be linked into the graph, it does not belong in the IR.

---

# 8. Summary

The IR module provides:

- Structural abstraction
- Runtime semantic modeling
- Dependency graph representation
- Template semantics modeling
- Migration governance system

Together, they form the foundation of EVUA’s semantic upgrade engine.