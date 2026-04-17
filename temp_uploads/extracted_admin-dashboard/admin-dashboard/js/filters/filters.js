angular.module('adminApp')

// Capitalize first letter of each word
.filter('titleCase', function() {
  return function(input) {
    if (!input) return '';
    return input.replace(/\w\S*/g, function(txt) {
      return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
    });
  };
})

// Shorten long email for display
.filter('shortEmail', function() {
  return function(email) {
    if (!email) return '';
    var parts = email.split('@');
    var name = parts[0].length > 10 ? parts[0].slice(0, 9) + '…' : parts[0];
    return name + '@' + parts[1];
  };
})

// Status badge label — maps 'active' → 'Active', etc.
.filter('statusLabel', function() {
  var map = { active: 'Active', inactive: 'Inactive', pending: 'Pending' };
  return function(status) { return map[status] || status; };
})

// Role color class
.filter('roleClass', function() {
  var map = { Admin: 'role-admin', Editor: 'role-editor', Viewer: 'role-viewer' };
  return function(role) { return map[role] || ''; };
})

// Pluralize — {{ count | pluralize:'user':'users' }}
.filter('pluralize', function() {
  return function(count, singular, plural) {
    return count === 1 ? singular : (plural || singular + 's');
  };
});
