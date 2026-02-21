angular.module('app').service('UserService', function ($http, $q) {
  this.getUsers = function () {
    var deferred = $q.defer();

    $http.get('/api/users')
      .then(function (res) {
        deferred.resolve(res.data);
      })
      .catch(function (err) {
        deferred.reject(err);
      });

    return deferred.promise;
  };
});
