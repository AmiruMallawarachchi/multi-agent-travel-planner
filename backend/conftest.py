"""Ensures `agents` and `core` are importable regardless of where pytest is
invoked from, without needing the package installed or PYTHONPATH set."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
