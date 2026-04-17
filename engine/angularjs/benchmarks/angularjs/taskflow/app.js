'use strict';

/**
 * TaskFlow - AngularJS Project Management App
 * A real-world AngularJS application designed to test AngularJS → Angular converters.
 *
 * Patterns covered:
 * - $routeProvider routing
 * - $scope / $rootScope
 * - $broadcast / $emit / $on
 * - Services & Factories
 * - Custom Directives (element & attribute)
 * - Filters
 * - $http with interceptors
 * - ng-repeat, ng-model, ng-if, ng-show, ng-class
 * - $watch, $watchCollection
 * - Two-way data binding
 * - $timeout / $interval
 * - $location
 * - Form validation with ngModel
 */

angular.module('taskflow', [
  'ngRoute',
  'ngAnimate',
  'taskflow.services',
  'taskflow.controllers',
  'taskflow.directives',
  'taskflow.filters'
])

.config(['$routeProvider', '$locationProvider', '$httpProvider',
  function($routeProvider, $locationProvider, $httpProvider) {

    // HTTP Interceptor - auth token injection & error handling
    $httpProvider.interceptors.push('AuthInterceptor');

    $routeProvider
      .when('/', {
        redirectTo: '/dashboard'
      })
      .when('/dashboard', {
        templateUrl: 'views/dashboard.html',
        controller: 'DashboardCtrl',
        controllerAs: 'vm',
        resolve: {
          projects: ['ProjectService', function(ProjectService) {
            return ProjectService.getAll();
          }],
          stats: ['StatsService', function(StatsService) {
            return StatsService.getSummary();
          }]
        }
      })
      .when('/projects', {
        templateUrl: 'views/projects.html',
        controller: 'ProjectListCtrl',
        controllerAs: 'vm'
      })
      .when('/projects/new', {
        templateUrl: 'views/project-form.html',
        controller: 'ProjectFormCtrl',
        controllerAs: 'vm'
      })
      .when('/projects/:projectId', {
        templateUrl: 'views/project-detail.html',
        controller: 'ProjectDetailCtrl',
        controllerAs: 'vm',
        resolve: {
          project: ['$route', 'ProjectService', function($route, ProjectService) {
            return ProjectService.getById($route.current.params.projectId);
          }]
        }
      })
      .when('/projects/:projectId/tasks', {
        templateUrl: 'views/task-board.html',
        controller: 'TaskBoardCtrl',
        controllerAs: 'vm',
        resolve: {
          project: ['$route', 'ProjectService', function($route, ProjectService) {
            return ProjectService.getById($route.current.params.projectId);
          }],
          tasks: ['$route', 'TaskService', function($route, TaskService) {
            return TaskService.getByProject($route.current.params.projectId);
          }]
        }
      })
      .when('/tasks/:taskId', {
        templateUrl: 'views/task-detail.html',
        controller: 'TaskDetailCtrl',
        controllerAs: 'vm'
      })
      .when('/team', {
        templateUrl: 'views/team.html',
        controller: 'TeamCtrl',
        controllerAs: 'vm'
      })
      .when('/profile', {
        templateUrl: 'views/profile.html',
        controller: 'ProfileCtrl',
        controllerAs: 'vm'
      })
      .when('/login', {
        templateUrl: 'views/login.html',
        controller: 'AuthCtrl',
        controllerAs: 'vm'
      })
      .otherwise({
        redirectTo: '/dashboard'
      });
  }
])

.run(['$rootScope', '$location', 'AuthService', 'NotificationService',
  function($rootScope, $location, AuthService, NotificationService) {

    // Global state on $rootScope (classic AngularJS pattern)
    $rootScope.appName = 'TaskFlow';
    $rootScope.currentUser = null;
    $rootScope.isLoading = false;
    $rootScope.notifications = [];

    // Route change guards
    $rootScope.$on('$routeChangeStart', function(event, next, current) {
      $rootScope.isLoading = true;

      const publicRoutes = ['/login'];
      const isPublic = publicRoutes.some(r => next.$$route && next.$$route.originalPath === r);

      if (!isPublic && !AuthService.isAuthenticated()) {
        event.preventDefault();
        $location.path('/login');
      }
    });

    $rootScope.$on('$routeChangeSuccess', function() {
      $rootScope.isLoading = false;
    });

    $rootScope.$on('$routeChangeError', function(event, current, previous, rejection) {
      $rootScope.isLoading = false;
      NotificationService.error('Failed to load page: ' + rejection);
    });

    // Global notification listener
    $rootScope.$on('notification:add', function(event, notification) {
      $rootScope.notifications.push(notification);
      if (notification.autoDismiss !== false) {
        // Dismissed via $timeout in the service
      }
    });

    $rootScope.$on('notification:remove', function(event, id) {
      $rootScope.notifications = $rootScope.notifications.filter(n => n.id !== id);
    });

    // Initialize auth state
    AuthService.restoreSession().then(function(user) {
      $rootScope.currentUser = user;
    });
  }
]);
