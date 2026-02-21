angular.module('app').config(function ($stateProvider, $urlRouterProvider) {
  $urlRouterProvider.otherwise('/home');

  $stateProvider
    .state('home', {
      url: '/home',
      template: '<h1>Home</h1><a ui-sref="profile">Profile</a>'
    })
    .state('profile', {
      url: '/profile/:id',
      controller: 'ProfileCtrl',
      template: '<p>User {{ id }}</p>'
    });
});
