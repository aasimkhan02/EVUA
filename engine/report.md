# EVUA Migration Report

## Controllers Detected
- **AdminController** (`C:\Users\moidin\Desktop\Projects\EVUA\engine\demo-angularjs-advanced\app.js`)
- **UserController** (`C:\Users\moidin\Desktop\Projects\EVUA\engine\demo-angularjs-advanced\app.js`)

## Proposed Changes
- **AdminController** (`C:\Users\moidin\Desktop\Projects\EVUA\engine\demo-angularjs-advanced\app.js`) → Angular Component  
  Output: `out\angular\admin.component.ts`  
  Risk: **RiskLevel.RISKY** — Controller → Component is a semantic paradigm shift
- **UserController** (`C:\Users\moidin\Desktop\Projects\EVUA\engine\demo-angularjs-advanced\app.js`) → Angular Component  
  Output: `out\angular\user.component.ts`  
  Risk: **RiskLevel.RISKY** — Controller → Component is a semantic paradigm shift

## Validation
- Tests passed: **False**
  - ❌ Tests failed