"""VELDO-0003: a work source for work that is not construction.

This fragment is executed by scripts/selftest.py into shared.py's namespace, in manifest order,
like every other fragment. Every name it uses beyond its own is bound by shared.py, which always
runs, so its declared prerequisite closure is ITSELF ALONE:

  python3 scripts/selftest.py --suite 20_veldo_0003_task_source

WHAT IS UNDER TEST. .veldo/tasks.py, driven directly, handed validate.py's ONE front-matter parser
and ONE failure reporter exactly as validate.py hands them to every other organ. THE CLAIM LEDGER
AND THE FLEET LOOP ARE THE REAL ONES: this item's whole claim is that it adds no second mechanism,
so a stub ledger would prove only that the stub agrees with itself, and a stub loop would prove
nothing about whether fleet.py needed changing. Both are loaded from disk and driven.

EVERY CRITERION'S BLOCK IS WRAPPED. A raise at fragment scope takes every row below it with it,
which is how a mutation that DELETES coverage passes as a shorter run instead of a red one.
_ts_block reds a NAMED row instead.

BOTH DIRECTIONS, EVERYWHERE. Every refusal is paired with an accepting fixture differing in exactly
one field, because a refusal asserted alone is indistinguishable from a validator that refuses
everything.
"""
TS = V._VC._organ("tasks", ROOT / ".veldo" / "tasks.py")
TSCL = V._VC._organ("claim", ROOT / ".veldo" / "claim.py")
TSFL = V._VC._organ("fleet", ROOT / ".veldo" / "fleet.py")


def _ts_block(label, fn):
    """Red a NAMED row when a criterion's block raises, instead of losing every row below it."""
    try:
        fn()
    except Exception as _ts_e:                   # noqa: BLE001 - a raise must RED a row, never skip
        expect("VELDO-0003 %s: the block ran to completion rather than raising (%r)"
               % (label, _ts_e), False)


def _ts_re_organs(src):
    """Which sibling organs this module loads, read from its own AST rather than by substring: a
    docstring naming the organ it deliberately does NOT touch is prose, and an absence claim built
    on substrings is a false positive waiting to happen."""
    import ast as _ts_a
    out = []
    for node in _ts_a.walk(_ts_a.parse(src)):
        if (isinstance(node, _ts_a.Call) and isinstance(node.func, _ts_a.Name)
                and node.func.id == "_organ" and node.args
                and isinstance(node.args[0], _ts_a.Constant)):
            out.append(node.args[0].value)
    return out


def _ts_task(tid="TASK-0001", kind="review", target="specs/EXAMPLE.md",
             produces="build/review-EXAMPLE.md", drop=(), **extra):
    """One task whose ONLY defect can be the thing a row is about, because a fixture missing two
    things cannot tell which one a refusal came from."""
    t = {"id": tid, "kind": kind, "target": target, "produces": produces}
    for k in drop:
        t.pop(k, None)
    t.update(extra)
    return t


def _ts_emit(tasks, sid="TASKSET-1", schema=TS.SCHEMA, drop=(), **extra):
    """Render a task set in the yamlish subset the ONE parser reads."""
    head = {"schema": schema, "id": sid, "version": 1}
    for k in drop:
        head.pop(k, None)
    head.update(extra)
    lines = ["%s: %s" % (k, head[k]) for k in head]
    lines.append("tasks:")
    for t in tasks:
        first = True
        for k in t:
            lead = "  - " if first else "    "
            first = False
            v = t[k]
            if isinstance(v, list):
                lines.append("%s%s:" % (lead, k))
                for item in v:
                    lines.append("      - %s" % item)
            else:
                lines.append("%s%s: %s" % (lead, k, v))
    return "\n".join(lines) + "\n"


def _ts_tree(d, sets=(), produced=()):
    """Write task sets and any already-produced artifacts. Returns (base, tasks_dir, claims_dir)."""
    base = Path(d)
    td = base / ".veldo" / "tasks"
    td.mkdir(parents=True, exist_ok=True)
    for name, text in sets:
        (td / name).write_text(text)
    for rel in produced:
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("produced")
    return base, td, str(base / "claims")


def _ts_check(sets, produced=()):
    """(errs, printed) from the structural check over a fresh tree."""
    import contextlib as _ts_ctx
    import io as _ts_io
    with tempfile.TemporaryDirectory() as d:
        base, td, _ = _ts_tree(d, sets, produced)
        buf = _ts_io.StringIO()
        with _ts_ctx.redirect_stdout(buf):
            n = TS.check_tasks_dir(td, base, V.parse_yamlish, V.fail)
        return n, buf.getvalue()


# ---------------------------------------------------------------------------------------
# AC1. A TASK SET IS A CLOSED CONTRACT.
#
# FALSIFIED BY: widen KINDS to accept any string, and the kind row must go red.
# ---------------------------------------------------------------------------------------


def _ts_ac1():
    good_n, _ = _ts_check([("a.yaml", _ts_emit([_ts_task()]))])
    expect("VELDO-0003 AC1 NEGATIVE CONTROL FIRST: a well-formed task set is ACCEPTED with zero "
           "errors, so every refusal below is discriminating rather than a validator that refuses "
           "every task set it is shown",
           good_n == 0)

    n, out = _ts_check([("a.yaml", _ts_emit([_ts_task(kind="build")]))])
    expect("VELDO-0003 AC1: a task declaring kind BUILD is refused with TASK_KIND_UNKNOWN and the "
           "allowed kinds named. `build` is the one kind that must never be accepted here: "
           "construction already has a work source in the frontier, and a second one would be two "
           "enumerations of a single set, which is this repository's most repeated defect",
           n > 0 and TS.CAUSE_KIND_UNKNOWN in out and "review" in out and "audit" in out)

    for field in TS.TASK_REQUIRED:
        n_f, out_f = _ts_check([("a.yaml", _ts_emit([_ts_task(drop=(field,))]))])
        expect("VELDO-0003 AC1: a task declaring no %s is refused with TASK_MISSING_FIELD naming "
               "the field, so an author reads which one is missing rather than that the set is "
               "invalid" % field,
               n_f > 0 and TS.CAUSE_MISSING_FIELD in out_f and field in out_f)

    n_k, out_k = _ts_check([("a.yaml", _ts_emit([_ts_task(waived="because I said so")]))])
    expect("VELDO-0003 AC1: an UNRECOGNISED key on a task is refused, not ignored, with the allowed "
           "keys named. A key invented to smuggle a meaning past the contract - `waived` here - "
           "must be a refusal, because a closed set whose extra keys are ignored is not closed",
           n_k > 0 and TS.CAUSE_KEY_UNRECOGNIZED in out_k and "waived" in out_k)

    n_s, out_s = _ts_check([("a.yaml", _ts_emit([_ts_task(sid="TASKSET-1")], drop=("id",)))])
    expect("VELDO-0003 AC1: a task SET missing its own id is refused too, so the set's keys are as "
           "closed as its tasks' keys",
           n_s > 0 and TS.CAUSE_MISSING_FIELD in out_s)

    n_d, out_d = _ts_check([("a.yaml", _ts_emit([_ts_task()])),
                            ("b.yaml", _ts_emit([_ts_task()], sid="TASKSET-2"))])
    expect("VELDO-0003 AC1: one task id declared by TWO files is refused with BOTH files named, "
           "because 'one of them vanished' is not something an author can act on",
           n_d > 0 and TS.CAUSE_DECLARED_TWICE in out_d
           and "a.yaml" in out_d and "b.yaml" in out_d)
    expect("VELDO-0003 AC1: `build` is absent from KINDS and every declared cause is registered in "
           "CAUSES under a unique name, so no two refusals share a spelling",
           "build" not in TS.KINDS and len(set(TS.CAUSES)) == len(TS.CAUSES)
           and TS.CAUSE_KIND_UNKNOWN in TS.CAUSES)


_ts_block("AC1", _ts_ac1)


# ---------------------------------------------------------------------------------------
# AC2. DONE IS THE PRODUCT EXISTING, NEVER A STATUS A WORKER WROTE.
#
# FALSIFIED BY: read done from the task's own status field, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _ts_ac2():
    with tempfile.TemporaryDirectory() as d:
        base, td, claims = _ts_tree(d, [("a.yaml", _ts_emit([_ts_task(status="done")]))])
        rep = TS.task_report(tdir=td, root=base, parse=V.parse_yamlish, claims_root=claims)
        expect("VELDO-0003 AC2: a task whose STATUS SAYS DONE while the artifact it produces is "
               "absent is still OPEN. A worker that announced success and left nothing behind is "
               "the failure this method keeps finding, and it is the same rule VELDO-0002 applies "
               "to a run's own word",
               [r["id"] for r in rep["open"]] == ["TASK-0001"] and rep["concluded"] == []
               and TS.concluded(_ts_task(status="done"), root=base) is False)

    with tempfile.TemporaryDirectory() as d:
        base, td, claims = _ts_tree(d, [("a.yaml", _ts_emit([_ts_task(status="open")]))],
                                    produced=["build/review-EXAMPLE.md"])
        rep = TS.task_report(tdir=td, root=base, parse=V.parse_yamlish, claims_root=claims)
        expect("VELDO-0003 AC2 NEGATIVE CONTROL: the same task with its STATUS STILL OPEN reads "
               "CONCLUDED once its product is on disk, so the product decides in both directions "
               "and the status field is consulted in neither. The two fixtures differ in exactly "
               "one file",
               [r["id"] for r in rep["concluded"]] == ["TASK-0001"] and rep["open"] == [])

    for bad, why in ((("/etc/passwd"), "absolute"), ("../outside/thing.md", "escaping with .."),
                     ("", "empty")):
        n, out = _ts_check([("a.yaml", _ts_emit([_ts_task(produces=bad)]))])
        expect("VELDO-0003 AC2: a produces that is %s is refused with TASK_PRODUCES_UNBOUND, so no "
               "task can be concluded by pointing at something outside the repository. A task set "
               "is an AUTHORED file, so this is reachable by anyone who can write one" % why,
               n > 0 and (TS.CAUSE_PRODUCES_UNBOUND in out or TS.CAUSE_MISSING_FIELD in out))
    expect("VELDO-0003 AC2: produces_problems ACCEPTS an ordinary in-tree path, so the three "
           "refusals above are discriminating rather than a function that rejects every path",
           TS.produces_problems("build/review-EXAMPLE.md") is None)


_ts_block("AC2", _ts_ac2)


# ---------------------------------------------------------------------------------------
# AC3. TWO WORKERS NEVER GET ONE TASK, THROUGH THE LEDGER THAT ALREADY GUARANTEES IT.
#
# FALSIFIED BY: make claimable() skip the ledger consultation, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _ts_ac3():
    with tempfile.TemporaryDirectory() as d:
        base, td, claims = _ts_tree(d, [("a.yaml", _ts_emit(
            [_ts_task(), _ts_task(tid="TASK-0002", produces="build/review-TWO.md")]))])
        ok1, why1 = TS.claim_task("TASK-0001", "worker-a", tdir=td, root=base,
                                  parse=V.parse_yamlish, claims_root=claims)
        ok2, why2 = TS.claim_task("TASK-0001", "worker-b", tdir=td, root=base,
                                  parse=V.parse_yamlish, claims_root=claims)
        expect("VELDO-0003 AC3: the FIRST worker is granted a task and the SECOND is refused with "
               "the ledger's own reason `claimed`. DRIVEN THROUGH THE REAL .veldo/claim.py, whose "
               "per-unit lock is the property being relied on: a stub would prove only that the "
               "stub agrees with itself",
               (ok1, why1) == (True, "granted") and ok2 is False and why2 == "claimed")

        ok3, why3 = TS.claim_task("TASK-0002", "worker-b", tdir=td, root=base,
                                  parse=V.parse_yamlish, claims_root=claims)
        expect("VELDO-0003 AC3 NEGATIVE CONTROL: worker-b IS granted a DIFFERENT task, so the "
               "refusal above is arbitration over one unit rather than a ledger that refuses "
               "every second claim",
               (ok3, why3) == (True, "granted"))

        left = [t["id"] for t in TS.claimable(tdir=td, root=base, parse=V.parse_yamlish,
                                              claims_root=claims)]
        expect("VELDO-0003 AC3: with both tasks held live, claimable() returns NEITHER - the read "
               "model consults the same ledger the claim went through, so a pool never hands one "
               "task to two workers",
               left == [])

        TSCL.release("TASK-0001", "worker-a", root=claims)
        after = [t["id"] for t in TS.claimable(tdir=td, root=base, parse=V.parse_yamlish,
                                               claims_root=claims)]
        expect("VELDO-0003 AC3: RELEASING a claim makes the task claimable again, through the "
               "ledger's own release rather than any bookkeeping here. This is also what makes a "
               "dead worker harmless: the ledger already ages a stale claim out and the task "
               "returns to the queue with nothing having to remember it",
               after == ["TASK-0001"])

    with tempfile.TemporaryDirectory() as d:
        base, td, claims = _ts_tree(d, [("a.yaml", _ts_emit(
            [_ts_task(requires=["kotlin"])]))])
        okc, whyc = TS.claim_task("TASK-0001", "worker-a", worker_caps=["python"], tdir=td,
                                 root=base, parse=V.parse_yamlish, claims_root=claims)
        okd, whyd = TS.claim_task("TASK-0001", "worker-a", worker_caps=["python", "kotlin"],
                                  tdir=td, root=base, parse=V.parse_yamlish, claims_root=claims)
        expect("VELDO-0003 AC3: a task whose requirements exceed the worker's capabilities is "
               "refused `capability`, and the SAME task is granted to a worker that has them - so "
               "the queue reports work left that nobody HERE can do, which sends an operator "
               "somewhere different from an empty queue",
               okc is False and whyc == "capability" and (okd, whyd) == (True, "granted"))

    with tempfile.TemporaryDirectory() as d:
        base, td, claims = _ts_tree(d, [("a.yaml", _ts_emit([_ts_task()]))],
                                    produced=["build/review-EXAMPLE.md"])
        oke, whye = TS.claim_task("TASK-0001", "worker-a", tdir=td, root=base,
                                 parse=V.parse_yamlish, claims_root=claims)
        expect("VELDO-0003 AC3: a task whose PRODUCT already exists is refused `concluded` before "
               "the ledger is even asked, so a pool cannot spend a worker redoing finished work",
               oke is False and whye == TS.REFUSED_CONCLUDED)


_ts_block("AC3", _ts_ac3)


# ---------------------------------------------------------------------------------------
# AC4. IT ADDS NO SECOND FLEET.
#
# FALSIFIED BY: add a control loop, a spawner or a pacing decision to .veldo/tasks.py, and the
# scan row below must go red.
# ---------------------------------------------------------------------------------------


def _ts_ac4():
    src = (ROOT / ".veldo" / "tasks.py").read_text()
    import ast as _ts_ast
    tree = _ts_ast.parse(src)
    names = set()
    for node in _ts_ast.walk(tree):
        if isinstance(node, _ts_ast.Name):
            names.add(node.id)
        elif isinstance(node, _ts_ast.Attribute):
            names.add(node.attr)
    forbidden = {"sleep", "spawn", "retire", "desired_workers", "resume_at_epoch", "Popen",
                 "fork", "Thread", "Process"}
    loaded = set(_ts_re_organs(src))
    expect("VELDO-0003 AC4: .veldo/tasks.py REFERENCES NO SPAWNER, NO SLEEP AND NO PACING "
           "PRIMITIVE, and loads no governor or fleet organ. The elastic loop, the governor, the "
           "in-session spawner and the resume waiter already exist and are already governed, so a "
           "work source that reached for any of them would be the first step toward a second "
           "UNGOVERNED pool - the one shape PLAN-0018 NG2 forbids in those words. AST identifiers, "
           "not substrings, because a docstring naming the thing it refuses to do is prose",
           not (names & forbidden) and not ({"governor", "fleet"} & loaded))

    with tempfile.TemporaryDirectory() as d:
        base, td, claims = _ts_tree(d, [("a.yaml", _ts_emit(
            [_ts_task(), _ts_task(tid="TASK-0002", produces="build/review-TWO.md")]))])
        ctl = TS.TaskController(desired=lambda: 2, resume_at=lambda: 0.0, now=lambda: 1000.0,
                               tdir=td, root=base, parse=V.parse_yamlish, claims_root=claims)
        _ts_contract = sorted(k for k in vars(TSFL.FleetController) if not k.startswith("_"))
        expect("VELDO-0003 AC4: the controller satisfies the EXISTING FleetController contract "
               "STRUCTURALLY, and the contract is DERIVED from that class rather than typed here. "
               "Structural and not by inheritance ON PURPOSE: inheriting would make this module "
               "load fleet.py, which is the very coupling this criterion forbids. It owns exactly "
               "one of the four methods - desired, resume_at and now are INJECTED callables, which "
               "is how the module holds no governor reference at all (contract: %s)"
               % ", ".join(_ts_contract),
               sorted(k for k in vars(TS.TaskController) if not k.startswith("_"))
               == _ts_contract
               and (ctl.desired(), ctl.resume_at(), ctl.now()) == (2, 0.0, 1000.0)
               and ctl.work_remains() is True)

        class _TsSpawner(TSFL.WorkerSpawner):
            def __init__(self):
                self.spawned, self.retired = [], 0

            def spawn(self, wid, scope):
                return ("h", wid, self.spawned.append(wid))

            def retire(self, handle):
                self.retired += 1

        class _TsWaiter:
            def __init__(self):
                self.waits = []

            def wait_until(self, epoch):
                self.waits.append(epoch)

            def tick(self):
                pass

        sp, wt = _TsSpawner(), _TsWaiter()
        TSFL.veldo_fleet(sp, ctl, wt, max_workers=4, scope="tasks", max_ticks=3)
        expect("VELDO-0003 AC4: fleet.veldo_fleet DRAINS A QUEUE OF TASKS WITH NO CHANGE TO "
               "fleet.py AT ALL - the real loop, driven to completion over the real controller, "
               "spawning up to the governed target and retiring every worker when it stops. This "
               "is the whole proof that the item added a work source and not a second fleet",
               len(sp.spawned) == 2 and sp.retired == len(sp.spawned))

        # THE LOOP CONSULTS work_remains ONLY WHEN THE GOVERNED TARGET IS ZERO, which is its
        # documented drain-versus-backoff distinction: a nonzero target means workers run and
        # discover an empty queue themselves. MEASURED, and it corrected this row: an earlier
        # version asserted the loop would refuse to spawn over a concluded queue, and driving it
        # showed the loop spawning two workers. The assertion was wrong, not the loop. So the
        # property worth asserting is the one that exists - and it is the stronger one, because it
        # proves THIS controller's work_remains is what decides between stopping and waiting.
        for rel in ("build/review-EXAMPLE.md", "build/review-TWO.md"):
            p = base / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("done")
        expect("VELDO-0003 AC4: with every product now on disk the SAME controller reports no work "
               "remaining, so the queue state reaches the loop through the real read model",
               ctl.work_remains() is False)

        drained = TS.TaskController(desired=lambda: 0, resume_at=lambda: 9e9, now=lambda: 1000.0,
                                    tdir=td, root=base, parse=V.parse_yamlish, claims_root=claims)
        sp2, wt2 = _TsSpawner(), _TsWaiter()
        TSFL.veldo_fleet(sp2, drained, wt2, max_workers=4, scope="tasks", max_ticks=3)
        expect("VELDO-0003 AC4: at a governed target of ZERO with the queue CONCLUDED, the loop "
               "DRAINS - it stops, retires, and never waits - so a finished task queue ends the "
               "fleet instead of parking it on a resume time that would never come",
               sp2.spawned == [] and wt2.waits == [])

        with tempfile.TemporaryDirectory() as d2:
            base2, td2, claims2 = _ts_tree(d2, [("a.yaml", _ts_emit([_ts_task()]))])
            backoff = TS.TaskController(desired=lambda: 0, resume_at=lambda: 4200.0,
                                        now=lambda: 1000.0, tdir=td2, root=base2,
                                        parse=V.parse_yamlish, claims_root=claims2)
            sp3, wt3 = _TsSpawner(), _TsWaiter()
            TSFL.veldo_fleet(sp3, backoff, wt3, max_workers=4, scope="tasks", max_ticks=2)
            expect("VELDO-0003 AC4 NEGATIVE CONTROL, and it is the leg that matters: at the SAME "
                   "zero target with work STILL OPEN, the same loop WAITS for the resume time "
                   "instead of draining. The two fixtures differ in exactly one thing - whether "
                   "the product exists - so this controller's work_remains is provably what the "
                   "loop reads to tell 'nothing left' from 'budget spent, work remains'",
                   wt3.waits and set(wt3.waits) == {4200.0} and sp3.spawned == []
                   and backoff.work_remains() is True)


_ts_block("AC4", _ts_ac4)


# ---------------------------------------------------------------------------------------
# AC5. ADOPTION SAFE, AND IT ENFORCES NOTHING.
#
# FALSIFIED BY: remove the absent-directory stand-down, and the row below must go red.
# ---------------------------------------------------------------------------------------


def _ts_ac5():
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        rep = TS.task_report(tdir=base / ".veldo" / "tasks", root=base, parse=V.parse_yamlish,
                             claims_root=str(base / "claims"))
        lines = TS.report_lines(rep)
        expect("VELDO-0003 AC5: a repository with no .veldo/tasks/ directory STANDS THE READ MODEL "
               "DOWN and names which condition fired, never reporting zero open tasks as though it "
               "had looked and found none. 'This repository declares no non-construction work' and "
               "'there is none left to do' are different facts and a zero cannot tell them apart",
               rep["stood_down"] is True and "NOT the same fact" in rep["reason"]
               and any("stood down" in ln for ln in lines))
        expect("VELDO-0003 AC5: the check itself returns clean over an absent directory, so an "
               "adopting repository is byte-identically unaffected by this contract existing",
               TS.check_tasks_dir(base / ".veldo" / "tasks", base, V.parse_yamlish, V.fail) == 0)

    with tempfile.TemporaryDirectory() as d:
        base, td, claims = _ts_tree(d, [])
        rep_empty = TS.task_report(tdir=td, root=base, parse=V.parse_yamlish, claims_root=claims)
        expect("VELDO-0003 AC5: a directory that exists but declares NO TASK stands down with a "
               "DIFFERENT reason, because an empty queue and an unadopted repository are not the "
               "same fact either",
               rep_empty["stood_down"] is True
               and rep_empty["reason"] == TS.STAND_DOWN_NO_TASKS)

    with tempfile.TemporaryDirectory() as d:
        base, td, claims = _ts_tree(d, [("a.yaml", _ts_emit([_ts_task()]))])
        rep_live = TS.task_report(tdir=td, root=base, parse=V.parse_yamlish, claims_root=claims)
        expect("VELDO-0003 AC5 NEGATIVE CONTROL: with a task directory present the SAME report "
               "answers, so the stand-down is a measurement of the tree and not this module's only "
               "behaviour",
               rep_live["stood_down"] is False and len(rep_live["open"]) == 1)
        expect("VELDO-0003 AC5: the report carries ONE KEY SHAPE whether it stood down or not, so "
               "a consumer never guesses whether a key is missing or genuinely empty",
               sorted(rep_live) == sorted(TS.REPORT_KEYS)
               and sorted(rep_empty) == sorted(TS.REPORT_KEYS))

    # NO GATE STAGE LOADS THIS, asserted over LOADS and not over MENTIONS. An earlier version of
    # this row asserted no file so much as NAMED tasks.py, and it correctly caught the item's own
    # lay-down entry: /veldo:init must name the module in order to ship it to an adopter, which is
    # not consulting it. A mention is prose or a manifest; a LOAD is the coupling this criterion is
    # about, and telling them apart needs the AST - the same lesson the behaviour-floor build learned
    # when a docstring mentioning a function defeated a substring scan for its absence.
    import ast as _ts_a2

    def _ts_loads_tasks(path):
        try:
            tree = _ts_a2.parse(path.read_text())
        except (OSError, SyntaxError):
            return False
        for node in _ts_a2.walk(tree):
            if not isinstance(node, _ts_a2.Call):
                continue
            fname = (node.func.attr if isinstance(node.func, _ts_a2.Attribute)
                     else getattr(node.func, "id", ""))
            if fname not in ("spec_from_file_location", "_organ", "_load", "_sibling",
                             "import_module"):
                continue
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                if isinstance(arg, _ts_a2.Constant) and isinstance(arg.value, str) \
                        and arg.value.rstrip(".py").endswith("tasks"):
                    return True
        return False

    _ts_loaders = sorted(p.name for p in list((ROOT / ".veldo").glob("*.py"))
                         + list((ROOT / "scripts").glob("*.py"))
                         if p.name != "tasks.py" and _ts_loads_tasks(p))
    expect("VELDO-0003 AC5: NO GATE STAGE LOADS THIS. Across .veldo/*.py and scripts/*.py no file "
           "but this module's own suite loads tasks.py, so nothing a gate runs can refuse a change "
           "because a task is open - a queue that could block work would turn an advisory organ "
           "into a gate, which PLAN-0018 NG3 forbids in those words. Asserted over LOADS via the "
           "AST rather than over mentions, because /veldo:init legitimately NAMES the module in "
           "order to ship it and naming is not consulting",
           _ts_loaders == [])
    expect("VELDO-0003 AC5 NEGATIVE CONTROL for the row above: the load detector is not blind - it "
           "finds this module's OWN load of the claim ledger, so an absence claim built on it is a "
           "measurement rather than a scan that never matches anything",
           _ts_re_organs((ROOT / ".veldo" / "tasks.py").read_text()) == ["claim", "claim"])


_ts_block("AC5", _ts_ac5)
