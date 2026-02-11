describe('WatcherController', function () {
  beforeEach(module('watcherApp'));

  let $controller;
  let $rootScope;

  beforeEach(inject(function (_$controller_, _$rootScope_) {
    $controller = _$controller_;
    $rootScope = _$rootScope_;
  }));

  it('should normalize name and update status via watchers', function () {
    const $scope = $rootScope.$new();
    $controller('WatcherController', { $scope });

    $scope.user.name = '  alice  ';
    $scope.$digest();

    expect($scope.normalizedName).toBe('ALICE');

    $scope.user.age = 20;
    $scope.$digest();

    expect($scope.status).toBe('adult');
  });

  it('should mark long-name when normalizedName is long', function () {
    const $scope = $rootScope.$new();
    $controller('WatcherController', { $scope });

    $scope.user.name = 'averyverylongname';
    $scope.$digest();

    expect($scope.status).toBe('long-name');
  });
});
