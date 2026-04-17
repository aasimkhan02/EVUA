import subprocess
from pathlib import Path

class TestRunner:
    def run(self, repo_path: str):
        """
        Runs framework-aware tests.
        - If generated Angular workspace exists, runs ng test there
        - Else falls back to npm test in the original repo
        Returns: (passed: bool, output: str)
        """
        repo_path = Path(repo_path)
        angular_out = Path("out/angular-app")

        try:
            if (angular_out / "angular.json").exists():
                cmd = ["ng", "test", "--watch=false", "--browsers=ChromeHeadless"]
                cwd = angular_out
            elif (repo_path / "angular.json").exists():
                cmd = ["ng", "test", "--watch=false", "--browsers=ChromeHeadless"]
                cwd = repo_path
            else:
                cmd = ["npm", "test", "--", "--watch=false"]
                cwd = repo_path

            result = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=180,
            )

            passed = result.returncode == 0
            output = result.stdout + "\n" + result.stderr
            return passed, output

        except FileNotFoundError as e:
            return False, f"Test command not found: {e}"
        except subprocess.TimeoutExpired:
            return False, "Test execution timed out"
        except Exception as e:
            return False, str(e)
