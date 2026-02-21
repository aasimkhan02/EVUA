angular.module('realApp')
  .service('AuthService', function($http) {
    this.login = function(user) {
      return $http.post('/api/login', user);
    };
  });
