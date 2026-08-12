#!/usr/bin/env python3
"""VELDO task source: claimable units for work that is NOT construction.

WHAT THIS IS NOT, first, because that is the design. It is NOT a second fleet. The elastic
control loop, the token governor, the in-session worker spawner and the resume waiter already
exist in .veldo/fleet.py and .veldo/governor.py and are already governed. The whole contract
that loop asks of a controller is four methods - desired, work_remains, resume_at, now - so a
new kind of work needs a WORK SOURCE and nothing else. A work source that grew its own loop
would be an ungoverned second pool beside the governed one, which is the one shape that must
never exist here (PLAN-0018 NG2).

So this module holds exactly one of those four methods. `work_remains` is its own, because
only it knows what a task is. `desired`, `resume_at` and `now` are INJECTED, the same way
fleet.py injects its spawner and its waiter, which is why nothing in this file references a
governor, a spawner or a sleep.

WHAT A TASK IS. An authored record in .veldo/tasks/*.yaml: an id, a kind from a CLOSED set,
what it is about, and THE ARTIFACT IT PRODUCES. `build` is deliberately not a kind - the
frontier is already construction's work source and a second one would be two enumerations of
one set.

DONE IS THE PRODUCT EXISTING, NEVER A STATUS A WORKER WROTE. A review concludes when its
review is on disk. A task whose status says done and whose product is absent is still OPEN,
for the same reason VELDO-0002 refuses a run's own word: a worker that announced success and
left nothing behind is the failure this method keeps finding. It also makes the queue correct
after a dead session for free - a worker that died mid-review leaves a stale claim the ledger
already ages out, and the task simply becomes claimable again. Nothing has to remember.

TWO WORKERS NEVER GET ONE TASK, and not because of anything written here: claimability is
answered by consulting .veldo/claim.py, whose per-unit lock already arbitrates a whole claim
decision. A second mechanism would be a second answer.

IT ENFORCES NOTHING. No gate stage consults this, no build is refused because a task is open,
and an absent .veldo/tasks/ directory stands the read model down by name rather than reporting
zero open tasks as though it had looked.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.tasks/v1"

# CLOSED key sets. A key nobody recognises is refused rather than ignored, so a field invented
# to smuggle a meaning past the contract is a refusal and not a silent no-op.
TASK_SET_KEYS = {"schema", "id", "version", "tasks"}
TASK_KEYS = {"id", "kind", "target", "produces", "status", "requires", "note"}
TASK_SET_REQUIRED = ("schema", "id", "tasks")
TASK_REQUIRED = ("id", "kind", "target", "produces")

# `build` IS NOT HERE ON PURPOSE. Construction's work source is the frontier; adding it here
# would be a second enumeration of one set, which is this repository's most repeated defect.
KINDS = ("review", "audit", "authoring", "investigation", "migration")

# A status is ADVISORY. It records what an author or a worker believes; the product on disk is
# what decides. Kept in the contract so a wrong value is refused rather than silently believed.
STATUSES = ("open", "done")

TASK_ID_PREFIX = "TASK-"

CAUSE_UNREADABLE = "TASK_UNREADABLE"
CAUSE_MISSING_FIELD = "TASK_MISSING_FIELD"
CAUSE_KEY_UNRECOGNIZED = "TASK_KEY_UNRECOGNIZED"
CAUSE_KIND_UNKNOWN = "TASK_KIND_UNKNOWN"
CAUSE_DECLARED_TWICE = "TASK_DECLARED_TWICE"
CAUSE_PRODUCES_UNBOUND = "TASK_PRODUCES_UNBOUND"
CAUSE_BAD_STATUS = "TASK_BAD_STATUS"
CAUSES = (CAUSE_UNREADABLE, CAUSE_MISSING_FIELD, CAUSE_KEY_UNRECOGNIZED, CAUSE_KIND_UNKNOWN,
          CAUSE_DECLARED_TWICE, CAUSE_PRODUCES_UNBOUND, CAUSE_BAD_STATUS)

# The claim answers. The first three are the LEDGER'S OWN vocabulary, reused rather than
# respelled; only CONCLUDED is this module's, because only it knows what finishing looks like.
GRANTED = "granted"
REFUSED_CAPABILITY = "capability"
REFUSED_CLAIMED = "claimed"
REFUSED_CONCLUDED = "concluded"
REFUSED_UNKNOWN = "no_such_task"

STAND_DOWN_NO_DIRECTORY = ("no .veldo/tasks/ directory: this repository declares no "
                           "non-construction work, which is NOT the same fact as having none "
                           "left to do")
STAND_DOWN_NO_TASKS = ("a .veldo/tasks/ directory that declares no task at all, so there is "
                       "nothing to divide rather than nothing left")

REPORT_KEYS = ("stood_down", "reason", "sets", "tasks", "open", "claimed", "concluded",
               "unclaimable")


class TaskRecordError(ValueError):
    """A task set could not be read as a task set. Raised by the loader, reported by the
    caller's reporter, never swallowed into a count."""


def _organ(name):
    spec = importlib.util.spec_from_file_location(
        "veldo_tasks_" + name, ROOT / ".veldo" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def default_tasks_dir(root=None):
    return (Path(root) if root is not None else ROOT) / ".veldo" / "tasks"


def load_task_set(path, parse):
    """Parse one task set with the CALLER'S front-matter parser, so this module ships no second
    YAML parser. Raises TaskRecordError with the path named on anything unreadable."""
    p = Path(path)
    try:
        text = p.read_text()
    except OSError as e:
        raise TaskRecordError("%s: %s: %s" % (p, CAUSE_UNREADABLE, e))
    try:
        data = parse(text)
    except Exception as e:                        # noqa: BLE001 - any parser failure is the same fact
        raise TaskRecordError("%s: %s: task set outside the record subset: %s"
                              % (p, CAUSE_UNREADABLE, e))
    if not isinstance(data, dict):
        raise TaskRecordError("%s: %s: a task set is a mapping, got %s"
                              % (p, CAUSE_UNREADABLE, type(data).__name__))
    return data


def produces_problems(produces):
    """Why a `produces` value cannot bind, or None. IT MUST NAME A PATH INSIDE THE REPOSITORY:
    a task set is an AUTHORED file, so an absolute path or one escaping the tree would let a
    task be concluded by pointing at something outside it."""
    if not isinstance(produces, str) or not produces.strip():
        return "produces is empty, so nothing could ever conclude this task"
    if produces.startswith("/") or (len(produces) > 1 and produces[1] == ":"):
        return ("produces '%s' is absolute, so it could be concluded by a file outside this "
                "repository" % produces)
    parts = [seg for seg in produces.replace("\\", "/").split("/") if seg]
    if ".." in parts:
        return ("produces '%s' escapes the repository with '..', so it could be concluded from "
                "outside the tree" % produces)
    return None


def task_problems(task, where):
    """Every structural problem with ONE task, as (cause, message) pairs. All of them, not the
    first, because an author fixing one at a time is the thing a named taxonomy prevents."""
    out = []
    if not isinstance(task, dict):
        return [(CAUSE_UNREADABLE, "%s: a task is a mapping, got %s"
                 % (where, type(task).__name__))]
    tid = task.get("id") if isinstance(task.get("id"), str) else ""
    label = tid or where
    for field in TASK_REQUIRED:
        if not task.get(field):
            out.append((CAUSE_MISSING_FIELD,
                        "%s: task %s declares no %s" % (where, label, field)))
    for key in sorted(set(task) - TASK_KEYS):
        out.append((CAUSE_KEY_UNRECOGNIZED,
                    "%s: task %s declares unrecognised key '%s' (allowed: %s)"
                    % (where, label, key, ", ".join(sorted(TASK_KEYS)))))
    kind = task.get("kind")
    if kind is not None and kind not in KINDS:
        out.append((CAUSE_KIND_UNKNOWN,
                    "%s: task %s declares kind '%s' (allowed: %s). `build` is deliberately not "
                    "a kind: construction already has a work source"
                    % (where, label, kind, ", ".join(KINDS))))
    status = task.get("status")
    if status is not None and status not in STATUSES:
        out.append((CAUSE_BAD_STATUS, "%s: task %s declares status '%s' (allowed: %s)"
                    % (where, label, status, ", ".join(STATUSES))))
    if task.get("produces") is not None:
        why = produces_problems(task.get("produces"))
        if why:
            out.append((CAUSE_PRODUCES_UNBOUND, "%s: task %s: %s" % (where, label, why)))
    return out


def set_problems(data, where):
    """Every structural problem with one task SET, its own keys included."""
    out = []
    for field in TASK_SET_REQUIRED:
        if not data.get(field):
            out.append((CAUSE_MISSING_FIELD, "%s: task set declares no %s" % (where, field)))
    for key in sorted(set(data) - TASK_SET_KEYS):
        out.append((CAUSE_KEY_UNRECOGNIZED,
                    "%s: task set declares unrecognised key '%s' (allowed: %s)"
                    % (where, key, ", ".join(sorted(TASK_SET_KEYS)))))
    if data.get("schema") not in (None, SCHEMA):
        out.append((CAUSE_UNREADABLE, "%s: task set declares schema '%s', expected %s"
                    % (where, data.get("schema"), SCHEMA)))
    tasks = data.get("tasks")
    if tasks is not None and not isinstance(tasks, list):
        out.append((CAUSE_UNREADABLE, "%s: tasks is %s rather than a list of tasks"
                    % (where, type(tasks).__name__)))
        return out
    for n, task in enumerate(tasks or []):
        out.extend(task_problems(task, where))
    return out


def read_sets(tdir=None, root=None, parse=None):
    """[(path, data_or_None, error_or_None)] for every task set on disk, sorted. A set that
    cannot be read is CARRIED as an error rather than dropped, because a dropped file is a
    coverage figure quoted without the weakness that produced it."""
    d = Path(tdir) if tdir is not None else default_tasks_dir(root)
    out = []
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.yaml")):
        try:
            out.append((p, load_task_set(p, parse), None))
        except TaskRecordError as e:
            out.append((p, None, str(e)))
    return out


def check_tasks_dir(tdir, root, parse, fail):
    """Validate every task set structurally. Adoption safe: an absent directory returns clean.
    A task id declared by two files is refused with BOTH files named, because 'one of them
    vanished' is not something an author can act on."""
    d = Path(tdir)
    if not d.is_dir():
        return 0
    errs = 0
    seen = {}
    for path, data, err in read_sets(d, root, parse):
        if err is not None:
            errs += fail(path, err)
            continue
        for cause, msg in set_problems(data, str(path)):
            errs += fail(path, "%s: %s" % (cause, msg))
        for task in (data.get("tasks") or []):
            if isinstance(task, dict) and isinstance(task.get("id"), str) and task.get("id"):
                seen.setdefault(task["id"], []).append(str(path))
    for tid, paths in sorted(seen.items()):
        if len(paths) > 1:
            errs += fail(paths[0], "%s: task %s is declared by %d files: %s"
                         % (CAUSE_DECLARED_TWICE, tid, len(paths), ", ".join(sorted(paths))))
    return errs


def all_tasks(tdir=None, root=None, parse=None):
    """[(task, path)] for every WELL-FORMED task, in declaration order. Malformed tasks are
    excluded here and reported by check_tasks_dir, so a reader never acts on a half-read task."""
    out = []
    for path, data, err in read_sets(tdir, root, parse):
        if err is not None or not isinstance(data, dict):
            continue
        for task in (data.get("tasks") or []):
            if not task_problems(task, str(path)):
                out.append((task, path))
    return out


def concluded(task, root=None):
    """THE ONE DEFINITION OF DONE: the artifact the task declares it produces exists. A status
    field is not consulted, deliberately."""
    base = Path(root) if root is not None else ROOT
    produces = task.get("produces")
    if produces_problems(produces):
        return False
    return (base / produces).exists()


def claim_answer(task, worker_caps=None, root=None, claims_root=None):
    """Why this worker may or may not take this task, in ONE vocabulary. The first three
    answers are the LEDGER'S, asked of the ledger; only CONCLUDED is this module's."""
    if concluded(task, root):
        return REFUSED_CONCLUDED
    cl = _organ("claim")
    reqs = task.get("requires") or []
    if not cl.capability_ok(worker_caps, reqs):
        return REFUSED_CAPABILITY
    if cl.is_claimed(task["id"], root=claims_root):
        return REFUSED_CLAIMED
    return GRANTED


def claimable(worker_caps=None, tdir=None, root=None, parse=None, claims_root=None):
    """The tasks this worker may take right now, each with the answer that admitted it."""
    return [t for t, _p in all_tasks(tdir, root, parse)
            if claim_answer(t, worker_caps, root, claims_root) == GRANTED]


def claim_task(task_id, worker_id, worker_caps=None, tdir=None, root=None, parse=None,
               claims_root=None):
    """Take one task THROUGH THE EXISTING LEDGER. Returns (ok, reason) in the ledger's own
    shape, so a caller reads one vocabulary whatever refused it."""
    found = [t for t, _p in all_tasks(tdir, root, parse) if t.get("id") == task_id]
    if not found:
        return False, REFUSED_UNKNOWN
    task = found[0]
    if concluded(task, root):
        return False, REFUSED_CONCLUDED
    cl = _organ("claim")
    return cl.claim(task_id, worker_id, worker_caps=worker_caps,
                    requirements=task.get("requires") or [], root=claims_root)


def task_report(tdir=None, root=None, parse=None, claims_root=None, worker_caps=None):
    """ONE key shape whether it stood down or not, so a consumer never guesses whether a key is
    missing or genuinely empty. Each unclaimable task carries WHY, because 'no work left' and
    'work left that nobody here can do' send an operator in opposite directions."""
    d = Path(tdir) if tdir is not None else default_tasks_dir(root)
    rep = {"stood_down": True, "reason": None, "sets": 0, "tasks": 0, "open": [], "claimed": [],
           "concluded": [], "unclaimable": []}
    if not d.is_dir():
        rep["reason"] = STAND_DOWN_NO_DIRECTORY
        return rep
    sets = read_sets(d, root, parse)
    rep["sets"] = len(sets)
    tasks = all_tasks(d, root, parse)
    rep["tasks"] = len(tasks)
    if not tasks:
        rep["reason"] = STAND_DOWN_NO_TASKS
        return rep
    rep["stood_down"] = False
    for task, path in tasks:
        answer = claim_answer(task, worker_caps, root, claims_root)
        row = {"id": task.get("id"), "kind": task.get("kind"), "target": task.get("target"),
               "produces": task.get("produces"), "declared_in": str(path), "answer": answer}
        if answer == GRANTED:
            rep["open"].append(row)
        elif answer == REFUSED_CONCLUDED:
            rep["concluded"].append(row)
        elif answer == REFUSED_CLAIMED:
            rep["claimed"].append(row)
        else:
            rep["unclaimable"].append(row)
    return rep


def report_lines(rep):
    """The report as lines a stranger reads. Every problem line names a path."""
    if rep["stood_down"]:
        return ["task source: stood down - %s" % rep["reason"]]
    lines = ["task source: %d task(s) in %d set(s): %d open, %d claimed, %d concluded, "
             "%d unclaimable here"
             % (rep["tasks"], rep["sets"], len(rep["open"]), len(rep["claimed"]),
                len(rep["concluded"]), len(rep["unclaimable"]))]
    for row in rep["open"]:
        lines.append("  OPEN %s (%s) %s -> produces %s"
                     % (row["id"], row["kind"], row["target"], row["produces"]))
    for row in rep["unclaimable"]:
        lines.append("  UNCLAIMABLE HERE %s: %s, declared in %s"
                     % (row["id"], row["answer"], row["declared_in"]))
    return lines


class TaskController:
    """The EXISTING FleetController contract, satisfied for tasks.

    THIS CLASS OWNS EXACTLY ONE OF THE FOUR METHODS. `work_remains` is its own, because only a
    task source knows what a task is. `desired`, `resume_at` and `now` are INJECTED callables,
    which is why this module references no governor, no spawner and no sleep - the caller wires
    the governor in, exactly as fleet.py's caller wires the spawner and the waiter. A work
    source that reached for the governor itself would be the first step toward a second
    ungoverned pool."""

    def __init__(self, desired, resume_at, now, worker_caps=None, tdir=None, root=None,
                 parse=None, claims_root=None):
        self._desired = desired
        self._resume_at = resume_at
        self._now = now
        self._caps = worker_caps
        self._tdir = tdir
        self._root = root
        self._parse = parse
        self._claims_root = claims_root

    def desired(self):
        return self._desired()

    def resume_at(self):
        return self._resume_at()

    def now(self):
        return self._now()

    def work_remains(self):
        return bool(claimable(self._caps, self._tdir, self._root, self._parse,
                              self._claims_root))
