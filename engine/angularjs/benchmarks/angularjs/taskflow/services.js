'use strict';

angular.module('taskflow.services', [])

// ─────────────────────────────────────────────
// AUTH INTERCEPTOR (HTTP interceptor pattern)
// ─────────────────────────────────────────────
.factory('AuthInterceptor', ['$rootScope', '$q', '$injector',
  function($rootScope, $q, $injector) {
    return {
      request: function(config) {
        const AuthService = $injector.get('AuthService');
        const token = AuthService.getToken();
        if (token) {
          config.headers = config.headers || {};
          config.headers['Authorization'] = 'Bearer ' + token;
        }
        config.headers['X-App-Version'] = '1.0.0';
        return config;
      },
      responseError: function(rejection) {
        if (rejection.status === 401) {
          $rootScope.$broadcast('auth:unauthorized');
          const $location = $injector.get('$location');
          $location.path('/login');
        }
        if (rejection.status === 403) {
          $rootScope.$broadcast('auth:forbidden', rejection);
        }
        return $q.reject(rejection);
      }
    };
  }
])

// ─────────────────────────────────────────────
// AUTH SERVICE
// ─────────────────────────────────────────────
.service('AuthService', ['$http', '$q', '$rootScope',
  function($http, $q, $rootScope) {
    const self = this;
    let _token = localStorage.getItem('taskflow_token');
    let _currentUser = null;

    self.isAuthenticated = function() {
      return !!_token;
    };

    self.getToken = function() {
      return _token;
    };

    self.login = function(credentials) {
      return $http.post('/api/auth/login', credentials).then(function(response) {
        _token = response.data.token;
        _currentUser = response.data.user;
        localStorage.setItem('taskflow_token', _token);
        $rootScope.currentUser = _currentUser;
        $rootScope.$broadcast('auth:login', _currentUser);
        return _currentUser;
      });
    };

    self.logout = function() {
      return $http.post('/api/auth/logout').finally(function() {
        _token = null;
        _currentUser = null;
        localStorage.removeItem('taskflow_token');
        $rootScope.currentUser = null;
        $rootScope.$broadcast('auth:logout');
      });
    };

    self.restoreSession = function() {
      if (!_token) return $q.resolve(null);
      return $http.get('/api/auth/me').then(function(res) {
        _currentUser = res.data;
        return _currentUser;
      }).catch(function() {
        _token = null;
        localStorage.removeItem('taskflow_token');
        return null;
      });
    };

    self.getCurrentUser = function() {
      return _currentUser;
    };
  }
])

// ─────────────────────────────────────────────
// PROJECT SERVICE (Factory pattern)
// ─────────────────────────────────────────────
.factory('ProjectService', ['$http', '$q',
  function($http, $q) {
    const BASE = '/api/projects';

    // In-memory cache (classic AngularJS pattern)
    let _cache = null;

    function invalidateCache() {
      _cache = null;
    }

    return {
      getAll: function(forceRefresh) {
        if (_cache && !forceRefresh) {
          return $q.resolve(_cache);
        }
        return $http.get(BASE).then(function(res) {
          _cache = res.data;
          return _cache;
        });
      },

      getById: function(id) {
        return $http.get(BASE + '/' + id).then(function(res) {
          return res.data;
        });
      },

      create: function(project) {
        return $http.post(BASE, project).then(function(res) {
          invalidateCache();
          return res.data;
        });
      },

      update: function(id, updates) {
        return $http.put(BASE + '/' + id, updates).then(function(res) {
          invalidateCache();
          return res.data;
        });
      },

      patch: function(id, partialUpdate) {
        return $http.patch(BASE + '/' + id, partialUpdate).then(function(res) {
          invalidateCache();
          return res.data;
        });
      },

      delete: function(id) {
        return $http.delete(BASE + '/' + id).then(function() {
          invalidateCache();
        });
      },

      addMember: function(projectId, userId) {
        return $http.post(BASE + '/' + projectId + '/members', { userId: userId })
          .then(function(res) { return res.data; });
      },

      removeMember: function(projectId, userId) {
        return $http.delete(BASE + '/' + projectId + '/members/' + userId)
          .then(function(res) { return res.data; });
      }
    };
  }
])

// ─────────────────────────────────────────────
// TASK SERVICE
// ─────────────────────────────────────────────
.factory('TaskService', ['$http', '$rootScope',
  function($http, $rootScope) {
    const BASE = '/api/tasks';

    return {
      getByProject: function(projectId) {
        return $http.get('/api/projects/' + projectId + '/tasks')
          .then(function(res) { return res.data; });
      },

      getById: function(id) {
        return $http.get(BASE + '/' + id).then(function(res) { return res.data; });
      },

      create: function(task) {
        return $http.post(BASE, task).then(function(res) {
          $rootScope.$broadcast('task:created', res.data);
          return res.data;
        });
      },

      update: function(id, updates) {
        return $http.put(BASE + '/' + id, updates).then(function(res) {
          $rootScope.$broadcast('task:updated', res.data);
          return res.data;
        });
      },

      updateStatus: function(id, status) {
        return $http.patch(BASE + '/' + id + '/status', { status: status }).then(function(res) {
          $rootScope.$broadcast('task:statusChanged', { id: id, status: status });
          return res.data;
        });
      },

      assign: function(taskId, userId) {
        return $http.patch(BASE + '/' + taskId + '/assign', { assigneeId: userId })
          .then(function(res) {
            $rootScope.$broadcast('task:assigned', res.data);
            return res.data;
          });
      },

      delete: function(id) {
        return $http.delete(BASE + '/' + id).then(function() {
          $rootScope.$broadcast('task:deleted', { id: id });
        });
      },

      addComment: function(taskId, comment) {
        return $http.post(BASE + '/' + taskId + '/comments', comment)
          .then(function(res) { return res.data; });
      },

      getComments: function(taskId) {
        return $http.get(BASE + '/' + taskId + '/comments')
          .then(function(res) { return res.data; });
      },

      addAttachment: function(taskId, formData) {
        return $http.post(BASE + '/' + taskId + '/attachments', formData, {
          headers: { 'Content-Type': undefined },
          transformRequest: angular.identity
        }).then(function(res) { return res.data; });
      },

      updatePriority: function(id, priority) {
        return $http.patch(BASE + '/' + id + '/priority', { priority: priority })
          .then(function(res) { return res.data; });
      }
    };
  }
])

// ─────────────────────────────────────────────
// USER / TEAM SERVICE
// ─────────────────────────────────────────────
.factory('UserService', ['$http',
  function($http) {
    return {
      getAll: function() {
        return $http.get('/api/users').then(function(res) { return res.data; });
      },
      getById: function(id) {
        return $http.get('/api/users/' + id).then(function(res) { return res.data; });
      },
      updateProfile: function(id, data) {
        return $http.put('/api/users/' + id, data).then(function(res) { return res.data; });
      },
      updateAvatar: function(id, formData) {
        return $http.post('/api/users/' + id + '/avatar', formData, {
          headers: { 'Content-Type': undefined },
          transformRequest: angular.identity
        }).then(function(res) { return res.data; });
      },
      search: function(query) {
        return $http.get('/api/users/search', { params: { q: query } })
          .then(function(res) { return res.data; });
      }
    };
  }
])

// ─────────────────────────────────────────────
// STATS SERVICE
// ─────────────────────────────────────────────
.factory('StatsService', ['$http',
  function($http) {
    return {
      getSummary: function() {
        return $http.get('/api/stats/summary').then(function(res) { return res.data; });
      },
      getProjectStats: function(projectId) {
        return $http.get('/api/stats/projects/' + projectId).then(function(res) { return res.data; });
      },
      getTeamActivity: function(days) {
        return $http.get('/api/stats/activity', { params: { days: days || 7 } })
          .then(function(res) { return res.data; });
      }
    };
  }
])

// ─────────────────────────────────────────────
// NOTIFICATION SERVICE ($timeout + $broadcast)
// ─────────────────────────────────────────────
.service('NotificationService', ['$rootScope', '$timeout',
  function($rootScope, $timeout) {
    let _idCounter = 0;

    function add(type, message, options) {
      const id = ++_idCounter;
      const notification = angular.extend({
        id: id,
        type: type,
        message: message,
        timestamp: new Date(),
        autoDismiss: true,
        duration: 4000
      }, options);

      $rootScope.$broadcast('notification:add', notification);

      if (notification.autoDismiss) {
        $timeout(function() {
          $rootScope.$broadcast('notification:remove', id);
        }, notification.duration);
      }
      return id;
    }

    this.success = function(message, options) { return add('success', message, options); };
    this.error   = function(message, options) { return add('error', message, options); };
    this.warn    = function(message, options) { return add('warning', message, options); };
    this.info    = function(message, options) { return add('info', message, options); };
    this.dismiss = function(id) { $rootScope.$broadcast('notification:remove', id); };
  }
])

// ─────────────────────────────────────────────
// LOCAL STORAGE SERVICE
// ─────────────────────────────────────────────
.service('StorageService', [function() {
  this.get = function(key, defaultValue) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch(e) {
      return defaultValue;
    }
  };
  this.set = function(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch(e) { /* quota exceeded */ }
  };
  this.remove = function(key) {
    localStorage.removeItem(key);
  };
}]);
