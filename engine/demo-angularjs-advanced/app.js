angular.module('advancedApp', [])

  .service('UserService', function($http) {
    this.fetch = function() {
      return $http.get('/api/users');
    };
  })

  .factory('Logger', function() {
    return {
      log: function(msg) {
        console.log(msg);
      }
    };
  })

  .controller('UserController', function($scope, UserService, Logger) {
    $scope.users = [];
    $scope.query = "";

    $scope.load = function() {
      UserService.fetch().then(function(res) {
        $scope.users = res.data;
      });
    };

    $scope.add = function() {
      $scope.users.push({ name: $scope.query });
      Logger.log("Added user");
      $scope.query = "";
    };

    $scope.$watch('query', function(newVal) {
      Logger.log("Query changed: " + newVal);
    });
  })

  .controller('AdminController', function($scope) {
    $scope.isAdmin = true;

    $scope.toggle = function() {
      $scope.isAdmin = !$scope.isAdmin;
    };
  });
