"""Ensures local packages are importable without installing the repo."""
import pathlib
import sys

BACKEND_ROOT = pathlib.Path(__file__).parent
REPO_ROOT = BACKEND_ROOT.parent

for path in (BACKEND_ROOT, REPO_ROOT):
    sys.path.insert(0, str(path))
