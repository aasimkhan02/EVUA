// bench-03-directive-hazard/repo/src/app.js
// Tests: AngularJS directive with compile() and transclude — engine must flag MANUAL
// Safe controller alongside it must NOT be contaminated with MANUAL risk
// This is a precision test: wrong risk isolation = false positive on SafeController

angular.module('directiveApp', [])

// ── SafeController ────────────────────────────────────────────
// Completely safe — no watch, no compile, minimal scope writes
// ENGINE MUST: detect as controller, emit SAFE risk
.controller('SafeController', ['$scope', '$http', function($scope, $http) {

  $scope.items = [];

  $scope.load = function() {
    $http.get('/api/items').then(function(res) {
      $scope.items = res.data;
    });
  };

  $scope.load();
}])

// ── modalDirective ────────────────────────────────────────────
// Uses compile() and transclude — both hard MANUAL signals
// ENGINE MUST: detect has_compile=true, transclude=true → MANUAL
// ENGINE MUST NOT: bleed this MANUAL onto SafeController's changes
.directive('modalDirective', function() {
  return {
    restrict: 'E',
    transclude: true,
    template: '<div class="modal"><ng-transclude></ng-transclude></div>',
    compile: function(element, attrs) {
      // Pre-link: manipulate DOM before binding
      element.addClass('modal-compiled');
      return {
        pre: function(scope, el) {
          el.addClass('modal-pre');
        },
        post: function(scope, el) {
          el.addClass('modal-post');
        }
      };
    }
  };
})

// ── tooltipDirective ─────────────────────────────────────────
// Uses link() only — also MANUAL but lower severity than compile
.directive('tooltipDirective', ['$timeout', function($timeout) {
  return {
    restrict: 'A',
    link: function(scope, element, attrs) {
      $timeout(function() {
        element.attr('title', attrs.tooltipDirective);
      }, 0);
    }
  };
}]);