(function () {
  'use strict';

  angular
    .module('mediumApp')
    .controller('AdminController', function ($scope, AdminService) {
      $scope.maintenance = AdminService.isMaintenance();

      $scope.toggle = function () {
        $scope.maintenance = AdminService.toggle();
      };
    });
})();
