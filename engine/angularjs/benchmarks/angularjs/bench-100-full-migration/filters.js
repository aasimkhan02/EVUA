/**
 * bench-100 filters.js
 * Tests: multi-file ingestion, filter detection from separate file
 * Gap:   no FilterToPipeRule exists — these produce NO output files
 */
angular.module('bench100App')

.filter('currencyFormat', function() {
  return function(amount) {
    if (isNaN(amount)) return '$0.00';
    return '$' + parseFloat(amount).toFixed(2);
  };
});