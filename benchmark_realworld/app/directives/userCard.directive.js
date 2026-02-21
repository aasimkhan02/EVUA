angular.module('realApp')
  .directive('userCard', function() {
    return {
      restrict: 'E',
      transclude: true,
      scope: {
        user: '='
      },
      templateUrl: 'app/templates/user-card.html',
      link: function(scope, el) {
        console.log("Linked user card");
      }
    };
  });
