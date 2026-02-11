(function () {
  'use strict';

  angular
    .module('crudApp', [])
    .controller('TodoController', function ($scope, TodoService) {
      $scope.todos = TodoService.getTodos();
      $scope.newTodo = '';

      $scope.addTodo = function () {
        if (!$scope.newTodo) return;
        TodoService.addTodo($scope.newTodo);
        $scope.newTodo = '';
      };

      $scope.removeTodo = function (idx) {
        TodoService.removeTodo(idx);
      };
    });
})();
