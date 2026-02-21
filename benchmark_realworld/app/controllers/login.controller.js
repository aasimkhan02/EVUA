angular.module('realApp')
  .controller('LoginCtrl', function($scope, AuthService) {
    $scope.user = {};
    $scope.error = null;

    $scope.$watch('user.username', function(nv, ov) {
      if (!nv) $scope.error = "Username required";
    });

    $scope.login = function() {
      AuthService.login($scope.user)
        .then(function() {
          console.log("Logged in");
        });
    };
  });
