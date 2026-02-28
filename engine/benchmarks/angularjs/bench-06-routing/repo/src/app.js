// bench-06-routing/repo/src/app.js
//
// Comprehensive routing benchmark.
// Tests every route migration scenario EVUA must handle.
//
// Expected routes extracted:
//   ngRoute:
//     /                          → redirectTo /home (otherwise)
//     /home                      → HomeController
//     /users                     → UserListController
//     /users/:id                 → UserDetailController  (path param)
//     /users/:id/edit            → UserEditController    (nested path param)
//     /about                     → no controller         (static route)
//     /dashboard                 → DashboardController   (with resolve block)
//
//   uiRouter:
//     app                        → abstract parent state
//     app.home                   → HomeController
//     app.users                  → UserListController
//     app.users.detail (:userId) → UserDetailController  (param)
//     app.admin                  → AdminController        (resolve block)
//
// Expected Angular output:
//   app-routing.module.ts with all routes
//   userdata.resolver.ts + adminprofile.resolver.ts (from resolve blocks)

angular.module('routingApp', ['ngRoute', 'ui.router'])

// ── Controllers ───────────────────────────────────────────────

.controller('HomeController', ['$scope', function($scope) {
  $scope.message = 'Welcome home';
}])

.controller('UserListController', ['$scope', '$http', function($scope, $http) {
  $scope.users = [];
  $scope.load = function() {
    $http.get('/api/users').then(function(res) {
      $scope.users = res.data;
    });
  };
  $scope.load();
}])

.controller('UserDetailController', ['$scope', '$http', '$routeParams', function($scope, $http, $routeParams) {
  $scope.user = null;
  $http.get('/api/users/' + $routeParams.id).then(function(res) {
    $scope.user = res.data;
  });
}])

.controller('UserEditController', ['$scope', '$http', '$routeParams', function($scope, $http, $routeParams) {
  $scope.userId = $routeParams.id;
  $scope.save = function() {
    $http.put('/api/users/' + $scope.userId, $scope.user).then(function() {
      // redirect on save
    });
  };
}])

.controller('DashboardController', ['$scope', 'userData', function($scope, userData) {
  // userData comes from resolve block — injected directly
  $scope.userData = userData;
}])

.controller('AdminController', ['$scope', 'adminProfile', function($scope, adminProfile) {
  $scope.profile = adminProfile;
  $scope.users = [];
  $scope.roles = [];
  $scope.settings = {};
  $scope.auditLog = [];
}])

// ── ngRoute config ────────────────────────────────────────────

.config(['$routeProvider', function($routeProvider) {
  $routeProvider

    // Default redirect — otherwise must become Angular wildcard + redirectTo
    .otherwise({
      redirectTo: '/home'
    })

    // Static home route
    .when('/home', {
      controller: 'HomeController',
      templateUrl: 'views/home.html'
    })

    // List route — no params
    .when('/users', {
      controller: 'UserListController',
      templateUrl: 'views/users.html'
    })

    // Route with single path param
    .when('/users/:id', {
      controller: 'UserDetailController',
      templateUrl: 'views/user-detail.html'
    })

    // Route with nested path params
    .when('/users/:id/edit', {
      controller: 'UserEditController',
      templateUrl: 'views/user-edit.html'
    })

    // Static route — no controller, no templateUrl
    .when('/about', {
      templateUrl: 'views/about.html'
    })

    // Route with resolve block — must generate resolver stub
    .when('/dashboard', {
      controller: 'DashboardController',
      templateUrl: 'views/dashboard.html',
      resolve: {
        userData: ['$http', function($http) {
          return $http.get('/api/me').then(function(res) { return res.data; });
        }]
      }
    });
}])

// ── ui-router config ──────────────────────────────────────────

.config(['$stateProvider', '$urlRouterProvider', function($stateProvider, $urlRouterProvider) {

  $urlRouterProvider.otherwise('/home');

  $stateProvider

    // Abstract parent state — no component, sets up nested outlet
    .state('app', {
      abstract: true,
      url: '/app',
      templateUrl: 'views/layout.html'
    })

    // Child state of app
    .state('app.home', {
      url: '/home',
      controller: 'HomeController',
      templateUrl: 'views/home.html'
    })

    // Child state with list
    .state('app.users', {
      url: '/users',
      controller: 'UserListController',
      templateUrl: 'views/users.html'
    })

    // Child state with param
    .state('app.users.detail', {
      url: '/:userId',
      controller: 'UserDetailController',
      templateUrl: 'views/user-detail.html'
    })

    // State with resolve block — must generate resolver stub
    .state('app.admin', {
      url: '/admin',
      controller: 'AdminController',
      templateUrl: 'views/admin.html',
      resolve: {
        adminProfile: ['$http', function($http) {
          return $http.get('/api/admin/profile').then(function(res) { return res.data; });
        }]
      }
    });
}]);