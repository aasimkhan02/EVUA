// bench-02-multi-service/repo/src/app.js
// Tests: ServiceDetector finds all 3 registrations (2 services + 1 factory)
// Expected: all 3 SAFE, no MANUAL, correct component file attribution

angular.module('multiServiceApp', [])

// ── UserService ───────────────────────────────────────────────
// Plain DI syntax (no array) — tests non-array detection path
.service('UserService', function($http) {

  this.getAll = function() {
    return $http.get('/api/users');
  };

  this.getById = function(id) {
    return $http.get('/api/users/' + id);
  };

  this.create = function(user) {
    return $http.post('/api/users', user);
  };
})

// ── NotificationService ───────────────────────────────────────
// DI array syntax
.service('NotificationService', ['$http', function($http) {

  this.send = function(payload) {
    return $http.post('/api/notifications', payload);
  };

  this.getUnread = function() {
    return $http.get('/api/notifications/unread');
  };
}])

// ── ConfigFactory ─────────────────────────────────────────────
// factory keyword — engine must treat same as service
.factory('ConfigFactory', ['$http', function($http) {

  var config = null;

  return {
    load: function() {
      return $http.get('/api/config').then(function(res) {
        config = res.data;
        return config;
      });
    },
    get: function() {
      return config;
    }
  };
}])

// ── AppController ─────────────────────────────────────────────
// Simple controller that uses the services — should be SAFE
.controller('AppController', ['$scope', 'UserService', 'ConfigFactory',
  function($scope, UserService, ConfigFactory) {

  $scope.users = [];
  $scope.config = null;

  $scope.init = function() {
    UserService.getAll().then(function(res) {
      $scope.users = res.data;
    });
    ConfigFactory.load().then(function(cfg) {
      $scope.config = cfg;
    });
  };

  $scope.init();
}]);