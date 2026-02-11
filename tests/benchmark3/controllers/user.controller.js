(function () {
  'use strict';

  angular
    .module('mediumApp')
    .controller('UserController', function ($scope, UserService) {
      $scope.username = '';
      $scope.isLoggedIn = false;
      $scope.user = null;

      $scope.login = function () {
        if (!$scope.username) return;
        $scope.user = UserService.login($scope.username);
        $scope.isLoggedIn = true;
      };
    });
})();
