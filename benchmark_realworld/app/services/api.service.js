angular.module('realApp')
  .service('ApiService', function($http, $q) {
    this.getUsers = function() {
      return $http.get('/api/users');
    };

    this.loadAll = function() {
      var p1 = $http.get('/api/a');
      var p2 = $http.get('/api/b');
      return $q.all([p1, p2]);
    };
  });
