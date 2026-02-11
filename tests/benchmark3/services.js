(function () {
  'use strict';

  angular.module('mediumApp').factory('UserService', function () {
    var currentUser = null;

    return {
      login: function (name) {
        currentUser = { name: name };
        return currentUser;
      },
      getUser: function () {
        return currentUser;
      }
    };
  });

  angular.module('mediumApp').service('AdminService', function () {
    var maintenance = false;

    this.toggle = function () {
      maintenance = !maintenance;
      return maintenance;
    };

    this.isMaintenance = function () {
      return maintenance;
    };
  });
})();
