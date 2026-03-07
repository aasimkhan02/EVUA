// bench-05-mixed-realistic/repo/src/app.js
// Tests every transformation rule. Every risk level appears.
// Feature coverage:
//   Feature #1: HTTP calls merged into owning method body (not disconnected)
//   Feature #2: ngOnInit generated from top-level $scope.fn() calls
//   HttpToHttpClientRule → preserves .catch() using pipe(catchError)
//   Directive rules → stub generation
//
// NOTE: This benchmark intentionally has NO AngularJS routing config.
// RouteMigratorRule must NOT invent fallback routes.

angular.module('realisticApp', [])

// ── NotificationService ──────────────────────────────────────────────────
.service('NotificationService', ['$http', function($http) {

  this.getAll = function() {
    return $http.get('/api/notifications')
      .then(function(res) { return res.data; })
      .catch(function(err) {
        console.error('Notification fetch failed', err);
        throw err;
      });
  };

  this.markRead = function(id) {
    return $http.put('/api/notifications/' + id, { read: true })
      .then(function(res) { return res.data; });
  };
}])

// ── EmailService ─────────────────────────────────────────────────────────
.service('EmailService', ['$http', function($http) {

  this.send = function(payload) {
    return $http.post('/api/email', payload)
      .then(function(res) { return res.data; })
      .catch(function(err) {
        console.error('Email failed', err);
        throw err;
      });
  };

}])

// ── SearchController ─────────────────────────────────────────────────────
.controller('SearchController', ['$scope', '$http', function($scope, $http) {

  $scope.query   = '';
  $scope.results = [];

  $scope.$watch('query', function(val) {
    if (val && val.length >= 2) {
      $http.get('/api/search', { params: { q: val } })
        .then(function(res) {
          $scope.results = res.data;
        })
        .catch(function(err) {
          console.error('Search failed', err);
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
      .then(function(res) {
        deferred.resolve(res.data);
      })
      .catch(function(err) {
        deferred.reject(err);
      });

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

    $http.get('/api/admin/users')
      .then(function(res) { $scope.users = res.data; });

    $http.get('/api/admin/roles')
      .then(function(res) { $scope.roles = res.data; });

    $http.get('/api/admin/settings')
      .then(function(res) { $scope.settings = res.data; });

    $http.get('/api/admin/audit')
      .then(function(res) { $scope.auditLog = res.data; });
  };

  // Feature #2 → should become ngOnInit()
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
    $http.get('/api/products')
      .then(function(res) {
        $scope.products = res.data;
      })
      .catch(function(err) {
        console.error('Products failed', err);
      });
  };

  $scope.onProductSaved = function(product) {
    console.log('Product saved:', product);
  };

  // Feature #2 → should become ngOnInit()
  $scope.loadProducts();
}])

// ── highlightDirective (Element) ─────────────────────────────────────────
.directive('highlightDirective', function() {
  return {
    restrict: 'E',
    template: '<div>Highlight</div>'
  };
})

// ── uppercaseDirective (Attribute) ───────────────────────────────────────
.directive('uppercaseDirective', function() {
  return {
    restrict: 'A',
    link: function(scope, element) {
      element.text(element.text().toUpperCase());
    }
  };
});