angular.module('app').controller('TodoCtrl', function ($scope) {
  $scope.todos = [
    { text: 'Buy milk', done: false },
    { text: 'Ship EVUA', done: true }
  ];

  $scope.addTodo = function () {
    if ($scope.newTodo) {
      $scope.todos.push({ text: $scope.newTodo, done: false });
      $scope.newTodo = '';
    }
  };
});
