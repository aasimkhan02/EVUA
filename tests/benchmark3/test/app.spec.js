describe('Medium App Controllers', function () {
  beforeEach(module('mediumApp'));

  let $controller;
  let $rootScope;
  let UserService;
  let AdminService;

  beforeEach(inject(function (_$controller_, _$rootScope_, _UserService_, _AdminService_) {
    $controller = _$controller_;
    $rootScope = _$rootScope_;
    UserService = _UserService_;
    AdminService = _AdminService_;
  }));

  it('should login user and expose name', function () {
    const $scope = $rootScope.$new();
    $controller('UserController', { $scope, UserService });

    $scope.username = 'Alice';
    $scope.login();

    expect($scope.isLoggedIn).toBe(true);
    expect($scope.user.name).toBe('Alice');
  });

  it('should toggle maintenance mode', function () {
    const $scope = $rootScope.$new();
    $controller('AdminController', { $scope, AdminService });

    const initial = $scope.maintenance;
    $scope.toggle();

    expect($scope.maintenance).toBe(!initial);
  });
});
