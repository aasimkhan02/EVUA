/**
 * bench-100-full-coverage — AngularJS source for EVUA engine stress test
 *
 * Designed to hit every single transformation rule precisely:
 *  - ControllerToComponentRule   (6 controllers, various HTTP patterns)
 *  - ServiceToInjectableRule     (2 services, method names, HTTP inlining)
 *  - HttpToHttpClientRule        (should skip already-inlined calls)
 *  - RouteMigratorRule           ($routeProvider with 5 routes + otherwise)
 *  - SimpleWatchToRxjsRule       ($watch → BehaviorSubject injection)
 *  - AppModuleUpdaterRule        (FormsModule, HttpClientModule, providers)
 *  - ComponentInteractionRule    (parent template uses child selector)
 *  - Template migrator           (ng-* attributes, filters in templates)
 *  - DI mapper                   ($state, $location, $routeParams, custom svc)
 *
 * NOT expected to produce (engine gaps we are measuring):
 *  - DirectiveToComponentRule    (no such rule exists yet)
 *  - FilterToPipeRule            (no such rule exists yet)
 *  - $rootScope cross-component  (flagged only)
 *  - $compile / $q               (flagged only)
 */

angular.module('bench100App', ['ngRoute'])

// ═══════════════════════════════════════════════════════════════════════════
// SERVICES  (ServiceToInjectableRule target)
// ═══════════════════════════════════════════════════════════════════════════

// UserService — multi-method, each with HTTP + .then(), one with .catch()
.service('UserService', ['$http', function($http) {

  // Simple GET + .then()
  this.getAll = function() {
    return $http.get('/api/users')
      .then(function(res) { return res.data; });
  };

  // POST with request body + .then()
  this.create = function(payload) {
    return $http.post('/api/users', payload)
      .then(function(res) { return res.data; });
  };

  // Dynamic URL (BinaryExpression) + .catch()
  this.remove = function(id) {
    return $http.delete('/api/users/' + id)
      .catch(function(err) {
        console.error('remove failed', err);
        throw err;
      });
  };

}])

// AuthService — tests custom service DI injection into controllers
.service('AuthService', ['$http', function($http) {

  this.login = function(creds) {
    return $http.post('/api/auth/login', creds)
      .then(function(res) { return res.data; });
  };

  this.logout = function() {
    return $http.post('/api/auth/logout', {});
  };

}])

// ═══════════════════════════════════════════════════════════════════════════
// CONTROLLERS  (ControllerToComponentRule target)
// ═══════════════════════════════════════════════════════════════════════════

// ── 1. UserListController
//    Tests: ngOnInit (top-level call), $watch → BehaviorSubject,
//           $http DELETE with dynamic URL, .catch() → catchError,
//           $scope elimination, res.data elimination
.controller('UserListController', ['$scope', '$http',
  function($scope, $http) {

  $scope.users   = [];
  $scope.loading = false;
  $scope.error   = null;

  $scope.loadUsers = function() {
    $scope.loading = true;
    $http.get('/api/users')
      .then(function(res) {
        $scope.users   = res.data;
        $scope.loading = false;
      })
      .catch(function(err) {
        $scope.error   = err.message;
        $scope.loading = false;
      });
  };

  $scope.deleteUser = function(id) {
    $http.delete('/api/users/' + id)
      .then(function(res) {
        $scope.users = res.data;
      });
  };

  // $watch — should produce BehaviorSubject in output
  $scope.$watch('loading', function(newVal) {
    console.log('loading changed', newVal);
  });

  $scope.loadUsers();  // top-level call → ngOnInit

}])

// ── 2. UserDetailController
//    Tests: PUT with dynamic URL + body, .catch(), NO ngOnInit (no top-level call)
//           $scope body sanitisation ($scope.user → this.user in PUT body)
.controller('UserDetailController', ['$scope', '$http',
  function($scope, $http) {

  $scope.user = {};

  $scope.saveUser = function(id) {
    $http.put('/api/users/' + id, $scope.user)
      .then(function(res) {
        $scope.user = res.data;
      })
      .catch(function(err) {
        console.error('save failed', err);
        throw err;
      });
  };

  // No top-level $scope.fn() call → NO ngOnInit generated

}])

// ── 3. DashboardController
//    Tests: MULTIPLE top-level calls → all land in ngOnInit,
//           multiple $http GET calls, $watch
.controller('DashboardController', ['$scope', '$http',
  function($scope, $http) {

  $scope.stats    = {};
  $scope.activity = [];
  $scope.filter   = 'all';

  $scope.loadStats = function() {
    $http.get('/api/dashboard/stats')
      .then(function(res) {
        $scope.stats = res.data;
      });
  };

  $scope.loadActivity = function() {
    $http.get('/api/dashboard/activity')
      .then(function(res) {
        $scope.activity = res.data;
      });
  };

  $scope.$watch('filter', function(newVal) {
    console.log('filter changed', newVal);
  });

  // Two top-level calls → both must appear in ngOnInit
  $scope.loadStats();
  $scope.loadActivity();

}])

// ── 4. ProductController
//    Tests: POST with $scope.newProduct in body → body sanitised to this.newProduct,
//           ngOnInit, res.data removal
.controller('ProductController', ['$scope', '$http',
  function($scope, $http) {

  $scope.products   = [];
  $scope.newProduct = { name: '', price: 0 };

  $scope.loadProducts = function() {
    $http.get('/api/products')
      .then(function(res) {
        $scope.products = res.data;
      });
  };

  $scope.createProduct = function() {
    $http.post('/api/products', $scope.newProduct)
      .then(function(res) {
        $scope.products   = res.data;
        $scope.newProduct = { name: '', price: 0 };
      });
  };

  $scope.loadProducts();  // → ngOnInit

}])

// ── 5. AuthController
//    Tests: custom service DI (AuthService → injected as constructor param),
//           no $http direct usage, NO ngOnInit
.controller('AuthController', ['$scope', 'AuthService',
  function($scope, AuthService) {

  $scope.credentials = { username: '', password: '' };
  $scope.user = null;

  $scope.login = function() {
    AuthService.login($scope.credentials)
      .then(function(user) {
        $scope.user = user;
      });
  };

  $scope.logout = function() {
    AuthService.logout();
    $scope.user = null;
  };

  // No top-level call → NO ngOnInit

}])

// ── 6. SearchController
//    Tests: .catch() → catchError pipe, no ngOnInit,
//           $location DI token mapping
.controller('SearchController', ['$scope', '$http', '$location',
  function($scope, $http, $location) {

  $scope.query   = '';
  $scope.results = [];

  $scope.search = function() {
    $http.get('/api/search')
      .then(function(res) {
        $scope.results = res.data;
      })
      .catch(function(err) {
        console.error('search failed', err);
        $scope.results = [];
      });
  };

  // No top-level call → NO ngOnInit

}])

// ═══════════════════════════════════════════════════════════════════════════
// DIRECTIVES  (NO rule generates output — gap we are measuring)
// ═══════════════════════════════════════════════════════════════════════════

.directive('userCard', function() {
  return {
    restrict: 'E',
    scope: { user: '=' },
    templateUrl: 'templates/user-card.html',
    link: function($scope, el, attrs) {
      $scope.expanded = false;
    }
  };
})

.directive('loadingSpinner', function() {
  return {
    restrict: 'E',
    scope: { show: '=' },
    template: '<div class="spinner" ng-show="show">Loading...</div>'
  };
})

// ═══════════════════════════════════════════════════════════════════════════
// FILTERS  (NO rule generates output — gap we are measuring)
// ═══════════════════════════════════════════════════════════════════════════

.filter('capitalize', function() {
  return function(input) {
    if (!input) return '';
    return input.charAt(0).toUpperCase() + input.slice(1);
  };
})

.filter('truncate', function() {
  return function(input, limit) {
    limit = limit || 80;
    return input && input.length > limit
      ? input.substring(0, limit) + '…'
      : input;
  };
})

// ═══════════════════════════════════════════════════════════════════════════
// ROUTES  (RouteMigratorRule target)
// ═══════════════════════════════════════════════════════════════════════════

.config(['$routeProvider', function($routeProvider) {
  $routeProvider
    .when('/users', {
      templateUrl: 'templates/user-list.html',
      controller:  'UserListController'
    })
    .when('/users/:id', {
      templateUrl: 'templates/user-detail.html',
      controller:  'UserDetailController'
    })
    .when('/dashboard', {
      templateUrl: 'templates/dashboard.html',
      controller:  'DashboardController'
    })
    .when('/products', {
      templateUrl: 'templates/product-list.html',
      controller:  'ProductController'
    })
    .when('/search', {
      templateUrl: 'templates/search.html',
      controller:  'SearchController'
    })
    .otherwise({ redirectTo: '/dashboard' });
}]);