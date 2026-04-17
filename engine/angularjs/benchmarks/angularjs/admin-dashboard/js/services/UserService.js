angular.module('adminApp')

.factory('UserService', ['$http', '$q', function($http, $q) {

  // Seed data (simulates a backend store)
  var _users = [
    { id: 1, name: 'Alice Nguyen',    email: 'alice@corp.io',   role: 'Admin',   status: 'active',   joined: '2023-01-12', lastLogin: '2 hours ago',   avatar: 'AN' },
    { id: 2, name: 'Ben Okafor',      email: 'ben@corp.io',     role: 'Editor',  status: 'active',   joined: '2023-03-05', lastLogin: '1 day ago',     avatar: 'BO' },
    { id: 3, name: 'Clara Reyes',     email: 'clara@corp.io',   role: 'Viewer',  status: 'inactive', joined: '2023-06-22', lastLogin: '3 weeks ago',   avatar: 'CR' },
    { id: 4, name: 'David Park',      email: 'david@corp.io',   role: 'Editor',  status: 'active',   joined: '2023-08-14', lastLogin: '5 hours ago',   avatar: 'DP' },
    { id: 5, name: 'Elan Morris',     email: 'elan@corp.io',    role: 'Viewer',  status: 'pending',  joined: '2024-01-03', lastLogin: 'Never',         avatar: 'EM' },
    { id: 6, name: 'Fatima Malik',    email: 'fatima@corp.io',  role: 'Admin',   status: 'active',   joined: '2023-02-18', lastLogin: '30 min ago',    avatar: 'FM' },
    { id: 7, name: 'George Ito',      email: 'george@corp.io',  role: 'Editor',  status: 'inactive', joined: '2023-11-09', lastLogin: '2 months ago',  avatar: 'GI' },
    { id: 8, name: 'Hana Svensson',   email: 'hana@corp.io',    role: 'Viewer',  status: 'active',   joined: '2024-02-27', lastLogin: '1 hour ago',    avatar: 'HS' }
  ];

  var _nextId = 9;

  function _delay(data) {
    var deferred = $q.defer();
    setTimeout(function() { deferred.resolve(data); }, 220);
    return deferred.promise;
  }

  return {

    getAll: function() {
      // Simulates GET /api/users
      return _delay(angular.copy(_users));
    },

    getById: function(id) {
      var user = _users.find(function(u) { return u.id === parseInt(id); });
      return _delay(user ? angular.copy(user) : null);
    },

    create: function(userData) {
      var newUser = angular.extend({}, userData, {
        id: _nextId++,
        joined: new Date().toISOString().slice(0, 10),
        lastLogin: 'Never',
        avatar: userData.name.split(' ').map(function(n) { return n[0]; }).join('').slice(0, 2).toUpperCase()
      });
      _users.push(newUser);
      return _delay(angular.copy(newUser));
    },

    update: function(id, userData) {
      var idx = _users.findIndex(function(u) { return u.id === parseInt(id); });
      if (idx === -1) return $q.reject('User not found');
      _users[idx] = angular.extend(_users[idx], userData);
      return _delay(angular.copy(_users[idx]));
    },

    remove: function(id) {
      var idx = _users.findIndex(function(u) { return u.id === parseInt(id); });
      if (idx === -1) return $q.reject('User not found');
      _users.splice(idx, 1);
      return _delay({ success: true });
    },

    getRoles: function() {
      return ['Admin', 'Editor', 'Viewer'];
    },

    getStatuses: function() {
      return ['active', 'inactive', 'pending'];
    }
  };
}]);
