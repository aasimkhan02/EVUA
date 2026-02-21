from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold


def test_scaffold_creates_files(tmp_path):
    root = tmp_path / "out"
    s = AngularProjectScaffold(root)

    s.ensure()

    assert (root / "angular.json").exists()
    assert (root / "package.json").exists()
    assert (root / "tsconfig.json").exists()
    assert (root / "tsconfig.app.json").exists()
    assert (root / "src" / "main.ts").exists()
    assert (root / "src" / "index.html").exists()
    assert (root / "src" / "app" / "app.component.ts").exists()
    assert (root / "src" / "app" / "app.module.ts").exists()


def test_scaffold_idempotent(tmp_path):
    root = tmp_path / "out"
    s = AngularProjectScaffold(root)

    s.ensure()
    first = (root / "angular.json").read_text(encoding="utf-8")

    s.ensure()
    second = (root / "angular.json").read_text(encoding="utf-8")

    assert first == second
