/**
 * bench-08-routing-advanced
 * Tests: nested children, lazy loading, guards, redirects, onEnter/onExit, route ordering
 */

angular.module('benchApp', ['ui.router'])

// ── Controller definitions (required for ControllerToComponent rule) ──────
.controller('HomeController', ['$scope', function($scope) {
  $scope.title = 'Home';
}])

.controller('LoginController', ['$scope', '$state', function($scope, $state) {
  $scope.login = function() { $state.go('home'); };
}])

.controller('OrdersController', ['$scope', '$http', function($scope, $http) {
  $http.get('/api/orders').then(function(r) { $scope.orders = r.data; });
}])

.controller('ProfileController', ['$scope', '$stateParams', function($scope, $stateParams) {
  $scope.username = $stateParams.username;
}])

.controller('SettingsController', ['$scope', function($scope) {
  $scope.prefs = {};
}])

.controller('UserDetailController', ['$scope', '$stateParams', '$http',
  function($scope, $stateParams, $http) {
    $http.get('/api/users/' + $stateParams.userId).then(function(r) {
      $scope.user = r.data;
    });
  }
])

.controller('UserEditController', ['$scope', '$stateParams', '$http',
  function($scope, $stateParams, $http) {
    $scope.userId = $stateParams.userId;
  }
])

.controller('AdminDashboardController', ['$scope', '$http', function($scope, $http) {
  $http.get('/api/admin/stats').then(function(r) { $scope.stats = r.data; });
}])

// ── Route configuration ───────────────────────────────────────────────────
.config(['$stateProvider', '$urlRouterProvider',
  function($stateProvider, $urlRouterProvider) {

    $urlRouterProvider.otherwise('/home');

    $stateProvider

      // Feature 2: abstract root shell → lazy-loaded AppModule
      .state('app', {
        abstract: true,
        url: '',
        templateUrl: 'shell.html'
      })

      // Feature 1 + 3: nested, no controller (componentless parent)
      .state('app.users', {
        url: '/users',
        templateUrl: 'users/list.html'
      })

      // Feature 1 + 5: deep leaf — auth guard + data resolver
      .state('app.users.detail', {
        url: '/:userId',
        controller: 'UserDetailController',
        templateUrl: 'users/detail.html',
        resolve: {
          auth: function(AuthService) { return AuthService.check(); },
          userData: function(UserService, $stateParams) {
            return UserService.get($stateParams.userId);
          }
        }
      })

      // Feature 1 + 5: sibling leaf — auth guard only
      .state('app.users.edit', {
        url: '/:userId/edit',
        controller: 'UserEditController',
        templateUrl: 'users/edit.html',
        resolve: {
          auth: function(AuthService) { return AuthService.check(); }
        }
      })

      // Feature 2: abstract admin section → lazy-loaded AdminModule
      .state('app.admin', {
        abstract: true,
        url: '/admin',
        templateUrl: 'admin/shell.html'
      })

      // Feature 1 + 5: admin dashboard — session guard + stats resolver
      .state('app.admin.dashboard', {
        url: '/dashboard',
        controller: 'AdminDashboardController',
        templateUrl: 'admin/dashboard.html',
        resolve: {
          session: function(SessionService) { return SessionService.validate(); },
          stats: function(StatsService) { return StatsService.load(); }
        }
      })

      // Feature 6: onEnter + onExit hooks
      .state('orders', {
        url: '/orders',
        controller: 'OrdersController',
        templateUrl: 'orders/list.html',
        onEnter: function($rootScope) { $rootScope.inOrders = true; },
        onExit:  function($rootScope) { $rootScope.inOrders = false; }
      })

      // Feature 6: redirectTo annotation
      .state('login', {
        url: '/login',
        controller: 'LoginController',
        templateUrl: 'login.html',
        redirectTo: 'home'
      })

      // Feature 7: static — must appear before param routes
      .state('home', {
        url: '/home',
        controller: 'HomeController',
        templateUrl: 'home.html'
      })

      // Feature 7: param — must appear AFTER static routes
      .state('profile', {
        url: '/profile/:username',
        controller: 'ProfileController',
        templateUrl: 'profile.html'
      })

      // Feature 5: data resolver only (no auth guard)
      .state('settings', {
        url: '/settings',
        controller: 'SettingsController',
        templateUrl: 'settings.html',
        resolve: {
          prefs: function(PrefsService) { return PrefsService.load(); }
        }
      });
  }
]);