"""Worker-local immutable code for fixtures that repeatedly load installed siblings.

Only compilation is shared. Each load still executes in its own module namespace;
no service, repository, module globals or observations are reused. Read and digest
the source on every load, including same-size edits with unchanged timestamps.
"""
import contextlib
import hashlib
import importlib.machinery
import marshal
import os
from pathlib import Path
import sys
import tempfile
import types


@contextlib.contextmanager
def compiled_sources(directory, cache_directory=None):
    """Cache code in this process, optionally in a fixture-owned child-process cache."""
    directory = Path(directory)
    cache = Path(cache_directory) if cache_directory is not None else None
    if cache is not None:
        try:
            cache.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError:
            cache = None
    loader = importlib.machinery.SourceFileLoader
    original = loader.get_code
    codes = {}

    def get_code(self, fullname):
        if not Path(self.path).is_relative_to(directory):
            return original(self, fullname)
        source = self.get_data(self.path)
        key = (self.path, hashlib.sha256(source).digest(), sys.flags.optimize)
        if key not in codes:
            stored = None
            if cache is not None:
                identity = repr((key, sys.implementation.cache_tag)).encode()
                stored = cache / (hashlib.sha256(identity).hexdigest() + '.code')
                try:
                    code = marshal.loads(stored.read_bytes())
                    if isinstance(code, types.CodeType) and code.co_filename == self.path:
                        codes[key] = code
                except (OSError, EOFError, ValueError, TypeError):
                    pass
            if key not in codes:
                codes[key] = self.source_to_code(source, self.path)
                if stored is not None:
                    # Children of this fixture may publish the same immutable code together.
                    # Never expose a partially written marshal stream to another child.
                    name = None
                    try:
                        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as temporary:
                            name = temporary.name
                            temporary.write(marshal.dumps(codes[key]))
                        os.replace(name, stored)
                    except OSError:
                        pass
                    finally:
                        if name is not None:
                            with contextlib.suppress(OSError):
                                os.unlink(name)
        return codes[key]

    loader.get_code = get_code
    try:
        yield
    finally:
        loader.get_code = original
        codes.clear()


def install_main_cache(path, directory, cache_directory):
    """Enable the same cache in a private fixture executable's child interpreters.

    Only the fixture's copy is edited. Imports of that copy keep their ordinary
    namespace; its main process installs the loader before loading siblings. The
    cache directory belongs to this fixture and dies with it, never to another
    worker. No module objects, keys, repositories or service state are persisted.
    """
    import ast
    import re

    path, directory = Path(path), Path(directory)
    if not path.resolve().is_relative_to(directory.resolve()):
        raise ValueError('entry point must be inside the private fixture')
    source = path.read_bytes()
    lines = source.splitlines(keepends=True)
    # The interpreter recognizes a shebang and an encoding cookie only at the top.
    insertion = int(bool(lines and lines[0].startswith(b'#!')))
    for index, line in enumerate(lines[:2]):
        if re.match(br'^[ \t\f]*#.*?coding[:=][ \t]*[-\w.]+', line):
            insertion = index + 1
    # Keep the module docstring and future imports in their required positions.
    for node in ast.parse(source, str(path)).body:
        if ((isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
             and isinstance(node.value.value, str))
                or (isinstance(node, ast.ImportFrom) and node.module == '__future__')):
            insertion = node.end_lineno
        else:
            break
    bootstrap = (
        "\nif __name__ == '__main__':\n"
        "    import atexit as _fixture_atexit\n"
        "    _fixture_compiler_namespace = {'__file__': %s}\n"
        "    with open(_fixture_compiler_namespace['__file__'], 'rb') as _fixture_compiler_source:\n"
        "        exec(compile(_fixture_compiler_source.read(), _fixture_compiler_namespace['__file__'], 'exec'),\n"
        "             _fixture_compiler_namespace)\n"
        "    _fixture_compiler = _fixture_compiler_namespace['compiled_sources'](%s, %s)\n"
        "    _fixture_compiler.__enter__()\n"
        "    _fixture_atexit.register(_fixture_compiler.__exit__, None, None, None)\n\n"
        % (ascii(str(Path(__file__).resolve())), ascii(str(directory)), ascii(str(cache_directory))))
    lines.insert(insertion, bootstrap.encode('ascii'))
    path.write_bytes(b''.join(lines))
