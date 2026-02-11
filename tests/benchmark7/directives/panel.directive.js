(function () {
  'use strict';

  angular
    .module('legacyApp')
    .directive('legacyPanel', function () {
      return {
        restrict: 'E',
        transclude: true,
        scope: {
          title: '@'
        },
        template:
          '<div class="panel">' +
          '  <h3>{{ title }}</h3>' +
          '  <div ng-transclude></div>' +
          '</div>',
        link: function (scope) {
          // implicit scope inheritance inside transclusion
        }
      };
    });
})();
