(function () {
  'use strict';

  angular
    .module('helloApp', [])
    .controller('HelloController', function ($scope) {
      $scope.message = 'Hello AngularJS';
    });
})();
