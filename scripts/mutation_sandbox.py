"""The one confinement of a mutation worker and of a case-input proposal's traced worker.

The coordinator is trusted. Workers read the frozen tree and runtime, and write only their
private scratch directory; caller home is not exposed. The domain starts through
agent_sandbox.fork_gate_domain and agent_sandbox.landlock (worker profile), so a worker has
exactly the gate profile's network rule (VELDO-0208, owner decision Telegram 32421): this
module installs no network or socket rule of its own. Unsupported kernels fail closed; there is
no unsandboxed fallback.
"""
import importlib.util
import os
from pathlib import Path
import signal
import sys

RUNTIME = ('/usr', '/lib', '/lib64', '/etc')


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def confine(authority, root, scratch, runtime_paths=None, keep=(), reads=()):
    """Confine this process and every descendant before any candidate code runs.

    authority is the trusted checkout whose agent_sandbox.py and agent_sandbox.json are loaded;
    root is the tree the worker reads (the frozen snapshot or the repository), and reads any further
    read-only roots the caller owns (a linked worktree's Git common directory). runtime_paths is a
    declared case's keyed runtime set; without it (a fresh worker) the default runtime and the
    installed tools the gate profile grants the same suites are readable. As in the gate launcher,
    every descriptor above the standard three is closed in the domain except `keep` (the caller's
    own authority channels), so no inherited socket enters it. The calling process forks: the
    parent stays outside the domain as the child's broker (never running candidate code) and
    exits with the child's status; only the child returns, confined.
    """
    authority, root, scratch = Path(authority), Path(root), Path(scratch)
    boundary = load(authority / 'scripts/agent_sandbox.py')
    grants = [(root, boundary.READ), (scratch, boundary.READ | boundary.WRITE)]
    grants += [(Path(p), boundary.READ) for p in reads]
    grants += [(Path(p).resolve(), boundary.READ)
               for p in (RUNTIME if runtime_paths is None else runtime_paths) if Path(p).exists()]
    if runtime_paths is None:
        # A fresh worker reads the installed tools the gate profile grants the same suites (the
        # Codex and Claude Code binaries, the langgraph runtime), read only. A declared case runs
        # only its keyed runtime set, so it gets none of them.
        config = boundary.policy_module().configuration(authority / 'scripts/agent_sandbox.json')[1]
        grants += [(p, boundary.READ) for p in boundary.installed_tools(config)]
    grants += [(Path('/dev/null'), (1 << 1) | (1 << 2)), (Path('/dev/urandom'), 1 << 2)]
    # Suites serve and dial Unix sockets in their scratch and drive terminals; the parent brokers
    # them. The network rule is the gate profile's own (VELDO-0208, owner decision Telegram 32421).
    sys.stdout.flush()
    sys.stderr.flush()
    pid, side = boundary.fork_gate_domain([scratch])
    if pid:
        try:
            _, status = os.waitpid(pid, 0)
        finally:
            if side is not None:
                side.close()
        if os.WIFSIGNALED(status):
            signal.signal(os.WTERMSIG(status), signal.SIG_DFL)
            os.kill(os.getpid(), os.WTERMSIG(status))
        os._exit(os.waitstatus_to_exitcode(status))
    boundary.close_descriptors([], keep=(*side.keep(), *keep))
    if boundary.landlock(grants, profile='worker', broker=side) != 'strict':
        os.environ[boundary.BROKERED] = '1'
