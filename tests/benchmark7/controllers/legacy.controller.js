(function () {
  'use strict';

  angular
    .module('legacyApp')
    .controller('LegacyController', function ($scope) {
      $scope.user = { name: 'Alice' };
      $scope.clicks = 0;

      $scope.increment = function () {
        $scope.clicks++;
      };
    });
})();
