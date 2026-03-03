// bench-05-mixed-realistic/repo/src/app.js
// Tests every transformation rule. Every risk level appears.
// Feature coverage:
//   Feature #1: HTTP calls merged into owning method body (not disconnected)
//   Feature #2: ngOnInit generated from top-level $scope.fn() calls
//   AppModuleUpdaterRule  → app.module.ts declares all components + services
//   ComponentInteractionRule → @Input/@Output stubs when parent uses child in template
//
// Expected outcome:
//   NotificationService  → SAFE  (clean service, $http only)
//   SearchController     → SAFE  (shallow watch, few writes, no compile)
//   OrderController      → MANUAL ($q.defer + deep watch)
//   AdminController      → SAFE  (load() body calls fetchAdminUsers etc, ngOnInit calls load)
//   ProductCardController → SAFE (child component — receives @Input from parent)
//   DashboardController  → SAFE (ngOnInit calls loadProducts which calls fetchProducts)

angular.module('realisticApp', [])

// ── NotificationService ──────────────────────────────────────────────────
// Clean service. Should auto-migrate to @Injectable() as SAFE.
.service('NotificationService', ['$http', function($http) {

  this.getAll = function() {
    return $http.get('/api/notifications');
  };

  this.markRead = function(id) {
    return $http.put('/api/notifications/' + id, { read: true });
  };
}])

// ── SearchController ─────────────────────────────────────────────────────
// Shallow $watch on query string → safe RxJS BehaviorSubject migration
.controller('SearchController', ['$scope', '$http', function($scope, $http) {

  $scope.query   = '';
  $scope.results = [];

  $scope.$watch('query', function(val) {
    if (val && val.length >= 2) {
      $http.get('/api/search', { params: { q: val } }).then(function(res) {
        $scope.results = res.data;
      });
    }
  });
}])

// ── OrderController ──────────────────────────────────────────────────────
// $q.defer + deep watch on cart — double MANUAL trigger
.controller('OrderController', ['$scope', '$http', '$q', function($scope, $http, $q) {

  $scope.cart    = [];
  $scope.total   = 0;
  $scope.coupon  = null;

  $scope.$watch('cart', function(cart) {
    $scope.total = cart.reduce(function(sum, item) {
      return sum + (item.price * item.qty);
    }, 0);
  }, true);

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

// ── AdminController ──────────────────────────────────────────────────────
// TESTS Feature #1: $scope.load() contains all 4 $http.get calls.
// Expected: load() method body calls fetchAdminUsers(), fetchAdminRoles(), etc.
// TESTS Feature #2: $scope.load() is called at bottom of controller.
// Expected: ngOnInit() { this.load(); }
.controller('AdminController', ['$scope', '$http', function($scope, $http) {

  $scope.users     = [];
  $scope.roles     = [];
  $scope.settings  = {};
  $scope.auditLog  = [];
  $scope.activeTab = 'users';

  $scope.load = function() {
    $http.get('/api/admin/users').then(function(res) { $scope.users = res.data; });
    $http.get('/api/admin/roles').then(function(res) { $scope.roles = res.data; });
    $http.get('/api/admin/settings').then(function(res) { $scope.settings = res.data; });
    $http.get('/api/admin/audit').then(function(res) { $scope.auditLog = res.data; });
  };

  // Feature #2: top-level call → ngOnInit
  $scope.load();
}])

// ── ProductCardController ────────────────────────────────────────────────
.controller('ProductCardController', ['$scope', function($scope) {

  $scope.save = function() {
    if ($scope.onSaved) {
      $scope.onSaved({ product: $scope.product });
    }
  };
}])

// ── DashboardController ──────────────────────────────────────────────────
// TESTS Feature #1: $scope.loadProducts() contains $http.get('/api/products').
// Expected: loadProducts() body calls fetchProducts().
// TESTS Feature #2: $scope.loadProducts() called at bottom.
// Expected: ngOnInit() { this.loadProducts(); }
.controller('DashboardController', ['$scope', '$http', function($scope, $http) {

  $scope.products = [];
  $scope.selected = null;

  $scope.loadProducts = function() {
    $http.get('/api/products').then(function(res) {
      $scope.products = res.data;
    });
  };

  $scope.onProductSaved = function(product) {
    console.log('Product saved:', product);
  };

  // Feature #2: top-level call → ngOnInit
  $scope.loadProducts();
}]);