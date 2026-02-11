(function () {
  'use strict';

  angular.module('dashboardApp').filter('capitalize', function () {
    return function (input) {
      if (!input) return input;
      return input.charAt(0).toUpperCase() + input.slice(1);
    };
  });
})();
