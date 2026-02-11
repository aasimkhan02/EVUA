(function () {
  'use strict';

  angular
    .module('dashboardApp')
    .controller('StatsController', function ($scope, StateService) {
      $scope.state = StateService.getState();

      $scope.inc = function () {
        StateService.increment();
      };
    });
})();
