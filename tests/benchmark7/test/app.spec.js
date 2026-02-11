describe('Legacy Directive + Controller', function () {
  beforeEach(module('legacyApp'));

  let $compile;
  let $rootScope;

  beforeEach(inject(function (_$compile_, _$rootScope_) {
    $compile = _$compile_;
    $rootScope = _$rootScope_;
  }));

  it('should render transcluded content and update parent scope', function () {
    const scope = $rootScope.$new();
    scope.user = { name: 'Bob' };
    scope.clicks = 0;
    scope.increment = function () {
      scope.clicks++;
    };

    const el = $compile(
      '<legacy-panel title="Test">' +
        '<button ng-click="increment()">Clicks: {{ clicks }}</button>' +
      '</legacy-panel>'
    )(scope);

    scope.$digest();

    expect(el.html()).toContain('Test');
    expect(scope.clicks).toBe(0);

    scope.increment();
    scope.$digest();

    expect(scope.clicks).toBe(1);
  });
});
