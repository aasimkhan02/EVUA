(function () {
  'use strict';

  angular.module('asyncApp').service('ApiService', function ($http, $q) {
    this.fetchUsers = function () {
      return $http.get('/api/users')
        .then(function (res) {
          return res.data;
        })
        .catch(function () {
          return $q.reject('network-error');
        });
    };
  });
})();
