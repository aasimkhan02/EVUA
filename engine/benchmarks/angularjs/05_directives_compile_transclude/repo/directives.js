angular.module('app').directive('myPanel', function ($compile) {
  return {
    restrict: 'E',
    scope: {
      title: '@'
    },
    transclude: true,
    template: '<div class="panel"><h3>{{ title }}</h3><div ng-transclude></div></div>',
    link: function (scope, element) {
      var content = '<p>Compiled at runtime</p>';
      var el = $compile(content)(scope);
      element.append(el);
    }
  };
});
