// benchmarks/angularjs/evua-benchmark-01/repo/src/app.js
// ============================================================
// EVUA Benchmark — AngularJS app covering every migration pattern
//
// Patterns present:
//   ✅ 2 controllers (UserController, ProductController)
//   ✅ 1 service     (AuthService)
//   ✅ $http.get, $http.post
//   ✅ shallow $watch on UserController
//   ✅ deep $watch on ProductController (→ MANUAL)
//   ✅ $q.defer (→ MANUAL risk)
// ============================================================

angular.module('benchmarkApp', [])

// ── UserController ────────────────────────────────────────────
.controller('UserController', ['$scope', '$http', function($scope, $http) {

  $scope.users = [];
  $scope.query = '';
  $scope.loading = false;

  // Shallow $watch — safe for RxJS rewrite
  $scope.$watch('query', function(newVal, oldVal) {
    if (newVal !== oldVal) {
      $scope.filteredUsers = $scope.users.filter(function(u) {
        return u.name.indexOf(newVal) !== -1;
      });
    }
  });

  $scope.loadUsers = function() {
    $scope.loading = true;
    $http.get('/api/users').then(function(response) {
      $scope.users = response.data;
      $scope.loading = false;
    });
  };

  $scope.loadUsers();
}])

// ── ProductController ─────────────────────────────────────────
.controller('ProductController', ['$scope', '$http', '$q', function($scope, $http, $q) {

  $scope.products = [];
  $scope.cart     = [];
  $scope.total    = 0;

  // Deep $watch — NOT auto-migratable (MANUAL)
  $scope.$watch('cart', function(newCart) {
    $scope.total = newCart.reduce(function(sum, item) {
      return sum + item.price;
    }, 0);
  }, true);

  $scope.loadProducts = function() {
    $http.get('/api/products').then(function(res) {
      $scope.products = res.data;
    });
  };

  $scope.addToCart = function(product) {
    $scope.cart.push(product);
  };

  // $q.defer usage — MANUAL migration required
  $scope.checkout = function() {
    var deferred = $q.defer();

    $http.post('/api/checkout', { cart: $scope.cart }).then(function(res) {
      deferred.resolve(res.data);
    }, function(err) {
      deferred.reject(err);
    });

    return deferred.promise;
  };

  $scope.loadProducts();
}])

// ── AuthService ───────────────────────────────────────────────
.service('AuthService', ['$http', function($http) {

  this.login = function(credentials) {
    return $http.post('/api/login', credentials);
  };

  this.logout = function() {
    return $http.post('/api/logout', {});
  };

  this.getProfile = function() {
    return $http.get('/api/profile');
  };
}]);