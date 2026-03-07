// bench-10-service-methods — tests feature set #2 and #3
angular.module('bench10App', [])

// ── SERVICE: method names must be preserved exactly ───────────────────────
.service('NotificationService', ['$http', function($http) {

  this.getAll = function() {
    return $http.get('/api/notifications')
      .then(function(res) { return res.data; });
  };

  this.markRead = function(id) {
    return $http.put('/api/notifications/' + id, { read: true })
      .catch(function(err) {
        console.error('markRead failed', err);
        throw err;
      });
  };

  this.clear = function() {
    // local only — no HTTP
  };

}])

// ── CONTROLLER #1: ngOnInit via $scope.fn() at bottom ────────────────────
.controller('DashboardController', ['$scope', '$http', function($scope, $http) {

  $scope.items = [];
  $scope.loading = false;

  $scope.loadDashboard = function() {
    $scope.loading = true;
    $http.get('/api/dashboard')
      .then(function(res) {
        $scope.items = res.data;
        $scope.loading = false;
      });
  };

  $scope.refresh = function() {
    $scope.loadDashboard();
  };

  $scope.loadDashboard();   // top-level call → ngOnInit

}])

// ── CONTROLLER #2: no ngOnInit (no top-level call) ────────────────────────
.controller('SettingsController', ['$scope', '$http', function($scope, $http) {

  $scope.settings = {};

  $scope.saveSettings = function() {
    $http.post('/api/settings', $scope.settings)
      .then(function(res) {
        $scope.settings = res.data;
      });
  };

}]);