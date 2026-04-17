'use strict';

// ─────────────────────────────────────────────
// FILTERS MODULE
// ─────────────────────────────────────────────
angular.module('taskflow.filters', [])

// Capitalize first letter
.filter('capitalize', function() {
  return function(input) {
    if (!input) return '';
    return input.charAt(0).toUpperCase() + input.slice(1);
  };
})

// Truncate long text
.filter('truncate', function() {
  return function(input, length, suffix) {
    if (!input) return '';
    length = length || 100;
    suffix = suffix || '…';
    return input.length > length ? input.substring(0, length) + suffix : input;
  };
})

// Time ago (relative time)
.filter('timeAgo', ['$filter', function($filter) {
  return function(input) {
    if (!input) return '';
    const date = new Date(input);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60)   return 'just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    if (seconds < 604800) return Math.floor(seconds / 86400) + 'd ago';

    return $filter('date')(date, 'MMM d, yyyy');
  };
}])

// Format status label
.filter('statusLabel', function() {
  const labels = {
    'todo':        'To Do',
    'in-progress': 'In Progress',
    'review':      'In Review',
    'done':        'Done',
    'active':      'Active',
    'on-hold':     'On Hold',
    'completed':   'Completed',
    'archived':    'Archived'
  };
  return function(input) {
    return labels[input] || input;
  };
})

// Priority sort order
.filter('priorityOrder', function() {
  const order = { 'critical': 0, 'high': 1, 'medium': 2, 'low': 3 };
  return function(tasks) {
    if (!tasks) return [];
    return tasks.slice().sort(function(a, b) {
      return (order[a.priority] || 99) - (order[b.priority] || 99);
    });
  };
})

// File size human readable
.filter('fileSize', function() {
  return function(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };
})

// Count tasks by status
.filter('countByStatus', function() {
  return function(tasks, status) {
    if (!tasks) return 0;
    return tasks.filter(function(t) { return t.status === status; }).length;
  };
})

// Highlight search match
.filter('highlight', ['$sce', function($sce) {
  return function(input, query) {
    if (!query || !input) return input;
    const regex = new RegExp('(' + query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
    const result = String(input).replace(regex, '<mark>$1</mark>');
    return $sce.trustAsHtml(result);
  };
}]);
