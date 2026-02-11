import subprocess

class TestRunner:
    def run(self, repo_path: str):
        """
        Runs project tests. Expects `npm test` or similar to exist.
        Returns: (passed: bool, output: str)
        """
        try:
            result = subprocess.run(
                ["npm", "test", "--", "--watch=false"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            passed = result.returncode == 0
            output = result.stdout + "\n" + result.stderr
            return passed, output
        except Exception as e:
            return False, str(e)
