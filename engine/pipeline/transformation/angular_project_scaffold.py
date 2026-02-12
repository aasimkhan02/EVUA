from pathlib import Path
import json

class AngularProjectScaffold:
    def __init__(self, root="out/angular-app"):
        self.root = Path(root)
        self.src_dir = self.root / "src"
        self.app_dir = self.src_dir / "app"

    def _write_if_changed(self, path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            old = path.read_text(encoding="utf-8")
            if old == content:
                return  # idempotent: don't touch unchanged files
        path.write_text(content, encoding="utf-8")

    def ensure(self):
        self.app_dir.mkdir(parents=True, exist_ok=True)

        # angular.json (deterministic)
        angular_json = self.root / "angular.json"
        angular_json_content = json.dumps({
            "version": 1,
            "projects": {
                "evua-app": {
                    "projectType": "application",
                    "root": "",
                    "sourceRoot": "src",
                    "architect": {}
                }
            }
        }, indent=2)
        self._write_if_changed(angular_json, angular_json_content)

        # package.json (minimal bootable workspace)
        package_json = self.root / "package.json"
        package_json_content = json.dumps({
            "name": "evua-angular-app",
            "private": True,
            "version": "0.0.0",
            "scripts": {
                "start": "ng serve",
                "build": "ng build"
            },
            "dependencies": {
                "@angular/core": "^17.0.0",
                "@angular/common": "^17.0.0",
                "@angular/compiler": "^17.0.0",
                "@angular/platform-browser": "^17.0.0",
                "@angular/platform-browser-dynamic": "^17.0.0",
                "rxjs": "^7.8.0",
                "zone.js": "^0.14.0"
            },
            "devDependencies": {
                "@angular/cli": "^17.0.0",
                "typescript": "^5.2.0"
            }
        }, indent=2)
        self._write_if_changed(package_json, package_json_content)

        # tsconfig.json
        tsconfig = self.root / "tsconfig.json"
        tsconfig_content = json.dumps({
            "compilerOptions": {
                "target": "ES2022",
                "useDefineForClassFields": False,
                "module": "ES2022",
                "moduleResolution": "Node",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True
            }
        }, indent=2)
        self._write_if_changed(tsconfig, tsconfig_content)

        # src/main.ts
        main_ts = self.src_dir / "main.ts"
        main_ts_content = """\
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic()
  .bootstrapModule(AppModule)
  .catch(err => console.error(err));
"""
        self._write_if_changed(main_ts, main_ts_content.strip())

        # src/index.html
        index_html = self.src_dir / "index.html"
        index_html_content = """\
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
"""
        self._write_if_changed(index_html, index_html_content.strip())

        # src/app/app.component.ts
        app_component = self.app_dir / "app.component.ts"
        app_component_content = """\
import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  template: '<h1>EVUA Angular App</h1><router-outlet></router-outlet>'
})
export class AppComponent {}
"""
        self._write_if_changed(app_component, app_component_content.strip())

        # src/app/app.module.ts (deterministic base)
        app_module = self.app_dir / "app.module.ts"
        app_module_content = """\
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
"""
        self._write_if_changed(app_module, app_module_content.strip())
