"""Coordinator-owned file and metadata evidence, including unsuccessful probes."""
import ast
import os
from pathlib import Path
import re

QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"')
CALL = re.compile(r'\b([a-zA-Z0-9_]+)\((.*)\)\s+=\s+(.*)')
PATH_READS = {'open', 'openat', 'openat2', 'stat', 'lstat', 'statx', 'newfstatat',
              'access', 'faccessat', 'faccessat2', 'readlink', 'readlinkat',
              'statfs', 'getxattr', 'lgetxattr', 'listxattr', 'llistxattr',
              'execve', 'execveat', 'chdir', 'symlink', 'symlinkat'}
FD_READS = {'fstat', 'fstatfs', 'getdents', 'getdents64', 'fchdir'}


def command(trace, argv):
    # file includes metadata probes, even failed ones. getdents is not in file.
    return ['/usr/bin/strace', '-f', '-qq', '-yy', '-s', '65535',
            '-e', 'trace=%file,%process,fstat,fstatfs,getdents,getdents64,fchdir',
            '-o', str(trace), *argv]


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
    if pending:
        raise ValueError('incomplete file-read trace')


def accesses(trace, *, cwd=None):
    """Yield (absolute path, content/metadata/listing, success) for every probe.

    FD annotations resolve *at calls and getdents. Track cwd for older path syscalls
    and inherit it across fork/clone. Undecodable evidence is a failure, never a skip.
    """
    initial = Path(cwd or Path.cwd()).absolute()
    directories = {}
    for line in syscall_lines(trace):
        match = CALL.search(line)
        if not match:
            continue
        pid = line.split(None, 1)[0]
        call, arguments, result = match.groups()
        current = directories.setdefault(pid, initial)
        success = not result.startswith('-1 ')
        if call in ('fork', 'vfork', 'clone', 'clone3') and success:
            child = result.split()[0]
            if child.isdigit():
                directories[child] = current
            continue
        if call not in PATH_READS | FD_READS:
            continue
        kind = 'metadata'
        if call in FD_READS:
            fd = arguments.split(',', 1)[0]
            annotated = re.search(r'<(/[^<>]*)', fd)
            if not annotated:
                # Pipes, sockets and anonymous descriptors carry no file input.
                if '<' in fd or result.startswith('-1 EBADF'):
                    continue
                raise ValueError('unresolved syscall descriptor: ' + line[:200])
            name = annotated[1]
            if call.startswith('getdents'):
                kind = 'listing'
        else:
            quoted = QUOTED.search(arguments)
            if not quoted:
                if arguments.startswith('NULL,') and not success:
                    continue
                raise ValueError('undecodable syscall path: ' + line[:200])
            try:
                name = ast.literal_eval(quoted[0])
            except (ValueError, SyntaxError):
                raise ValueError('undecodable syscall path')
            if call in ('symlink', 'symlinkat'):
                # Treat aliases as input capabilities at creation, even if later deleted.
                destination = list(QUOTED.finditer(arguments))
                if len(destination) < 2:
                    raise ValueError('undecodable symlink destination')
                link = ast.literal_eval(destination[1][0])
                annotation = re.search(r'<(/[^<>]*)', arguments[quoted.end():destination[1].start()])
                linkbase = Path(annotation[1]) if annotation else current
                targetbase = (linkbase / link).parent
                if not name.startswith('/'):
                    name = str(targetbase / name)
                kind = 'content'
            if not name.startswith('/'):
                prefix = arguments[:quoted.start()]
                directory = re.search(r'<(/[^<>]*)', prefix)
                if directory:
                    base = Path(directory[1])
                elif not prefix or 'AT_FDCWD' in prefix:
                    base = current
                else:
                    raise ValueError('unresolved syscall directory: ' + line[:200])
                name = str(base / name)
            if call.startswith('open'):
                if 'O_DIRECTORY' in arguments:
                    kind = 'listing'
                elif 'O_WRONLY' not in arguments and 'O_PATH' not in arguments:
                    kind = 'content'
            elif call.startswith('execve'):
                kind = 'content'
        # Normalization must not erase a probe of an undeclared traversal component.
        parts = Path(name).parts
        for index, part in enumerate(parts):
            if part == '..' and index:
                yield Path(os.path.normpath(str(Path(*parts[:index])))), 'metadata', success
        path = Path(os.path.normpath(name))
        if call in ('chdir', 'fchdir') and success:
            directories[pid] = path
        yield path, kind, success


def opened_paths(trace, *, successful=False, cwd=None):
    # Compatibility name: now includes every file and metadata input, not just opens.
    for path, kind, success in accesses(trace, cwd=cwd):
        if not successful or success:
            yield path, kind == 'listing'


def reads(trace, root):
    root = Path(root).absolute()
    for path, directory in opened_paths(trace, cwd=root):
        if path == root or root in path.parents:
            yield str(path.relative_to(root)), directory


def check(trace, root, declared, absent=(), *, runtime=(), scratch=None, directories=(), runtime_absent=()):
    root = Path(root).absolute()
    allowed = set(declared) | set(absent)
    parents = {'.'}
    for name in allowed | set(directories):
        parents.update(str(p) for p in Path(name).parents)
    grants = [root, *(Path(p).resolve() for p in runtime)]
    if scratch is not None:
        grants.append(Path(scratch).resolve())
    devices = {Path('/dev/null'), Path('/dev/urandom')}
    for path, kind, success in accesses(trace, cwd=root):
        resolved = path.resolve()
        if resolved == root or root in resolved.parents:
            path = resolved
        if path == root or root in path.parents:
            name = str(path.relative_to(root))
            if kind == 'listing':
                permitted = name in directories
            else:
                permitted = name in allowed or (kind == 'metadata' and name in parents)
            if not permitted:
                raise ValueError('undeclared input read: ' + name + ' (' + kind + ')')
        elif scratch is not None:
            if not success and str(path) in runtime_absent:
                continue
            # Include failed external probes: an absent dependency still affects execution.
            resolved = path.resolve()
            if resolved in devices or any(resolved == p or p in resolved.parents for p in grants):
                continue
            if kind == 'metadata' and any(resolved in p.parents for p in grants):
                continue
            raise ValueError('undeclared runtime read: ' + str(path) + ' (' + kind + ')')
