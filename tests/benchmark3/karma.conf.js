module.exports = function (config) {
  config.set({
    basePath: '',
    frameworks: ['jasmine'],
    files: [
      'node_modules/angular/angular.js',
      'node_modules/angular-mocks/angular-mocks.js',
      'app.js',
      'services.js',
      'controllers/**/*.js',
      'test/**/*.spec.js'
    ],
    browsers: ['ChromeHeadless'],
    singleRun: true
  });
};
