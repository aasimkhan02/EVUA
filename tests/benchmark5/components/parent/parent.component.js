(function () {
  'use strict';

  angular
    .module('nestedApp')
    .component('parentComp', {
      templateUrl: 'components/parent/parent.template.html',
      controller: function () {
        this.count = 0;
        this.title = 'Parent Counter';

        this.increment = () => {
          this.count++;
        };
      }
    });
})();
