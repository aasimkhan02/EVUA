/**
 * bench-100 directives.js
 * Tests: multi-file ingestion, directive detection from separate file
 * Gap:   no DirectiveToComponentRule exists — these produce NO output files
 */
angular.module('bench100App')

.directive('statusBadge', function() {
  return {
    restrict: 'E',
    scope: { status: '@', label: '@' },
    template: '<span class="badge" ng-class="{\'active\': status === \'active\'}">{{label}}</span>'
  };
});