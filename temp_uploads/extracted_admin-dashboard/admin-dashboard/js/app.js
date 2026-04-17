angular.module('adminApp', ['ngRoute'])

.config(['$routeProvider', '$locationProvider', function($routeProvider) {
  $routeProvider
    .when('/dashboard', {
      templateUrl: 'views/dashboard.html',
      controller: 'DashboardController',
      controllerAs: 'dash'
    })
    .when('/users', {
      templateUrl: 'views/users.html',
      controller: 'UserController',
      controllerAs: 'uc'
    })
    .when('/users/new', {
      templateUrl: 'views/user-form.html',
      controller: 'UserFormController',
      controllerAs: 'ufc'
    })
    .when('/users/edit/:id', {
      templateUrl: 'views/user-form.html',
      controller: 'UserFormController',
      controllerAs: 'ufc'
    })
    .when('/activity', {
      templateUrl: 'views/activity.html',
      controller: 'ActivityController',
      controllerAs: 'ac'
    })
    .otherwise({ redirectTo: '/dashboard' });
}]);
