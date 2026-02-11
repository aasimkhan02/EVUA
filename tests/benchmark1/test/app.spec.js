describe('HelloController', function () {
  beforeEach(module('helloApp'));

  let $controller;
  let $rootScope;

  beforeEach(inject(function (_$controller_, _$rootScope_) {
    $controller = _$controller_;
    $rootScope = _$rootScope_;
  }));

  it('should set message on scope', function () {
    const $scope = $rootScope.$new();
    $controller('HelloController', { $scope });

    expect($scope.message).toBe('Hello AngularJS');
  });
});
