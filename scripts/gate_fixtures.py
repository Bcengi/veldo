"""Private gate fixture allocation, outside temporary and runtime roots.

VELDO_FIXTURE_PARENT is installation/launcher input; VELDO_FIXTURE_ROOT
is only an inherited allocation. Snapshot both before any run environment is built.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import pwd
import re
import shutil
import stat
import tempfile


class FixtureRefused(ValueError):
    pass


ENVIRONMENT = dict(os.environ)


def fixture_parent(environment):
    """The configured parent as given (a link in it is refused by placement), or the default:
    $XDG_STATE_HOME/vg (ignored unless absolute, as the XDG spec says) or the account home's
    .vg, resolved once here so a home reached through a link (/home -> /var/home) is
    judged by its real path. The ownership and placement checks still apply to the result."""
    configured = environment.get('VELDO_FIXTURE_PARENT')
    if configured:
        return Path(configured)
    state = environment.get('XDG_STATE_HOME', '')
    if not os.path.isabs(state):
        return Path(os.path.realpath(pwd.getpwuid(os.getuid()).pw_dir)) / '.vg'
    return Path(os.path.realpath(state)) / 'vg'


def socket_paths(paths):
    """Check filesystem AF_UNIX names in bytes, including room for the terminating NUL.

    Linux sun_path holds 108 bytes. Report the fixture and actual path before setup
    or bind, rather than turning every setup-dependent row into a product failure.
    """
    for name, path in paths.items():
        size = len(os.fsencode(path))
        if size >= 108:
            raise FixtureRefused('gate_fixture_root_socket_too_long: %s: %d bytes (maximum 107): %s'
                                 % (name, size, path))


def allocate(parent, prefix='g'):
    """An exclusive private mkdir; a collision retries without opening an existing child."""
    for _ in range(65536):
        child = Path(parent) / (prefix + os.urandom(2).hex())
        try:
            child.mkdir(mode=0o700)
        except FileExistsError:
            continue
        return child
    raise FixtureRefused('gate_fixture_root_unavailable: allocation names exhausted')


def watch_sockets(base):
    """Check every fixture bind, including dynamically named notification sockets.

    Python validates sun_path before emitting its socket.bind audit event, so
    wrap bind itself to give oversized names the fixture's diagnostic. This also
    covers imported services; child interpreters install the same wrapper.
    """
    import socket
    original = socket.socket.bind

    def bind(sock, address):
        if sock.family == socket.AF_UNIX:
            path = os.fsdecode(address)
            if path.startswith(str(base) + '/'):
                socket_paths({'bind': path})
        return original(sock, address)

    socket.socket.bind = bind
    return lambda: setattr(socket.socket, 'bind', original)


def private(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise FixtureRefused('gate_fixture_root_not_private: %s' % path)


def placement(path, environment):
    if not path.is_absolute() or '..' in path.parts or path.resolve() != path:
        raise FixtureRefused('gate_fixture_root_invalid_path: %s' % path)
    forbidden = ['/tmp', '/var/tmp', '/dev/shm', '/run', '/var/run', tempfile.gettempdir(),
                 environment.get('TMPDIR'), environment.get('XDG_RUNTIME_DIR')]
    for value in forbidden:
        if value:
            outside = Path(value).resolve()
            if path == outside or outside in path.parents:
                raise FixtureRefused('gate_fixture_root_unsafe_placement: %s' % path)


def parent_for(environment, configured=None):
    parent = Path(configured) if configured is not None else fixture_parent(environment)
    placement(parent, environment)
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    private(parent)
    inherited = environment.get('VELDO_FIXTURE_ROOT')
    if not inherited:
        return parent
    child = Path(inherited)
    placement(child, environment)
    if child == parent:
        return parent
    if parent not in child.parents:
        raise FixtureRefused('gate_fixture_root_outside_parent: %s' % child)
    # Only the allocator's fresh g/s directories and dispatcher's shard tags can
    # extend the pinned parent. Existing stores or keys are never candidate parents.
    relative = child.relative_to(parent)
    for index, part in enumerate(relative.parts):
        if not (re.fullmatch('[gs](?:[0-9a-f]{4}|[a-z0-9_]{8})', part) or
                (index > 0 and re.fullmatch('[0-9a-z]{2}|[0-9]{3,}', part))):
            raise FixtureRefused('gate_fixture_root_not_allocation: %s' % child)
        private(parent.joinpath(*relative.parts[:index + 1]))
    return child


def remove_tree(path):
    """Open shut directories without following links; remove only this allocation."""
    descriptor = os.open(path, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.chmod('/proc/self/fd/%d' % descriptor, 0o700)
        for _, directories, _, directory in os.fwalk(path, follow_symlinks=False):
            for name in directories:
                try:
                    inner = os.open(name, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                    dir_fd=directory)
                except OSError:
                    continue
                try:
                    os.chmod('/proc/self/fd/%d' % inner, 0o700)
                finally:
                    os.close(inner)
        shutil.rmtree(path)
    finally:
        os.close(descriptor)


@contextmanager
def directory(prefix='g', configured=None, protected=(), environment=None):
    source = ENVIRONMENT if environment is None else environment
    allocated = None
    try:
        parent = parent_for(source, configured)
        if any(parent == p or p in parent.parents for p in map(lambda p: Path(p).resolve(), protected)):
            raise FixtureRefused('gate_fixture_root_protected_overlap: %s' % parent)
        allocated = allocate(parent, prefix)
        private(allocated)
        if any(allocated == p or p in allocated.parents or allocated in p.parents
               for p in map(lambda p: Path(p).resolve(), protected)):
            raise FixtureRefused('gate_fixture_root_protected_overlap: %s' % allocated)
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as error:
        if allocated is not None:
            remove_tree(allocated)
        if isinstance(error, FixtureRefused):
            raise
        raise FixtureRefused('gate_fixture_root_unavailable: %s' % error) from None
    try:
        yield allocated
    finally:
        try:
            remove_tree(allocated)
        except OSError as error:
            # Never mask a shard result or an exception already in flight.
            import sys
            print('gate_fixture_cleanup_failed: %s: %s' % (allocated, error), file=sys.stderr, flush=True)
