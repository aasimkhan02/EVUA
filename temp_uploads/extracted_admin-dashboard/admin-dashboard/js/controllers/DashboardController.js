angular.module('adminApp')
.controller('DashboardController', ['$scope', 'StatsService', function($scope, StatsService) {
  var vm = this;

  vm.loading = true;
  vm.stats   = null;
  vm.chart   = null;
  vm.activity = [];

  // Fetch dashboard stats (simulates GET /api/dashboard)
  StatsService.getDashboardStats().then(function(data) {
    vm.stats = data;
  });

  // Fetch chart data (simulates GET /api/dashboard/chart)
  StatsService.getChartData().then(function(data) {
    vm.chart = data;
    vm.loading = false;
    _buildChart(data);
  });

  // Fetch recent activity (simulates GET /api/activity)
  StatsService.getRecentActivity().then(function(events) {
    vm.activity = events.slice(0, 5);
  });

  function _buildChart(data) {
    var maxVal = Math.max.apply(null, data.logins);
    var barW   = 28;
    var gap    = 14;
    var svgH   = 120;
    var svgW   = data.months.length * (barW + gap) - gap;

    var bars = data.months.map(function(month, i) {
      var loginH  = Math.round((data.logins[i]  / maxVal) * svgH);
      var signupH = Math.round((data.signups[i] / maxVal) * svgH);
      return {
        x:       i * (barW + gap),
        loginH:  loginH,
        signupH: signupH,
        loginY:  svgH - loginH,
        signupY: svgH - signupH,
        month:   month,
        logins:  data.logins[i],
        signups: data.signups[i]
      };
    });

    $scope.$apply(function() {
      vm.chartBars  = bars;
      vm.chartW     = svgW;
      vm.chartH     = svgH;
      vm.barW       = barW;
    });
  }

  vm.getStatusBarWidth = function(key) {
    if (!vm.stats) return '0%';
    var pct = Math.round((vm.stats[key] / vm.stats.totalUsers) * 100);
    return pct + '%';
  };
}]);
