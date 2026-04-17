# TaskFlow — AngularJS Test Project
## A Real-World AngularJS App for Testing Your AngularJS → Angular Converter

---

## 📁 Project Structure

```
taskflow/
├── index.html          # App shell, ng-app, ng-controller="AppCtrl"
├── app.js              # Module config, $routeProvider, .run() block
├── services.js         # Services & Factories
├── controllers.js      # All controllers
├── directives.js       # Custom directives
├── filters.js          # Custom filters
└── views.html          # All HTML templates (split into views/ folder in real use)
    ├── views/login.html
    ├── views/dashboard.html
    ├── views/task-board.html
    ├── views/task-detail.html
    └── views/profile.html
```

---

## ✅ AngularJS Patterns Covered (Your Converter Must Handle All Of These)

### Routing
- `$routeProvider` with `.when()` and `.otherwise()`
- `controllerAs` syntax on routes
- Route `resolve` (pre-fetching data before route activates)
- `$route.current.params` access in resolvers
- `$routeChangeStart` / `$routeChangeSuccess` / `$routeChangeError` listeners
- Auth guard in `.run()` using `event.preventDefault()`

### Scope & Binding
- `$scope` (traditional) AND `controllerAs: 'vm'` patterns (both used)
- `$rootScope` for global state
- `$scope.$watch()` with single expression
- `$scope.$watch()` with deep equality (`true` 3rd argument)
- `$scope.$watchCollection()` 
- `$scope.$on()` event listeners
- `$scope.$broadcast()` and `$rootScope.$broadcast()`
- `$scope.$emit()`
- `$scope.$apply()` inside DOM event handlers

### Services & DI
- `.service()` — using `this`
- `.factory()` — returning an object
- Constructor injection via array syntax: `['DepA', 'DepB', function(DepA, DepB) {}]`
- `$injector.get()` to avoid circular dependencies
- In-memory caching inside a factory
- `$q` promises and `$q.resolve()` / `$q.reject()`
- `$http` GET / POST / PUT / PATCH / DELETE
- File upload via `$http` with `Content-Type: undefined` + `transformRequest`
- HTTP interceptors (request + responseError)

### Directives
- `restrict: 'E'` (element directive)
- `restrict: 'A'` (attribute directive)
- Isolate scope with `@`, `=`, `&` bindings
- `templateUrl` and inline `template`
- `link` function with `scope`, `element`, `attrs`
- `controller` function inside directive
- `transclude: true`
- `require: 'ngModel'` with `$formatters` and `$parsers` and `$validators`
- `attrs.$observe()` for watching attribute changes
- `$timeout` inside directives
- `$document` service for global event listeners
- Manual DOM manipulation in link functions
- Cleanup in `scope.$on('$destroy', ...)` 

### Filters
- `capitalize` — basic string filter
- `truncate` — parameterized filter
- `timeAgo` — date filter injecting `$filter`
- `statusLabel` — lookup filter
- `priorityOrder` — array sorting filter
- `fileSize` — number formatting
- `countByStatus` — aggregate filter
- `highlight` — filter using `$sce.trustAsHtml`

### Templates
- `ng-model` with form validation
- `ng-repeat` with `track by`
- `ng-repeat` with `limitTo`
- `ng-if` / `ng-show` / `ng-hide`
- `ng-class` with object and expression
- `ng-style`
- `ng-submit`
- `ng-change`
- `ng-disabled`
- `ng-click`
- `ng-keyup`
- `ng-attr-type` (dynamic attribute)
- Pipes/Filters in templates: `{{value | filter:arg}}`
- Chained filters: `{{value | filterA | filterB:param}}`
- `ng-src`
- `ng-options` equivalent (ng-repeat in select)
- Form `$invalid`, `$touched`, `$pristine`, `$dirty` states
- `form.$setPristine()`, `form.$setUntouched()`
- `angular.copy()` for deep cloning
- `angular.equals()` for deep comparison
- `angular.extend()`

### Lifecycle
- `$interval` with cancellation on `$destroy`
- `$timeout` with cancellation
- `localStorage` access pattern
- `Promise.all()` usage alongside `$q`

### Built-in Directives Used
`ng-app`, `ng-controller`, `ng-view`, `ng-repeat`, `ng-if`, `ng-show`, `ng-hide`,
`ng-model`, `ng-class`, `ng-style`, `ng-click`, `ng-submit`, `ng-change`, `ng-disabled`,
`ng-keyup`, `ng-src`, `ng-attr-*`, `ng-include` (implied by templateUrl), `ng-bind`,
`ng-transclude`, `ng-options`

---

## 🔴 High-Difficulty Conversion Challenges

These are the things most converters fail on:

| Pattern | AngularJS | Angular Equivalent |
|---|---|---|
| `$scope.$watch` | Watch expressions | `ngOnChanges` / `effect()` |
| `$rootScope.$broadcast` | Global events | `EventEmitter` / `Subject` |
| `$routeProvider` resolve | Pre-route data | Route `resolve` with `ResolveFn` |
| `$http` interceptors | Service-level | `HttpInterceptor` |
| `link` function + DOM | Directive link | `ngAfterViewInit` + `ElementRef` |
| `$formatters`/`$parsers` | ngModel pipeline | `ControlValueAccessor` |
| `$q` promises | Angular's `$q` | Native `Promise` / `Observable` |
| `$interval` cleanup | `$destroy` event | `ngOnDestroy` + `takeUntil` |
| `controllerAs: 'vm'` | Controller alias | Component class (no alias needed) |
| `$scope.$apply()` | Manual digest | `NgZone.run()` |
| Deep `$watch` (3rd arg) | Object deep compare | `effect()` with deep signals |

---

## 🚀 How To Run

```bash
# Serve with any static file server
npx serve .
# or
python3 -m http.server 8080
```

Open http://localhost:8080

> **Note:** The backend API (`/api/*`) is mocked. Add a mock server (e.g., json-server)  
> or replace `$http` calls with local mock data to run fully offline.

---

## Mock Data Setup (Quick Start)

```bash
npm install -g json-server
# Create db.json with your data, then:
json-server --watch db.json --port 3000 --routes routes.json
```

Then update the API base URL in `services.js` to `http://localhost:3000`.
