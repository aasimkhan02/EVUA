angular.module('adminApp')
.controller('ActivityController', ['$scope', 'StatsService', function($scope, StatsService) {
  var vm = this;

  vm.events   = [];
  vm.loading  = true;
  vm.filter   = 'all';

  // Simulates GET /api/activity
  StatsService.getRecentActivity().then(function(events) {
    vm.events  = events;
    vm.loading = false;
  });

  vm.filteredEvents = function() {
    if (vm.filter === 'all') return vm.events;
    return vm.events.filter(function(e) { return e.icon === vm.filter; });
  };

  vm.actionTypes = [
    { key: 'all',    label: 'All' },
    { key: 'login',  label: 'Logins' },
    { key: 'create', label: 'Creations' },
    { key: 'edit',   label: 'Edits' },
    { key: 'delete', label: 'Deletions' }
  ];

  vm.iconSymbol = function(icon) {
    var map = { login: '→', create: '+', edit: '✎', delete: '✕', lock: '⚿', status: '◈' };
    return map[icon] || '·';
  };
}]);
