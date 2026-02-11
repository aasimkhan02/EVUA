(function () {
  'use strict';

  angular
    .module('dashboardApp')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/home', {
          templateUrl: 'views/home.html',
          controller: 'HomeController'
        })
        .when('/stats', {
          templateUrl: 'views/stats.html',
          controller: 'StatsController'
        })
        .otherwise({ redirectTo: '/home' });
    });
})();
