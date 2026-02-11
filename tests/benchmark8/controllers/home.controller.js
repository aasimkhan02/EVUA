(function () {
  'use strict';

  angular
    .module('dashboardApp')
    .controller('HomeController', function ($scope, StateService) {
      $scope.state = StateService.getState();

      // Anti-pattern: watcher on service state
      $scope.$watch(
        function () {
          return StateService.getState().clicks;
        },
        function (newVal) {
          $scope.localClicks = newVal;
        }
      );
    });
})();
