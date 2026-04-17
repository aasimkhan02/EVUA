const fs = require('fs');
const path = require('path');

function getAllFiles(dir) {
  const results = [];
  if (!fs.existsSync(dir)) return results;
  fs.readdirSync(dir).forEach(f => {
    const full = path.join(dir, f);
    if (fs.statSync(full).isDirectory() && !['node_modules', '.git'].includes(f)) {
      results.push(...getAllFiles(full));
    } else {
      results.push(full);
    }
  });
  return results;
}

function assertProject(assertFile, outputDir) {
  const data = JSON.parse(fs.readFileSync(assertFile, 'utf-8'));

  console.log('\n═══════════════════════════════════════');
  console.log('  AdminPulse — Project Assertion Check');
  console.log('═══════════════════════════════════════\n');

  const allFiles = getAllFiles(outputDir);
  const allCode  = allFiles
    .filter(f => f.endsWith('.js') || f.endsWith('.html'))
    .map(f => fs.readFileSync(f, 'utf-8')).join('\n');

  // 1. Components — match filename OR code reference
  console.log('📦 Components:');
  data.components.forEach(c => {
    const inFile = allFiles.some(f => path.basename(f).toLowerCase().includes(c.toLowerCase()));
    const inCode = allCode.toLowerCase().includes(c.toLowerCase());
    console.log(`   ${inFile || inCode ? '✅' : '❌'} ${c}`);
  });

  // 2. Routes in app.js
  console.log('\n🔀 Routes:');
  const appJs = fs.readFileSync(path.join(outputDir, 'js/app.js'), 'utf-8');
  data.routes.forEach(route => {
    const pattern = route.replace(/:[^/]+/g, '[^"\']+').replace(/\//g, '\\/');
    const found = new RegExp(pattern).test(appJs);
    console.log(`   ${found ? '✅' : '❌'} ${route}`);
  });

  // 3. Simulated HTTP endpoints in services
  console.log('\n🌐 Simulated HTTP endpoints (in services):');
  const serviceContent = allFiles
    .filter(f => f.includes('services'))
    .map(f => fs.readFileSync(f, 'utf-8')).join('\n');
  data.http_calls.forEach(api => {
    console.log(`   ${serviceContent.includes(api) ? '✅' : '❌'} ${api}`);
  });

  // 4. Features via keyword presence
  console.log('\n🔍 Features:');
  const featureKeywords = {
    list_users:           ['ng-repeat', 'pagedUsers'],
    create_user:          ['UserService.create'],
    edit_user:            ['/users/edit', 'UserService.update'],
    delete_user:          ['UserService.remove'],
    search_filter:        ['searchQuery', 'search-input'],
    role_filter:          ['roleFilter', 'filter-select'],
    status_filter:        ['statusFilter'],
    pagination:           ['currentPage', 'totalPages'],
    sort_columns:         ['sortBy', 'sortField'],
    activity_log:         ['ActivityController', 'timeline'],
    dashboard_stats:      ['getDashboardStats', 'stats-grid'],
    bar_chart:            ['chartBars', 'bar-login'],
    form_validation:      ['validate', 'form-error'],
    confirm_modal:        ['confirmDelete', 'modal-backdrop'],
    toast_notifications:  ['showToast', 'toast']
  };
  data.features.forEach(feature => {
    const keywords = featureKeywords[feature] || [feature];
    const found = keywords.every(kw => allCode.includes(kw));
    console.log(`   ${found ? '✅' : '❌'} ${feature}`);
  });

  // 5. Architecture summary
  console.log('\n📐 Architecture:');
  const controllers = allFiles.filter(f => f.includes('controllers')).length;
  const services    = allFiles.filter(f => f.includes('services')).length;
  const filters     = allFiles.filter(f => f.includes('filters')).length;
  const views       = allFiles.filter(f => f.includes('views') && f.endsWith('.html')).length;
  console.log(`   ${controllers >= 3 ? '✅' : '❌'} Controllers: ${controllers} (need ≥3)`);
  console.log(`   ${services   >= 2 ? '✅' : '❌'} Services:    ${services}    (need ≥2)`);
  console.log(`   ${filters    >= 1 ? '✅' : '❌'} Filters:     ${filters}`);
  console.log(`   ${views      >= 3 ? '✅' : '❌'} Views:       ${views}`);

  console.log('\n═══════════════════════════════════════\n');
}

assertProject('./dashboard.assert.json', './');
