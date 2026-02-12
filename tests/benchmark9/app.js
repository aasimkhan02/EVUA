var app = angular.module('legacyDashboardApp', ['ngRoute']);

app.config(function($routeProvider, $locationProvider) {
  $routeProvider
    .when('/dashboard', {
      templateUrl: 'templates/dashboard.html',
      controller: 'DashboardController'
    })
    .when('/users', {
      templateUrl: 'templates/users.html',
      controller: 'UserController'
    })
    .when('/admin', {
      templateUrl: 'templates/admin.html',
      controller: 'AdminController'
    })
    .otherwise({
      redirectTo: '/dashboard'
    });

  $locationProvider.hashPrefix('!');
});
