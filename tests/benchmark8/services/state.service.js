(function () {
  'use strict';

  angular.module('dashboardApp').service('StateService', function () {
    var state = {
      user: { name: 'alice' },
      clicks: 0
    };

    this.getState = function () {
      return state;
    };

    this.increment = function () {
      state.clicks++;
    };
  });
})();
