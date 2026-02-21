angular.module('app').service('UserService', function ($http, $q) {
  this.getUsers = function () {
    var d = $q.defer();
    $http.get('/api/users')
      .then(function (res) { d.resolve(res.data); })
      .catch(function (e) { d.reject(e); });
    return d.promise;
  };
});
