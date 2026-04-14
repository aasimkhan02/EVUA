angular.module('adminApp')

.factory('StatsService', ['$http', '$q', 'UserService', function($http, $q, UserService) {

  function _delay(data, ms) {
    var deferred = $q.defer();
    setTimeout(function() { deferred.resolve(data); }, ms || 280);
    return deferred.promise;
  }

  // Simulates GET /api/dashboard
  function getDashboardStats() {
    return UserService.getAll().then(function(users) {
      var active   = users.filter(function(u) { return u.status === 'active'; }).length;
      var inactive = users.filter(function(u) { return u.status === 'inactive'; }).length;
      var pending  = users.filter(function(u) { return u.status === 'pending'; }).length;
      var admins   = users.filter(function(u) { return u.role === 'Admin'; }).length;

      return {
        totalUsers:   users.length,
        activeUsers:  active,
        inactiveUsers: inactive,
        pendingUsers: pending,
        adminCount:   admins,
        growthRate:   '+12.4%',
        avgSessionMin: 34,
        uptimePct:    99.7
      };
    });
  }

  // Simulates GET /api/dashboard/chart
  function getChartData() {
    var months = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'];
    var logins  = [42, 58, 53, 70, 63, 89, 74, 95, 110];
    var signups = [5,  8,  6,  12, 9,  14, 11, 17, 22];
    return _delay({ months: months, logins: logins, signups: signups }, 180);
  }

  // Simulates GET /api/activity
  function getRecentActivity() {
    var events = [
      { user: 'Alice Nguyen',  action: 'Updated role',      target: 'Ben Okafor',   time: '2 min ago',   icon: 'edit',   color: 'blue' },
      { user: 'Fatima Malik',  action: 'Deleted user',      target: 'Old Account',  time: '14 min ago',  icon: 'delete', color: 'red' },
      { user: 'David Park',    action: 'Logged in',         target: '',             time: '1 hour ago',  icon: 'login',  color: 'green' },
      { user: 'Alice Nguyen',  action: 'Created user',      target: 'Elan Morris',  time: '3 hours ago', icon: 'create', color: 'purple' },
      { user: 'George Ito',    action: 'Status changed',    target: 'inactive',     time: '1 day ago',   icon: 'status', color: 'amber' },
      { user: 'Hana Svensson', action: 'Logged in',         target: '',             time: '1 day ago',   icon: 'login',  color: 'green' },
      { user: 'Clara Reyes',   action: 'Password reset',    target: '',             time: '2 days ago',  icon: 'lock',   color: 'blue' },
      { user: 'Ben Okafor',    action: 'Updated profile',   target: '',             time: '3 days ago',  icon: 'edit',   color: 'blue' }
    ];
    return _delay(events, 200);
  }

  return {
    getDashboardStats:  getDashboardStats,
    getChartData:       getChartData,
    getRecentActivity:  getRecentActivity
  };
}]);
