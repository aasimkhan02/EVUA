angular.module('app').config(function ($stateProvider, $urlRouterProvider) {
  $urlRouterProvider.otherwise('/users');

  $stateProvider
    .state('users', {
      url: '/users',
      controller: 'UserCtrl',
      template: `
        <h2>Users</h2>
        <ul>
          <li ng-repeat="u in users">
            <a ui-sref="profile({ id: u.id })">{{ u.name }}</a>
          </li>
        </ul>
      `
    })
    .state('profile', {
      url: '/profile/:id',
      controller: 'ProfileCtrl',
      template: `
        <my-panel title="{{ user.name }}">
          <input ng-model="user.name" />
        </my-panel>
      `
    });
});
