// ── NavController ──────────────────────────────────────────────
angular.module('adminApp')
.controller('NavController', ['$scope', '$location', function($scope, $location) {
  $scope.isActive = function(path) {
    return $location.path() === path;
  };
}]);
