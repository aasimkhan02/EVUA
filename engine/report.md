# EVUA Migration Report

## Controllers Detected
- **DashboardController** (`C:\Users\moidin\Desktop\Projects\EVUA\tests\benchmark9\controllers.js`)
- **UserController** (`C:\Users\moidin\Desktop\Projects\EVUA\tests\benchmark9\controllers.js`)
- **AdminController** (`C:\Users\moidin\Desktop\Projects\EVUA\tests\benchmark9\controllers.js`)

## Proposed Changes
- **DashboardController** (`C:\Users\moidin\Desktop\Projects\EVUA\tests\benchmark9\controllers.js`) → Angular Component  
  Output: `out\angular-app (files: out\angular-app\src\app\dashboard.component.ts, out\angular-app\src\app\dashboard.component.html)`  
  Risk: **RiskLevel.RISKY** — Heavy $scope mutation detected (state coupling risk)  
  Build: **False**, Snapshot: **False**
- **UserController** (`C:\Users\moidin\Desktop\Projects\EVUA\tests\benchmark9\controllers.js`) → Angular Component  
  Output: `N/A`  
  Risk: **RiskLevel.MANUAL** — Deep $watch detected (high behavioral coupling risk)  
  Build: **False**, Snapshot: **False**
- **AdminController** (`C:\Users\moidin\Desktop\Projects\EVUA\tests\benchmark9\controllers.js`) → Angular Component  
  Output: `out\angular-app (files: out\angular-app\src\app\admin.component.ts, out\angular-app\src\app\admin.component.html)`  
  Risk: **RiskLevel.RISKY** — Heavy $scope mutation detected (state coupling risk)  
  Build: **False**, Snapshot: **False**

## Validation Summary
- Tests passed: **False**
- Snapshot passed: **False**
  - ❌ Tests failed
  - ❌ Snapshot file(s) missing: C:\Users\moidin\Desktop\Projects\EVUA\tests\benchmark9\snapshots\before.json, C:\Users\moidin\Desktop\Projects\EVUA\tests\benchmark9\snapshots\after.json

## Run the migrated Angular app
```bash
cd out/angular-app
npm install
ng serve
```