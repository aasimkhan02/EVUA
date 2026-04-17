'use strict';

angular.module('taskflow.directives', [])

// ─────────────────────────────────────────────
// PRIORITY BADGE (element directive)
// ─────────────────────────────────────────────
.directive('tfPriorityBadge', function() {
  return {
    restrict: 'E',
    scope: {
      priority: '@'
    },
    template: '<span class="badge badge-priority badge-{{priority}}">' +
              '  <i class="icon-{{priority}}"></i>{{priority | capitalize}}' +
              '</span>',
    link: function(scope, element, attrs) {
      attrs.$observe('priority', function(newPriority) {
        element.removeClass('badge-low badge-medium badge-high badge-critical');
        element.addClass('badge-' + newPriority);
      });
    }
  };
})

// ─────────────────────────────────────────────
// AUTO FOCUS (attribute directive)
// ─────────────────────────────────────────────
.directive('tfAutofocus', ['$timeout', function($timeout) {
  return {
    restrict: 'A',
    link: function(scope, element, attrs) {
      // Use $timeout to wait for ng-if/ng-show rendering
      $timeout(function() {
        element[0].focus();
      }, 100);
    }
  };
}])

// ─────────────────────────────────────────────
// CONFIRM CLICK (attribute directive)
// ─────────────────────────────────────────────
.directive('tfConfirmClick', function() {
  return {
    restrict: 'A',
    scope: {
      tfConfirmClick: '&',
      tfConfirmMessage: '@'
    },
    link: function(scope, element, attrs) {
      element.on('click', function(e) {
        e.preventDefault();
        const message = scope.tfConfirmMessage || 'Are you sure?';
        if (window.confirm(message)) {
          scope.$apply(function() {
            scope.tfConfirmClick();
          });
        }
      });

      scope.$on('$destroy', function() {
        element.off('click');
      });
    }
  };
})

// ─────────────────────────────────────────────
// PROGRESS BAR (element directive with isolate scope)
// ─────────────────────────────────────────────
.directive('tfProgressBar', function() {
  return {
    restrict: 'E',
    scope: {
      value: '=',
      max: '=',
      color: '@',
      showLabel: '='
    },
    template:
      '<div class="progress-bar-wrapper">' +
      '  <div class="progress-bar-track">' +
      '    <div class="progress-bar-fill" ng-style="getStyle()"></div>' +
      '  </div>' +
      '  <span ng-if="showLabel" class="progress-label">{{getPercent()}}%</span>' +
      '</div>',
    link: function(scope, element, attrs) {
      scope.getPercent = function() {
        const max = scope.max || 100;
        return Math.min(100, Math.round((scope.value / max) * 100)) || 0;
      };

      scope.getStyle = function() {
        return {
          width: scope.getPercent() + '%',
          backgroundColor: scope.color || '#4F46E5'
        };
      };
    }
  };
})

// ─────────────────────────────────────────────
// AVATAR COMPONENT (element directive)
// ─────────────────────────────────────────────
.directive('tfAvatar', function() {
  return {
    restrict: 'E',
    scope: {
      user: '=',
      size: '@'
    },
    template:
      '<div class="avatar" ng-class="sizeClass()" title="{{user.name}}">' +
      '  <img ng-if="user.avatar" ng-src="{{user.avatar}}" alt="{{user.name}}">' +
      '  <span ng-if="!user.avatar" class="avatar-initials">{{getInitials()}}</span>' +
      '</div>',
    link: function(scope, element, attrs) {
      scope.getInitials = function() {
        if (!scope.user || !scope.user.name) return '?';
        return scope.user.name.split(' ')
          .slice(0, 2)
          .map(function(n) { return n[0]; })
          .join('').toUpperCase();
      };

      scope.sizeClass = function() {
        return {
          'avatar-sm':  scope.size === 'sm',
          'avatar-md':  !scope.size || scope.size === 'md',
          'avatar-lg':  scope.size === 'lg',
          'avatar-xl':  scope.size === 'xl'
        };
      };
    }
  };
})

// ─────────────────────────────────────────────
// TASK CARD (element directive with transclude)
// ─────────────────────────────────────────────
.directive('tfTaskCard', ['TaskService', 'NotificationService',
  function(TaskService, NotificationService) {
    return {
      restrict: 'E',
      transclude: true,
      scope: {
        task: '=',
        onDelete: '&',
        onMove: '&',
        compact: '='
      },
      templateUrl: 'templates/task-card.html',
      controller: ['$scope', function($scope) {
        $scope.isExpanded = false;

        $scope.toggle = function() {
          $scope.isExpanded = !$scope.isExpanded;
        };

        $scope.setPriority = function(priority) {
          const oldPriority = $scope.task.priority;
          $scope.task.priority = priority; // Optimistic

          TaskService.updatePriority($scope.task.id, priority).catch(function() {
            $scope.task.priority = oldPriority; // Rollback
            NotificationService.error('Could not update priority.');
          });
        };

        $scope.statusOptions = ['todo', 'in-progress', 'review', 'done'];
        $scope.priorityOptions = ['low', 'medium', 'high', 'critical'];
      }],
      link: function(scope, element, attrs) {
        // Add priority class reactively
        scope.$watch('task.priority', function(priority) {
          element.removeClass('priority-low priority-medium priority-high priority-critical');
          if (priority) element.addClass('priority-' + priority);
        });

        // Overdue detection
        scope.$watch('task.dueDate', function(dueDate) {
          if (dueDate) {
            scope.isOverdue = new Date(dueDate) < new Date() && scope.task.status !== 'done';
          }
        });
      }
    };
  }
])

// ─────────────────────────────────────────────
// INFINITE SCROLL (attribute directive)
// ─────────────────────────────────────────────
.directive('tfInfiniteScroll', ['$window', '$timeout',
  function($window, $timeout) {
    return {
      restrict: 'A',
      scope: {
        tfInfiniteScroll: '&',
        tfScrollThreshold: '@'
      },
      link: function(scope, element, attrs) {
        const threshold = parseInt(scope.tfScrollThreshold) || 100;

        function checkScroll() {
          const el = element[0];
          const bottomReached = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
          if (bottomReached) {
            scope.$apply(function() {
              scope.tfInfiniteScroll();
            });
          }
        }

        element.on('scroll', checkScroll);

        scope.$on('$destroy', function() {
          element.off('scroll', checkScroll);
        });
      }
    };
  }
])

// ─────────────────────────────────────────────
// CLICK OUTSIDE (attribute directive)
// ─────────────────────────────────────────────
.directive('tfClickOutside', ['$document',
  function($document) {
    return {
      restrict: 'A',
      scope: {
        tfClickOutside: '&'
      },
      link: function(scope, element, attrs) {
        function handler(event) {
          if (!element[0].contains(event.target)) {
            scope.$apply(function() {
              scope.tfClickOutside();
            });
          }
        }

        $document.on('click', handler);

        scope.$on('$destroy', function() {
          $document.off('click', handler);
        });
      }
    };
  }
])

// ─────────────────────────────────────────────
// TOOLTIP (attribute directive)
// ─────────────────────────────────────────────
.directive('tfTooltip', ['$timeout',
  function($timeout) {
    return {
      restrict: 'A',
      scope: {
        tfTooltip: '@',
        tfTooltipPosition: '@'
      },
      link: function(scope, element, attrs) {
        let tooltip = null;

        element.on('mouseenter', function() {
          $timeout(function() {
            if (!scope.tfTooltip) return;
            tooltip = angular.element('<div class="tf-tooltip"></div>');
            tooltip.text(scope.tfTooltip);
            tooltip.addClass('tooltip-' + (scope.tfTooltipPosition || 'top'));
            angular.element(document.body).append(tooltip);

            const rect = element[0].getBoundingClientRect();
            tooltip.css({
              position: 'fixed',
              top: rect.top - 32 + 'px',
              left: rect.left + (rect.width / 2) + 'px',
              transform: 'translateX(-50%)'
            });
          }, 300);
        });

        element.on('mouseleave', function() {
          if (tooltip) {
            tooltip.remove();
            tooltip = null;
          }
        });

        scope.$on('$destroy', function() {
          element.off('mouseenter mouseleave');
          if (tooltip) tooltip.remove();
        });
      }
    };
  }
])

// ─────────────────────────────────────────────
// DATE PICKER WRAPPER (attribute directive)
// ─────────────────────────────────────────────
.directive('tfDatepicker', ['$timeout',
  function($timeout) {
    return {
      restrict: 'A',
      require: 'ngModel',
      link: function(scope, element, attrs, ngModel) {
        // Format model value to string for input
        ngModel.$formatters.push(function(value) {
          if (!value) return '';
          const d = new Date(value);
          return d.toISOString().substring(0, 10);
        });

        // Parse string back to Date
        ngModel.$parsers.push(function(value) {
          if (!value) return null;
          return new Date(value);
        });

        // Validation: must not be in the past for new tasks
        ngModel.$validators.futureDate = function(modelValue) {
          if (!modelValue || attrs.tfDatepicker === 'allow-past') return true;
          return new Date(modelValue) >= new Date(new Date().setHours(0,0,0,0));
        };
      }
    };
  }
])

// ─────────────────────────────────────────────
// NOTIFICATION TOAST CONTAINER
// ─────────────────────────────────────────────
.directive('tfNotifications', function() {
  return {
    restrict: 'E',
    template:
      '<div class="notifications-container">' +
      '  <div class="notification notification-{{n.type}}" ' +
      '       ng-repeat="n in notifications track by n.id" ' +
      '       ng-class="{\'notification-exit\': n.exiting}">' +
      '    <span class="notification-message">{{n.message}}</span>' +
      '    <button class="notification-close" ng-click="dismiss(n.id)">&times;</button>' +
      '  </div>' +
      '</div>',
    controller: ['$scope', '$rootScope', 'NotificationService',
      function($scope, $rootScope, NotificationService) {
        $scope.notifications = $rootScope.notifications;
        $scope.dismiss = function(id) {
          NotificationService.dismiss(id);
        };

        $scope.$watchCollection(
          function() { return $rootScope.notifications; },
          function(notifications) {
            $scope.notifications = notifications;
          }
        );
      }
    ]
  };
});
