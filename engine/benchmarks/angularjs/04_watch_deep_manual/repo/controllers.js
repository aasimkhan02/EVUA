angular.module('app').controller('ProfileCtrl', function ($scope) {
  $scope.profile = {
    name: 'Alice',
    settings: {
      theme: 'dark',
      notifications: true
    }
  };

  $scope.$watch('profile', function (newVal, oldVal) {
    console.log('Profile changed', newVal);
  }, true); // DEEP WATCH
});
