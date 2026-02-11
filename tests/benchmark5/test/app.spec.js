describe('Nested Components', function () {
  beforeEach(module('nestedApp'));

  let $rootScope;
  let $compile;

  beforeEach(inject(function (_$rootScope_, _$compile_) {
    $rootScope = _$rootScope_;
    $compile = _$compile_;
  }));

  it('should allow child to increment parent count via two-way binding + callback', function () {
    const scope = $rootScope.$new();
    const el = $compile('<parent-comp></parent-comp>')(scope);

    scope.$digest();

    const parentCtrl = el.controller('parentComp');
    expect(parentCtrl.count).toBe(0);

    parentCtrl.increment();
    scope.$digest();

    expect(parentCtrl.count).toBe(1);
  });
});
