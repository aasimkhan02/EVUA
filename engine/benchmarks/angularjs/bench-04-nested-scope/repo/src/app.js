// bench-04-nested-scope/repo/src/app.js
// Tests: controller with BOTH nested $scope.$new() AND deep $watch
// Both are independent MANUAL signals — engine should flag MANUAL on first hit
// Also tests: a completely clean controller in same file stays SAFE
// ENGINE STRESS: has_nested_scopes detection via $scope.$new() call pattern

angular.module('nestedScopeApp', [])

// ── DashboardController ───────────────────────────────────────
// Has nested scope AND deep watch — double MANUAL trigger
// ENGINE MUST: detect has_nested_scopes=true AND watch_depths=['deep']
// ENGINE MUST: emit RiskLevel.MANUAL (either signal is sufficient)
.controller('DashboardController', ['$scope', '$http', function($scope, $http) {

  $scope.panels = [];
  $scope.activePanel = null;
  $scope.filters = { status: 'all', dateRange: null };

  // Deep $watch on complex filter object — MANUAL
  $scope.$watch('filters', function(newFilters, oldFilters) {
    if (newFilters !== oldFilters) {
      $scope.applyFilters(newFilters);
    }
  }, true);  // <-- third arg true = deep watch

  // Nested scope creation — MANUAL
  $scope.openPanel = function(panel) {
    var childScope = $scope.$new();
    childScope.panel = panel;
    childScope.close = function() {
      childScope.$destroy();
    };
    $scope.activePanel = childScope;
  };

  $scope.applyFilters = function(filters) {
    $http.get('/api/dashboard', { params: filters }).then(function(res) {
      $scope.panels = res.data;
    });
  };

  $scope.applyFilters($scope.filters);
}])

// ── ReportController ──────────────────────────────────────────
// ONLY has nested scope (no deep watch) — still MANUAL
// Tests: has_nested_scopes alone is sufficient for MANUAL
.controller('ReportController', ['$scope', '$http', function($scope, $http) {

  $scope.reports = [];
  $scope.currentReport = null;

  $scope.viewReport = function(report) {
    // Nested scope for isolated report view
    var reportScope = $scope.$new();
    reportScope.data = report;
    $scope.currentReport = reportScope;
  };

  $http.get('/api/reports').then(function(res) {
    $scope.reports = res.data;
  });
}])

// ── StatusController ──────────────────────────────────────────
// Completely clean — no watch, no nested scope, minimal writes
// ENGINE MUST: stay SAFE despite dangerous controllers in same file
.controller('StatusController', ['$scope', '$http', function($scope, $http) {

  $scope.status = 'loading';

  $http.get('/api/status').then(function(res) {
    $scope.status = res.data.status;
  });
}]);