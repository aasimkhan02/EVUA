angular.module('app').directive('myPanel', function ($compile) {
  return {
    restrict: 'E',
    scope: { title: '@' },
    transclude: true,
    template: '<div><h3>{{ title }}</h3><div ng-transclude></div></div>',
    link: function (scope, element) {
      var el = $compile('<p>Runtime compiled</p>')(scope);
      element.append(el);
    }
  };
});
