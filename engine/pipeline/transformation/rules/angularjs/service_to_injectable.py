from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.helpers import iter_services


class ServiceToInjectableRule:
    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project  = AngularProjectScaffold(out_dir)
        self.out_dir  = Path(out_dir) / "src" / "app"
        self.dry_run  = dry_run

    def apply(self, analysis, patterns):
        print("\n========== ServiceToInjectableRule.apply() ==========")
        if self.dry_run:
            print("[ServiceToInjectable] DRY RUN — no files will be written")

        changes = []

        if not self.dry_run:
            self.project.ensure()

        services = list(iter_services(analysis, patterns))
        print(f"[ServiceToInjectable] Services detected: {len(services)}")

        for node in services:
            raw_name = node.name

            # Normalise: AuthService → AuthService
            #            ConfigFactory → ConfigFactoryService (keep Factory in name)
            #            UserSvc → UserService
            if raw_name.lower().endswith("service") or raw_name.lower().endswith("svc"):
                base       = raw_name.replace("Service", "").replace("Svc", "")
                class_name = base + "Service"
            elif raw_name.lower().endswith("factory"):
                # Keep full name so AuthorityFactory → AuthorityFactoryService is clear
                class_name = raw_name  # e.g. ConfigFactory stays ConfigFactory
                base       = raw_name
            else:
                class_name = raw_name + "Service"
                base       = raw_name

            # File name: full lowercased name so ConfigFactory → configfactory.service.ts
            file_name = f"{raw_name.lower()}.service.ts"
            ts_path   = self.out_dir / file_name

            ts_code = (
                f"import {{ Injectable }} from '@angular/core';\n\n"
                f"@Injectable({{\n"
                f"  providedIn: 'root'\n"
                f"}})\n"
                f"export class {class_name} {{\n"
                f"  // TODO: migrate service logic from AngularJS {raw_name}\n"
                f"}}\n"
            )

            if self.dry_run:
                print(f"[DRY RUN] Would write: {ts_path}")
                print(f"[DRY RUN] Content preview:\n{ts_code[:200]}")
            else:
                if not ts_path.exists() or ts_path.read_text(encoding="utf-8") != ts_code:
                    ts_path.parent.mkdir(parents=True, exist_ok=True)
                    ts_path.write_text(ts_code, encoding="utf-8")
                    print(f"[ServiceToInjectable] Written: {ts_path}")

            changes.append(Change(
                before_id=node.id,
                after_id="injectable_" + node.id,
                source=ChangeSource.RULE,
                reason=f"Service → @Injectable(providedIn: 'root') at {ts_path}"
            ))

        print("========== ServiceToInjectableRule DONE ==========\n")
        return changes