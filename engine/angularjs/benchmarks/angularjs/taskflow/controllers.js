'use strict';

angular.module('taskflow.controllers', [])

// ─────────────────────────────────────────────
// MAIN APP CONTROLLER (parent scope)
// ─────────────────────────────────────────────
.controller('AppCtrl', ['$scope', '$rootScope', '$location', 'AuthService',
  function($scope, $rootScope, $location, AuthService) {
    $scope.menuOpen = false;

    $scope.toggleMenu = function() {
      $scope.menuOpen = !$scope.menuOpen;
    };

    $scope.logout = function() {
      AuthService.logout().then(function() {
        $location.path('/login');
      });
    };

    $scope.isActive = function(route) {
      return $location.path().indexOf(route) === 0;
    };

    // Listen to route changes to close menu
    $scope.$on('$routeChangeSuccess', function() {
      $scope.menuOpen = false;
    });
  }
])

// ─────────────────────────────────────────────
// AUTH CONTROLLER
// ─────────────────────────────────────────────
.controller('AuthCtrl', ['$scope', '$rootScope', '$location', 'AuthService', 'NotificationService',
  function($scope, $rootScope, $location, AuthService, NotificationService) {
    const vm = this;

    vm.credentials = { email: '', password: '', rememberMe: false };
    vm.isLoading = false;
    vm.error = null;
    vm.showPassword = false;

    // Redirect if already logged in
    if (AuthService.isAuthenticated()) {
      $location.path('/dashboard');
    }

    vm.login = function(form) {
      if (form.$invalid) {
        vm.error = 'Please fill in all required fields.';
        return;
      }
      vm.isLoading = true;
      vm.error = null;

      AuthService.login(vm.credentials)
        .then(function(user) {
          NotificationService.success('Welcome back, ' + user.name + '!');
          $location.path('/dashboard');
        })
        .catch(function(err) {
          vm.error = (err.data && err.data.message) || 'Invalid credentials. Please try again.';
        })
        .finally(function() {
          vm.isLoading = false;
        });
    };

    vm.togglePassword = function() {
      vm.showPassword = !vm.showPassword;
    };
  }
])

// ─────────────────────────────────────────────
// DASHBOARD CONTROLLER (uses route resolve)
// ─────────────────────────────────────────────
.controller('DashboardCtrl', ['$scope', '$rootScope', 'projects', 'stats',
  'TaskService', 'NotificationService', '$interval',
  function($scope, $rootScope, projects, stats, TaskService, NotificationService, $interval) {
    const vm = this;

    vm.projects = projects;
    vm.stats = stats;
    vm.recentTasks = [];
    vm.activityFeed = [];
    vm.selectedPeriod = '7days';

    // $watch example
    $scope.$watch(function() { return vm.selectedPeriod; }, function(newVal, oldVal) {
      if (newVal !== oldVal) {
        vm.loadActivity();
      }
    });

    vm.loadActivity = function() {
      vm.activityLoading = true;
      const days = vm.selectedPeriod === '7days' ? 7 : vm.selectedPeriod === '30days' ? 30 : 1;
      // Simulated; real app uses StatsService
      vm.activityLoading = false;
    };

    // Auto-refresh every 60s using $interval
    const refreshInterval = $interval(function() {
      vm.lastRefreshed = new Date();
    }, 60000);

    // Clean up $interval on destroy (critical pattern)
    $scope.$on('$destroy', function() {
      $interval.cancel(refreshInterval);
    });

    // Listen to task events broadcast from TaskService
    $scope.$on('task:created', function(event, task) {
      vm.stats.totalTasks++;
      NotificationService.info('New task created: ' + task.title);
    });

    $scope.$on('task:statusChanged', function(event, data) {
      if (data.status === 'done') {
        vm.stats.completedTasks++;
      }
    });

    vm.getCompletionPercent = function(project) {
      if (!project.totalTasks) return 0;
      return Math.round((project.completedTasks / project.totalTasks) * 100);
    };

    vm.getPriorityClass = function(priority) {
      return {
        'priority-critical': priority === 'critical',
        'priority-high':     priority === 'high',
        'priority-medium':   priority === 'medium',
        'priority-low':      priority === 'low'
      };
    };
  }
])

// ─────────────────────────────────────────────
// PROJECT LIST CONTROLLER
// ─────────────────────────────────────────────
.controller('ProjectListCtrl', ['$scope', 'ProjectService', 'NotificationService',
  function($scope, ProjectService, NotificationService) {
    const vm = this;

    vm.projects = [];
    vm.isLoading = true;
    vm.searchQuery = '';
    vm.sortField = 'name';
    vm.sortReverse = false;
    vm.viewMode = 'grid'; // 'grid' | 'list'

    // $watchCollection example
    $scope.$watchCollection(
      function() { return vm.projects; },
      function(newProjects) {
        vm.projectCount = newProjects.length;
      }
    );

    vm.load = function() {
      vm.isLoading = true;
      ProjectService.getAll(true).then(function(projects) {
        vm.projects = projects;
      }).catch(function() {
        NotificationService.error('Failed to load projects.');
      }).finally(function() {
        vm.isLoading = false;
      });
    };

    vm.deleteProject = function(project) {
      if (!confirm('Delete project "' + project.name + '"? This cannot be undone.')) return;
      ProjectService.delete(project.id).then(function() {
        vm.projects = vm.projects.filter(function(p) { return p.id !== project.id; });
        NotificationService.success('Project deleted.');
      }).catch(function() {
        NotificationService.error('Failed to delete project.');
      });
    };

    vm.setSortField = function(field) {
      if (vm.sortField === field) {
        vm.sortReverse = !vm.sortReverse;
      } else {
        vm.sortField = field;
        vm.sortReverse = false;
      }
    };

    vm.load();
  }
])

// ─────────────────────────────────────────────
// PROJECT FORM CONTROLLER (create/edit)
// ─────────────────────────────────────────────
.controller('ProjectFormCtrl', ['$scope', '$routeParams', '$location',
  'ProjectService', 'UserService', 'NotificationService',
  function($scope, $routeParams, $location, ProjectService, UserService, NotificationService) {
    const vm = this;

    vm.isEditMode = !!$routeParams.projectId;
    vm.isLoading = false;
    vm.isSaving = false;
    vm.teamMembers = [];
    vm.availableUsers = [];

    vm.project = {
      name: '',
      description: '',
      status: 'active',
      priority: 'medium',
      dueDate: null,
      color: '#4F46E5',
      members: []
    };

    vm.statusOptions = ['active', 'on-hold', 'completed', 'archived'];
    vm.priorityOptions = ['low', 'medium', 'high', 'critical'];
    vm.colorOptions = ['#4F46E5', '#7C3AED', '#DB2777', '#DC2626', '#D97706', '#059669', '#0891B2'];

    if (vm.isEditMode) {
      vm.isLoading = true;
      ProjectService.getById($routeParams.projectId).then(function(project) {
        vm.project = project;
      }).finally(function() {
        vm.isLoading = false;
      });
    }

    UserService.getAll().then(function(users) {
      vm.availableUsers = users;
    });

    vm.addMember = function(user) {
      const already = vm.project.members.some(function(m) { return m.id === user.id; });
      if (!already) {
        vm.project.members.push(user);
      }
    };

    vm.removeMember = function(user) {
      vm.project.members = vm.project.members.filter(function(m) { return m.id !== user.id; });
    };

    vm.save = function(form) {
      if (form.$invalid) return;
      vm.isSaving = true;

      const action = vm.isEditMode
        ? ProjectService.update($routeParams.projectId, vm.project)
        : ProjectService.create(vm.project);

      action.then(function(saved) {
        NotificationService.success(vm.isEditMode ? 'Project updated.' : 'Project created!');
        $location.path('/projects/' + saved.id);
      }).catch(function(err) {
        vm.serverError = (err.data && err.data.message) || 'Save failed.';
        NotificationService.error(vm.serverError);
      }).finally(function() {
        vm.isSaving = false;
      });
    };

    vm.cancel = function() {
      $location.path(vm.isEditMode ? '/projects/' + $routeParams.projectId : '/projects');
    };
  }
])

// ─────────────────────────────────────────────
// PROJECT DETAIL CONTROLLER
// ─────────────────────────────────────────────
.controller('ProjectDetailCtrl', ['$scope', 'project', '$routeParams', '$location',
  'TaskService', 'ProjectService', 'NotificationService',
  function($scope, project, $routeParams, $location, TaskService, ProjectService, NotificationService) {
    const vm = this;

    vm.project = project;
    vm.tasks = [];
    vm.activeTab = 'overview';
    vm.taskFilter = 'all';
    vm.isLoadingTasks = true;

    TaskService.getByProject(project.id).then(function(tasks) {
      vm.tasks = tasks;
    }).finally(function() {
      vm.isLoadingTasks = false;
    });

    vm.setTab = function(tab) {
      vm.activeTab = tab;
    };

    vm.filteredTasks = function() {
      if (vm.taskFilter === 'all') return vm.tasks;
      return vm.tasks.filter(function(t) { return t.status === vm.taskFilter; });
    };

    vm.archiveProject = function() {
      ProjectService.patch(project.id, { status: 'archived' }).then(function() {
        vm.project.status = 'archived';
        NotificationService.warn('Project archived.');
      });
    };

    // Listen for task events to update local state
    $scope.$on('task:created', function(event, task) {
      if (task.projectId === project.id) {
        vm.tasks.push(task);
      }
    });

    $scope.$on('task:deleted', function(event, data) {
      vm.tasks = vm.tasks.filter(function(t) { return t.id !== data.id; });
    });
  }
])

// ─────────────────────────────────────────────
// TASK BOARD CONTROLLER (Kanban)
// ─────────────────────────────────────────────
.controller('TaskBoardCtrl', ['$scope', 'project', 'tasks',
  'TaskService', 'UserService', 'NotificationService',
  function($scope, project, tasks, TaskService, UserService, NotificationService) {
    const vm = this;

    vm.project = project;
    vm.columns = [
      { id: 'todo',        label: 'To Do',       tasks: [] },
      { id: 'in-progress', label: 'In Progress',  tasks: [] },
      { id: 'review',      label: 'In Review',    tasks: [] },
      { id: 'done',        label: 'Done',         tasks: [] }
    ];
    vm.teamMembers = [];
    vm.assigneeFilter = null;
    vm.priorityFilter = null;
    vm.newTaskTitle = '';
    vm.showNewTaskForm = {};

    // Distribute tasks into columns
    function distributeTasks(taskList) {
      vm.columns.forEach(function(col) { col.tasks = []; });
      taskList.forEach(function(task) {
        const col = vm.columns.find(function(c) { return c.id === task.status; });
        if (col) col.tasks.push(task);
      });
    }

    distributeTasks(tasks);

    UserService.getAll().then(function(users) {
      vm.teamMembers = users;
    });

    vm.moveTask = function(task, newStatus) {
      const oldStatus = task.status;
      task.status = newStatus; // Optimistic update

      // Re-distribute
      distributeTasks(vm.columns.reduce(function(acc, col) {
        return acc.concat(col.tasks);
      }, []));

      TaskService.updateStatus(task.id, newStatus).catch(function() {
        task.status = oldStatus; // Rollback on failure
        distributeTasks(vm.columns.reduce(function(acc, col) {
          return acc.concat(col.tasks);
        }, []));
        NotificationService.error('Failed to update task status.');
      });
    };

    vm.quickAddTask = function(columnId) {
      if (!vm.newTaskTitle.trim()) return;
      TaskService.create({
        title: vm.newTaskTitle,
        status: columnId,
        projectId: project.id,
        priority: 'medium'
      }).then(function(task) {
        const col = vm.columns.find(function(c) { return c.id === columnId; });
        if (col) col.tasks.push(task);
        vm.newTaskTitle = '';
        vm.showNewTaskForm[columnId] = false;
        NotificationService.success('Task added!');
      });
    };

    vm.deleteTask = function(task, column) {
      TaskService.delete(task.id).then(function() {
        column.tasks = column.tasks.filter(function(t) { return t.id !== task.id; });
        NotificationService.success('Task deleted.');
      });
    };

    vm.getFilteredTasks = function(column) {
      return column.tasks.filter(function(task) {
        if (vm.assigneeFilter && task.assigneeId !== vm.assigneeFilter) return false;
        if (vm.priorityFilter && task.priority !== vm.priorityFilter) return false;
        return true;
      });
    };

    // Deep watch task changes for a badge counter
    $scope.$watch(function() {
      return vm.columns.reduce(function(total, col) {
        return total + col.tasks.length;
      }, 0);
    }, function(newCount) {
      vm.totalTaskCount = newCount;
    });
  }
])

// ─────────────────────────────────────────────
// TASK DETAIL CONTROLLER
// ─────────────────────────────────────────────
.controller('TaskDetailCtrl', ['$scope', '$routeParams', '$location',
  'TaskService', 'UserService', 'NotificationService',
  function($scope, $routeParams, $location, TaskService, UserService, NotificationService) {
    const vm = this;

    vm.task = null;
    vm.comments = [];
    vm.teamMembers = [];
    vm.newComment = { content: '' };
    vm.isLoading = true;
    vm.isSavingComment = false;
    vm.isEditing = false;

    function loadTask() {
      return TaskService.getById($routeParams.taskId).then(function(task) {
        vm.task = task;
        vm.editData = angular.copy(task); // Deep copy for edit form
      });
    }

    function loadComments() {
      return TaskService.getComments($routeParams.taskId).then(function(comments) {
        vm.comments = comments;
      });
    }

    Promise.all([loadTask(), loadComments()]).finally(function() {
      vm.isLoading = false;
    });

    UserService.getAll().then(function(users) {
      vm.teamMembers = users;
    });

    vm.startEdit = function() {
      vm.editData = angular.copy(vm.task);
      vm.isEditing = true;
    };

    vm.cancelEdit = function() {
      vm.isEditing = false;
    };

    vm.saveEdit = function() {
      TaskService.update(vm.task.id, vm.editData).then(function(updated) {
        vm.task = updated;
        vm.isEditing = false;
        NotificationService.success('Task updated.');
      }).catch(function() {
        NotificationService.error('Failed to save changes.');
      });
    };

    vm.submitComment = function(form) {
      if (form.$invalid || !vm.newComment.content.trim()) return;
      vm.isSavingComment = true;

      TaskService.addComment(vm.task.id, vm.newComment).then(function(comment) {
        vm.comments.push(comment);
        vm.newComment = { content: '' };
        form.$setPristine();
        form.$setUntouched();
      }).catch(function() {
        NotificationService.error('Failed to post comment.');
      }).finally(function() {
        vm.isSavingComment = false;
      });
    };

    vm.changeStatus = function(status) {
      TaskService.updateStatus(vm.task.id, status).then(function() {
        vm.task.status = status;
        NotificationService.success('Status updated to ' + status);
      });
    };

    vm.assignTo = function(userId) {
      TaskService.assign(vm.task.id, userId).then(function(updated) {
        vm.task.assignee = updated.assignee;
        NotificationService.info('Task reassigned.');
      });
    };

    vm.deleteTask = function() {
      if (!confirm('Delete this task?')) return;
      TaskService.delete(vm.task.id).then(function() {
        NotificationService.success('Task deleted.');
        $location.path('/projects/' + vm.task.projectId);
      });
    };
  }
])

// ─────────────────────────────────────────────
// TEAM CONTROLLER
// ─────────────────────────────────────────────
.controller('TeamCtrl', ['$scope', 'UserService', 'NotificationService',
  function($scope, UserService, NotificationService) {
    const vm = this;

    vm.members = [];
    vm.searchQuery = '';
    vm.isLoading = true;
    vm.selectedMember = null;

    UserService.getAll().then(function(users) {
      vm.members = users;
    }).finally(function() {
      vm.isLoading = false;
    });

    vm.selectMember = function(member) {
      vm.selectedMember = member === vm.selectedMember ? null : member;
    };

    vm.getAvatarUrl = function(user) {
      return user.avatar || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(user.name);
    };

    // $watch with object equality (deep watch)
    $scope.$watch(function() { return vm.searchQuery; }, function(query) {
      if (query.length > 0) {
        vm.filteredMembers = vm.members.filter(function(m) {
          return m.name.toLowerCase().indexOf(query.toLowerCase()) > -1 ||
                 m.email.toLowerCase().indexOf(query.toLowerCase()) > -1;
        });
      } else {
        vm.filteredMembers = vm.members;
      }
    });

    vm.filteredMembers = vm.members;
  }
])

// ─────────────────────────────────────────────
// PROFILE CONTROLLER
// ─────────────────────────────────────────────
.controller('ProfileCtrl', ['$scope', '$rootScope', 'UserService',
  'AuthService', 'NotificationService', 'StorageService',
  function($scope, $rootScope, UserService, AuthService, NotificationService, StorageService) {
    const vm = this;

    vm.user = angular.copy($rootScope.currentUser) || {};
    vm.originalUser = angular.copy(vm.user);
    vm.isSaving = false;
    vm.isDirty = false;
    vm.preferences = StorageService.get('userPreferences', {
      emailNotifications: true,
      desktopNotifications: false,
      theme: 'light',
      defaultView: 'board'
    });

    // Watch for unsaved changes
    $scope.$watch(function() { return vm.user; }, function(newVal) {
      vm.isDirty = !angular.equals(newVal, vm.originalUser);
    }, true); // deep watch

    vm.saveProfile = function(form) {
      if (form.$invalid) return;
      vm.isSaving = true;

      UserService.updateProfile(vm.user.id, vm.user).then(function(updated) {
        vm.originalUser = angular.copy(updated);
        vm.user = updated;
        $rootScope.currentUser = updated;
        vm.isDirty = false;
        NotificationService.success('Profile saved!');
      }).catch(function() {
        NotificationService.error('Failed to save profile.');
      }).finally(function() {
        vm.isSaving = false;
      });
    };

    vm.savePreferences = function() {
      StorageService.set('userPreferences', vm.preferences);
      NotificationService.success('Preferences saved.');
    };

    vm.resetProfile = function() {
      vm.user = angular.copy(vm.originalUser);
    };
  }
]);
