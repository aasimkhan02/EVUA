angular.module('advancedApp', [])

  .service('UserService', function($http) {
    this.fetch = function() {
      return $http.get('/api/users');
    };
  })

  .factory('Logger', function() {
    return {
      log: function(msg) {
        console.log(msg);
      }
    };
  })

  .controller('UserController', function($scope, $compile, UserService, Logger) {
    $scope.users = [];
    $scope.query = "";

    $scope.load = function() {
      UserService.fetch().then(function(res) {
        $scope.users = res.data;
      });
    };

    $scope.add = function() {
      $scope.users.push({ name: $scope.query });
      Logger.log("Added user");
      $scope.query = "";
    };

    // shallow watch
    $scope.$watch('query', function(newVal) {
      Logger.log("Query changed: " + newVal);
    });

    // 🔥 deep watch (edge case)
    $scope.$watch('users', function(newVal) {
      Logger.log("Users changed");
    }, true);

    // 🔥 nested scope inheritance (edge case)
    var childScope = $scope.$new();
    childScope.temp = "nested";

    // 🔥 $compile usage (edge case)
    var el = angular.element("<div>{{query}}</div>");
    var compiled = $compile(el)($scope);
  })

  .controller('AdminController', function($scope) {
    $scope.isAdmin = true;

    $scope.toggle = function() {
      $scope.isAdmin = !$scope.isAdmin;
    };
  })

  // 🔥 custom directive with compile + link + transclusion (edge case)
  .directive('fancyPanel', function() {
    return {
      restrict: 'E',
      transclude: true,
      scope: {
        title: '@'
      },
      compile: function(tElem, tAttrs) {
        tElem.append('<div class="content" ng-transclude></div>');
        return function link(scope, elem, attrs) {
          console.log("Linking fancyPanel:", attrs.title);
        };
      }
    };
  });

  angular.module('advancedApp')
  .directive('fancyPanel', function($compile) {
    return {
      transclude: true,
      compile: function(tElem) {
        return function link(scope) {
          var el = $compile("<div>{{scopeVar}}</div>")(scope);
          tElem.append(el);
          var child = scope.$new();   // nested scope
        };
      }
    };
  });

