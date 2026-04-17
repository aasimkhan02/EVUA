"""
File Scanner
Discovers PHP files for the migration pipeline.
"""
import os
from pathlib import Path

# Directories that should always be skipped
_DEFAULT_SKIP_DIRS = frozenset({
    "vendor",
    "node_modules",
    ".git",
    ".svn",
    ".hg",
    ".idea",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
})


class FileScanner:
    """
    Recursively scans a directory tree for PHP source files.

    Parameters
    ----------
    extensions : tuple[str, ...]
        File extensions to include (default: ``(".php",)``).
    skip_dirs : set[str] | None
        Directory names to skip.  Defaults to a standard set that excludes
        vendor/, node_modules/, .git/, etc.
    """

    def __init__(
        self,
        extensions: tuple[str, ...] = (".php",),
        skip_dirs: set[str] | None = None,
    ):
        self.extensions = extensions
        self.skip_dirs: frozenset[str] = (
            frozenset(skip_dirs) if skip_dirs is not None else _DEFAULT_SKIP_DIRS
        )

    def scan(self, directory: str) -> list[str]:
        """
        Return a sorted list of absolute paths to all matching files found
        under *directory*.

        Parameters
        ----------
        directory : str
            Root directory to scan.

        Returns
        -------
        list[str]
        """
        files: list[str] = []

        for root, dirs, filenames in os.walk(directory):
            # Prune skipped directories in-place so os.walk won't recurse into them
            dirs[:] = sorted(
                d for d in dirs if d not in self.skip_dirs
            )

            for fname in filenames:
                if any(fname.endswith(ext) for ext in self.extensions):
                    files.append(os.path.join(root, fname))

        return sorted(files)

    def scan_paths(self, paths: list[str]) -> list[str]:
        """
        Accept a mix of file paths and directories, returning a flat list
        of all matching PHP files.
        """
        result: list[str] = []
        for path in paths:
            p = Path(path)
            if p.is_file():
                if any(p.suffix == ext for ext in self.extensions):
                    result.append(str(p))
            elif p.is_dir():
                result.extend(self.scan(str(p)))
        return sorted(set(result))
