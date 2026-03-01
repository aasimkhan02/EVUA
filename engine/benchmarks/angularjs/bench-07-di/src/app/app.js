
/**
 * bench-07-di — DI constructor generation benchmark
 *
 * Tests every DI pattern the engine needs to handle:
 *   1. Array annotation  (survives minification)
 *   2. Plain function params
 *   3. Known Angular built-ins: $http, $routeParams, $state, $q
 *   4. Custom services injected alongside built-ins
 *   5. $scope (should be OMITTED from constructor + comment added)
 *   6. Duplicate Angular type (e.g. $state + $location both → Router, deduplicated)
 *   7. Service that itself has DI
 */

angular.module('benchApp', ['ngRoute', 'ui.router'])

// ── 1. Array-annotated controller with known built-ins ─────────────────────
.controller('UserListController', ['$scope', '$http', '$routeParams', 'UserService',
  function($scope, $http, $routeParams, UserService) {
    $scope.users = [];
    $http.get('/api/users').then(function(res) {
      $scope.users = res.data;
    });
  }
])

// ── 2. Plain-params controller (no array annotation) ──────────────────────
.controller('HomeController', function($scope) {
  $scope.title = 'Home';
})

// ── 3. $state + $location → both map to Router (deduplicate) ──────────────
.controller('NavController', ['$scope', '$state', '$location',
  function($scope, $state, $location) {
    $scope.go = function(s) { $state.go(s); };
  }
])

// ── 4. $q — should be omitted + comment ───────────────────────────────────
.controller('DashboardController', ['$scope', '$http', '$q', 'DataService',
  function($scope, $http, $q, DataService) {
    var deferred = $q.defer();
    $http.get('/api/dashboard').then(function(r) { deferred.resolve(r.data); });
  }
])

// ── 5. ui-router $stateParams ─────────────────────────────────────────────
.controller('ProductController', ['$scope', '$stateParams', '$http',
  function($scope, $stateParams, $http) {
    $http.get('/api/products/' + $stateParams.id).then(function(res) {
      $scope.product = res.data;
    });
  }
])

// ── 6. Service with its own DI ────────────────────────────────────────────
.service('UserService', ['$http', '$q',
  function($http, $q) {
    this.getAll = function() {
      return $http.get('/api/users');
    };
  }
])

// ── 7. Service injected into another service ──────────────────────────────
.service('DataService', ['$http', 'UserService',
  function($http, UserService) {
    this.load = function() {
      return UserService.getAll();
    };
  }
])

// ── Route config ───────────────────────────────────────────────────────────
.config(['$routeProvider', function($routeProvider) {
  $routeProvider
    .when('/home',     { controller: 'HomeController',     templateUrl: 'home.html' })
    .when('/users',    { controller: 'UserListController', templateUrl: 'users.html' })
    .when('/products/:id', { controller: 'ProductController', templateUrl: 'product.html' })
    .when('/dashboard', { controller: 'DashboardController', templateUrl: 'dashboard.html' })
    .otherwise({ redirectTo: '/home' });
}]);