(function () {
  'use strict';

  angular
    .module('watcherApp')
    .controller('WatcherController', function ($scope) {
      $scope.user = {
        name: '',
        age: 0
      };

      $scope.normalizedName = '';
      $scope.status = 'idle';

      // Shallow watch
      $scope.$watch('user.name', function (newVal, oldVal) {
        if (newVal !== oldVal) {
          $scope.normalizedName = (newVal || '').trim().toUpperCase();
        }
      });

      // Deep watch
      $scope.$watch(
        'user',
        function (newVal, oldVal) {
          if (newVal !== oldVal) {
            if (newVal.age > 18) {
              $scope.status = 'adult';
            } else {
              $scope.status = 'minor';
            }
          }
        },
        true
      );

      // Mutation inside watch (nasty pattern)
      $scope.$watch('normalizedName', function (val) {
        if (val && val.length > 10) {
          $scope.status = 'long-name';
        }
      });
    });
})();
