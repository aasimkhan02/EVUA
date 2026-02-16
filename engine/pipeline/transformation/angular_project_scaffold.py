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
                return  # idempotent
        path.write_text(content, encoding="utf-8")

    def ensure(self):
        self.app_dir.mkdir(parents=True, exist_ok=True)

        # ✅ angular.json (Angular CLI bootable)
        angular_json = self.root / "angular.json"
        angular_json_content = json.dumps({
            "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
            "version": 1,
            "defaultProject": "evua-app",
            "projects": {
                "evua-app": {
                    "projectType": "application",
                    "root": "",
                    "sourceRoot": "src",
                    "architect": {
                        "build": {
                            "builder": "@angular-devkit/build-angular:browser",
                            "options": {
                                "outputPath": "dist/evua-app",
                                "index": "src/index.html",
                                "main": "src/main.ts",
                                "tsConfig": "tsconfig.app.json",
                                "assets": ["src/favicon.ico", "src/assets"],
                                "styles": [],
                                "scripts": []
                            }
                        },
                        "serve": {
                            "builder": "@angular-devkit/build-angular:dev-server",
                            "options": {
                                "browserTarget": "evua-app:build"
                            }
                        }
                    }
                }
            }
        }, indent=2)
        self._write_if_changed(angular_json, angular_json_content)

        # package.json
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
                "@angular/router": "^17.0.0",
                "rxjs": "^7.8.0",
                "zone.js": "^0.14.0"
            },
            "devDependencies": {
                "@angular/cli": "^17.0.0",
                "@angular-devkit/build-angular": "^17.0.0",
                "typescript": "^5.2.0"
            }
        }, indent=2)
        self._write_if_changed(package_json, package_json_content)

        # tsconfig.json (base)
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

        # tsconfig.app.json (REQUIRED by Angular CLI)
        tsconfig_app = self.root / "tsconfig.app.json"
        tsconfig_app_content = json.dumps({
            "extends": "./tsconfig.json",
            "compilerOptions": {
                "outDir": "./out-tsc/app",
                "types": []
            },
            "files": [
                "src/main.ts"
            ],
            "include": [
                "src/**/*.ts"
            ]
        }, indent=2)
        self._write_if_changed(tsconfig_app, tsconfig_app_content)

        # src/main.ts
        main_ts = self.src_dir / "main.ts"
        self._write_if_changed(main_ts, """\
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic()
  .bootstrapModule(AppModule)
  .catch(err => console.error(err));
""".strip())

        # src/index.html
        index_html = self.src_dir / "index.html"
        self._write_if_changed(index_html, """\
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

        # src/polyfills.ts (some Angular setups expect this)
        polyfills = self.src_dir / "polyfills.ts"
        self._write_if_changed(polyfills, """\
// Polyfills placeholder (Angular CLI expects this file to exist)
import 'zone.js';
""".strip())

        # src/app/app.component.ts
        app_component = self.app_dir / "app.component.ts"
        self._write_if_changed(app_component, """\
import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  template: '<h1>EVUA Angular App</h1><router-outlet></router-outlet>'
})
export class AppComponent {}
""".strip())

        # src/app/app.module.ts (NO RouterModule here; routing lives in AppRoutingModule)
        app_module = self.app_dir / "app.module.ts"
        self._write_if_changed(app_module, """\
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { AppComponent } from './app.component';
import { AppRoutingModule } from './app-routing.module';

@NgModule({
  declarations: [AppComponent],
  imports: [BrowserModule, AppRoutingModule],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule {}
""".strip())
