"""The one confinement of a mutation worker and of a case-input proposal's traced worker.

The coordinator is trusted. Workers read the frozen tree and runtime, and write only their
private scratch directory; caller home is not exposed. The domain starts through
agent_sandbox.fork_gate_domain and agent_sandbox.landlock (worker profile), so a worker has
exactly the gate profile's network rule (VELDO-0208, owner decision Telegram 32421): this
module installs no network or socket rule of its own. Unsupported kernels fail closed; there is
no unsandboxed fallback.

A fresh worker (no declared runtime set) first enters a tree the agent launcher makes
(enter_tree, VELDO-0210 AC7) and confines itself inside it (confine_in_tree), so a gate one of its
cases starts nests like any other nested launch. A declared case, traced by the coordinator, never
enters a tree: confine, as before.
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
    grants = worker_grants(boundary, authority, root, scratch, runtime_paths, reads)
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


def worker_grants(boundary, authority, root, scratch, runtime_paths=None, reads=()):
    """A worker's Landlock grants: `root` and `reads` read only, `scratch` read and write, the
    runtime (a declared case's keyed set, else the default and the installed tools)."""
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
        boundary.toolchain_environment(config, scratch, grants, os.environ)
    grants += [(Path('/dev/null'), (1 << 1) | (1 << 2)), (Path('/dev/urandom'), 1 << 2)]
    return grants


def enter_tree(authority, root, scratch, mode, keep=()):
    """A fresh worker's start (VELDO-0210 AC7), in the authority bootstrap before anything else
    runs: this same command again, its mode argument `mode`, as the agent of a tree the agent
    launcher makes (agent_sandbox.worker_tree), which returns the tree's exit status. This process
    stays outside the tree, brokering the worker's Unix sockets beneath `scratch`."""
    boundary = load(Path(authority) / 'scripts/agent_sandbox.py')
    argv = [sys.executable, *sys.orig_argv[1:]]
    position = len(argv) - len(sys.argv)
    if argv[position + 1:] != sys.argv[1:]:
        raise RuntimeError('cannot repeat the worker command inside its tree')
    argv[position + 1] = mode
    return boundary.worker_tree(argv, dict(os.environ), root, scratch, inherit=keep)


class Installed:
    """The IPC filter the tree's agent already installed (agent_sandbox.confined_agent, worker
    profile), as landlock() asks a broker for it: 'broker' when the launcher outside the tree serves
    its listener, else 'strict'."""

    def __init__(self, mode):
        self.mode = mode

    def install(self, libc):
        return self.mode


def confine_in_tree(authority, root, scratch, keep=(), reads=(), boundary=None):
    """A fresh worker's confinement inside the tree enter_tree made (VELDO-0210 AC7): refuses unless
    this process is inside such a tree, then applies the worker's Landlock (the fresh grants, as
    confine gives them) beneath the IPC filter the tree's agent installed, keeping `keep` and the
    tree's marker, which every gate a case starts is handed. boundary is the authority's
    agent_sandbox the caller already loaded, else it is loaded here. Returns confined."""
    authority, root, scratch = Path(authority), Path(root), Path(scratch)
    boundary = boundary or load(authority / 'scripts/agent_sandbox.py')
    if boundary.nested_namespace() is None:
        raise RuntimeError('a fresh confined worker runs only inside a tree the agent launcher made')
    grants = worker_grants(boundary, authority, root, scratch, None, reads)
    problem = boundary.launcher_write_problem(grants)
    if problem:
        raise RuntimeError(problem)
    boundary.close_descriptors([], keep=(*keep, *boundary.launcher_fds()))
    mode = 'broker' if os.environ.get(boundary.BROKERED) == '1' else 'strict'
    boundary.landlock(grants, profile='worker', broker=Installed(mode))
