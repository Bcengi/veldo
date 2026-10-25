"""Worker-local immutable code for fixtures that repeatedly load installed siblings.

Only compilation is shared. Each load still executes in its own module namespace;
no service, repository, module globals or observations are reused. Read and digest
the source on every load, including same-size edits with unchanged timestamps.
"""
import contextlib
import hashlib
import importlib.machinery
from pathlib import Path
import sys


@contextlib.contextmanager
def compiled_sources(directory):
    directory = Path(directory)
    loader = importlib.machinery.SourceFileLoader
    original = loader.get_code
    codes = {}

    def get_code(self, fullname):
        if not Path(self.path).is_relative_to(directory):
            return original(self, fullname)
        source = self.get_data(self.path)
        key = (self.path, hashlib.sha256(source).digest(), sys.flags.optimize)
        if key not in codes:
            codes[key] = self.source_to_code(source, self.path)
        return codes[key]

    loader.get_code = get_code
    try:
        yield
    finally:
        loader.get_code = original
        codes.clear()
