angular.module('app')
  .controller('UserCtrl', function ($scope, UserService) {
    $scope.users = [];
    UserService.getUsers().then(function (users) {
      $scope.users = users;
    });
  })
  .controller('ProfileCtrl', function ($scope, $stateParams) {
    $scope.user = { id: $stateParams.id, name: 'Alice' };

    $scope.$watch('user', function () {
      console.log('User changed');
    }, true); // deep watch
  });
