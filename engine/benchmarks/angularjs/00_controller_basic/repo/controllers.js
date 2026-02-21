angular.module('app').controller('MainCtrl', function ($scope) {
  $scope.title = 'Hello EVUA';
  $scope.count = 0;

  $scope.increment = function () {
    $scope.count += 1;
  };
});
