"""Coordinator-owned syscall evidence for declared workers and sequential proposals."""
import ast
import os
from pathlib import Path
import re

# -yy supplies directory FD paths, including AT_FDCWD, so relative openat reads
# remain attributable across exec and child processes without trusting audit hooks.
OPEN = re.compile(r'\b(open|openat|openat2)\((.*)\)\s+=')
QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"')


def command(trace, argv):
    return ['/usr/bin/strace', '-f', '-qq', '-yy', '-s', '65535',
            '-e', 'trace=file', '-o', str(trace), *argv]


def syscall_lines(trace):
    pending = {}
    for line in Path(trace).read_text(errors='replace').splitlines():
        pid = line.split(None, 1)[0]
        if '<unfinished ...>' in line:
            pending[pid] = line.replace('<unfinished ...>', '')
            continue
        if ' resumed>' in line:
            if pid not in pending:
                raise ValueError('unmatched resumed syscall')
            line = pending.pop(pid) + line.split(' resumed>', 1)[1]
        yield line
    if any(OPEN.search(line + ') =') for line in pending.values()):
        raise ValueError('incomplete file-read trace')


def opened_paths(trace, *, successful=False):
    for line in syscall_lines(trace):
        match = OPEN.search(line)
        if successful and '= -1 ' in line:
            continue
        if not match:
            continue
        arguments = match[2]
        quoted = QUOTED.search(arguments)
        if not quoted or 'O_WRONLY' in arguments or 'O_PATH' in arguments:
            continue
        try:
            name = ast.literal_eval(quoted[0])
        except (ValueError, SyntaxError):
            raise ValueError('undecodable syscall path')
        if not name.startswith('/'):
            prefix = arguments[:quoted.start()]
            directory = re.search(r'<(/[^>]*)>', prefix)
            if not directory:
                raise ValueError('unresolved syscall directory: ' + line[:200])
            name = str(Path(directory[1]) / name)
        yield Path(os.path.normpath(name)), 'O_DIRECTORY' in arguments


def reads(trace, root):
    root = Path(root).absolute()
    for path, directory in opened_paths(trace):
        if path == root or root in path.parents:
            yield str(path.relative_to(root)), directory


def check(trace, root, declared, absent=(), *, runtime=(), scratch=None):
    for line in syscall_lines(trace):
        if OPEN.search(line) and '= -1 EACCES' in line:
            raise ValueError('undeclared input read: sandbox denied a file open')
    # Startup happens before Landlock. Check its reads too, including preloaded libraries.
    if scratch is not None:
        grants = [Path(root).resolve(), Path(scratch).resolve(),
                  *(Path(p).resolve() for p in runtime)]
        devices = {Path('/dev/null'), Path('/dev/urandom')}
        for path, directory in opened_paths(trace, successful=True):
            resolved = path.resolve()
            if resolved in devices or any(resolved == p or p in resolved.parents for p in grants):
                continue
            raise ValueError('undeclared runtime read: ' + str(path))
    allowed = set(declared) | set(absent)
    directories = {'.'}
    for name in allowed:
        directories.update(str(p) for p in Path(name).parents)
    violations = []
    for name, directory in reads(trace, root):
        if name in allowed or name in directories:
            continue
        # Bytecode is deliberately absent and never an execution input (-B).
        if '__pycache__' in Path(name).parts and name.endswith('.pyc'):
            continue
        violations.append(name)
    if violations:
        raise ValueError('undeclared input read: ' + ', '.join(sorted(set(violations))[:8]))
