angular.module('app').controller('PriceCtrl', function ($scope) {
  $scope.price = 10;
  $scope.total = 0;

  $scope.$watch('price', function (newVal, oldVal) {
    if (newVal !== oldVal) {
      $scope.total = newVal * 1.18; // add tax
    }
  });
});
