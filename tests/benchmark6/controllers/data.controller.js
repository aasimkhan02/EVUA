(function () {
  'use strict';

  angular
    .module('asyncApp')
    .controller('DataController', function ($scope, ApiService) {
      $scope.users = [];
      $scope.loading = false;
      $scope.error = false;

      $scope.load = function () {
        $scope.loading = true;
        $scope.error = false;

        ApiService.fetchUsers()
          .then(function (users) {
            $scope.users = users;
          })
          .catch(function () {
            $scope.error = true;
          })
          .finally(function () {
            $scope.loading = false;
          });
      };
    });
})();
