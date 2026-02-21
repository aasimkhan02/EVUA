angular.module('app').controller('ProfileCtrl', function ($scope, $stateParams) {
  $scope.id = $stateParams.id;
});
