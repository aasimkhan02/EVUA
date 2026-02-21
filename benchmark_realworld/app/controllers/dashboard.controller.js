angular.module('realApp')
  .controller('DashboardCtrl', function($scope, ApiService) {
    $scope.users = [];

    ApiService.getUsers().then(function(res) {
      $scope.users = res.data;
    });

    $scope.$watch('users', function(nv, ov) {
      console.log("Users changed");
    }, true); // deep watch

    var child = $scope.$new(); // nested scope
    child.temp = 123;
  });
