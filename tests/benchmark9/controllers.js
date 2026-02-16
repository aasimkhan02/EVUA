app.controller('DashboardController', function($scope, MetricsService) {
  $scope.loading = true;
  $scope.metrics = {};
  $scope.error = null;
  $scope.filters = { showTrends: true };

  $scope.refreshMetrics = function() {
    $scope.loading = true;
    MetricsService.loadDashboardMetrics()
      .then(function(data) {
        $scope.metrics = data;
      })
      .catch(function() {
        $scope.error = 'Failed to load metrics';
      })
      .finally(function() {
        $scope.loading = false;
      });
  };

  $scope.$watch('filters.showTrends', function(newVal) {
    console.log('showTrends toggled:', newVal);
  });

  $scope.refreshMetrics();
});

app.controller('UserController', function($scope, UserService) {
  $scope.users = [];
  $scope.selectedUser = null;
  $scope.form = {};
  $scope.error = null;
  $scope.loading = false;

  $scope.loadUsers = function() {
    $scope.loading = true;
    UserService.fetchUsers()
      .then(function(data) {
        $scope.users = data;
      })
      .catch(function() {
        $scope.error = 'Could not load users';
      })
      .finally(function() {
        $scope.loading = false;
      });
  };

  $scope.selectUser = function(user) {
    $scope.selectedUser = angular.copy(user);
    $scope.form = angular.copy(user);
  };

  $scope.saveUser = function() {
    if (!$scope.form || !$scope.form.id) return;
    UserService.updateUserLocal($scope.form);
    $scope.selectedUser = angular.copy($scope.form);
  };

  $scope.$watch('selectedUser', function(newVal, oldVal) {
    if (newVal && oldVal && newVal.email !== oldVal.email) {
      console.log('User email changed (deep watch)');
    }
  }, true);

  var tempScope = $scope.$new();
  tempScope.resetForm = function() {
    $scope.form = {};
  };

  $scope.loadUsers();
});

app.controller('AdminController', function($scope, UserService) {
  $scope.stats = {
    totalUsers: 0,
    flaggedUsers: []
  };
  $scope.auditLog = [];
  $scope.loading = false;

  $scope.recalculateStats = function() {
    $scope.loading = true;
    UserService.fetchUsers()
      .then(function(users) {
        $scope.stats.totalUsers = users.length;
        $scope.stats.flaggedUsers = users.filter(function(u) {
          return u.email && u.email.indexOf('.biz') > -1;
        });
        $scope.auditLog.push({
          at: new Date(),
          action: 'Recalculated user stats'
        });
      })
      .finally(function() {
        $scope.loading = false;
      });
  };

  $scope.flagUser = function(user) {
    if (!user) return;
    if ($scope.stats.flaggedUsers.indexOf(user) === -1) {
      $scope.stats.flaggedUsers.push(user);
    }
    $scope.auditLog.push({
      at: new Date(),
      action: 'Flagged user ' + user.id
    });
  };

  $scope.recalculateStats();
});
