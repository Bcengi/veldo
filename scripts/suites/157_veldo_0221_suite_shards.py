# VELDO-0221: a gate leg runs its suites as isolated parallel closure shards, with an isolation
# check in every gate. Every row drives the shipped dispatcher (scripts/selftest.py) and the
# shipped shard machinery (scripts/run_scope.py) over fixture trees: the same two files, copied.
#
# NO ROW DEPENDS ON MACHINE SPEED (owner rule 42829). A fixture leg is synchronized on what the
# dispatcher itself records (the order of its starts and ends, each shard's report) and on files
# the fixtures write for each other, never on a sleep or a short deadline. The row about a deadline
# keeps the production deadline and moves the dispatcher's CLOCK instead, and only after the
# fixture suite has said it is running. Every wait below is a hang detector of 600 seconds.


def _veldo_0221():
    import errno
    import hashlib
    import importlib.util
    import shutil
    import socket
    import threading
    import time
    from unittest.mock import patch

    def load(path, name):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    RS = load(ROOT / "scripts" / "run_scope.py", "v221_run_scope")
    GL = load(ROOT / "scripts" / "gate_legs.py", "v221_gate_legs")
    digest = "sha256:" + "0" * 64
    outer = ("VELDO_GATE_LEG", "VELDO_GATE_UNCONFINED", "VELDO_GATE_DECLARATION", "VELDO_GATE_FORCE_FRESH",
             "VELDO_GATE_LEDGER_FD", "VELDO_GATE_SHARD_LEDGER_FD", "VELDO_GATE_SHARD_CLAIMS", "VELDO_GATE_SHARD_METRICS_FD",
             "VELDO_GATE_UNIT_SECONDS", "VELDO_SUITE_ORDER")
    plain = {k: v for k, v in os.environ.items() if k not in outer}

    def leg_env(leg, listed, **extra):
        return dict(plain, VELDO_GATE_LEG=leg, VELDO_GATE_UNCONFINED=listed, VELDO_GATE_DECLARATION=digest,
                    **extra)

    fixture_shared = (
        'import os\nimport sys\nfrom pathlib import Path\n'
        'ROOT = Path(__file__).resolve().parents[2]\nPASS = FAIL = 0\nSCOPE = None\n'
        'def suite_file():\n    return Path(globals().get("__suite_file__", ""))\n'
        'def leg_runs(rows=None):\n    import run_scope as _rs\n    return _rs.leg_runs(suite_file().stem, rows)\n'
        'def expect(name, condition):\n    global PASS, FAIL\n    if condition:\n        PASS += 1\n'
        '    else:\n        FAIL += 1\n        print("  SELFTEST FAIL: %s" % name)\n'
        'def report():\n    print(SCOPE.aggregate_line(PASS, FAIL)); return SCOPE.exit_code(FAIL)\n')

    def tree(top, bodies, requires=None, resources=None, capacities=None, closures=True, launcher=True):
        """A fixture candidate: the shipped dispatcher and shard machinery over fixture suites."""
        top = Path(top)
        (top / "scripts/suites").mkdir(parents=True)
        shutil.copyfile(ROOT / "scripts" / "selftest.py", top / "scripts/selftest.py")
        shutil.copyfile(ROOT / "scripts" / "run_scope.py", top / "scripts/run_scope.py")
        shutil.copyfile(ROOT / "scripts" / "gate_fixtures.py", top / "scripts/gate_fixtures.py")
        if launcher:
            shutil.copyfile(ROOT / "scripts" / "agent_sandbox.py", top / "scripts/agent_sandbox.py")
        (top / "scripts/suites/shared.py").write_text(fixture_shared)
        for name, body in bodies.items():
            (top / "scripts/suites" / (name + ".py")).write_text(body)
        manifest = {"schema": "veldo.suites/v1", "entry": "selftest.py", "shared": "shared.py",
                    "resource_capacities": capacities or {},
                    "suites": [dict({"name": n, "file": n + ".py"},
                                    **({"resources": resources[n]} if n in (resources or {}) else {}))
                               for n in bodies]}
        (top / "scripts/suites/manifest.json").write_text(json.dumps(manifest))
        if closures:
            table = {n: [n] for n in bodies}
            table.update(requires or {})
            (top / "scripts/suites/requires.json").write_text(json.dumps({"requires": table}))
        return top

    def through_dispatcher(root, env):
        """One leg through the shipped scripts/selftest.py, as the gate starts it. The leg's home and
        temporary directory are this fixture's own, as the launcher's scratch is the gate leg's: the
        isolation check reads both, and what other sessions put in the real ones is no part of a row."""
        private = Path(tempfile.mkdtemp(prefix="leg-", dir=str(top)))
        (private / "tmp").mkdir()
        env = dict(env, HOME=str(private), TMPDIR=str(private / "tmp"))
        return subprocess.run([sys.executable, str(Path(root) / "scripts/selftest.py")], cwd=str(root),
                              env=env, capture_output=True, text=True, timeout=600,
                              stdin=subprocess.DEVNULL, pass_fds=launcher_fds())

    def shards(root, leg, targets, listed="none_listed", **options):
        """One leg through run_scope.run_shards in this process, with a fixture's own shared places."""
        lines = []
        options.setdefault("places", [])
        # A fixture leg's runtime directories stand beside its other roots unless a row says where.
        options.setdefault("runtime", "")
        options.setdefault("units", None)
        options.setdefault("settle", 0)
        options.setdefault("parallel", 4)
        extra = options.pop("extra", {})
        drop = options.pop("drop", ())
        environ = {k: v for k, v in leg_env(leg, listed, **extra).items() if k not in drop}
        if "HOME" not in extra:
            # A fixture leg's own home and temporary directory, unless a row names them: run inside the
            # ordered confined leg this suite's are the launcher's scratch, which the dispatcher would
            # take for the scratch of the fixture leg and stand its shards' temporary directories in.
            private = Path(tempfile.mkdtemp(prefix="leg-", dir=str(top)))
            (private / "tmp").mkdir()
            environ.update(HOME=str(private), TMPDIR=str(private / "tmp"))
        result = RS.run_shards(root, leg, targets, environ=environ, emit=lines.append, **options)
        return result, lines

    def codes(result, suite):
        return sorted(code for code, _words in result["charged"].get(suite, []))

    with tempfile.TemporaryDirectory(prefix="v221-") as temporary:
        top = Path(temporary)

        # ==== AC1: every suite of a leg is one shard's target exactly once, and every failure fails ====
        # The full manifest in both legs: this repository's own manifest, closure table and unconfined
        # list, with every suite's body replaced by one row, so both legs run for real in seconds.
        manifest = json.loads((ROOT / "scripts/suites/manifest.json").read_text())
        names = [s["name"] for s in RS.fragments(manifest)]
        stubs = top / "stubs"
        (stubs / "scripts/suites").mkdir(parents=True)
        shutil.copyfile(ROOT / "scripts" / "selftest.py", stubs / "scripts/selftest.py")
        shutil.copyfile(ROOT / "scripts" / "run_scope.py", stubs / "scripts/run_scope.py")
        shutil.copyfile(ROOT / "scripts" / "gate_fixtures.py", stubs / "scripts/gate_fixtures.py")
        shutil.copyfile(ROOT / "scripts" / "agent_sandbox.py", stubs / "scripts/agent_sandbox.py")
        (stubs / "scripts/suites/shared.py").write_text(fixture_shared)
        for suite in RS.fragments(manifest):
            (stubs / "scripts/suites" / suite["file"]).write_text('expect("stub ran", True)\n')
        (stubs / "scripts/suites/manifest.json").write_text(json.dumps(manifest))
        shutil.copyfile(ROOT / "scripts/suites/requires.json", stubs / "scripts/suites/requires.json")
        declaration, _ = GL.load(ROOT / "scripts/gate_unconfined.json")
        entries = ",".join(GL.entries(declaration))
        whole = {e["suite"] for e in declaration["suites"] if "rows" not in e}
        every = {e["suite"] for e in declaration["suites"]}
        expected = {"confined": [n for n in names if n not in whole],
                    "unconfined": [n for n in names if n in every]}
        full = {}
        for leg in ("confined", "unconfined"):
            _leg, listed = RS.gate_leg(leg_env(leg, entries))
            targets = RS.leg_suites(leg, listed, names)
            result, _ = shards(stubs, leg, targets, listed=entries, parallel=8)
            full[leg] = (targets, result)
        coverage = []
        for leg, (targets, result) in full.items():
            ran = [s["name"] for s in result["shards"]]
            if not (targets == expected[leg] and sorted(ran) == sorted(expected[leg]) and len(set(ran)) == len(ran)
                    and result["failed"] == 0 and result["passed"] == len(ran)
                    and all(s["passed"] == 1 for s in result["shards"])):
                coverage.append("%s leg: %d targets, %d expected, %d passed, %d failed"
                                % (leg, len(ran), len(expected[leg]), result["passed"], result["failed"]))
        if set(expected["confined"]) | set(expected["unconfined"]) != set(names) or not expected["unconfined"]:
            coverage.append("the two legs do not cover the manifest")
        # A leg with a failing suite, a shard that dies without a verdict, one whose target asserts
        # nothing and one whose undeclared prerequisite is missing from the closure table.
        failing = tree(top / "failing", {
            "01_good": 'SHARED_VALUE = 41\nexpect("good one", True)\nexpect("good two", True)\n',
            "02_closure": 'expect("closure sees its prerequisite", SHARED_VALUE == 41)\n',
            "03_fails": 'expect("three holds", True)\nexpect("three breaks: detail", False)\n',
            "04_dies": 'expect("four ran", True)\nsys.stdout.flush()\nos._exit(0)\n',
            "05_nothing": 'UNUSED = 1\n',
            "06_undeclared": 'expect("six needs what it never declared", SHARED_VALUE == 41)\n',
        }, requires={"02_closure": ["01_good", "02_closure"]})
        result, _ = shards(failing, "confined",
                           ["01_good", "02_closure", "03_fails", "04_dies", "05_nothing", "06_undeclared"])
        by_name = {s["name"]: s for s in result["shards"]}
        if not (codes(result, "01_good") == [] and codes(result, "02_closure") == []
                and by_name["01_good"]["passed"] == 2 and by_name["02_closure"]["passed"] == 1
                and by_name["02_closure"]["closure"] == ["01_good", "02_closure"]
                and by_name["03_fails"]["failed"] == 1 and codes(result, "03_fails") == []):
            coverage.append("good, closure or failing suite miscounted: %r" % result["charged"])
        if codes(result, "04_dies") != ["no_verdict"]:
            coverage.append("a shard that died without a verdict was charged %r" % codes(result, "04_dies"))
        if codes(result, "05_nothing") != ["asserted_nothing"]:
            coverage.append("a target that asserted nothing was charged %r" % codes(result, "05_nothing"))
        if codes(result, "06_undeclared") != ["no_verdict"]:
            coverage.append("a missing prerequisite was charged %r" % codes(result, "06_undeclared"))
        # passed: 2 + 1 + 1 rows; failed: one row of 03 and one for each of 04, 05 and 06.
        if (result["passed"], result["failed"]) != (4, 4):
            coverage.append("counts %d passed, %d failed, not 4 and 4" % (result["passed"], result["failed"]))
        # The same tree through the shipped dispatcher: the leg is red, its aggregate line is composed
        # from the targets, and the failure names it prints are exactly the failures it counts.
        ran = through_dispatcher(failing, leg_env("confined", "none_listed"))
        printed = [line for line in ran.stdout.splitlines() if RS.FAIL_MARK in line]
        if not (ran.returncode == 1 and "selftest: 4 passed, 4 failed" in ran.stdout.splitlines()
                and len(printed) == 4 and "selftest leg confined: 6 shard(s)" in ran.stdout):
            coverage.append("through the dispatcher: exit %d, %d failure names, last lines %r"
                            % (ran.returncode, len(printed), ran.stdout.splitlines()[-2:]))
        # The ordered run hid a missing prerequisite: the same two suites pass there, in one namespace.
        hidden = tree(top / "hidden", {
            "01_good": 'SHARED_VALUE = 41\nexpect("good", True)\n',
            "02_undeclared": 'expect("needs what it never declared", SHARED_VALUE == 41)\n'})
        ordered = subprocess.run([sys.executable, str(hidden / "scripts/selftest.py")], cwd=str(hidden), env=plain,
                                 capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
        result, _ = shards(hidden, "confined", ["01_good", "02_undeclared"])
        if not (ordered.returncode == 0 and ordered.stdout.splitlines()[-1] == "selftest: 2 passed, 0 failed"
                and codes(result, "02_undeclared") == ["no_verdict"] and codes(result, "01_good") == []
                and (result["passed"], result["failed"]) == (1, 1)):
            coverage.append("the missing prerequisite the ordered run hid: ordered exit %d, shards charged %r"
                            % (ordered.returncode, result["charged"]))
        # A suite the closure table does not carry fails its shard by name, without running.
        unlisted = tree(top / "unlisted", {"01_only": 'expect("one", True)\n', "02_absent": 'expect("two", True)\n'})
        table = json.loads((unlisted / "scripts/suites/requires.json").read_text())
        del table["requires"]["02_absent"]
        (unlisted / "scripts/suites/requires.json").write_text(json.dumps(table))
        result, _ = shards(unlisted, "confined", ["01_only", "02_absent"])
        if codes(result, "02_absent") != ["closure_unavailable"] or result["failed"] != 1:
            coverage.append("a suite with no closure was charged %r" % codes(result, "02_absent"))
        expect("VELDO-0221 AC1 suite-shards/coverage: " + "; ".join(coverage), not coverage)

        # A good leg is green through the dispatcher, and --shard is refused to a person.
        good = tree(top / "good", {"01_a": 'expect("a", True)\n', "02_b": 'expect("b", True)\n'})
        ran = through_dispatcher(good, leg_env("confined", "none_listed"))
        expect("VELDO-0221 suite-shards/green-leg-through-the-dispatcher: " + ran.stdout[-400:],
               ran.returncode == 0 and ran.stdout.splitlines()[-1] == "selftest: 2 passed, 0 failed"
               and "isolation check held" in ran.stdout and ran.stdout.count("Landlock layer in force") == 2)
        by_hand = subprocess.run([sys.executable, str(good / "scripts/selftest.py"), "--suite", "01_a", "--shard", "1",
                                  "--shard-root", str(top)], cwd=str(good), env=plain, capture_output=True,
                                 text=True, timeout=600, stdin=subprocess.DEVNULL)
        expect("VELDO-0221 suite-shards/shard-flag-refused-outside-a-leg: " + by_hand.stdout[-200:],
               by_hand.returncode == 2 and "SHARD_REFUSED" in by_hand.stdout)
        # A selector and a bare run keep the ordered single-namespace run, and so does a leg of a tree
        # with no closure table, which says so.
        bare = subprocess.run([sys.executable, str(good / "scripts/selftest.py")], cwd=str(good), env=plain,
                              capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
        tableless = tree(top / "tableless", {"01_a": 'expect("a", True)\n'}, closures=False)
        ordered_leg = through_dispatcher(tableless, leg_env("confined", "none_listed"))
        launcherless = tree(top / "launcherless", {"01_a": 'expect("a", True)\n'}, launcher=False)
        unlaunched = through_dispatcher(launcherless, leg_env("confined", "none_listed"))
        outside = through_dispatcher(launcherless, leg_env("unconfined", "01_a"))
        expect("VELDO-0221 suite-shards/ordered-run-kept-outside-a-leg: " + ordered_leg.stdout[-300:],
               bare.returncode == 0 and "selftest shard" not in bare.stdout
               and bare.stdout.splitlines()[-1] == "selftest: 2 passed, 0 failed"
               and ordered_leg.returncode == 0 and "no closure table" in ordered_leg.stdout
               and "selftest shard" not in ordered_leg.stdout
               and ordered_leg.stdout.splitlines()[-1] == "selftest: 1 passed, 0 failed"
               # No launcher to take a Landlock layer from: the confined leg stays ordered, and the
               # unconfined leg, which stacks none, still runs as shards.
               and unlaunched.returncode == 0 and "no launcher" in unlaunched.stdout
               and "selftest shard" not in unlaunched.stdout
               and unlaunched.stdout.splitlines()[-1] == "selftest: 1 passed, 0 failed"
               and "selftest shard" in outside.stdout)
        # A shard that makes no progress for its deadline is a failure of its suite. EVENT
        # SYNCHRONIZED: the deadline is the production one, and the dispatcher's clock is moved
        # forward only once the suite has written that it is running, then by more than the deadline
        # at every reading. The suite sleeps for ever after that, so some reading finds it without
        # progress whatever this machine's speed; before the mark the clock is the real one.
        running_mark = top / "hung-is-running"
        hung = tree(top / "hung", {"01_hangs": (
            'import time\nexpect("started", True)\nsys.stdout.flush()\n'
            'Path(os.environ["V221_MARK"]).write_text("running")\nwhile True:\n    time.sleep(3600)\n')})
        moved = [0.0]

        def moving_clock():
            if running_mark.exists():
                moved[0] += 10 * RS.SHARD_DEADLINE_S
            return time.monotonic() + moved[0]
        # An unconfined fixture leg: the mark stands outside the shard's roots, where a confined
        # shard's layer would refuse it.
        result, _ = shards(hung, "unconfined", ["01_hangs"], listed="01_hangs", clock=moving_clock, tick=0.05,
                           extra={"V221_MARK": str(running_mark)})
        words = [w for _c, w in result["charged"].get("01_hangs", [])]
        expect("VELDO-0221 suite-shards/deadline-fails-the-suite: %r" % result["charged"],
               codes(result, "01_hangs") == ["deadline_exceeded"] and result["failed"] == 1
               and running_mark.exists() and "no progress" in words[0] and RS.SHARD_DEADLINE_S >= 1800)
        # The rule itself, on numbers: the deadline runs from a shard's LAST PROGRESS, never from its
        # start, so a suite that is slow, or that runs on a loaded machine, is not ended for it.
        slow = {"started": 0.0, "progress_at": 0.0, "marks": (0, 0), "deadline": 1800.0}
        verdicts = []
        for now, marks in ((1000.0, (10, 5)), (2500.0, (10, 9)), (4000.0, (11, 9)), (5700.0, (11, 9)),
                           (5801.0, (11, 9))):
            RS.shard_progress(slow, now, marks)
            verdicts.append(RS.shard_stalled(slow, now))
        expect("VELDO-0221 suite-shards/deadline-runs-from-the-last-progress: %r %r" % (verdicts, slow),
               verdicts == [False, False, False, False, True] and slow["progress_at"] == 4000.0)

        # ==== AC2: shards are isolated by construction ==========================================
        engine_names = (
            'import importlib.util\n'
            'def _load(path, name):\n    spec = importlib.util.spec_from_file_location(name, path)\n'
            '    module = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(module)\n    return module\n'
            'CC = _load(os.environ["V221_ENGINE"] + "/control_client.py", "v221_cc")\n'
            'C = _load(os.environ["V221_ENGINE"] + "/control_containment.py", "v221_c")\n'
            'binding = {"domain_uuid": "d" * 8, "store_uuid": "s" * 8}\n'
            'unit = CC.service_unit(binding)\n'
            'print("V221-NAMES %s %s" % (suite_file().stem, json.dumps({"authority": unit, '
            '"api": "veldo-api-" + unit[len(CC.SERVICE_BASE):], "slice": C.DEFAULT_SLICE, '
            '"scope": C.unit_name("dispatch-1"), "instance": C.instance_name(), '
            '"same_rule": CC.SERVICE_PREFIX == CC.SERVICE_BASE + C.instance_part()})), flush=True)\n')
        writer = (
            'import json\n'
            'roots = {v: os.environ[v] for v in ("HOME", "TMPDIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", '
            '"XDG_CACHE_HOME", "XDG_STATE_HOME", "XDG_RUNTIME_DIR", "VELDO_FIXTURE_ROOT") if v in os.environ}\n'
            'for variable in ("HOME", "TMPDIR", "XDG_RUNTIME_DIR", "VELDO_FIXTURE_ROOT"):\n'
            '    target = Path(roots[variable]) / "same-relative-path"\n'
            '    expect("the path is new in my own root: " + variable, not target.exists())\n'
            '    target.write_text(suite_file().stem)\n'
            '    expect("I read back what I wrote: " + variable, target.read_text() == suite_file().stem)\n'
            'print("V221-ROOTS %s %s" % (suite_file().stem, json.dumps(roots)), flush=True)\n'
            'print("V221-RUNTIME %s %s" % (suite_file().stem, json.dumps(sorted(\n'
            '    str(p.relative_to(roots["XDG_RUNTIME_DIR"])) for p in Path(roots["XDG_RUNTIME_DIR"]).rglob("*")\n'
            '    if p.name != "same-relative-path"))), flush=True)\n' + engine_names)
        intruder = (
            'mine = Path(os.environ["TMPDIR"])\n'
            'fixtures = Path(os.environ["VELDO_FIXTURE_ROOT"])\n'
            'refused = []\n'
            'for target in (mine.parent / "p" / "intruder", mine.parent / "00h" / "intruder", '
            'fixtures.parent / "intruder", fixtures.parent / "00" / "intruder"):\n'
            '    try:\n        target.write_text("x")\n        refused.append("wrote")\n'
            '    except PermissionError:\n        refused.append("refused")\n'
            '    except FileNotFoundError:\n        refused.append("gone")\n'
            'print("V221-INTRUDER %s" % ",".join(refused), flush=True)\n'
            'expect("my own root is writable", (Path(os.environ["HOME"]) / "ok").write_text("x") == 1)\n')
        isolated = tree(top / "isolated", {"01_first": writer, "02_second": writer, "03_intruder": intruder})
        # The leg's environment names all four XDG base directories here, so each shard is given
        # its own of each; a row below drives a leg that names none.
        engine = {"V221_ENGINE": str(ROOT / ".veldo"), "XDG_CONFIG_HOME": str(top / "leg-xdg-c"),
                  "XDG_DATA_HOME": str(top / "leg-xdg-d"), "XDG_CACHE_HOME": str(top / "leg-xdg-k"),
                  "XDG_STATE_HOME": str(top / "leg-xdg-s")}
        problems = []
        for leg in ("unconfined", "confined"):
            result, lines = shards(isolated, leg, ["01_first", "02_second", "03_intruder"],
                                   listed="01_first,02_second,03_intruder" if leg == "unconfined" else "none_listed",
                                   extra=engine)
            said = {}
            for line in lines:
                if line.startswith("V221-"):
                    kind, rest = line.split(" ", 1)
                    said.setdefault(kind, []).append(rest)
            roots = {text.split(" ", 1)[0]: json.loads(text.split(" ", 1)[1]) for text in said.get("V221-ROOTS", [])}
            named = {text.split(" ", 1)[0]: json.loads(text.split(" ", 1)[1]) for text in said.get("V221-NAMES", [])}
            runtime = {text.split(" ", 1)[0]: json.loads(text.split(" ", 1)[1]) for text in said.get("V221-RUNTIME", [])}
            if set(roots) != {"01_first", "02_second"} or result["failed"]:
                problems.append("%s: the two writers did not both pass: %r %r" % (leg, result["charged"], lines[-6:]))
                continue
            first, second = roots["01_first"], roots["02_second"]
            every_root = list(first.values()) + list(second.values())
            if len(set(every_root)) != 16 or len(first) != 8:
                problems.append("%s: the two shards share a root: %r %r" % (leg, first, second))
            # Each shard's roots are its own siblings of one leg directory, named by its own tag.
            tags = {name: Path(r["TMPDIR"]).name for name, r in roots.items()}
            legs_base = {str(Path(value).parent) for r in roots.values() for key, value in r.items()
                         if key != "VELDO_FIXTURE_ROOT"}
            if tags["01_first"] == tags["02_second"] or len(legs_base) != 1 or not all(
                    Path(value).name.startswith(tags[name]) and len(Path(value).name) <= len(tags[name]) + 1
                    for name, r in roots.items() for value in r.values()):
                problems.append("%s: a root is not its own shard's: %r" % (leg, roots))
            fixture_roots = [Path(r["VELDO_FIXTURE_ROOT"]) for r in roots.values()]
            if (len({p.parent for p in fixture_roots}) != 1
                    or any(p.exists() for p in fixture_roots)
                    or any(Path(r[v]) in Path(r["VELDO_FIXTURE_ROOT"]).parents
                           for r in roots.values() for v in ("HOME", "TMPDIR", "XDG_RUNTIME_DIR"))):
                problems.append("%s: fixture roots overlap launch places or survive leg cleanup" % leg)
            # The runtime directory holds only links to the user manager's own sockets and the
            # shard's instance name, which every tool the suite starts reads there.
            if not all({"veldo-instance.json"} <= set(found) <= {"bus", "systemd", "systemd/private", "systemd/user",
                                                                 "veldo-instance.json"} for found in runtime.values()):
                problems.append("%s: a runtime directory holds more than the manager's sockets: %r" % (leg, runtime))
            # Every unit, slice and scope name carries its shard's instance name, IN BOTH LEGS: the
            # leg's token, the shard's tag and the suite's name. The two shards' differ, and the
            # dispatcher's own pattern reads the instance back out of each name.
            given = {s["name"]: s["instance"] for s in result["shards"]}
            for name, item in named.items():
                instance = item["instance"]
                if not (instance == given[name] and instance.startswith(result["token"])
                        and instance.endswith("_" + name) and item["same_rule"]
                        and all(instance in item[key] for key in ("authority", "api", "slice", "scope"))
                        and all(RS.unit_instance(item[key]) == (True, instance)
                                for key in ("authority", "api", "slice", "scope"))
                        # The slice is a sibling of the production slice, never its child: the manager
                        # nests by dashes, and nothing follows `veldo-workers` but an underscore.
                        and item["slice"] == "veldo-workers_%s.slice" % instance):
                    problems.append("%s: %s names something without its instance name: %r" % (leg, name, item))
            if len(named) != 2 or any(named["01_first"][key] == named["02_second"][key]
                                      for key in ("authority", "api", "slice", "scope")):
                problems.append("%s: the two shards would name a unit alike: %r" % (leg, named))
            crossing = said.get("V221-INTRUDER", [""])[0].split(",")
            if leg == "confined" and not (len(crossing) == 4 and crossing[0] == "refused"
                                          and crossing[1] in ("refused", "gone")
                                          and crossing[2] == "refused" and crossing[3] in ("refused", "gone")):
                problems.append("confined: a write into another shard's root or beside the roots was %r" % crossing)
            if leg == "confined" and codes(result, "03_intruder"):
                problems.append("confined: the refused intruder was charged %r" % codes(result, "03_intruder"))
        # Results arrive per shard over each shard's own pipe: the counts above are per suite, and a
        # report descriptor is closed to everything a suite starts.
        leak = tree(top / "leak", {"01_child": (
            'import subprocess\n'
            'mine = [a for a in sys.argv if a.isdigit()]\n'
            'in_child = subprocess.run([sys.executable, "-c", "import os, sys\\ntry:\\n    os.fstat(int(sys.argv[1]))\\n'
            '    print(\'open\')\\nexcept OSError:\\n    print(\'closed\')", mine[0]], capture_output=True, text=True,\n'
            '                          close_fds=False).stdout.strip()\n'
            'expect("a child of the suite does not hold the report pipe: " + in_child, in_child == "closed")\n')})
        result, lines = shards(leak, "confined", ["01_child"])
        if result["failed"] or result["passed"] != 1:
            problems.append("a suite's child inherited the report pipe: %r" % lines[-4:])
        # Two legs at once on one host never share an instance name: the token is the leg's own.
        other, _ = shards(isolated, "unconfined", ["01_first"], listed="01_first", extra=engine)
        if other["token"] == result["token"] or len(other["token"]) != 8 \
                or RS.instance_of("abcdef01", 0, "x" * 80) != ("abcdef0100_" + "x" * 80)[:64]:
            problems.append("two legs share a token, or a long suite name overflows the instance name")
        # A leg whose environment names no XDG base directory: its shards name none either, so each
        # one's default lies beneath that shard's own HOME, as in the ordered run. One the leg names is
        # replaced by the shard's own, never inherited.
        xdg = ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME")
        result, lines = shards(isolated, "unconfined", ["01_first", "02_second"], listed="01_first,02_second",
                               extra={"V221_ENGINE": str(ROOT / ".veldo"), "XDG_DATA_HOME": str(top / "leg-xdg-d")},
                               drop=("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"))
        named_roots = [json.loads(line.split(" ", 2)[2]) for line in lines if line.startswith("V221-ROOTS ")]
        if not (result["failed"] == 0 and len(named_roots) == 2
                and all(sorted(r) == ["HOME", "TMPDIR", "VELDO_FIXTURE_ROOT", "XDG_DATA_HOME", "XDG_RUNTIME_DIR"] for r in named_roots)
                and named_roots[0]["XDG_DATA_HOME"] != named_roots[1]["XDG_DATA_HOME"]
                and str(top / "leg-xdg-d") not in (named_roots[0]["XDG_DATA_HOME"], named_roots[1]["XDG_DATA_HOME"])
                and RS.SHARD_ALWAYS == ("TMPDIR", "HOME", "XDG_RUNTIME_DIR")
                and sorted(v for v, _leaf in RS.SHARD_ROOTS) == sorted(RS.SHARD_ALWAYS + xdg + ("VELDO_FIXTURE_ROOT",))):
            problems.append("a shard names an XDG directory its leg does not, or inherits the leg's: %r" % named_roots)
        expect("VELDO-0221 AC2 suite-shards/isolated-by-construction: " + "; ".join(problems), not problems)

        # A confined shard cannot signal a sibling shard or the dispatcher: its layer is also a
        # Landlock signal scope. EVENT SYNCHRONIZED: the target writes its process id and waits
        # until the sender has written that it tried; the sender waits for the process id. Reading
        # a sibling's files is possible (the layer handles writes), which is how they find each other.
        target = ('import time\nmine = Path(os.environ["HOME"])\n(mine / "pid").write_text(str(os.getpid()))\n'
                  'tried = mine.parent / "01h" / "tried"\nlimit = time.monotonic() + 600\n'
                  'while not tried.exists() and time.monotonic() < limit:\n    time.sleep(0.01)\n'
                  'expect("the sender tried and I am still here", tried.exists())\n')
        sender = ('import signal, time\nmine = Path(os.environ["HOME"])\nsibling = mine.parent / "00h" / "pid"\n'
                  'limit = time.monotonic() + 600\nfound = ""\n'
                  'while not found and time.monotonic() < limit:\n'
                  '    found = sibling.read_text().strip() if sibling.exists() else ""\n    time.sleep(0.01)\n'
                  'said = []\n'
                  'for pid, number in ((int(found or -1), signal.SIGTERM), (os.getppid(), 0)):\n'
                  '    try:\n        if pid > 1:\n            os.kill(pid, number)\n            said.append("sent")\n'
                  '    except PermissionError:\n        said.append("refused")\n'
                  'os.kill(os.getpid(), 0)  # its own processes are inside its scope\n'
                  'print("V221-SIGNAL %s" % ",".join(said), flush=True)\n(mine / "tried").write_text("x")\n'
                  'expect("ran", True)\n')
        signalling = tree(top / "signalling", {"01_target": target, "02_sender": sender})
        result, lines = shards(signalling, "confined", ["01_target", "02_sender"])
        said = [line.split(" ", 1)[1] for line in lines if line.startswith("V221-SIGNAL ")]
        expect("VELDO-0221 AC2 suite-shards/no-signal-between-shards: %r %r" % (said, result["charged"]),
               said == ["refused,refused"] and result["failed"] == 0 and result["passed"] == 2)

        # In the gate's confined leg, whose temporary directory is `tmp` in the launcher's scratch, a
        # shard's temporary directory is a sibling of it and exactly as long: a suite's socket path
        # beneath it fits as it did in the ordered run. Anywhere else the roots stay in one directory.
        scratch = top / "veldo-agent-fixture0"
        (scratch / "tmp").mkdir(parents=True)
        result, lines = shards(isolated, "confined", ["01_first", "02_second"],
                               extra=dict(engine, HOME=str(scratch), TMPDIR=str(scratch / "tmp")),
                               # Only the fixture's own scratch is read: the real temporary directory
                               # holds what other sessions make, which is no part of this row.
                               places=[{"name": "leg home", "path": scratch, "depth": 1, "rule": "attributed"}])
        placed = {text.split(" ", 1)[0]: json.loads(text.split(" ", 1)[1]) for text in
                  (line.split(" ", 1)[1] for line in lines if line.startswith("V221-ROOTS "))}
        temporaries = [Path(r["TMPDIR"]) for r in placed.values()]
        elsewhere = RS.leg_scratch({"HOME": str(top), "TMPDIR": str(top / "tmp")}, isolated)
        expect("VELDO-0221 suite-shards/temporary-directory-no-longer-than-the-legs: %r %r %r"
               % (placed, result["charged"], result["unattributed"]),
               len(temporaries) == 2 and temporaries[0] != temporaries[1] and result["failed"] == 0
               and all(path.parent == scratch and len(path.name) == 3 and path.name != "tmp"
                       and len(str(path)) == len(str(scratch / "tmp")) for path in temporaries)
               and all(not r["HOME"].startswith(str(scratch)) for r in placed.values())
               and not result["breaches"] and not result["unattributed"]
               and RS.leg_scratch({"HOME": str(scratch), "TMPDIR": str(scratch / "tmp")}, isolated) == scratch
               and elsewhere is None and RS.leg_scratch({"HOME": str(scratch), "TMPDIR": "/tmp"}, isolated) is None)

        # In an unconfined leg a shard's runtime directory stands inside the real runtime directory, in
        # a directory of the leg's own, never beneath a temporary directory: the engine refuses a
        # protected target beneath one, and nineteen suites stand their fixtures in XDG_RUNTIME_DIR for
        # that reason. The fixture's own directory stands for the real one. The leg's directory is not
        # an item the leg left behind, and it is gone when the leg ends. A confined leg keeps its
        # runtime directories beside its other roots: it cannot write the real one.
        real_runtime = top / "fixture-run-user"
        real_runtime.mkdir()
        stood = {}
        for leg in ("unconfined", "confined"):
            result, lines = shards(isolated, leg, ["01_first", "02_second"], runtime=str(real_runtime), extra=engine,
                                   listed="01_first,02_second" if leg == "unconfined" else "none_listed",
                                   places=[{"name": "runtime directory", "path": real_runtime, "depth": 1, "rule": "strict"}])
            stood[leg] = ([Path(s["roots"]["XDG_RUNTIME_DIR"]) for s in result["shards"]],
                          [Path(s["roots"]["HOME"]) for s in result["shards"]], result["token"], result["failed"],
                          result["breaches"], [json.loads(line.split(" ", 2)[2]) for line in lines
                                               if line.startswith("V221-RUNTIME ")])
        outside, homes, token, failed, breaches, held = stood["unconfined"]
        beside = stood["confined"]
        expect("VELDO-0221 AC2 suite-shards/runtime-directory-outside-the-temporary-directory: %r %r" % (stood, list(real_runtime.iterdir())),
               len(outside) == 2 and outside[0] != outside[1] and failed == 0 and not breaches
               and len({path.parent for path in outside}) == 1 and outside[0].parent.parent == real_runtime
               and outside[0].parent.name.startswith("veldo-leg-%s-" % token)
               and not any(str(path).startswith(str(home.parent)) for path, home in zip(outside, homes))
               and all({"veldo-instance.json"} <= set(found) for found in held)
               and list(real_runtime.iterdir()) == []
               and all(path.parent == home.parent for path, home in zip(beside[0], beside[1]))
               and beside[3] == 0 and not beside[4]
               # No directory to stand them in: beside the other roots, as before.
               and RS.leg_runtime("") is None and RS.leg_runtime(str(top / "no-such-directory")) is None
               and RS.leg_runtime(str(real_runtime)) == real_runtime)

        # Another live leg must remain attributable even when it has no running
        # shard. A directory name alone is not evidence: the owner holds it open.
        owner_code = (
            'import importlib.util,sys\nfrom pathlib import Path\n'
            's=importlib.util.spec_from_file_location("scope",sys.argv[1])\n'
            'm=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n'
            'with m.RuntimeStand(Path(sys.argv[2]), "other") as p:\n'
            ' print(p,flush=True)\n sys.stdin.read(1)\n')
        owner = subprocess.Popen([sys.executable, '-I', '-c', owner_code,
                                  str(ROOT / 'scripts/run_scope.py'), str(real_runtime)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                 env=plain)
        try:
            ready, _, _ = __import__('select').select([owner.stdout], [], [], WAITS.WAIT_HANG_SECONDS)
            assert ready, 'runtime owner did not publish its directory'
            path = Path(owner.stdout.readline().strip())
            attribution = RS.attribute('runtime directory', path.name, path, top / 'observer', [])
            owner.communicate('x', timeout=WAITS.WAIT_HANG_SECONDS)
            expect('VELDO-0221 AC3 suite-shards/concurrent-runtime-owner-is-attributed',
                   attribution[1] == 'foreign' and str(owner.pid) in attribution[2]
                   and owner.returncode == 0 and not path.exists())
        finally:
            if owner.poll() is None:
                owner.kill()
                owner.wait(timeout=WAITS.WAIT_HANG_SECONDS)

        # With no instance configured, which is every production installation, every name is today's.
        probe = (
            'import importlib.util, json, sys\n'
            'def load(path, name):\n    spec = importlib.util.spec_from_file_location(name, path)\n'
            '    module = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(module)\n    return module\n'
            'CC = load(sys.argv[1] + "/control_client.py", "cc")\nC = load(sys.argv[1] + "/control_containment.py", "c")\n'
            'unit = CC.service_unit({"domain_uuid": "d" * 8, "store_uuid": "s" * 8})\n'
            'print(json.dumps({"authority": unit, "api": "veldo-api-" + unit[len(CC.SERVICE_BASE):], '
            '"prefix": CC.SERVICE_PREFIX, "slice": C.DEFAULT_SLICE, "scope": C.unit_name("dispatch-1"), '
            '"scope_prefix": C.UNIT_PREFIX, "instance": [C.instance_name(), C.instance_part()]}))\n')

        def engine_says(environment, directory=ROOT / ".veldo"):
            answer = subprocess.run([sys.executable, "-c", probe, str(directory)], capture_output=True, text=True,
                                    timeout=600, env=environment, stdin=subprocess.DEVNULL)
            return json.loads(answer.stdout) if answer.returncode == 0 else {"error": answer.stderr[-300:]}
        empty = top / "no-instance"
        empty.mkdir()
        service_id = hashlib.sha256(("%s\n%s" % ("d" * 8, "s" * 8)).encode()).hexdigest()[:16]
        today = {"authority": "veldo-authority-%s.service" % service_id, "api": "veldo-api-%s.service" % service_id,
                 "prefix": "veldo-authority-", "slice": "veldo-workers.slice",
                 "scope": "veldo-dispatch-%s.scope" % hashlib.sha256(b"dispatch-1").hexdigest()[:32],
                 "scope_prefix": "veldo-dispatch-", "instance": ["", ""]}

        def in_runtime(document):
            (empty / "veldo-instance.json").write_text(json.dumps(document))
            return engine_says(dict(plain, HOME=str(empty), XDG_CONFIG_HOME=str(empty), XDG_RUNTIME_DIR=str(empty)))
        unprefixed = engine_says(dict(plain, HOME=str(empty), XDG_CONFIG_HOME=str(empty), XDG_RUNTIME_DIR=str(empty)))
        from_runtime = in_runtime({"schema": "veldo.instance/v1", "prefix": "shard_a"})
        foreign_file = in_runtime({"schema": "another.tool/v1", "prefix": "x"})
        unsafe = in_runtime({"schema": "veldo.instance/v1", "prefix": "a-b.slice"})
        # A process inside one of the engine's own units reads the name from its unit's name, whatever
        # environment the manager gave it: the installed service needs no file of its own for it.
        C = load(ROOT / ".veldo" / "control_containment.py", "v221_containment")
        membership = top / "membership"
        from_unit = []
        for group in ("0::/session.slice/manager.service/app.slice/veldo-authority-shard_a-0123abcd.service",
                      "0::/session.slice/manager.service/app.slice/veldo-api-shard_a-0123abcd.service",
                      "0::/session.slice/manager.service/veldo.slice/veldo-workers_shard_a.slice/veldo-dispatch-shard_a-00ff.scope",
                      "0::/session.slice/manager.service/app.slice/veldo-authority-0123abcd.service",
                      "0::/session.slice/manager.service/app.slice/vte-spawn-0123.scope"):
            membership.write_text(group + "\n")
            from_unit.append(C.instance_name({}, str(membership)))
        (empty / "veldo-instance.json").write_text(json.dumps({"schema": "veldo.instance/v1", "prefix": "shard_b"}))
        membership.write_text("0::/app.slice/veldo-authority-shard_a-0123abcd.service\n")
        runtime_first = C.instance_name({"XDG_RUNTIME_DIR": str(empty)}, str(membership))
        OWN = load(ROOT / "scripts" / "mutation_ownership.py", "v221_ownership")
        accepted = [bool(OWN.SERVICE.fullmatch(name)) for name in (
            today["authority"], "veldo-authority-0a1b2c3d07_66_veldo_0047_authority-%s.service" % service_id,
            "veldo-authority-.service", "other-authority-%s.service" % service_id,
            "veldo-authority-a-b-%s.service" % service_id)]
        templates = {name: hashlib.sha256((ROOT / ".veldo/services" / name).read_bytes()).hexdigest()[:16]
                     for name in ("veldo-authority.service", "veldo-api.service")}
        expect("VELDO-0221 AC2 suite-shards/production-names: %r %r %r %r %r %r %r"
               % (unprefixed, from_runtime, foreign_file, unsafe, from_unit, runtime_first, templates),
               unprefixed == today
               and from_runtime.get("authority") == "veldo-authority-shard_a-%s.service" % service_id
               and from_runtime.get("api") == "veldo-api-shard_a-%s.service" % service_id
               and from_runtime.get("slice") == "veldo-workers_shard_a.slice"
               and from_runtime.get("scope", "").startswith("veldo-dispatch-shard_a-")
               and foreign_file == today and "invalid instance name" in unsafe.get("error", "")
               and from_unit == ["shard_a", "shard_a", "shard_a", "", ""] and runtime_first == "shard_b"
               # Nothing is written into an installation for the name: the installer is as it was.
               and not [word for word in ("INSTANCE_FILE", "instance_name", "instance.json")
                        if word in (ROOT / ".veldo" / "control_service.py").read_text()]
               and accepted == [True, True, False, False, False]
               and templates == {"veldo-authority.service": "a5da05e391fc6838", "veldo-api.service": "d24663f489bd528b"})

        # ==== AC3: every gate checks that isolation held, force-fresh or not ======================
        checked = []
        # A confined shard whose Landlock layer is skipped: the dispatcher copy of this tree never
        # stacks it. Every shard of the leg is a breach, in an ordinary gate.
        skipped = tree(top / "skipped", {"01_a": 'expect("a", True)\n', "02_b": 'expect("b", True)\n'})
        source = (skipped / "scripts/selftest.py").read_text()
        confine = ('    _in_force, _refused, _detail = RS.confine_shard(SHARD_ROOT_VALUES[0], RS.shard_launcher(HERE.parent))\n'
                   '    SHARD.send(event="layer", in_force=_in_force, refused=_refused, detail=_detail)\n')
        (skipped / "scripts/selftest.py").write_text(source.replace(confine, "    pass\n"))
        ran = through_dispatcher(skipped, leg_env("confined", "none_listed"))
        if not (source.count(confine) == 1 and ran.returncode == 1 and "isolation check FAILED: isolation_breach" in ran.stdout
                and ran.stdout.count("SELFTEST FAIL: suite-shard") == 2 and "suite-shard 01_a isolation_breach" in ran.stdout
                and "suite-shard 02_b isolation_breach" in ran.stdout and "selftest: 2 passed, 2 failed" in ran.stdout):
            checked.append("a skipped Landlock layer: exit %d, %r" % (ran.returncode, ran.stdout.splitlines()[-4:]))
        # A layer that reports itself in force while the probe beside the roots was written is a breach too.
        lying = tree(top / "lying", {"01_a": 'expect("a", True)\n'})
        (lying / "scripts/selftest.py").write_text(source.replace(
            confine, '    open(RS.shard_probe(SHARD_ROOT_VALUES[0]), "w").close()\n'
                     '    SHARD.send(event="layer", in_force=True, refused=True, detail="")\n'))
        ran = through_dispatcher(lying, leg_env("confined", "none_listed"))
        if not (ran.returncode == 1 and "its probe outside its roots was written" in ran.stdout):
            checked.append("a written probe: exit %d, %r" % (ran.returncode, ran.stdout.splitlines()[-3:]))
        # The only shards without a layer of their own are the ones the protected table names, each
        # with its reason, and the leg says so: such a shard is not charged, and writes where the
        # leg's domain lets it, while its neighbour is still confined to its roots.
        beside = top / "beside-the-roots"
        beside.mkdir()
        writes = ('target = Path(os.environ["V221_BESIDE"]) / suite_file().stem\n'
                  'try:\n    target.write_text("x")\n    wrote = True\nexcept PermissionError:\n    wrote = False\n'
                  'print("V221-BESIDE %s %s" % (suite_file().stem, wrote), flush=True)\nexpect("ran", True)\n')
        exempt = tree(top / "exempt", {"02_layered": writes, "03_layered": writes, "151_veldo_0313_space_run": writes})
        result, lines = shards(exempt, "confined", ["02_layered", "03_layered", "151_veldo_0313_space_run"],
                               extra={"V221_BESIDE": str(beside)})
        wrote = dict(line.split()[1:3] for line in lines if line.startswith("V221-BESIDE "))
        # IT RUNS ALONE: it is started first, beside nothing, and nothing is started until it ended,
        # though it is named last here and four may run at once.
        order = [(e["event"], e["suite"], e["running"], e.get("alone")) for e in result["events"]]
        if order[:2] != [("start", "151_veldo_0313_space_run", [], True), ("end", "151_veldo_0313_space_run", [], None)] \
                or [e[1] for e in order[2:] if e[0] == "start"] != ["02_layered", "03_layered"] \
                or order[3][:3] != ("start", "03_layered", ["02_layered"]):
            checked.append("the exempt shard did not run alone: %r" % order)
        if not (sorted(RS.UNLAYERED) == ["151_veldo_0313_space_run"] and all(len(r) > 80 for r in RS.UNLAYERED.values())
                and result["failed"] == 0 and wrote == {"151_veldo_0313_space_run": "True", "02_layered": "False",
                                                         "03_layered": "False"}
                and any("NO Landlock layer of its own" in line and "151_veldo_0313_space_run" in line for line in lines)
                and any("ran without a Landlock layer of its own" in line for line in lines)):
            checked.append("the exempt shard: %r %r %r" % (wrote, result["charged"], sorted(RS.UNLAYERED)))
        # An unconfined shard that leaves a file in /dev/shm, one that starts a unit without its
        # prefix (and stops it again), and one that leaves a unit of its own behind. The fixture's
        # own directory and unit list stand for /dev/shm and the manager: the gate runs this suite
        # inside its confinement, where the real ones are out of reach. EVENT SYNCHRONIZED: the
        # fixture manager writes down every name it has ever listed, and the suite that starts and
        # stops a unit stops it only once the dispatcher has read it.
        shm, unit_list, listed_once = top / "fixture-dev-shm", top / "fixture-units", top / "fixture-units-read"
        descriptions = top / "fixture-descriptions"
        shm.mkdir()
        places = [{"name": "/dev/shm", "path": shm, "depth": 1, "rule": "strict"}]

        def listed_units():
            found = unit_list.read_text().split()
            with open(listed_once, "a") as handle:
                handle.write("".join(name + "\n" for name in found))
            return found

        def described(unit):
            return json.loads(descriptions.read_text()).get(unit, "") if descriptions.exists() else ""
        mine = ('import json\ninstance = json.loads(Path(os.environ["XDG_RUNTIME_DIR"], "veldo-instance.json").read_text())["prefix"]\n'
                'def add(unit, text=""):\n'
                '    known = json.loads(Path(os.environ["V221_DESCRIPTIONS"]).read_text())\n'
                '    known[unit] = text\n    Path(os.environ["V221_DESCRIPTIONS"]).write_text(json.dumps(known))\n'
                '    with open(os.environ["V221_UNITS"], "a") as handle:\n        handle.write(unit + "\\n")\n')
        bodies = {
            "01_clean": 'expect("clean", True)\n',
            "02_leaves_shm": ('Path(os.environ["V221_SHM"], "left-behind").write_text("made by %s" % os.environ["HOME"])\n'
                              'expect("left a file", True)\n'),
            # An engine-shaped unit with no prefix, whose command stands in this shard's home: started,
            # read by the dispatcher, stopped again. It is gone at the leg's end and still a breach.
            "03_starts_unit": mine + (
                'import time\nunit = "veldo-authority-0123456789abcdef.service"\n'
                'add(unit, "ExecStart=%s/bin/veldo-authority" % os.environ["HOME"])\n'
                'limit = time.monotonic() + 600\nread = Path(os.environ["V221_READ"])\n'
                'while unit not in (read.read_text().split() if read.exists() else []) and time.monotonic() < limit:\n'
                '    time.sleep(0.01)\n'
                'kept = [name for name in Path(os.environ["V221_UNITS"]).read_text().split() if name != unit]\n'
                'Path(os.environ["V221_UNITS"]).write_text("".join(name + "\\n" for name in kept))\n'
                'expect("started a unit without my prefix and stopped it", True)\n'),
            "04_prefixed_unit": mine + ('add("veldo-authority-%s-0123456789abcdef.service" % instance)\n'
                                        'expect("left its own unit", True)\n'),
            "05_tidy": ('target = Path(os.environ["V221_SHM"], "tidied")\ntarget.write_text("x")\ntarget.unlink()\n'
                        'expect("made and removed a file", True)\n'),
            # A unit that is not the engine's, tied to this shard by its command, and left behind.
            "06_leaves_scope": mine + ('add("run-u4242.scope", "WorkingDirectory=%s" % os.environ["TMPDIR"])\n'
                                       'expect("left a scope of its own", True)\n'),
        }
        leaky = tree(top / "leaky", bodies)
        fixture_env = {"V221_SHM": str(shm), "V221_UNITS": str(unit_list), "V221_READ": str(listed_once),
                       "V221_DESCRIPTIONS": str(descriptions)}

        def reset():
            for path in shm.iterdir():
                path.unlink()
            unit_list.write_text("existing.service\n")
            listed_once.write_text("")
            descriptions.write_text("{}")
        for force in (None, "0"):
            reset()
            extra = dict(fixture_env, **({"VELDO_GATE_FORCE_FRESH": force} if force is not None else {}))
            result, lines = shards(leaky, "unconfined", list(bodies), listed=",".join(bodies), places=places,
                                   units=listed_units, describe=described, parallel=1, tick=0.02, extra=extra)
            got = {name: codes(result, name) for name in bodies}
            words = {name: [w for _c, w in result["charged"].get(name, [])] for name in bodies}
            if got != {"01_clean": [], "02_leaves_shm": ["isolation_breach"], "03_starts_unit": ["isolation_breach"],
                       "04_prefixed_unit": ["isolation_breach"], "05_tidy": [], "06_leaves_scope": ["isolation_breach"]}:
                checked.append("force-fresh %r: charged %r" % (force, got))
                continue
            if not ("left-behind" in words["02_leaves_shm"][0]
                    and "veldo-authority-0123456789abcdef.service was started without its shard's prefix"
                    in words["03_starts_unit"][0]
                    and "veldo-authority-0123456789abcdef.service" not in unit_list.read_text()
                    and "its name carries the shard's instance name" in words["04_prefixed_unit"][0]
                    and "run-u4242.scope was left behind" in words["06_leaves_scope"][0]
                    and result["failed"] == 4 and result["passed"] == 6 and RS.LEG_OWNER not in result["charged"]
                    and any("isolation check FAILED: isolation_breach" in line for line in lines)):
                checked.append("force-fresh %r: breaches not named: %r" % (force, words))
        # THE SHARDS WITH NO INSTANCE NAME are the three the protected table names, each with its
        # reason, and the leg says so. Such a shard's engine names are today's, a unit it starts and
        # stops again is not a breach for lacking a prefix it was never given, and one it leaves
        # behind still is, tied to it by its roots.
        reset()
        unnamed_bodies = {
            "86_veldo_0189_engine_upgrade": bodies["03_starts_unit"].replace(
                'instance = json.loads(Path(os.environ["XDG_RUNTIME_DIR"], "veldo-instance.json").read_text())["prefix"]\n',
                'print("V221-UNNAMED %s" % Path(os.environ["XDG_RUNTIME_DIR"], "veldo-instance.json").exists(), flush=True)\n'),
            "117_veldo_0227_ui_location": (
                bodies["06_leaves_scope"].replace(
                    'instance = json.loads(Path(os.environ["XDG_RUNTIME_DIR"], "veldo-instance.json").read_text())["prefix"]\n', "")
                .replace("run-u4242.scope", "veldo-authority-fedcba9876543210.service")),
        }
        unnamed = tree(top / "unnamed", unnamed_bodies)
        result, lines = shards(unnamed, "unconfined", list(unnamed_bodies), listed=",".join(unnamed_bodies), places=places,
                               units=listed_units, describe=described, parallel=1, tick=0.02, extra=fixture_env)
        left = [w for _c, w in result["charged"].get("117_veldo_0227_ui_location", [])]
        if not (sorted(RS.UNNAMED) == ["106_veldo_0185_dispatch_setup", "117_veldo_0227_ui_location",
                                       "127_veldo_0234_https_port", "85_veldo_0171_setup_api",
                                       "86_veldo_0189_engine_upgrade", "91_veldo_0167_setup_records"]
                and all(len(reason) > 80 for reason in RS.UNNAMED.values())
                and "V221-UNNAMED False" in lines and codes(result, "86_veldo_0189_engine_upgrade") == []
                and len(left) == 1 and "veldo-authority-fedcba9876543210.service was left behind" in left[0]
                and sum("ran without an instance name" in line for line in lines) == 2):
            checked.append("the unnamed shards: %r %r" % (result["charged"], [l for l in lines if "V221" in l or "instance name" in l]))
        # A clean unconfined leg holds.
        reset()
        result, lines = shards(leaky, "unconfined", ["01_clean", "05_tidy"], listed="01_clean,05_tidy", places=places,
                               units=listed_units, describe=described, extra=fixture_env)
        if result["failed"] or not any("isolation check held" in line for line in lines):
            checked.append("a clean leg did not hold: %r" % result["charged"])
        # The shared places of the real unconfined leg are the ones the specification names.
        real = {p["name"]: (str(p["path"]), p["rule"]) for p in RS.unconfined_places(top / "vs-fixture")}
        import pwd
        home = pwd.getpwuid(os.getuid()).pw_dir
        if real != {"systemd configuration": (home + "/.config/systemd/user", "strict"),
                    "runtime directory": ("/run/user/%d" % os.getuid(), "strict"),
                    "runtime unit directory": ("/run/user/%d/systemd/user" % os.getuid(), "strict"),
                    "/dev/shm": ("/dev/shm", "strict"), "temporary directory": (str(top), "attributed"),
                    "owner cache": (home + "/.cache/veldo", "strict"),
                    "owner state": (home + "/.local/state/veldo", "strict")}:
            checked.append("the real shared places are %r" % real)
        expect("VELDO-0221 AC3 suite-shards/isolation-checked: " + "; ".join(checked), not checked)

        # ONLY THIS INSTANCE'S UNITS ARE JUDGED. While a clean leg runs, another session starts and
        # leaves units on the one manager: another leg's shard of the same suite (another token), an
        # installation with no instance at all, a transient service and a slice. None refers to this
        # leg's roots, so none is charged and the leg is green; each is named on the summary.
        reset()
        foreign = ["veldo-authority-0a1b2c3d00_01_clean-0123456789abcdef.service",
                   "veldo-authority-fedcba9876543210.service", "veldo-workers_0a1b2c3d00_01_clean.slice",
                   "run-u777.service", "v0a1b2c3d.slice"]
        descriptions.write_text(json.dumps({name: "ExecStart=/somewhere/else/bin/x" for name in foreign}))
        calls = [0]

        def busy_manager():
            calls[0] += 1
            if calls[0] == 2:  # after the leg's first reading: these appeared DURING the leg
                with open(unit_list, "a") as handle:
                    handle.write("".join(name + "\n" for name in foreign))
            return listed_units()
        result, lines = shards(leaky, "unconfined", ["01_clean", "05_tidy"], listed="01_clean,05_tidy", places=places,
                               units=busy_manager, describe=described, extra=fixture_env, tick=0.02)
        expect("VELDO-0221 AC3 suite-shards/other-sessions-units-are-not-judged: %r %r %r"
               % (result["charged"], result["strangers"], lines[-3:]),
               result["failed"] == 0 and result["passed"] == 2 and result["strangers"] == sorted(foreign)
               and not result["breaches"] and any("isolation check held" in line for line in lines)
               and any("5 unit(s) appeared during the leg that nothing ties to this instance" in line for line in lines))

        # THE RULE FOR A FILE NOBODY CAN BE TIED TO, IN A STRICT PLACE (every shared place but the top
        # of the system temporary directory): it fails the leg's isolation check, by name, with the
        # suites that ran when it appeared, and is never silently allowed. EVENT SYNCHRONIZED: the
        # entry is made at the dispatcher's own second reading of its clock, which is after it started
        # its first shards and before it read the place again. One the leg can tie to a shard is
        # charged to that shard instead.
        temporary_top = top / "fixture-tmp"
        temporary_top.mkdir()
        strict_place = [{"name": "/dev/shm", "path": temporary_top, "depth": 1, "rule": "strict"}]
        tmp_place = [{"name": "temporary directory", "path": temporary_top, "depth": 1, "rule": "attributed"}]
        readings = [0]

        def orphaning_clock():
            readings[0] += 1
            if readings[0] == 2:
                (temporary_top / "orphan-entry").write_text("nothing ties this to a shard")
            return time.monotonic()

        def emptied():
            for entry in temporary_top.iterdir():
                entry.unlink()
            readings[0] = 0
        tmp_bodies = {"01_a": 'expect("a", True)\n', "02_b": 'expect("b", True)\n',
                      "03_refers": ('Path(os.environ["V221_TMP"], "refers").write_text("made in %s" % os.environ["HOME"])\n'
                                    'expect("left a file that names my home", True)\n')}
        tmp_tree = tree(top / "tmp-rule", tmp_bodies)
        result, lines = shards(tmp_tree, "unconfined", list(tmp_bodies), listed=",".join(tmp_bodies), places=strict_place,
                               clock=orphaning_clock, extra={"V221_TMP": str(temporary_top)})
        leg_words = [w for _c, w in result["charged"].get(RS.LEG_OWNER, [])]
        # One shard alone in the leg when the entry appears is still not charged with it: who ran
        # when it appeared is not attribution (another session's file once named the wrong suite).
        emptied()
        lone, _ = shards(tmp_tree, "unconfined", ["01_a"], listed="01_a", places=strict_place, clock=orphaning_clock,
                         extra={"V221_TMP": str(temporary_top)})
        lone_words = [w for _c, w in lone["charged"].get(RS.LEG_OWNER, [])]
        expect("VELDO-0221 AC3 suite-shards/unattributed-entry-fails-the-leg: %r %r" % (result["charged"], lines[-6:]),
               len(leg_words) == 1 and "orphan-entry" in leg_words[0] and "could be tied to no shard" in leg_words[0]
               and "01_a, 02_b, 03_refers" in leg_words[0]
               and codes(result, "03_refers") == ["isolation_breach"] and codes(result, "01_a") == []
               and codes(result, "02_b") == [] and (result["passed"], result["failed"]) == (3, 2)
               and [line for line in lines if RS.FAIL_MARK in line]
               == ["  %s suite-shard 03_refers isolation_breach" % RS.FAIL_MARK,
                   "  %s suite-shard-leg unconfined isolation_breach" % RS.FAIL_MARK]
               and not [line for line in lines if "not charged" in line and "orphan-entry" in line]
               and not result["recorded"]
               and codes(lone, "01_a") == [] and len(lone_words) == 1 and "orphan-entry" in lone_words[0]
               and lone_words[0].endswith("first appeared: 01_a") and (lone["passed"], lone["failed"]) == (1, 1))

        # THE TOP OF THE SYSTEM TEMPORARY DIRECTORY (lead decision 2026-11-21, revised: other sessions
        # of a shared host leave files there all the time). The same entry, tied to nothing, in the
        # place with the rule "attributed": it fails no shard and not the leg. It is recorded in the
        # leg's result and shown on its output with the suites that ran when it appeared.
        emptied()
        result, lines = shards(tmp_tree, "unconfined", ["01_a", "02_b"], listed="01_a,02_b", places=tmp_place,
                               clock=orphaning_clock, extra={"V221_TMP": str(temporary_top)})
        shown = [line for line in lines if "orphan-entry" in line]
        expect("VELDO-0221 AC3 suite-shards/unattributed-temporary-entry-is-recorded-not-charged: %r %r %r"
               % (result["charged"], result["recorded"], lines[-5:]),
               (result["passed"], result["failed"]) == (2, 0) and not result["charged"] and not result["breaches"]
               and result["recorded"] == [{"place": "temporary directory", "path": str(temporary_top / "orphan-entry"),
                                           "suspects": ["01_a", "02_b"]}]
               and len(shown) == 1 and "isolation record, tied to no shard and not charged" in shown[0]
               and shown[0].endswith("first appeared: 01_a, 02_b")
               and any("isolation check held" in line for line in lines)
               and not [line for line in lines if RS.FAIL_MARK in line])

        # A SHARD'S OWN ENTRY THERE STILL FAILS IT, by each of the three ties: its text names the
        # shard's private roots; its name carries the shard's instance name; a process of the shard's
        # own tree holds it. The third shard's child is given an empty environment and a file whose
        # name and text say nothing, so only the tree ties it; the suite ends only after the child
        # wrote that it holds the file (event synchronized), and the dispatcher reads the place before
        # it ends what the suite left running. The orphan beside them is recorded as before, and the
        # two clean shards are charged nothing.
        emptied()
        leak_bodies = dict(tmp_bodies)
        leak_bodies["04_named"] = (
            'import json\n'
            'mine = json.loads(Path(os.environ["XDG_RUNTIME_DIR"], "veldo-instance.json").read_text())["prefix"]\n'
            'Path(os.environ["V221_TMP"], "left-" + mine).write_text("x")\n'
            'expect("left a file that carries my instance name", True)\n')
        leak_bodies["05_held"] = (
            'import subprocess\n'
            'holder = ("import sys, time\\nhandle = open(sys.argv[1], \'w\')\\nprint(\'held\', flush=True)\\n"\n'
            '          "time.sleep(600)\\n")\n'
            'child = subprocess.Popen([sys.executable, "-c", holder, os.path.join(os.environ["V221_TMP"], "held-entry")],\n'
            '                         env={}, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,\n'
            '                         text=True)\n'
            'expect("my child holds a file at the top", child.stdout.readline().strip() == "held")\n')
        leak_tree = tree(top / "tmp-leak", leak_bodies)
        result, lines = shards(leak_tree, "unconfined", list(leak_bodies), listed=",".join(leak_bodies), places=tmp_place,
                               clock=orphaning_clock, extra={"V221_TMP": str(temporary_top)}, parallel=5)
        words = {name: [w for _c, w in result["charged"].get(name, [])] for name in leak_bodies}
        left = sorted(entry.name for entry in temporary_top.iterdir())
        expect("VELDO-0221 AC3 suite-shards/own-temporary-entry-fails-its-shard: %r %r %r"
               % (result["charged"], result["recorded"], left),
               (result["passed"], result["failed"]) == (5, 3) and RS.LEG_OWNER not in result["charged"]
               and [codes(result, name) for name in sorted(leak_bodies)]
               == [[], [], ["isolation_breach"], ["isolation_breach"], ["isolation_breach"]]
               and len(words["03_refers"]) == 1 and "it refers to a shard's roots" in words["03_refers"][0]
               and len(words["04_named"]) == 1 and "its name carries the shard's instance name" in words["04_named"][0]
               and len(words["05_held"]) == 1 and "held-entry" in words["05_held"][0]
               and "a process of the shard's own tree held it when it appeared" in words["05_held"][0]
               and [entry["path"] for entry in result["recorded"]] == [str(temporary_top / "orphan-entry")]
               and sorted(line for line in lines if RS.FAIL_MARK in line)
               == ["  %s suite-shard %s isolation_breach" % (RS.FAIL_MARK, name)
                   for name in ("03_refers", "04_named", "05_held")]
               and any("isolation check FAILED" in line for line in lines)
               and len(left) == 4 and "held-entry" in left and "orphan-entry" in left and "refers" in left)

        # An item is charged to the shard it can be tied to, and what cannot be the leg's is not.
        jobs = [{"name": "01_first", "index": 0}, {"name": "02_second", "index": 1}]
        base = top / "vs-attribution"
        (base / "01h").mkdir(parents=True)
        place = top / "attribution-place"
        place.mkdir()
        (place / "plain").write_text("nothing here")
        (place / "refers").write_text("ExecStart=%s/01h/bin/run\n" % base)
        os.symlink(base / "01h", place / "link")
        (place / "named-02_second").write_text("x")
        told = {name: RS.attribute("place", name, place / name, base, jobs)[:2]
                for name in ("plain", "refers", "link", "named-02_second")}
        # A live process holds the item: one that carries a shard's roots makes it that shard's, and
        # one of another tree makes it foreign. Each holder says it has opened the file before it is asked.
        holds = ('import sys\nhandle = open(sys.argv[1])\nprint("held", flush=True)\nsys.stdin.read()\n')

        def held_by(environment):
            process = subprocess.Popen([sys.executable, "-c", holds, str(place / "plain")], env=environment,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            try:
                process.stdout.readline()
                return RS.attribute("place", "plain", place / "plain", base, jobs)[:2]
            finally:
                process.stdin.close()
                process.wait()
        holder = (held_by(dict(plain, HOME=str(top))), held_by(dict(plain, HOME=str(base / "01h"))))
        by_unit = RS.attribute("unit", "run-u7.scope", None, base, jobs,
                               lambda unit: "WorkingDirectory=%s/00\nExecStart=%s/011/x" % (base, base))
        expect("VELDO-0221 suite-shards/attribution: %r %r %r" % (told, holder, by_unit),
               told == {"plain": (None, "unknown"), "refers": ("02_second", "leg"), "link": ("02_second", "leg"),
                        "named-02_second": ("02_second", "leg")}
               and holder == ((None, "foreign"), ("02_second", "leg")) and by_unit[:2] == ("01_first", "leg"))

        # ==== AC4: shards claim from the gate-wide ledger; an exclusive manager suite runs alone ====
        lock = top / "manager.lock"
        lock.write_text("")
        user = ('import fcntl\nhandle = open(os.environ["V221_LOCK"])\n'
                'try:\n    fcntl.flock(handle, fcntl.%s | fcntl.LOCK_NB)\n    alone = True\n'
                'except BlockingIOError:\n    alone = False\n'
                'expect("the manager is mine as declared", alone)\n'
                'print("V221-HELD %%s" %% suite_file().stem, flush=True)\n')
        managed = tree(top / "managed", {
            "01_exclusive": user % "LOCK_EX", "02_shared": user % "LOCK_SH", "03_shared": user % "LOCK_SH",
            "04_exclusive": user % "LOCK_EX", "05_shared": user % "LOCK_SH", "06_none": 'expect("no manager", True)\n',
        }, resources={"01_exclusive": {"systemd_user_manager": "exclusive"}, "02_shared": {"systemd_user_manager": 1},
                      "03_shared": {"systemd_user_manager": 1}, "04_exclusive": {"systemd_user_manager": "exclusive"},
                      "05_shared": {"systemd_user_manager": 1}}, capacities={"systemd_user_manager": 16})
        ours, theirs = socket.socketpair()
        asked = []

        def serve():
            stream = ours.makefile("rwb", buffering=0)
            refusals = {"06_none": 2}  # the ledger refuses this claim twice before it grants it
            for line in stream:
                request = json.loads(line)
                asked.append(request)
                granted = True
                if request["operation"] == "acquire" and refusals.get(request["name"], 0):
                    refusals[request["name"]] -= 1
                    granted = False
                stream.write((json.dumps({"granted": granted, "resource": None if granted else "cpu"}) + "\n").encode())
        server = threading.Thread(target=serve, daemon=True)
        server.start()
        measured = {"02_shared": {"cpu": 2.5, "memory": 300000000, "seconds": 9.0},
                    "bad": {"cpu": -1, "memory": 1}}
        try:
            result, lines = shards(
                managed, "unconfined",
                ["01_exclusive", "02_shared", "03_shared", "04_exclusive", "05_shared", "06_none"],
                listed="01_exclusive,02_shared,03_shared,04_exclusive,05_shared,06_none", tick=0.05, parallel=None,
                extra={"V221_LOCK": str(lock), "VELDO_GATE_SHARD_LEDGER_FD": str(theirs.fileno()),
                       "VELDO_GATE_SHARD_CLAIMS": json.dumps(measured)})
        finally:
            theirs.close()
            ours.close()
        managers = {"01_exclusive", "02_shared", "03_shared", "04_exclusive", "05_shared"}
        exclusives = {"01_exclusive", "04_exclusive"}
        overlaps = []
        for event in result["events"]:
            if event["event"] != "start":
                continue
            beside = set(event["running"]) & managers
            if (event["suite"] in exclusives and beside) or (event["suite"] in managers and beside & exclusives):
                overlaps.append("%s started beside %s" % (event["suite"], sorted(beside)))
        starts = [e["suite"] for e in result["events"] if e["event"] == "start"]
        claims = {r["name"]: r["claim"] for r in asked if r["operation"] == "acquire"}
        acquired = [r["name"] for r in asked if r["operation"] == "acquire"]
        released = sorted(r["name"] for r in asked if r["operation"] == "release")
        shared_together = any(e["event"] == "start" and e["suite"] in managers - exclusives
                              and set(e["running"]) & (managers - exclusives) for e in result["events"])
        expect("VELDO-0221 AC4 suite-shards/manager-exclusive: %r %r failed=%d %r"
               % (overlaps, starts, result["failed"], result["charged"]),
               not overlaps and sorted(starts) == sorted(managers | {"06_none"}) and result["failed"] == 0
               and result["passed"] == 6 and shared_together)
        expect("VELDO-0221 AC4 suite-shards/ledger-claims: %r" % claims,
               released == sorted(managers | {"06_none"})
               and claims["02_shared"]["cpu"] == 2.5 and claims["02_shared"]["memory"] == 300000000
               and claims["01_exclusive"]["cpu"] == RS.SHARD_UNMEASURED["cpu"]
               and claims["01_exclusive"]["memory"] == RS.SHARD_UNMEASURED["memory"]
               and all(c["manager"] == "none" and c["ports"] == [] for c in claims.values())
               and acquired.count("06_none") == 3 and result["parallelism"] is None
               # The measured suite is the longest known, so it is asked for after the unmeasured ones.
               and RS.handed_claims({"VELDO_GATE_SHARD_CLAIMS": json.dumps(measured)}) == {"02_shared": measured["02_shared"]})

        # The gate ledger's own channel stays with the authority's leg runner, which asks it for each
        # shard with ITS measured claim. Whatever size a candidate names is not read, and nothing but a
        # checked suite name is forwarded.
        gate_side, runner_side = socket.socketpair()
        forwarded = []

        def gate_ledger():
            stream = gate_side.makefile("rwb", buffering=0)
            for line in stream:
                request = json.loads(line)
                forwarded.append(request)
                stream.write((json.dumps({"granted": request["name"] != "03_refused"}) + "\n").encode())
        threading.Thread(target=gate_ledger, daemon=True).start()
        asking = GL.ShardClaims(runner_side.fileno(), {"01_a": {"cpu": 2.5, "memory": 5000, "seconds": 10.0}})
        client = RS.ShardLedger(asking.fileno())
        answers = [client.acquire("01_a", {"cpu": 99.0, "memory": 1}), client.acquire("02_new", RS.SHARD_UNMEASURED),
                   client.acquire("03_refused", RS.SHARD_UNMEASURED)]
        for operation, name in (("acquire", "../x"), ("acquire", "01_a"), ("release", "04_never"), ("handoff", "01_a")):
            try:
                client.request(operation, name)
                answers.append("answered")
            except RS.LegRefused:
                answers.append("refused")
        client.release("01_a")
        client.close()
        asking.close()
        gate_side.close()
        runner_side.close()
        seen = [(r["operation"], r["name"], (r["claim"] or {}).get("cpu"), (r["claim"] or {}).get("memory"))
                for r in forwarded]
        expect("VELDO-0221 AC4 suite-shards/ledger-stays-with-the-leg-runner: %r %r" % (answers, seen),
               answers == [True, True, False, "refused", "refused", "refused", "refused"]
               and seen == [("acquire", "01_a", 2.5, 5000), ("acquire", "02_new", 1.0, 1 << 30),
                            ("acquire", "03_refused", 1.0, 1 << 30), ("release", "01_a", None, None),
                            # what the dispatcher still held when the leg ended is released for it
                            ("release", "02_new", None, None)])

        # What the authority's leg runner hands a leg and keeps from a candidate.
        store = top / "store"
        text = "\n".join([json.dumps({"suite": "01_a", "wall_seconds": 10.0, "cpu_seconds": 25.0, "peak_anon_bytes": 5000}),
                          json.dumps({"suite": "02_b", "wall_seconds": 100.0, "cpu_seconds": 1.0, "peak_anon_bytes": 7000}),
                          json.dumps({"suite": "../x", "wall_seconds": 1.0, "cpu_seconds": 1.0, "peak_anon_bytes": 1}),
                          json.dumps({"suite": "03_c", "wall_seconds": 0, "cpu_seconds": 1.0, "peak_anon_bytes": 1}),
                          "not json"])
        first = GL.shard_measurements(text)
        GL.record_shard_claims(store, digest, "confined", first)
        GL.record_shard_claims(store, digest, "confined", {"01_a": {"cpu": 1.0, "memory": 9000, "seconds": 12.0}})
        kept = GL.read_shard_claims(store, digest, "confined")
        saved = dict(os.environ)
        try:
            os.environ.update({"VELDO_GATE_SHARD_CLAIMS": '{"forged": {"cpu": 99}}', "VELDO_GATE_SHARD_METRICS_FD": "7",
                               "VELDO_GATE_LEDGER_FD": "8", "VELDO_GATE_SHARD_LEDGER_FD": "9"})
            handed = GL._env("confined", ["a"], digest, None, kept)
            bare_env = GL._env()
        finally:
            os.environ.clear()
            os.environ.update(saved)
        # The first-use check hands its nested dispatcher the channels it inherited in a leg, and none
        # outside one. Asked of the shipped file in a process of its own, which holds a real pipe.
        asks = ('import importlib.util, json, os, sys\n'
                'spec = importlib.util.spec_from_file_location("first_use", sys.argv[1])\n'
                'module = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(module)\n'
                'fd = sys.argv[2]\n'
                'print(json.dumps([list(module.shard_fds({"VELDO_GATE_LEG": "confined", "VELDO_GATE_SHARD_LEDGER_FD": fd, '
                '"VELDO_GATE_SHARD_METRICS_FD": "not-a-number"})), list(module.shard_fds({"VELDO_GATE_SHARD_LEDGER_FD": fd})), '
                'list(module.shard_fds({"VELDO_GATE_LEG": "confined", "VELDO_GATE_SHARD_LEDGER_FD": "987654"}))]))\n')
        read_end, write_end = os.pipe()
        try:
            answer = subprocess.run([sys.executable, "-c", asks, str(ROOT / "scripts" / "check_first_use.py"),
                                     str(write_end)], capture_output=True, text=True, timeout=600, env=plain,
                                    stdin=subprocess.DEVNULL, pass_fds=(write_end,))
            passed_on = json.loads(answer.stdout) if answer.returncode == 0 else answer.stderr[-300:]
        finally:
            os.close(read_end)
            os.close(write_end)
        AS = load(ROOT / "scripts" / "agent_sandbox.py", "v221_agent_sandbox")
        # The gate launcher and the dispatcher share the same fixed placement rule.
        # These are real directories inside this run's grant, never account-wide fixtures.
        F = AS.FIXTURES
        F.socket_paths({'boundary': '/' + 'x' * 106})
        socket_refusals = []
        for name, path in (('boundary', '/' + 'x' * 107), ('encoded', '/' + '\u00e9' * 54)):
            try:
                F.socket_paths({name: path})
            except F.FixtureRefused as error:
                socket_refusals.append(str(error).startswith('gate_fixture_root_socket_too_long: ' + name + ':'))
        expect('VELDO-0221 gate-fixtures/socket-byte-boundary', socket_refusals == [True, True])
        original_bind = socket.socket.bind
        stop_watching = F.watch_sockets(top)
        try:
            with socket.socket(socket.AF_UNIX) as listener:
                try:
                    listener.bind(str(top / ('x' * 108)))
                    bind_refused = False
                except F.FixtureRefused as error:
                    bind_refused = str(error).startswith('gate_fixture_root_socket_too_long: bind:')
        finally:
            stop_watching()
        expect('VELDO-0221 gate-fixtures/dynamic-socket-preflight',
               bind_refused and socket.socket.bind is original_bind)
        with AS.gate_fixture_directory('gate', top / 'store', []) as allocated:
            print('VELDO-0221 gate-fixtures: parent=%s; /var/lib/veldo exists=%s'
                  % (allocated.parent, Path('/var/lib/veldo').exists()))
            expect('VELDO-0221 gate-fixtures/default-owned-private',
                   allocated.is_dir() and allocated.stat().st_uid == os.getuid()
                   and allocated.stat().st_mode & 0o777 == 0o700)
            with patch.object(F, 'ENVIRONMENT', {'XDG_STATE_HOME': str(allocated / 'state')}):
                with AS.gate_fixture_directory('gate', top / 'store', []) as default:
                    expect('VELDO-0221 gate-fixtures/xdg-default',
                           default.parent == allocated / 'state/vg'
                           and default.parent.stat().st_mode & 0o777 == 0o700)
            from types import SimpleNamespace
            with patch.object(F.pwd, 'getpwuid', return_value=SimpleNamespace(pw_dir=str(allocated))), \
                    patch.object(F, 'ENVIRONMENT', {}):
                with AS.gate_fixture_directory('gate', top / 'store', []) as default:
                    expect('VELDO-0221 gate-fixtures/account-default',
                           default.parent == allocated / '.vg')
            linked_home = allocated / 'home-link'
            linked_home.symlink_to(allocated, target_is_directory=True)
            with patch.object(F.pwd, 'getpwuid', return_value=SimpleNamespace(pw_dir=str(linked_home))), \
                    patch.object(F, 'ENVIRONMENT', {}):
                with AS.gate_fixture_directory('gate', top / 'store', []) as default:
                    expect('VELDO-0221 gate-fixtures/symlink-account-home',
                           default.parent == allocated / '.vg')
            with patch.object(F, 'ENVIRONMENT', {'XDG_STATE_HOME': str(linked_home / 'state')}):
                with AS.gate_fixture_directory('gate', top / 'store', []) as default:
                    expect('VELDO-0221 gate-fixtures/symlink-xdg-default',
                           default.parent == allocated / 'state/vg')
            with patch.object(F, 'ENVIRONMENT', {'VELDO_FIXTURE_PARENT': str(linked_home / 'configured')}):
                try:
                    with AS.gate_fixture_directory('gate', top / 'store', []):
                        configured_link_refused = False
                except F.FixtureRefused as error:
                    configured_link_refused = str(error).startswith('gate_fixture_root_invalid_path:')
            expect('VELDO-0221 gate-fixtures/configured-symlink-still-refused', configured_link_refused)
            configured = allocated / 'configured'
            source = {'VELDO_FIXTURE_PARENT': str(configured)}
            with patch.object(F, 'ENVIRONMENT', source):
                with AS.gate_fixture_directory('gate', top / 'store', []) as outer_root:
                    marker = configured / 'keep'
                    marker.write_text('outside cleanup')
                    (outer_root / 'link').symlink_to(configured, target_is_directory=True)
                    shut = outer_root / 'shut'
                    shut.mkdir()
                    (shut / 'file').write_text('inside cleanup')
                    shut.chmod(0o500)
                    with patch.object(F, 'ENVIRONMENT', dict(source, VELDO_FIXTURE_ROOT=str(outer_root))):
                        with AS.gate_fixture_directory('gate', top / 'store', []) as nested:
                            expect('VELDO-0221 gate-fixtures/nested', nested.parent == outer_root)
                    expect('VELDO-0221 gate-fixtures/nested-cleanup', not nested.exists())
                expect('VELDO-0221 gate-fixtures/cleanup-stays-inside-root',
                       not outer_root.exists() and marker.read_text() == 'outside cleanup')
            problems = []
            bad_mode = allocated / 'public'
            bad_mode.mkdir(mode=0o755)
            bad_mode.chmod(0o755)
            fake = allocated / 'foreign'
            fake.mkdir(mode=0o700)
            wrong_owner = fake.stat()
            def owner_info(path):
                if path == fake:
                    return SimpleNamespace(st_mode=wrong_owner.st_mode, st_uid=os.getuid() + 1)
                return original_lstat(path)
            original_lstat = Path.lstat
            for name, env, protected in (
                    ('temporary', {'VELDO_FIXTURE_PARENT': str(top / 'bad')}, []),
                    ('mode', {'VELDO_FIXTURE_PARENT': str(bad_mode)}, []),
                    ('owner', {'VELDO_FIXTURE_PARENT': str(fake)}, []),
                    ('outside', dict(source, VELDO_FIXTURE_ROOT=str(allocated)), []),
                    ('not-allocation', dict(source, VELDO_FIXTURE_ROOT=str(configured / 'keys')), []),
                    ('protected', source, [configured]),
                    ('unavailable', {'VELDO_FIXTURE_PARENT': str(marker / 'child')}, [])):
                with patch.object(F, 'ENVIRONMENT', env), patch.object(Path, 'lstat', owner_info):
                    try:
                        with AS.gate_fixture_directory('gate', top / 'store', protected):
                            problems.append(name + ': accepted')
                    except F.FixtureRefused as error:
                        if not str(error).startswith('gate_fixture_root_'):
                            problems.append(name + ': unnamed')
            expect('VELDO-0221 gate-fixtures/refused-placement-mode-owner-overlap', not problems)
            with patch.object(F, 'ENVIRONMENT', {}):
                with AS.gate_fixture_directory('gate', top / 'store', [], configured=str(configured)) as explicit:
                    expect('VELDO-0221 gate-fixtures/installation-setting', explicit.parent == configured)
            with patch.dict(os.environ, VELDO_FIXTURE_ROOT=str(top / 'redirect'),
                            VELDO_FIXTURE_PARENT=str(top / 'redirect')):
                with AS.gate_fixture_directory('gate', top / 'store', []) as pinned:
                    expect('VELDO-0221 gate-fixtures/environment-is-pinned', pinned.parent == allocated.parent)
            with RS.fixture_stand() as pinned:
                expect('VELDO-0221 gate-fixtures/dispatcher-pinned-parent', Path(pinned).parent == allocated.parent)
        expect('VELDO-0221 gate-fixtures/default-cleanup', not allocated.exists())
        allocation_tree = tree(top / 'allocation-tree', {'01_ok': 'expect("fixture/ok", True)\n'})
        result, _lines = shards(allocation_tree, 'confined', ['01_ok'], extra={
            'VELDO_FIXTURE_ROOT': str(top / 'redirect'), 'VELDO_FIXTURE_PARENT': str(top / 'redirect')})
        expect('VELDO-0221 gate-fixtures/run-environment-cannot-redirect',
               result['failed'] == 0 and not (top / 'redirect').exists())
        refused = through_dispatcher(allocation_tree, dict(leg_env('confined', 'none_listed'),
                                     VELDO_FIXTURE_PARENT='relative-fixture-parent'))
        expect('VELDO-0221 gate-fixtures/dispatcher-named-refusal-no-traceback',
               refused.returncode == 2 and 'gate_fixture_root_invalid_path' in refused.stdout
               and 'Traceback' not in refused.stdout + refused.stderr)
        # The launcher's broker refuses a shard's bind outside the shard's own roots: it finds the
        # caller's shard by ancestry and reads the roots the dispatcher started that shard with.
        broker = AS.Broker.__new__(AS.Broker)
        shard_like = ('import os, sys, subprocess\n'
                      'child = subprocess.Popen([sys.executable, "-c", "import sys; print(\'up\', flush=True); sys.stdin.read()"],\n'
                      '                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, env={"PATH": os.environ["PATH"]})\n'
                      'child.stdout.readline()\nprint(child.pid, flush=True)\nsys.stdin.read()\nchild.stdin.close()\nchild.wait()\n')
        shard_roots = {name.decode(): str(top / "broker" / name.decode().lower()) for name in AS.Broker.SHARD_ROOT_VARIABLES}
        process = subprocess.Popen([sys.executable, "-c", shard_like, "--suite", "x", "--shard", "9", "--shard-root", "r"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=dict(plain, **shard_roots))
        try:
            grandchild = int(process.stdout.readline())
            narrowed = broker._shard_roots(grandchild)
            verdicts = []
            for target in (shard_roots["TMPDIR"] + "/a/sock", str(top / "broker" / "sock"), shard_roots["HOME"] + "x/sock",
                           *[value + "/../sibling/sock" for value in shard_roots.values()]):
                try:
                    broker._within_shard(grandchild, b"\x01\x00" + target.encode() + b"\0")
                    verdicts.append("allowed")
                except OSError as error:
                    verdicts.append(error.errno)
            # This suite's own process: in no shard when the suite is run by hand, and in its own
            # shard, by its real ancestry, when a gate leg runs it. Both are judged.
            mine = broker._shard_roots(os.getpid())
            try:
                broker._within_shard(os.getpid(), b"\x01\x00/anywhere\0")
                anywhere = None
            except OSError as error:
                anywhere = error.errno
            if "--shard" in sys.argv:
                unsharded = (sorted(mine or []) == sorted(os.environ[name.decode()].encode()
                                                          for name in AS.Broker.SHARD_ROOT_VARIABLES
                                                          if name.decode() in os.environ),
                             anywhere == errno.EACCES)
            else:
                unsharded = (mine is None, anywhere is None)
        finally:
            process.stdin.close()
            process.wait()
        expect("VELDO-0221 AC2 suite-shards/broker-binds-within-the-shard: %r %r %r" % (narrowed, verdicts, unsharded),
               sorted(narrowed or []) == sorted(value.encode() for value in shard_roots.values())
               and verdicts == ["allowed", errno.EACCES, errno.EACCES] + [errno.EACCES] * len(shard_roots) and unsharded == (True, True)
               and sorted(name.decode() for name in AS.Broker.SHARD_ROOT_VARIABLES)
               == sorted(variable for variable, _leaf in RS.SHARD_ROOTS)
               and "--shard" in RS.SHARD_ARGUMENTS and "--shard-root" in RS.SHARD_ARGUMENTS)
        # The bind race (VELDO-0221 gate fix round 3). The production broker walks and pins the
        # bind's parent; a real helper binds. Between the two, an attacker thread swaps the
        # checked directory for a link: to a sibling shard's directory, and to another directory
        # of the same shard. The pause and the swap are ordered by events, not sleeps (the waits
        # are hang detectors only). The bind must land in the pinned directory or be refused;
        # it must never reach the link's target. A control without a swap binds, and keeps the
        # caller's own path as the socket's name. A link already present before the walk is
        # refused by the walk itself. The mutant is the path-based bind the fix replaced: the
        # helper binds the path limited only by the domain root, and the sibling swap escapes.
        import inspect
        import textwrap
        original_bind = AS.Broker._bind_path
        mutant_source = textwrap.dedent(inspect.getsource(original_bind))
        mutant_source = mutant_source.replace("for fd in (sock, *pinned)", "for fd in (sock, self.roots[0][1])")
        mutant_namespace = dict(AS.__dict__)
        exec(compile(mutant_source, '<path-based-bind-mutant>', 'exec'), mutant_namespace)

        def brokered_bind(live, path, bind_method):
            opened, error = [], None
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            raw = b'\x01\x00' + os.fsencode(path) + b'\0'
            notification = AS._Notification()
            notification.pid = os.getpid()
            notification.data.nr = 49
            notification.data.args[2] = len(raw)
            try:
                with patch.object(live, '_read', return_value=raw), \
                        patch.object(live, '_descriptor', return_value=sock.fileno()), \
                        patch.object(live, '_valid', return_value=True), \
                        patch.object(live, '_bind_path', bind_method):
                    live._perform(notification, opened)
            except OSError as failure:
                error = failure.errno
            finally:
                for fd in opened:
                    os.close(fd)
            return sock, error

        def bind_race(bind_method, tag):
            domain = top / tag
            own, sibling = domain / 'a', domain / 'b'
            own.mkdir(parents=True)
            sibling.mkdir()
            live = AS.Broker([domain])
            results = []
            try:
                with patch.object(live, '_shard_roots', return_value=[os.fsencode(own)]):
                    control = own / 'control'
                    control.mkdir()
                    sock, error = brokered_bind(live, control / 's', lambda *a: bind_method(live, *a))
                    with sock:
                        named = sock.getsockname() if error is None else None
                    results.append({'case': 'control', 'error': error, 'name-is-path': named == str(control / 's'),
                                    'safe': error is None and (control / 's').is_socket() and named == str(control / 's')})
                    linked = own / 'linked'
                    linked.symlink_to(sibling, target_is_directory=True)
                    sock, error = brokered_bind(live, linked / 'pre', lambda *a: bind_method(live, *a))
                    sock.close()
                    results.append({'case': 'link-before-walk', 'error': error,
                                    'safe': error == errno.EACCES and not (sibling / 'pre').exists()})
                    for index, destination in enumerate((sibling, own / 'decoy')):
                        destination.mkdir(exist_ok=True)
                        parent, held = own / ('d%d' % index), own / ('held%d' % index)
                        parent.mkdir()
                        checked, swapped = threading.Event(), threading.Event()
                        attack_errors = []

                        def attack():
                            try:
                                if not checked.wait(WAITS.WAIT_HANG_SECONDS):
                                    raise RuntimeError('bind race never reached the pinned parent')
                                parent.rename(held)
                                parent.symlink_to(destination, target_is_directory=True)
                            except BaseException as error:
                                attack_errors.append(repr(error))
                            finally:
                                swapped.set()

                        def paused_bind(*arguments):
                            checked.set()
                            if not swapped.wait(WAITS.WAIT_HANG_SECONDS):
                                raise RuntimeError('bind race attacker hung')
                            return bind_method(live, *arguments)
                        attacker = threading.Thread(target=attack, daemon=True)
                        attacker.start()
                        try:
                            sock, error = brokered_bind(live, parent / 's', paused_bind)
                            sock.close()
                        finally:
                            checked.set()
                            attacker.join(WAITS.WAIT_HANG_SECONDS)
                        landed, escaped = (held / 's').is_socket(), (destination / 's').exists()
                        results.append({'case': 'swap-to-' + ('sibling' if index == 0 else 'own-decoy'),
                                        'error': error, 'pinned': landed, 'redirected': escaped,
                                        'attack_errors': attack_errors,
                                        'safe': (not attacker.is_alive() and not attack_errors and not escaped
                                                 and ((error is None and landed)
                                                      or (error == errno.EACCES and not landed)))})
                        if escaped:
                            (destination / 's').unlink()
            finally:
                live.close()
            return results

        race = bind_race(original_bind, 'race')
        mutant_race = bind_race(mutant_namespace['_bind_path'], 'mutant')
        print('VELDO-0221 broker race baseline=%r path-bind-mutant=%r' % (race, mutant_race), flush=True)
        expect('VELDO-0221 AC2 suite-shards/broker-directory-swap-pinned: %r' % race,
               [result['case'] for result in race] == ['control', 'link-before-walk', 'swap-to-sibling',
                                                        'swap-to-own-decoy']
               and all(result['safe'] for result in race))
        # A launcher started inside a shard (a worker tree a suite starts) serves a domain that
        # lies inside the shard's root: its binds are pinned from the deeper root, the domain's.
        nested_domain = top / 'nested-shard' / 'domain'
        nested_domain.mkdir(parents=True)
        inner = AS.Broker([nested_domain])
        try:
            with patch.object(inner, '_shard_roots', return_value=[os.fsencode(top / 'nested-shard')]):
                sock, nested_error = brokered_bind(inner, nested_domain / 's', lambda *a: original_bind(inner, *a))
                sock.close()
        finally:
            inner.close()
        expect('VELDO-0221 AC2 suite-shards/broker-domain-inside-shard-binds: %r' % nested_error,
               nested_error is None and (nested_domain / 's').is_socket())
        # In a brokered process (the confined leg) this suite's own helper cannot bind by itself:
        # its bind is a mediated call the launcher's broker answers, with this same pinned walk,
        # which refuses the swapped link. There the mutant is contained by the outer broker and
        # the row asserts exactly that; the mutant turns the row red wherever binds are direct.
        if os.environ.get('VELDO_SANDBOX_BROKERED') == '1':
            mutant_verdict = all(result['safe'] and not result.get('redirected') for result in mutant_race)
        else:
            mutant_verdict = not mutant_race[2]['safe'] and mutant_race[2]['redirected']
        expect('VELDO-0221 AC2 suite-shards/broker-directory-swap-path-mutant-red: %r' % mutant_race,
               mutant_source != textwrap.dedent(inspect.getsource(original_bind)) and mutant_verdict)
        # The bind helper's own Landlock layer (VELDO-0221 gate fix round 4), in every leg. In a
        # brokered process (the confined leg) the helper's bind is a mediated call the outer broker
        # answers, so the layer the helper applies beneath the pinned directories never decides
        # there and the rows above test the walk. These rows drive the real helper process (the
        # request it is sent, its per-request child and every layer that child applies) and swap
        # only that child's last call, the bind, for mknodat of the socket file: a call no outer
        # filter mediates, which Landlock judges by the same MAKE_SOCK right. The walk pins first,
        # then the row moves a directory, then the helper creates: beside the pinned directory in
        # the same shard (no link at all), and through a link swapped in for the last and for an
        # intermediate component. The layer refuses every one, and the control lands. The mutant
        # drops the layer (the helper never calls _confine_binder), and every one of them lands.
        import ctypes
        import stat as stat_module

        class DirectHelper(AS.Broker):
            def _make_socket(self, libc, sock, address):
                path = address[2:].split(b'\0', 1)[0]
                made = libc.mknodat(-100, path, stat_module.S_IFSOCK | 0o600, 0)  # AT_FDCWD
                return 0 if made == 0 else ctypes.get_errno()

        layer_source = textwrap.dedent(inspect.getsource(AS.Broker._binder))
        unlayered_source = layer_source.replace('self._confine_binder(libc, pinned)', 'pass')
        unlayered_namespace = dict(AS.__dict__)
        exec(compile(unlayered_source, '<helper-without-layer-mutant>', 'exec'), unlayered_namespace)

        class UnlayeredHelper(DirectHelper):
            _binder = unlayered_namespace['_binder']

        def helper_layer(helper_class, tag):
            domain = top / ('helper-' + tag)
            own, sibling = domain / 'a', domain / 'b'
            for directory in (own / 'p', own / 'other', own / 'm' / 'p', sibling / 'p'):
                directory.mkdir(parents=True)
            live = helper_class([domain])
            results = []

            def request(pin, target, move=None):
                opened, error = [], None
                try:
                    parentfd, rootfd = live._pin_bind(os.getpid(), b'\x01\x00' + os.fsencode(pin) + b'\0', opened)
                    if move is not None:
                        move()
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                        live._bind_path(sock.fileno(), b'\x01\x00' + os.fsencode(target) + b'\0', rootfd, parentfd)
                except OSError as failure:
                    error = failure.errno
                finally:
                    for fd in opened:
                        os.close(fd)
                return error

            def swap(name, held):
                def move():
                    (own / name).rename(own / held)
                    (own / name).symlink_to(sibling if name == 'm' else sibling / 'p', target_is_directory=True)
                return move
            try:
                with patch.object(live, '_shard_roots', return_value=[os.fsencode(own)]):
                    error = request(own / 'p' / 'c', own / 'p' / 'c')
                    results.append({'case': 'control', 'error': error,
                                    'safe': error is None and (own / 'p' / 'c').is_socket()})
                    error = request(own / 'p' / 'x', own / 'other' / 'x')
                    results.append({'case': 'beside-pinned', 'error': error,
                                    'escaped': os.path.lexists(own / 'other' / 'x'),
                                    'safe': error == errno.EACCES and not os.path.lexists(own / 'other' / 'x')})
                    error = request(own / 'p' / 'y', own / 'p' / 'y', swap('p', 'held-p'))
                    results.append({'case': 'last-component-swap', 'error': error,
                                    'escaped': os.path.lexists(sibling / 'p' / 'y'),
                                    'safe': error == errno.EACCES and not os.path.lexists(sibling / 'p' / 'y')})
                    error = request(own / 'm' / 'p' / 'z', own / 'm' / 'p' / 'z', swap('m', 'held-m'))
                    results.append({'case': 'intermediate-component-swap', 'error': error,
                                    'escaped': os.path.lexists(sibling / 'p' / 'z'),
                                    'safe': error == errno.EACCES and not os.path.lexists(sibling / 'p' / 'z')})
            finally:
                live.close()
            return results

        layered = helper_layer(DirectHelper, 'layered')
        unlayered = helper_layer(UnlayeredHelper, 'unlayered')
        print('VELDO-0221 helper layer baseline=%r no-layer-mutant=%r' % (layered, unlayered), flush=True)
        cases = ['control', 'beside-pinned', 'last-component-swap', 'intermediate-component-swap']
        expect('VELDO-0221 AC2 suite-shards/bind-helper-layer-holds-unbrokered: %r' % layered,
               [result['case'] for result in layered] == cases and all(result['safe'] for result in layered))
        expect('VELDO-0221 AC2 suite-shards/bind-helper-layer-mutant-red: %r' % unlayered,
               unlayered_source != layer_source and [result['case'] for result in unlayered] == cases
               and unlayered[0]['safe'] and all(result['escaped'] for result in unlayered[1:]))
        refusals = []
        with open(top / "a-regular-file", "w") as regular:
            for profile, descriptor in (("agent", regular.fileno()), ("gate", regular.fileno()), ("gate", 1)):
                try:
                    AS.prepared_launch(None, None, [], profile, None, inherit=(descriptor,))
                    refusals.append("launched")
                except ValueError as error:
                    refusals.append(str(error))
                except Exception as error:  # noqa: BLE001 - anything else means the check did not come first
                    refusals.append("other: %r" % error)
        expect("VELDO-0221 AC4 suite-shards/leg-runner-hands-claims: %r %r %r %r" % (first, kept, passed_on, refusals),
               first == {"01_a": {"cpu": 2.5, "memory": 5000, "seconds": 10.0},
                         "02_b": {"cpu": 0.1, "memory": 7000, "seconds": 100.0}}
               and kept == {"01_a": {"cpu": 2.5, "memory": 9000, "seconds": 12.0},
                            "02_b": {"cpu": 0.1, "memory": 7000, "seconds": 100.0}}
               and GL.read_shard_claims(store, digest, "unconfined") == {}
               and json.loads(handed["VELDO_GATE_SHARD_CLAIMS"]) == kept
               and not [k for k in ("VELDO_GATE_SHARD_METRICS_FD", "VELDO_GATE_LEDGER_FD",
                                    "VELDO_GATE_SHARD_LEDGER_FD") if k in handed]
               and not [k for k in ("VELDO_GATE_SHARD_CLAIMS", "VELDO_GATE_SHARD_METRICS_FD", "VELDO_GATE_LEDGER_FD",
                                    "VELDO_GATE_SHARD_LEDGER_FD") if k in bare_env]
               and passed_on == [[write_end], [], []]
               and refusals == ["only the gate profile inherits a descriptor",
                                # VELDO-0358 widened the refusal with its opened-files ledger.
                                "an inherited descriptor must be a pipe or a socket above the standard three, "
                                "or the append-only opened-files ledger",
                                "an inherited descriptor must be a pipe or a socket above the standard three, "
                                "or the append-only opened-files ledger"])


        # ==== F1: a leg node claims only its dispatcher, so its shards run in parallel beneath the
        # mutation floor ========================================================================
        # The real scheduler (scripts/gate_schedule.py run), its ledger and the leg runner's channel
        # (gate_legs.ShardClaims), over a fixture graph of this host's shape: 20 cores, a mutation
        # floor of 11, and a unit.confined node whose own claim is what its whole cgroup measured in
        # an earlier gate, 8.3 cores, shards included. The mutation node holds its floor until the
        # leg has finished (it waits for the leg's file). The leg asks for three one-core shards at
        # once, then runs three real shards through the dispatcher that each wait for the other two.
        GS = load(ROOT / "scripts" / "gate_schedule.py", "v221_gate_schedule")
        GS.HERE = ROOT / "scripts"  # the leg runner beside the shipped scheduler, wherever this copy stands
        sched = top / "schedule"
        sched.mkdir()
        barrier = sched / "barrier"
        barrier.mkdir()
        waits = ('import time\n(Path(os.environ["V221_BARRIER"]) / suite_file().stem).write_text("x")\n'
                 'limit = time.monotonic() + 600\n'
                 'while len(list(Path(os.environ["V221_BARRIER"]).iterdir())) < 3 and time.monotonic() < limit:\n'
                 '    time.sleep(0.01)\n'
                 'expect("three shards ran at once", len(list(Path(os.environ["V221_BARRIER"]).iterdir())) == 3)\n')
        parallel_tree = tree(top / "parallel", {"01_a": waits, "02_b": waits, "03_c": waits})
        leg_script = sched / "leg.py"
        leg_script.write_text(
            'import importlib.util, json, os, sys\nfrom pathlib import Path\n'
            'def load(path, name):\n    spec = importlib.util.spec_from_file_location(name, path)\n'
            '    module = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(module)\n    return module\n'
            'root, out, tree, environment = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], json.loads(sys.argv[4])\n'
            'GL, RS = load(root / "scripts/gate_legs.py", "leg_gl"), load(root / "scripts/run_scope.py", "leg_rs")\n'
            'said = {"grants": [], "huge": None, "shards": None}\n'
            'try:\n'
            '    asking = GL.ShardClaims(os.environ["VELDO_GATE_LEDGER_FD"], {"04_huge": {"cpu": 500.0, "memory": 1e15, "seconds": 1.0}})\n'
            '    client = RS.ShardLedger(asking.fileno())\n'
            '    said["grants"] = [client.acquire(name, RS.SHARD_UNMEASURED) for name in ("01_a", "02_b", "03_c")]\n'
            '    for name, granted in zip(("01_a", "02_b", "03_c"), said["grants"]):\n'
            '        if granted:\n            client.release(name)\n'
            '    try:\n        said["huge"] = client.acquire("04_huge", RS.SHARD_UNMEASURED)\n'
            '        if said["huge"]:\n            client.release("04_huge")\n'
            '    except RS.LegRefused as error:\n        said["huge"] = str(error)\n'
            '    client.close()\n'
            '    if all(said["grants"]):\n'
            '        lines = []\n'
            '        result = RS.run_shards(tree, "unconfined", ["01_a", "02_b", "03_c"], emit=lines.append, places=[],\n'
            '                               units=None, settle=0, tick=0.02,\n'
            '                               environ=dict(environment, VELDO_GATE_SHARD_LEDGER_FD=str(asking.fileno())))\n'
            '        said["shards"] = {"passed": result["passed"], "failed": result["failed"],\n'
            '                          "parallelism": result["parallelism"],\n'
            '                          "peak": max(len(e["running"]) + 1 for e in result["events"] if e["event"] == "start")}\n'
            '    asking.close()\n'
            'finally:\n    out.write_text(json.dumps(said))\n    (out.parent / "leg-done").write_text("x")\n')
        waiter = ('import sys, time\nfrom pathlib import Path\nlimit = time.monotonic() + 600\n'
                  'while not Path(sys.argv[1]).exists() and time.monotonic() < limit:\n    time.sleep(0.01)\n')
        command = "fixture leg command"
        declaration_path = sched / "gate_unconfined.json"
        declaration_path.write_text(json.dumps({
            "schema": "veldo.gate-unconfined/v1", "authority": "controlled ticket fixture",
            "stages": {"unit": command, "mutation": "authority mutation stage"},
            "suites": [{"suite": "01_fixture", "reason": "controlled fixture leg for scheduling"}]}))
        graph_path = sched / "gate_graph.json"
        graph_path.write_text(json.dumps({
            "schema": "veldo.gate-graph/v1",
            "nodes": {name: {"depends_on": [], "writes_candidate": False, "manager": "none", "ports": []}
                      for name in ("unit.confined", "unit.unconfined", "mutation")},
            "reserve": {"cpu": 0, "memory": 0}, "mutation_floor": {"cpu": 11, "memory": 9 << 30}}))
        earlier = {"mutation": {"cpu_rate": 11, "peak_anon_bytes": 9 << 30},
                   "unit.confined": {"cpu_rate": 8.3, "peak_anon_bytes": 8 << 30},
                   "unit.unconfined": {"cpu_rate": 0.5, "peak_anon_bytes": 1 << 30}}

        class FixtureMeter:
            def __init__(self, name):
                self.name = name

            def command(self, argv):
                return argv

            def sample(self):
                return {"cpu_seconds": .01, "peak_anon_bytes": 1024, "metrics_source": "cgroup-v2-anon-sampled-50ms"}

            def finish(self):
                return dict(self.sample(), live_descendants=False)

        class FixtureInputs:
            def __init__(self, root, destination):
                self.root, self.common = Path(root), Path(root)

            def unchanged(self):
                return True

            def close(self):
                pass

        def scheduled(number):
            """One run of the real scheduler over the fixture graph; (its result, what the leg said,
            what it recorded for the leg node)."""
            module = GS
            out = sched / ("run-%d" % number)
            out.mkdir()
            store = out / "store"
            loads = module.load_module

            def fixture_load(name):
                loaded = loads(name)
                if name == "gate_legs":
                    loaded.read_resources = lambda _times, _key, node: dict(earlier[node])
                    loaded.LEG_TIMES = store  # never the owner's store
                return loaded

            def node_command(_root, stage, leg, *_rest):
                if stage == "mutation":
                    return [sys.executable, "-c", waiter, str(out / "leg-done")]
                if leg == "confined":
                    return [sys.executable, str(leg_script), str(ROOT), str(out / "leg.json"), str(parallel_tree),
                            json.dumps(leg_env("unconfined", "01_a,02_b,03_c", V221_BARRIER=str(barrier)))]
                return [sys.executable, "-c", "pass"]
            for path in barrier.iterdir():
                path.unlink()
            import contextlib
            import io
            with patch.object(module, "load_module", fixture_load), patch.object(module, "command_for", node_command), \
                    contextlib.redirect_stdout(io.StringIO()):
                result = module.run({"unit": command, "mutation": "authority mutation stage"}, top, out, out / "record",
                                    out / "receipt", graph_path=graph_path, declaration_path=declaration_path,
                                    capacity={"cpu": 20, "memory": 31 << 30, "manager": 16},
                                    meter_factory=FixtureMeter, guard_factory=lambda _root: (lambda: True),
                                    node_inputs_factory=FixtureInputs)
            said = json.loads((out / "leg.json").read_text()) if (out / "leg.json").exists() else {}
            recorded = {}
            for path in (store.iterdir() if store.exists() else ()):
                try:
                    item = json.loads(path.read_text())
                except ValueError:
                    continue
                if item.get("node"):
                    recorded[item["node"]] = item
            return result, said, recorded
        result, said, recorded = scheduled(1)
        ledger = result["ledger"]
        actions = [(e["action"], e["claimant"]) for e in ledger]
        shard_grants = [i for i, e in enumerate(ledger) if e["action"] == "grant" and e["claimant"].startswith("unit.confined/")]
        mutation_released = actions.index(("release", "mutation")) if ("release", "mutation") in actions else -1
        dispatcher_at = actions.index(("dispatcher", "unit.confined")) if ("dispatcher", "unit.confined") in actions else -1
        third = ledger[shard_grants[2]] if len(shard_grants) > 2 else {"granted": {"cpu": 0}}
        clamps = [e["claim"] for e in ledger if e["action"] == "clamp"]
        leg_record = recorded.get("unit.confined", {})
        expect("VELDO-0221 AC4 suite-shards/leg-node-claims-only-its-dispatcher: %r %r %r %r"
               % (said, actions[:14], clamps, {k: leg_record.get(k) for k in ("cpu_rate", "peak_anon_bytes", "dispatcher")}),
               said.get("grants") == [True, True, True] and result["stages"] == {"unit": "pass", "mutation": "pass"}
               # The node shrank to its dispatcher at its first shard request, before any shard was granted.
               and 0 < dispatcher_at < shard_grants[0]
               and ledger[dispatcher_at]["claim"]["cpu"] == GS.LEG_DISPATCHER["cpu"] == 1.0
               and ledger[dispatcher_at]["claim"]["memory"] == GS.LEG_DISPATCHER["memory"]
               # Three shards held at once while mutation still held its whole floor: 11 + 1 + 3 cores.
               and shard_grants[2] < mutation_released and 15.0 <= third["granted"]["cpu"] <= 15.5
               # Three REAL shards then ran at once through the dispatcher, as that ledger granted them.
               and said.get("shards") == {"passed": 3, "failed": 0, "parallelism": None, "peak": 3}
               # A measured claim larger than the ledger could ever grant is held to what it can: the
               # capacity less the floor and the two legs' dispatchers. It is granted, never refused.
               and said.get("huge") is True and len(clamps) == 1 and clamps[0]["cpu"] == 20 - 11 - 2 * 1.0
               and clamps[0]["memory"] == (31 << 30) - (9 << 30) - 2 * (1 << 30)
               # What the node records for the next gate is its dispatcher's claim, not its cgroup's.
               and leg_record.get("dispatcher") is True and abs(leg_record.get("cpu_rate", 0) - 1.0) < 1e-6
               and leg_record.get("peak_anon_bytes") == 1 << 30
               and recorded.get("mutation", {}).get("dispatcher") is False)
        # The two kinds of record never mix: a dispatcher's claim replaces a cgroup's total and the
        # other way round, and the larger-of-two rule holds within one kind only. A leg that could
        # not be cut into shards keeps its whole claim: it never asks, so it is never shrunk.
        kinds = top / "kinds"
        whole = {"cpu_seconds": 830.0, "peak_anon_bytes": 8 << 30, "metrics_source": "cgroup-v2-anon-sampled-50ms"}
        dispatching = {"cpu_seconds": 100.0, "peak_anon_bytes": 1 << 30, "metrics_source": "cgroup-v2-anon-sampled-50ms",
                       "dispatcher": True}
        seen = []
        for metrics in (whole, dispatching, dict(dispatching, cpu_seconds=50.0), dict(whole, cpu_seconds=200.0)):
            GL.record_resources(kinds, "key", "unit.confined", 100.0, metrics)
            item = GL.read_resources(kinds, "key", "unit.confined")
            seen.append((item["cpu_rate"], item["dispatcher"]))
        sources = [GS.node_claim({"manager": "none", "ports": []}, measured, {"cpu": 20, "memory": 1})[1]
                   for measured in ({"cpu_rate": 1.0, "peak_anon_bytes": 5, "dispatcher": True},
                                    {"cpu_rate": 8.3, "peak_anon_bytes": 5, "dispatcher": False})]
        expect("VELDO-0221 AC4 suite-shards/leg-record-kinds-never-mix: %r %r" % (seen, sources),
               seen == [(8.3, False), (1.0, True), (1.0, True), (2.0, False)]
               and sources == ["leg dispatcher claim; its shards claim for themselves",
                               "authority anonymous-memory measurement"])


        # The long suite's split (lead decision 2026-11-21): 15_warp_1404_historical_analogy took 634
        # seconds alone, 545 of them in its twenty audit cases, and was the floor of the confined leg.
        # The cases are cut into three suites over ONE table. The three files must hold the table
        # byte for byte and their slices must cover its twenty cases exactly once, so no row of it
        # was lost or doubled, and each part is its own shard with itself as its whole closure.
        import ast
        import re
        split_names = ["15_warp_1404_historical_analogy", "15_warp_1404_historical_analogy_audit_b",
                       "15_warp_1404_historical_analogy_audit_c"]
        tables, slices, loops = [], [], []
        for name in split_names:
            text = (ROOT / "scripts/suites" / (name + ".py")).read_text()
            begin, end = text.index("    _w1404_cases = (\n"), text.index("    _w1404_dependency = ")
            tables.append(text[begin:end].rstrip())
            slices += re.findall(r"for _w1404_case, _w1404_event, _w1404_call in _w1404_cases(\[[0-9:]*\]):", text)
            at = text.index("        for _w1404_case, _w1404_event, _w1404_call in _w1404_cases")
            loops.append(re.sub(r"_w1404_cases\[[0-9:]*\]", "_w1404_cases", text[at:text.index("    finally:", at)]))
        import textwrap
        cases = len(ast.parse(textwrap.dedent(tables[0])).body[0].value.elts)
        known = {"[:4]": slice(None, 4), "[4:12]": slice(4, 12), "[12:]": slice(12, None)}
        covered = sorted(index for text in slices for index in range(cases)[known.get(text, slice(0))])
        order = [s["name"] for s in RS.fragments(manifest)]
        closures = json.loads((ROOT / "scripts/suites/requires.json").read_text())["requires"]
        expect("VELDO-0221 suite-shards/long-suite-split: %r %d cases, covered %r" % (slices, cases, covered),
               slices == ["[:4]", "[4:12]", "[12:]"] and cases == 20 and covered == list(range(20))
               and tables[0] == tables[1] == tables[2] and loops[0] == loops[1] == loops[2]
               and [order.index(name) for name in split_names] == list(range(order.index(split_names[0]),
                                                                           order.index(split_names[0]) + 3))
               and all(closures[name] == [name] for name in split_names))


_veldo_0221()
