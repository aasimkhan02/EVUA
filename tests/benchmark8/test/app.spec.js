describe('Mini Dashboard integration', function () {
  beforeEach(module('dashboardApp'));

  let $controller;
  let $rootScope;
  let StateService;

  beforeEach(inject(function (_$controller_, _$rootScope_, _StateService_) {
    $controller = _$controller_;
    $rootScope = _$rootScope_;
    StateService = _StateService_;
  }));

  it('should share state across controllers', function () {
    const homeScope = $rootScope.$new();
    const statsScope = $rootScope.$new();

    $controller('HomeController', { $scope: homeScope, StateService });
    $controller('StatsController', { $scope: statsScope, StateService });

    statsScope.inc();
    $rootScope.$digest();

    expect(homeScope.localClicks).toBe(1);
  });
});
