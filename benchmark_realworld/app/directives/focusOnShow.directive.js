angular.module('realApp')
  .directive('focusOnShow', function() {
    return {
      restrict: 'A',
      compile: function() {
        return {
          post: function(scope, el) {
            el[0].focus();
          }
        };
      }
    };
  });
