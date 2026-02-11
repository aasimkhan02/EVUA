# EVUA Migration Report

## Controllers Detected
- **AdminController** (`C:\Users\moidin\Desktop\Projects\EVUA\engine\demo-angularjs-advanced\app.js`)
- **UserController** (`C:\Users\moidin\Desktop\Projects\EVUA\engine\demo-angularjs-advanced\app.js`)

## Proposed Changes
- **AdminController** (`C:\Users\moidin\Desktop\Projects\EVUA\engine\demo-angularjs-advanced\app.js`) → Angular Component  
  Output: `out\angular-app (files: out\angular-app\src\app\admin.component.ts, out\angular-app\src\app\admin.component.html)`  
  Risk: **RiskLevel.RISKY** — Multiple $scope writes detected  
  Build: **False**, Snapshot: **True**
- **UserController** (`C:\Users\moidin\Desktop\Projects\EVUA\engine\demo-angularjs-advanced\app.js`) → Angular Component  
  Output: `out\angular-app (files: out\angular-app\src\app\user.component.ts, out\angular-app\src\app\user.component.html)`  
  Risk: **RiskLevel.RISKY** — Multiple $scope writes detected  
  Build: **False**, Snapshot: **True**

## Validation Summary
- Tests passed: **False**
- Snapshot passed: **True**
  - ❌ Tests failed

## Run the migrated Angular app
```bash
cd out/angular-app
npm install
ng serve
```