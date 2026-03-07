// bench-05-merge-strict/repo/src/app.js
// STRICT benchmark for HTTP inlining correctness

angular.module('strictMergeApp', [])

/* ────────────────────────────────────────────────────────────────
   SERVICE — must remain service methods (NOT inlined into component)
   ──────────────────────────────────────────────────────────────── */

.service('UserService', ['$http', function($http) {

  this.getUsers = function() {
    return $http.get('/api/users')
      .then(function(res) { return res.data; });
  };

  this.createUser = function(payload) {
    return $http.post('/api/users', payload)
      .then(function(res) { return res.data; })
      .catch(function(err) {
        console.error('Create failed', err);
        throw err;
      });
  };

}])

/* ────────────────────────────────────────────────────────────────
   INLINE TEST #1 — Multiple HTTP inside ONE method
   ──────────────────────────────────────────────────────────────── */

.controller('AdminController', ['$scope', '$http', function($scope, $http) {

  $scope.users = [];
  $scope.roles = [];

  $scope.load = function() {

    $http.get('/api/admin/users')
      .then(function(res) {
        $scope.users = res.data;
      });

    $http.get('/api/admin/roles')
      .then(function(res) {
        $scope.roles = res.data;
      });

  };

  $scope.load(); // → must become ngOnInit()

}])

/* ────────────────────────────────────────────────────────────────
   INLINE TEST #2 — HTTP inside DIFFERENT methods
   ──────────────────────────────────────────────────────────────── */

.controller('SettingsController', ['$scope', '$http', function($scope, $http) {

  $scope.settings = {};
  $scope.auditLog = [];

  $scope.loadSettings = function() {
    $http.get('/api/settings')
      .then(function(res) {
        $scope.settings = res.data;
      });
  };

  $scope.loadAudit = function() {
    $http.get('/api/audit')
      .then(function(res) {
        $scope.auditLog = res.data;
      });
  };

}])

/* ────────────────────────────────────────────────────────────────
   INLINE TEST #3 — HTTP + params object
   ──────────────────────────────────────────────────────────────── */

.controller('SearchController', ['$scope', '$http', function($scope, $http) {

  $scope.query = '';
  $scope.results = [];

  $scope.search = function() {
    $http.get('/api/search', { params: { q: $scope.query } })
      .then(function(res) {
        $scope.results = res.data;
      })
      .catch(function(err) {
        console.error('Search failed', err);
      });
  };

}])

/* ────────────────────────────────────────────────────────────────
   INLINE TEST #4 — POST + dynamic URL
   ──────────────────────────────────────────────────────────────── */

.controller('OrderController', ['$scope', '$http', function($scope, $http) {

  $scope.cart = [];
  $scope.lastOrder = null;

  $scope.placeOrder = function() {
    $http.post('/api/orders', { cart: $scope.cart })
      .then(function(res) {
        $scope.lastOrder = res.data;
      });
  };

  $scope.loadOrder = function(id) {
    $http.get('/api/orders/' + id)
      .then(function(res) {
        $scope.lastOrder = res.data;
      });
  };

}])

/* ────────────────────────────────────────────────────────────────
   INLINE TEST #5 — HTTP directly in controller body (not method)
   ──────────────────────────────────────────────────────────────── */

.controller('BootstrapController', ['$scope', '$http', function($scope, $http) {

  $scope.version = null;

  $http.get('/api/version')
    .then(function(res) {
      $scope.version = res.data;
    });

}])

/* ────────────────────────────────────────────────────────────────
   Directive — must not affect HTTP merge logic
   ──────────────────────────────────────────────────────────────── */

.directive('testDirective', function() {
  return {
    restrict: 'E',
    template: '<div>Test</div>'
  };
});