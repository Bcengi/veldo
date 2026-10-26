"""The PM cycles' graph stage inside a suite fixture's own run directory, for the whole suite process.

control_graph.resolve_runtime() puts the graph runtime's stage under the account's home, which
control_graph_lock.account_home() reads from the password database (pwd.getpwuid(os.getuid()).pw_dir, never
$HOME), so an exchange made without an explicit stage stages its runner under ~/.local/state/veldo/graph-stage.
That is every exchange of a line whose cycles the product builds itself (control_service Line.build_cycles), as
well as every installed_runtime() a suite calls. A fixture enters own(base): for its duration, that one read (the
account home resolve_runtime takes for the stage) answers base/graph-home, so every exchange in this process, on
any line, stages in the fixture's directory, whatever builds the cycles and whenever. Every other password
database read is the real one, the runtime's own directory (control_graph_lock.runtime_directory) among them.
The real reader is put back when the fixture ends.

The guard: while a fixture is active, a resolution of the real account stage is recorded with its call chain,
and the fixture's end raises Escaped naming each one, so the suite's rows go red rather than pass. With the seam
in place none can happen. VELDO_SUITE_GRAPH_STAGE_SEAM=off stands the seam aside (the falsifier): the real
resolution then runs unchanged and the guard reports it.

The guard shares the seam's one frame match (_stage_read), so a rename of account_home or resolve_runtime, or the
read inlined, would stand both aside together. pm_runners checks the outcome instead: the suites assert that the
fixture's own stage (the path own yields) received a PM exchange's staged runner.
"""
import contextlib
import os
from pathlib import Path
import pwd
import sys

SWITCH = 'VELDO_SUITE_GRAPH_STAGE_SEAM'
STAGE_RELATIVE = Path('.local/state/veldo/graph-stage')


class Escaped(AssertionError):
    """The real account stage was resolved while a fixture was active."""
    graph_stage_escaped = True


def _named(frame, filename, function):
    return frame is not None and frame.f_code.co_name == function and Path(frame.f_code.co_filename).name == filename


def _stage_read(frame):
    """Whether `frame` is account_home() called by resolve_runtime() for the stage (not by runtime_directory)."""
    return _named(frame, 'control_graph_lock.py', 'account_home') \
        and _named(frame.f_back, 'control_graph.py', 'resolve_runtime')


def _chain(frame, depth=10):
    """The call chain from resolve_runtime outward, as file:function:line."""
    found = []
    while frame is not None and len(found) < depth:
        found.append('%s:%s:%d' % (Path(frame.f_code.co_filename).name, frame.f_code.co_name, frame.f_lineno))
        frame = frame.f_back
    return ' < '.join(found)


def pm_runners(stage, mods):
    """How many runners staged under `stage` are a PM exchange's. control_graph.stage copies each runner it launches,
    content-addressed, to <stage>/runners/<sha256>.py and never removes it (only the exchange's working directory
    under <stage>/work goes), so every one lasts as long as the stage; a PM exchange's runner is
    control_graph_langgraph.py with mods/control_graph_pm.py inside it (control_workflow_cycle_pm exchange). This
    is the seam's outcome, judged apart from its frame match: an exchange that resolved the real account stage left
    nothing here."""
    runners = Path(stage) / 'runners'
    extension = (Path(mods) / 'control_graph_pm.py').read_text()
    return sum(1 for path in sorted(runners.glob('*.py')) if extension in path.read_text()) if runners.is_dir() else 0


@contextlib.contextmanager
def own(base):
    """For the with block: the account stage this process resolves is base/graph-home/<stage>; yields that path."""
    home = Path(base) / 'graph-home'
    seam = os.environ.get(SWITCH, 'on') != 'off'
    escaped = []
    real = pwd.getpwuid

    def getpwuid(uid):
        entry = real(uid)
        caller = sys._getframe(1)
        if not _stage_read(caller):
            return entry
        if seam:
            return pwd.struct_passwd(tuple(entry[:5]) + (str(home),) + tuple(entry[6:]))
        escaped.append(_chain(caller.f_back))
        return entry

    pwd.getpwuid = getpwuid
    ended = False
    try:
        yield home / STAGE_RELATIVE
        ended = True
    finally:
        pwd.getpwuid = real
        if escaped:
            report = 'GRAPH STAGE ESCAPED: %d resolution(s) of the account stage %s while the fixture at %s was ' \
                     'active' % (len(escaped), Path(real(os.getuid()).pw_dir) / STAGE_RELATIVE, base)
            print('  ' + report)
            for site in sorted(set(escaped)):
                print('    %dx %s' % (escaped.count(site), site))
            if ended:
                raise Escaped(report + ': ' + '; '.join(sorted(set(escaped)))[:2000])
