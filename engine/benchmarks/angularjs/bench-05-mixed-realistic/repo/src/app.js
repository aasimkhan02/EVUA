// bench-05-mixed-realistic/repo/src/app.js
// The hardest benchmark. Every transformation rule fires. Every risk level appears.
// Tests that changes are isolated — a MANUAL change must not make adjacent SAFE changes RISKY.
//
// Expected outcome:
//   NotificationService  → SAFE  (clean service, $http only)
//   SearchController     → SAFE  (shallow watch, few writes, no compile)
//   OrderController      → MANUAL ($q.defer + deep watch)
//   AdminController      → RISKY (5 scope writes, no watch — heavy mutation)

angular.module('realisticApp', [])

// ── NotificationService ───────────────────────────────────────
// Clean service. Should auto-migrate to @Injectable() as SAFE.
.service('NotificationService', ['$http', function($http) {

  this.getAll = function() {
    return $http.get('/api/notifications');
  };

  this.markRead = function(id) {
    return $http.put('/api/notifications/' + id, { read: true });
  };
}])

// ── SearchController ──────────────────────────────────────────
// Shallow $watch on query string → safe RxJS BehaviorSubject migration
// Only 2 scope writes → SAFE (under threshold of 5)
.controller('SearchController', ['$scope', '$http', function($scope, $http) {

  $scope.query   = '';
  $scope.results = [];

  // Shallow watch — safe for BehaviorSubject rewrite
  $scope.$watch('query', function(val) {
    if (val && val.length >= 2) {
      $http.get('/api/search', { params: { q: val } }).then(function(res) {
        $scope.results = res.data;
      });
    }
  });
}])

// ── OrderController ───────────────────────────────────────────
// $q.defer + deep watch on cart — double MANUAL trigger
// Tests that $q.defer alone is enough for MANUAL even before WatcherRiskRule fires
.controller('OrderController', ['$scope', '$http', '$q', function($scope, $http, $q) {

  $scope.cart    = [];
  $scope.total   = 0;
  $scope.coupon  = null;

  // Deep watch on cart object — MANUAL
  $scope.$watch('cart', function(cart) {
    $scope.total = cart.reduce(function(sum, item) {
      return sum + (item.price * item.qty);
    }, 0);
  }, true);

  // $q.defer — MANUAL (Promise chain, must be rewritten to Observable manually)
  $scope.placeOrder = function() {
    var deferred = $q.defer();
    $http.post('/api/orders', { cart: $scope.cart, coupon: $scope.coupon })
      .then(function(res) { deferred.resolve(res.data); })
      .catch(function(err) { deferred.reject(err); });
    return deferred.promise;
  };

  $scope.addItem = function(item) {
    $scope.cart.push(item);
  };
}])

// ── AdminController ───────────────────────────────────────────
// No watch, no compile, no nested scope — but 5 scope writes
// Tests the heavy mutation RISKY path (>= 5 unique writes with threshold at 5)
// NOTE: with threshold=6 this becomes SAFE. With threshold=5 it's RISKY.
// This benchmark deliberately tests the boundary — document the expected behavior.
.controller('AdminController', ['$scope', '$http', function($scope, $http) {

  $scope.users     = [];
  $scope.roles     = [];
  $scope.settings  = {};
  $scope.auditLog  = [];
  $scope.activeTab = 'users';

  // 5 unique scope writes above — RISKY at threshold=5, SAFE at threshold=6
  // Benchmark uses threshold=6 (current engine default) → expects SAFE
  // Change _HEAVY_SCOPE_WRITE_THRESHOLD back to 5 to make this RISKY

  $scope.load = function() {
    $http.get('/api/admin/users').then(function(res) { $scope.users = res.data; });
    $http.get('/api/admin/roles').then(function(res) { $scope.roles = res.data; });
    $http.get('/api/admin/settings').then(function(res) { $scope.settings = res.data; });
    $http.get('/api/admin/audit').then(function(res) { $scope.auditLog = res.data; });
  };

  $scope.load();
}]);