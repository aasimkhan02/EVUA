(function () {
  'use strict';

  angular
    .module('nestedApp')
    .component('childComp', {
      bindings: {
        count: '=',
        onInc: '&'
      },
      templateUrl: 'components/child/child.template.html',
      controller: function () {
        this.inc = () => {
          this.onInc();
        };
      }
    });
})();
