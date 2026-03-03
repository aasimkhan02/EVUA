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

// NOTE: This benchmark intentionally has NO AngularJS routing config.
// RouteMigratorRule must NOT invent fallback routes.
// Expected output: empty Routes[] with TODO.

angular.module('realisticApp', [])

// ── NotificationService ──────────────────────────────────────────────────
.service('NotificationService', ['$http', function($http) {

  this.getAll = function() {
    return $http.get('/api/notifications');
  };

  this.markRead = function(id) {
    return $http.put('/api/notifications/' + id, { read: true });
  };
}])

// ── EmailService ──────────────────────────────────────────────────
.service('EmailService', ['$http', function($http) {

  this.send = function(payload) {
    return $http.post('/api/email', payload);
  };

}])

// ── SearchController ─────────────────────────────────────────────────────
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

  $scope.loadProducts();
}])

// ── highlightDirective (Element → Component) ─────────────────────────────
.directive('highlightDirective', function() {
  return {
    restrict: 'E',
    template: '<div>Highlight</div>'
  };
})

// ── uppercaseDirective (Attribute → Pipe) ────────────────────────────────
.directive('uppercaseDirective', function() {
  return {
    restrict: 'A',
    link: function(scope, element) {
      element.text(element.text().toUpperCase());
    }
  };
});