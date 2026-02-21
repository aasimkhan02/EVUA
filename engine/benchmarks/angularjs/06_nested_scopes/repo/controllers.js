angular.module('app')
  .controller('ParentCtrl', function ($scope) {
    $scope.shared = { count: 0 };
  })
  .controller('ChildCtrl', function ($scope) {
    $scope.shared.count += 1; // mutates inherited object
  });
