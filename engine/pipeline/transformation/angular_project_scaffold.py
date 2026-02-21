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

    def check_integrity(self):
        """
        Verify all expected scaffold files are present.
        Logs a warning for each missing file so rules don't silently bail.
        """
        expected = [
            self.root / "angular.json",
            self.root / "package.json",
            self.root / "tsconfig.json",
            self.root / "tsconfig.app.json",
            self.src_dir / "main.ts",
            self.src_dir / "index.html",
            self.app_dir / "app.component.ts",
            self.app_dir / "app.module.ts",
            self.app_dir / "app-routing.module.ts",
        ]
        all_ok = True
        for p in expected:
            if not p.exists():
                print(f"[Scaffold] ⚠️  MISSING expected file: {p}")
                all_ok = False
        if all_ok:
            print("[Scaffold] ✅ All scaffold files present")
        return all_ok

    def ensure(self):
        self.app_dir.mkdir(parents=True, exist_ok=True)

        # angular.json
        self._write_if_changed(self.root / "angular.json", json.dumps({
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
                            "options": {"browserTarget": "evua-app:build"}
                        }
                    }
                }
            }
        }, indent=2))

        # package.json
        self._write_if_changed(self.root / "package.json", json.dumps({
            "name": "evua-angular-app",
            "private": True,
            "version": "0.0.0",
            "scripts": {"start": "ng serve", "build": "ng build"},
            "dependencies": {
                "@angular/core": "^17.0.0",
                "@angular/common": "^17.0.0",
                "@angular/common/http": "^17.0.0",
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
        }, indent=2))

        # tsconfig.json
        self._write_if_changed(self.root / "tsconfig.json", json.dumps({
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
        }, indent=2))

        # tsconfig.app.json
        self._write_if_changed(self.root / "tsconfig.app.json", json.dumps({
            "extends": "./tsconfig.json",
            "compilerOptions": {"outDir": "./out-tsc/app", "types": []},
            "files": ["src/main.ts"],
            "include": ["src/**/*.ts"]
        }, indent=2))

        # src/main.ts
        self._write_if_changed(self.src_dir / "main.ts", """\
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

platformBrowserDynamic()
  .bootstrapModule(AppModule)
  .catch(err => console.error(err));""")

        # src/index.html
        self._write_if_changed(self.src_dir / "index.html", """\
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
</html>""")

        # src/polyfills.ts
        self._write_if_changed(self.src_dir / "polyfills.ts", "import 'zone.js';")

        # src/app/app.component.ts
        self._write_if_changed(self.app_dir / "app.component.ts", """\
import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  template: '<h1>EVUA Angular App</h1><router-outlet></router-outlet>'
})
export class AppComponent {}""")

        # src/app/app.module.ts  (will be patched by HttpToHttpClientRule later)
        self._write_if_changed(self.app_dir / "app.module.ts", """\
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
export class AppModule {}""")

        # src/app/app-routing.module.ts  ← NEW: scaffold now always creates this
        routing_path = self.app_dir / "app-routing.module.ts"
        if not routing_path.exists():
            self._write_if_changed(routing_path, """\
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

const routes: Routes = [];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}""")

        self.check_integrity()
