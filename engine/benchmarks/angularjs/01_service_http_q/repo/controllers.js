angular.module('app').controller('UserCtrl', function ($scope, UserService) {
  $scope.users = [];
  $scope.error = null;

  UserService.getUsers()
    .then(function (users) {
      $scope.users = users;
    })
    .catch(function (err) {
      $scope.error = 'Failed to load users';
    });
});
