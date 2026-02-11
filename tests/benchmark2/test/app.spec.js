describe('TodoController + TodoService', function () {
  beforeEach(module('crudApp'));

  let $controller;
  let $rootScope;
  let TodoService;

  beforeEach(inject(function (_$controller_, _$rootScope_, _TodoService_) {
    $controller = _$controller_;
    $rootScope = _$rootScope_;
    TodoService = _TodoService_;
  }));

  it('should add and remove todos', function () {
    const $scope = $rootScope.$new();
    $controller('TodoController', { $scope, TodoService });

    expect($scope.todos.length).toBe(2);

    $scope.newTodo = 'Write tests';
    $scope.addTodo();
    expect($scope.todos).toContain('Write tests');

    $scope.removeTodo(0);
    expect($scope.todos.length).toBe(2);
  });
});
