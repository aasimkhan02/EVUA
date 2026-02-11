from pathlib import Path

class AngularProjectScaffold:
    def __init__(self, root="out/angular-app"):
        self.root = Path(root)
        self.src_dir = self.root / "src"
        self.app_dir = self.src_dir / "app"

    def ensure(self):
        self.app_dir.mkdir(parents=True, exist_ok=True)

        angular_json = self.root / "angular.json"
        if not angular_json.exists():
            angular_json.write_text("""
{
  "version": 1,
  "projects": {
    "evua-app": {
      "projectType": "application",
      "root": "",
      "sourceRoot": "src",
      "architect": {}
    }
  }
}
""".strip())

        app_module = self.app_dir / "app.module.ts"
        if not app_module.exists():
            app_module.write_text("""
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { RouterModule, Routes } from '@angular/router';
import { AppComponent } from './app.component';

const routes: Routes = [];

@NgModule({
  declarations: [AppComponent],
  imports: [BrowserModule, RouterModule.forRoot(routes)],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule {}
""".strip())

        app_component = self.app_dir / "app.component.ts"
        if not app_component.exists():
            app_component.write_text("""
import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  template: '<h1>EVUA Angular App</h1><router-outlet></router-outlet>'
})
export class AppComponent {}
""".strip())

        # Minimal boot files (so ng serve can actually run later)
        main_ts = self.src_dir / "main.ts"
        if not main_ts.exists():
            main_ts.write_text("""
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
""".strip())

        index_html = self.src_dir / "index.html"
        if not index_html.exists():
            index_html.write_text("""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>EVUA Angular App</title>
    <base href="/">
  </head>
  <body>
    <app-root></app-root>
  </body>
</html>
""".strip())
