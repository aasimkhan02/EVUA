(function () {
  'use strict';

  angular.module('crudApp').service('TodoService', function () {
    var todos = ['Learn AngularJS', 'Migrate with EVUA'];

    this.getTodos = function () {
      return todos;
    };

    this.addTodo = function (todo) {
      todos.push(todo);
    };

    this.removeTodo = function (idx) {
      todos.splice(idx, 1);
    };
  });
})();
