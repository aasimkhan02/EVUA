# EVUA System Design

This document provides a detailed low-level design of the EVUA modernization platform, extending the System Architecture with specific data models, algorithms, and interface specifications.

## 1. Data Model & Entity Design

### 🅰️ AngularJS Internal Representation (IR)
The AngularJS engine represents code as a lifecycle-aware object graph.

| Entity | Description |
| :--- | :--- |
| `Module` | Root container for AngularJS units (services, controllers). |
| `IRNode` | base class for all entities, holding metadata and source reference. |
| `Change` | A mapping record between an original `IRNode` and its modern Angular equivalent. |
| `AnalysisResult` | The composite object containing all identified modules, dependencies, and artifacts. |

### 🐘 PHP AST-based Model
The PHP engine utilizes a direct Abstract Syntax Tree (AST) mapping.

| Entity | Description |
| :--- | :--- |
| `ASTNode` | A recursive structure representing logic blocks with line/column coordinates. |
| `MigrationIssue` | An identified vulnerability or deprecation, containing a `suggested_fix` and `requires_ai` flag. |
| `RuleMatch` | A specific instance where a migration rule matched a block of code. |
| `MigrationResult` | The final record for a file, containing `migrated_code` and a collection of matches. |

---

## 2. Algorithm Design

### 🔄 AngularJS Transformation Pipeline
The `RuleApplier` follows a **Multi-Pass Transformation Strategy**:

1.  **Discovery Pass**: Detectors (Controller, Http, etc.) populate the `PatternResult`.
2.  **Scaffolding Pass**: Rules like `RouteMigrator` and `AppModuleUpdater` create the foundational Angular files (`app.module.ts`).
3.  **Entity Transformation Pass**: individual rules (e.g., `ControllerToComponentRule`) iterate through detected nodes and generate modern TS code.
4.  **Refinement Pass**: Optional `AIAssistStage` performs final cleanup on generated stubs.

### 🛡️ PHP Rule Engine logic
The PHP engine uses a **Context-Aware Substitution** algorithm:
- It traverses the AST to find nodes mapping to known deprecations (e.g., `mysql_*` functions).
- It calculates a `RiskScore` using a weighted formula:
  $$Score = 0.45(Issues) + 0.25(Complexity) + 0.15(Nesting) + 0.15(DynamicCode)$$
- If an issue is flagged as `requires_ai`, the snippet is sent to the `GeminiHandoffProcessor` for intelligent refactoring.

---

## 3. Interface Design (API)

### Unified Migration Endpoint (`POST /api/migrate`)
The system follows a synchronous trigger design with real-time log streaming through indicator capturing.

**Request (Form-Data):**
- `engine`: `"angular" | "php"`
- `strategy`: `"migrate" | "dry-run" | "diff"`
- `project_name`: `string`
- `file`: `Binary (ZIP)`
- `target_version`: `string` (e.g., `"17"` or `"8.3"`)

**Response:**
```json
{
  "status": "success",
  "result": {
    "engine": "angular",
    "success": true,
    "indicators": ["Migration summary...", "15 classes found..."],
    "log": ["...raw engine output..."]
  }
}
```

---

## 4. Storage & Persistence Design

### File-System as Database
EVUA treats the filesystem as a high-performance primary store for migration artifacts.

- **`.evua/jobs/`**: Stores job-specific JSON reports named by UUID.
- **`reports/<project_name>/`**: Stores the high-level human-readable `.evua_report.md` and machine-readable `.evua_report.json`.
- **`temp_uploads/`**: Serves as a scratchpad for transient data; cleaned daily by the backend service.

---

## 5. Frontend Component Architecture

### Workspace Logic
The Workspace is designed around a **Report-Driven View State**:
1.  On load, it fetches the JSON report for the selected project.
2.  It iterates through `results.files` (PHP) or `transformation.changes` (Angular).
3.  It utilizes a **Unified Diff Provider** to feed `CodeMirror` with side-by-side blocks:
    - **Left**: `original_code`
    - **Right**: `migrated_code` (if available) or AI-suggested fix.
4.  **Action Dispatcher**: Handles manual approvals which are persisted back to the modified file list.
