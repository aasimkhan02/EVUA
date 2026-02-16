app.service('UserService', function($http, $q) {
  var cachedUsers = null;

  this.fetchUsers = function() {
    if (cachedUsers) {
      return $q.resolve(cachedUsers);
    }

    return $http.get('https://jsonplaceholder.typicode.com/users')
      .then(function(res) {
        cachedUsers = res.data;
        return cachedUsers;
      })
      .catch(function(err) {
        console.error('UserService.fetchUsers failed', err);
        return $q.reject(err);
      });
  };

  this.updateUserLocal = function(user) {
    if (!cachedUsers) return;
    var idx = cachedUsers.findIndex(function(u) { return u.id === user.id; });
    if (idx >= 0) {
      cachedUsers[idx] = angular.copy(user);
    }
  };
});

app.service('MetricsService', function($q, $timeout) {

  this.loadDashboardMetrics = function() {
    return this._loadCounts()
      .then(this._loadTrends)
      .then(this._combineMetrics);
  };

  this._loadCounts = function() {
    var defer = $q.defer();
    $timeout(function() {
      defer.resolve({ users: 42, activeSessions: 7 });
    }, 300);
    return defer.promise;
  };

  this._loadTrends = function(counts) {
    var defer = $q.defer();
    $timeout(function() {
      counts.trends = {
        usersGrowth: '+5%',
        sessionsGrowth: '-2%'
      };
      defer.resolve(counts);
    }, 300);
    return defer.promise;
  };

  this._combineMetrics = function(metrics) {
    var defer = $q.defer();
    $timeout(function() {
      metrics.generatedAt = new Date();
      defer.resolve(metrics);
    }, 200);
    return defer.promise;
  };
});
