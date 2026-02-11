angular.module('demoApp', [])

  .service('UserService', function($http) {
    this.saveUser = function(user) {
      return $http.post('/api/user', user);
    };
  })

  .controller('UserController', function($scope, UserService) {
    $scope.users = [];
    $scope.newUser = { name: "" };

    $scope.load = function() {
      // mock data
      $scope.users = [
        { name: "Aasim" },
        { name: "Alex" }
      ];
    };

    $scope.add = function() {
      UserService.saveUser($scope.newUser);
      $scope.users.push({ name: $scope.newUser.name });
      $scope.newUser.name = "";
    };
  })

  .controller('AdminController', function($scope) {
    $scope.isAdmin = true;

    $scope.toggleAdmin = function() {
      $scope.isAdmin = !$scope.isAdmin;
    };
  });
