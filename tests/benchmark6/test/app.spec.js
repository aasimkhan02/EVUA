describe('DataController async flow', function () {
  beforeEach(module('asyncApp'));

  let $controller;
  let $rootScope;
  let $q;
  let ApiService;

  beforeEach(inject(function (_$controller_, _$rootScope_, _$q_, _ApiService_) {
    $controller = _$controller_;
    $rootScope = _$rootScope_;
    $q = _$q_;
    ApiService = _ApiService_;
  }));

  it('should load users and update state', function () {
    spyOn(ApiService, 'fetchUsers').and.callFake(function () {
      const d = $q.defer();
      d.resolve([{ id: 1, name: 'Alice' }]);
      return d.promise;
    });

    const $scope = $rootScope.$new();
    $controller('DataController', { $scope, ApiService });

    $scope.load();
    $rootScope.$digest();

    expect($scope.users.length).toBe(1);
    expect($scope.loading).toBe(false);
    expect($scope.error).toBe(false);
  });

  it('should set error on rejection', function () {
    spyOn(ApiService, 'fetchUsers').and.callFake(function () {
      const d = $q.defer();
      d.reject('fail');
      return d.promise;
    });

    const $scope = $rootScope.$new();
    $controller('DataController', { $scope, ApiService });

    $scope.load();
    $rootScope.$digest();

    expect($scope.error).toBe(true);
    expect($scope.loading).toBe(false);
  });
});
