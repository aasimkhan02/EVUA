angular.module('realApp').config(function($routeProvider) {
  $routeProvider
    .when('/login', {
      templateUrl: 'app/templates/login.html',
      controller: 'LoginCtrl'
    })
    .when('/dashboard', {
      templateUrl: 'app/templates/dashboard.html',
      controller: 'DashboardCtrl'
    });
});
