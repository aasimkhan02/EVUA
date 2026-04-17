// ── UserController ─────────────────────────────────────────────
angular.module('adminApp')
.controller('UserController', ['$scope', '$location', 'UserService',
  function($scope, $location, UserService) {
  var vm = this;

  vm.users       = [];
  vm.loading     = true;
  vm.searchQuery = '';
  vm.roleFilter  = '';
  vm.statusFilter= '';
  vm.sortField   = 'name';
  vm.sortReverse = false;
  vm.currentPage = 1;
  vm.pageSize    = 5;
  vm.toast       = null;
  vm.confirmDelete = null;

  // Load users — simulates GET /api/users
  UserService.getAll().then(function(users) {
    vm.users   = users;
    vm.loading = false;
  });

  vm.sortBy = function(field) {
    if (vm.sortField === field) {
      vm.sortReverse = !vm.sortReverse;
    } else {
      vm.sortField   = field;
      vm.sortReverse = false;
    }
  };

  vm.sortIcon = function(field) {
    if (vm.sortField !== field) return '↕';
    return vm.sortReverse ? '↑' : '↓';
  };

  vm.filteredUsers = function() {
    return vm.users.filter(function(u) {
      var q = (vm.searchQuery || '').toLowerCase();
      var matchSearch = !q || u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q);
      var matchRole   = !vm.roleFilter   || u.role   === vm.roleFilter;
      var matchStatus = !vm.statusFilter || u.status === vm.statusFilter;
      return matchSearch && matchRole && matchStatus;
    });
  };

  vm.pagedUsers = function() {
    var all   = vm.filteredUsers();
    var start = (vm.currentPage - 1) * vm.pageSize;
    return all.slice(start, start + vm.pageSize);
  };

  vm.totalPages = function() {
    return Math.ceil(vm.filteredUsers().length / vm.pageSize) || 1;
  };

  vm.pages = function() {
    var arr = [];
    for (var i = 1; i <= vm.totalPages(); i++) arr.push(i);
    return arr;
  };

  vm.goToPage = function(p) {
    if (p >= 1 && p <= vm.totalPages()) vm.currentPage = p;
  };

  vm.resetFilters = function() {
    vm.searchQuery  = '';
    vm.roleFilter   = '';
    vm.statusFilter = '';
    vm.currentPage  = 1;
  };

  vm.editUser = function(id) {
    $location.path('/users/edit/' + id);
  };

  vm.askDelete = function(user) {
    vm.confirmDelete = user;
  };

  vm.cancelDelete = function() {
    vm.confirmDelete = null;
  };

  vm.confirmDeleteUser = function() {
    var user = vm.confirmDelete;
    vm.confirmDelete = null;
    UserService.remove(user.id).then(function() {
      vm.users = vm.users.filter(function(u) { return u.id !== user.id; });
      vm.showToast(user.name + ' was removed.', 'success');
    });
  };

  vm.showToast = function(msg, type) {
    vm.toast = { msg: msg, type: type || 'info' };
    $scope.$$phase || $scope.$apply();
    setTimeout(function() {
      vm.toast = null;
      $scope.$apply();
    }, 3200);
  };

  vm.getRoles    = function() { return UserService.getRoles(); };
  vm.getStatuses = function() { return UserService.getStatuses(); };
}])


// ── UserFormController ─────────────────────────────────────────
.controller('UserFormController', ['$scope', '$location', '$routeParams', 'UserService',
  function($scope, $location, $routeParams, UserService) {
  var vm = this;

  vm.isEdit    = !!$routeParams.id;
  vm.loading   = vm.isEdit;
  vm.saving    = false;
  vm.errors    = {};
  vm.user      = { status: 'active', role: 'Viewer' };
  vm.roles     = UserService.getRoles();
  vm.statuses  = UserService.getStatuses();

  if (vm.isEdit) {
    UserService.getById($routeParams.id).then(function(user) {
      if (!user) { $location.path('/users'); return; }
      vm.user    = angular.copy(user);
      vm.loading = false;
    });
  }

  vm.validate = function() {
    vm.errors = {};
    if (!vm.user.name  || vm.user.name.trim().length < 2)
      vm.errors.name = 'Name must be at least 2 characters.';
    if (!vm.user.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(vm.user.email))
      vm.errors.email = 'Enter a valid email address.';
    if (!vm.user.role)
      vm.errors.role = 'Select a role.';
    return Object.keys(vm.errors).length === 0;
  };

  vm.submit = function() {
    if (!vm.validate()) return;
    vm.saving = true;

    var action = vm.isEdit
      ? UserService.update($routeParams.id, vm.user)
      : UserService.create(vm.user);

    action.then(function() {
      $location.path('/users');
    }).catch(function(err) {
      vm.saving = false;
      vm.errors.server = err;
    });
  };

  vm.cancel = function() {
    $location.path('/users');
  };
}]);
