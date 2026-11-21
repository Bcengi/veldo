# VELDO-0221: a gate leg runs its suites as isolated parallel closure shards, with an isolation
# check in every gate. Every row drives the shipped dispatcher (scripts/selftest.py) and the
# shipped shard machinery (scripts/run_scope.py) over fixture trees: the same two files, copied.
#
# NO ROW DEPENDS ON MACHINE SPEED (owner rule 42829). A fixture leg is synchronized on what the
# dispatcher itself records (the order of its starts and ends, each shard's report), never on a
# sleep or a short deadline. The one row about a deadline uses a suite that never ends, so its
# verdict is the same however slow the machine is.


def _veldo_0221():
    import hashlib
    import importlib.util
    import shutil
    import socket
    import threading

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

    def tree(top, bodies, requires=None, resources=None, capacities=None, closures=True):
        """A fixture candidate: the shipped dispatcher and shard machinery over fixture suites."""
        top = Path(top)
        (top / "scripts/suites").mkdir(parents=True)
        shutil.copyfile(ROOT / "scripts" / "selftest.py", top / "scripts/selftest.py")
        shutil.copyfile(ROOT / "scripts" / "run_scope.py", top / "scripts/run_scope.py")
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
        """One leg through the shipped scripts/selftest.py, as the gate starts it."""
        return subprocess.run([sys.executable, str(Path(root) / "scripts/selftest.py")], cwd=str(root),
                              env=env, capture_output=True, text=True, timeout=600,
                              stdin=subprocess.DEVNULL, pass_fds=launcher_fds())

    def shards(root, leg, targets, listed="none_listed", **options):
        """One leg through run_scope.run_shards in this process, with a fixture's own shared places."""
        lines = []
        options.setdefault("places", [])
        options.setdefault("units", None)
        options.setdefault("settle", 0)
        options.setdefault("parallel", 4)
        extra = options.pop("extra", {})
        result = RS.run_shards(root, leg, targets, environ=leg_env(leg, listed, **extra), emit=lines.append,
                               **options)
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
        expect("VELDO-0221 suite-shards/ordered-run-kept-outside-a-leg: " + ordered_leg.stdout[-300:],
               bare.returncode == 0 and "selftest shard" not in bare.stdout
               and bare.stdout.splitlines()[-1] == "selftest: 2 passed, 0 failed"
               and ordered_leg.returncode == 0 and "no closure table" in ordered_leg.stdout
               and "selftest shard" not in ordered_leg.stdout
               and ordered_leg.stdout.splitlines()[-1] == "selftest: 1 passed, 0 failed")
        # A shard past its deadline is a failure of its suite. The suite never ends, so the verdict
        # does not depend on how fast this machine is.
        hung = tree(top / "hung", {"01_hangs": 'import time\nexpect("started", True)\nwhile True:\n    time.sleep(3600)\n'})
        result, _ = shards(hung, "confined", ["01_hangs"], deadline=1.0)
        expect("VELDO-0221 suite-shards/deadline-fails-the-suite: %r" % result["charged"],
               codes(result, "01_hangs") == ["deadline_exceeded"] and result["failed"] == 1)

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
            '"scope": C.unit_name("dispatch-1"), "instance": CC.instance_name(), '
            '"same_rule": CC.instance_name() == C.instance_name()})), flush=True)\n')
        writer = (
            'import json\n'
            'roots = {v: os.environ[v] for v in ("HOME", "TMPDIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", '
            '"XDG_CACHE_HOME", "XDG_STATE_HOME", "XDG_RUNTIME_DIR")}\n'
            'for variable in ("HOME", "TMPDIR", "XDG_RUNTIME_DIR"):\n'
            '    target = Path(roots[variable]) / "same-relative-path"\n'
            '    expect("the path is new in my own root: " + variable, not target.exists())\n'
            '    target.write_text(suite_file().stem)\n'
            '    expect("I read back what I wrote: " + variable, target.read_text() == suite_file().stem)\n'
            'print("V221-ROOTS %s %s" % (suite_file().stem, json.dumps(roots)), flush=True)\n'
            'print("V221-RUNTIME %s %s" % (suite_file().stem, json.dumps(sorted(\n'
            '    str(p.relative_to(roots["XDG_RUNTIME_DIR"])) for p in Path(roots["XDG_RUNTIME_DIR"]).rglob("*")\n'
            '    if p.name != "same-relative-path"))), flush=True)\n' + engine_names)
        intruder = (
            'mine = Path(os.environ["HOME"]).parent\n'
            'refused = []\n'
            'for target in (mine.parent / "probe" / "intruder", mine.parent / "000" / "h" / "intruder"):\n'
            '    try:\n        target.write_text("x")\n        refused.append("wrote")\n'
            '    except PermissionError:\n        refused.append("refused")\n'
            '    except FileNotFoundError:\n        refused.append("gone")\n'
            'print("V221-INTRUDER %s" % ",".join(refused), flush=True)\n'
            'expect("my own root is writable", (Path(os.environ["HOME"]) / "ok").write_text("x") == 1)\n')
        isolated = tree(top / "isolated", {"01_first": writer, "02_second": writer, "03_intruder": intruder})
        engine = {"V221_ENGINE": str(ROOT / ".veldo")}
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
            if len(set(every_root)) != 14 or len(first) != 7:
                problems.append("%s: the two shards share a root: %r %r" % (leg, first, second))
            base_of = {name: str(Path(r["HOME"]).parent) for name, r in roots.items()}
            if base_of["01_first"] == base_of["02_second"] or not all(
                    value.startswith(base_of[name] + "/") for name, r in roots.items() for value in r.values()):
                problems.append("%s: a root lies outside its shard's own directory" % leg)
            # The runtime directory holds only links to the user manager's own sockets, or nothing.
            if not all(set(found) <= {"bus", "systemd", "systemd/private"} for found in runtime.values()):
                problems.append("%s: a runtime directory holds more than the manager's sockets: %r" % (leg, runtime))
            # Every unit, slice and scope name carries its shard's name, and the two shards' differ.
            for name, item in named.items():
                if not (item["instance"] == name and item["same_rule"] and all(
                        name in item[key] for key in ("authority", "api", "slice", "scope"))):
                    problems.append("%s: %s names something without its instance name: %r" % (leg, name, item))
            if len(named) != 2 or any(named["01_first"][key] == named["02_second"][key]
                                      for key in ("authority", "api", "slice", "scope")):
                problems.append("%s: the two shards would name a unit alike: %r" % (leg, named))
            crossing = said.get("V221-INTRUDER", [""])[0].split(",")
            if leg == "confined" and not (crossing[0] == "refused" and crossing[1] in ("refused", "gone")):
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
        expect("VELDO-0221 AC2 suite-shards/isolated-by-construction: " + "; ".join(problems), not problems)

        # With no instance configured, which is every production installation, every name is today's.
        probe = (
            'import importlib.util, json, sys\n'
            'def load(path, name):\n    spec = importlib.util.spec_from_file_location(name, path)\n'
            '    module = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(module)\n    return module\n'
            'CC = load(sys.argv[1] + "/control_client.py", "cc")\nC = load(sys.argv[1] + "/control_containment.py", "c")\n'
            'unit = CC.service_unit({"domain_uuid": "d" * 8, "store_uuid": "s" * 8})\n'
            'print(json.dumps({"authority": unit, "api": "veldo-api-" + unit[len(CC.SERVICE_BASE):], '
            '"prefix": CC.SERVICE_PREFIX, "slice": C.DEFAULT_SLICE, "scope": C.unit_name("dispatch-1"), '
            '"scope_prefix": C.UNIT_PREFIX, "instance": [CC.instance_name(), C.instance_name()]}))\n')

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
        unprefixed = engine_says(dict(plain, HOME=str(empty), XDG_CONFIG_HOME=str(empty)))
        # An installed engine reads the name beside its bin, whatever environment the manager gives it.
        installed = top / "installed"
        (installed / "bin").mkdir(parents=True)
        (installed / "config").mkdir()
        for module in (ROOT / ".veldo").glob("control_*.py"):
            shutil.copyfile(module, installed / "bin" / module.name)
        (installed / "config/instance.json").write_text(json.dumps({"schema": "veldo.instance/v1", "prefix": "shard_a"}))
        from_installation = engine_says(dict(plain, HOME=str(empty), XDG_CONFIG_HOME=str(empty)), installed / "bin")
        (installed / "config/instance.json").write_text(json.dumps({"schema": "another.tool/v1", "prefix": "x"}))
        foreign_file = engine_says(dict(plain, HOME=str(empty), XDG_CONFIG_HOME=str(empty)), installed / "bin")
        (installed / "config/instance.json").write_text(json.dumps({"schema": "veldo.instance/v1", "prefix": "a-b.slice"}))
        unsafe = engine_says(dict(plain, HOME=str(empty), XDG_CONFIG_HOME=str(empty)), installed / "bin")
        OWN = load(ROOT / "scripts" / "mutation_ownership.py", "v221_ownership")
        accepted = [bool(OWN.SERVICE.fullmatch(name)) for name in (
            today["authority"], "veldo-authority-66_veldo_0047_authority-%s.service" % service_id,
            "veldo-authority-.service", "other-authority-%s.service" % service_id,
            "veldo-authority-a-b-%s.service" % service_id)]
        templates = {name: hashlib.sha256((ROOT / ".veldo/services" / name).read_bytes()).hexdigest()[:16]
                     for name in ("veldo-authority.service", "veldo-api.service")}
        expect("VELDO-0221 AC2 suite-shards/production-names: %r %r %r %r %r"
               % (unprefixed, from_installation, foreign_file, unsafe, templates),
               unprefixed == today
               and from_installation.get("authority") == "veldo-authority-shard_a-%s.service" % service_id
               and from_installation.get("api") == "veldo-api-shard_a-%s.service" % service_id
               and from_installation.get("slice") == "veldo-workers-shard_a.slice"
               and from_installation.get("scope", "").startswith("veldo-dispatch-shard_a-")
               and foreign_file == today and "invalid instance name" in unsafe.get("error", "")
               and accepted == [True, True, False, False, False]
               and templates == {"veldo-authority.service": "a5da05e391fc6838", "veldo-api.service": "d24663f489bd528b"})

        # ==== AC3: every gate checks that isolation held, force-fresh or not ======================
        checked = []
        # A confined shard whose Landlock layer is skipped: the dispatcher copy of this tree never
        # stacks it. Every shard of the leg is a breach, in an ordinary gate.
        skipped = tree(top / "skipped", {"01_a": 'expect("a", True)\n', "02_b": 'expect("b", True)\n'})
        source = (skipped / "scripts/selftest.py").read_text()
        confine = ('    _in_force, _refused, _detail = RS.confine_shard(SHARD_ROOT_VALUES[0])\n'
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
        # An unconfined shard that leaves a file in /dev/shm, and one that starts a unit without its
        # prefix. The fixture's own directory and unit list stand for the two: the gate runs this
        # suite inside its confinement, where the real ones are out of reach.
        shm, unit_list = top / "fixture-dev-shm", top / "fixture-units"
        shm.mkdir()
        unit_list.write_text("existing.service\n")
        places = [{"name": "/dev/shm", "path": shm, "depth": 1, "rule": "strict"}]

        def listed_units():
            return unit_list.read_text().split()
        bodies = {
            "01_clean": 'expect("clean", True)\n',
            "02_leaves_shm": 'Path(os.environ["V221_SHM"], "left-behind").write_text("x")\nexpect("left a file", True)\n',
            "03_starts_unit": ('with open(os.environ["V221_UNITS"], "a") as handle:\n'
                               '    handle.write("stray-fixture.service\\n")\nexpect("started a unit", True)\n'),
            "04_prefixed_unit": ('with open(os.environ["V221_UNITS"], "a") as handle:\n'
                                 '    handle.write("veldo-authority-04_prefixed_unit-0123456789abcdef.service\\n")\n'
                                 'expect("left its own unit", True)\n'),
            "05_tidy": ('target = Path(os.environ["V221_SHM"], "tidied")\ntarget.write_text("x")\ntarget.unlink()\n'
                        'expect("made and removed a file", True)\n'),
        }
        leaky = tree(top / "leaky", bodies)
        fixture_env = {"V221_SHM": str(shm), "V221_UNITS": str(unit_list)}
        for force in (None, "0"):
            for path in shm.iterdir():
                path.unlink()
            unit_list.write_text("existing.service\n")
            extra = dict(fixture_env, **({"VELDO_GATE_FORCE_FRESH": force} if force is not None else {}))
            result, lines = shards(leaky, "unconfined", list(bodies), listed=",".join(bodies), places=places,
                                   units=listed_units, describe=lambda unit: "", parallel=1, extra=extra)
            got = {name: codes(result, name) for name in bodies}
            words = {name: [w for _c, w in result["charged"].get(name, [])] for name in bodies}
            if got != {"01_clean": [], "02_leaves_shm": ["isolation_breach"], "03_starts_unit": ["isolation_breach"],
                       "04_prefixed_unit": ["isolation_breach"], "05_tidy": []}:
                checked.append("force-fresh %r: charged %r" % (force, got))
                continue
            if not ("left-behind" in words["02_leaves_shm"][0]
                    and "stray-fixture.service" in words["03_starts_unit"][0]
                    and "carries no shard's prefix" in words["03_starts_unit"][0]
                    and "its name carries the suite's instance name" in words["04_prefixed_unit"][0]
                    and result["failed"] == 3 and result["passed"] == 5
                    and any("isolation check FAILED: isolation_breach" in line for line in lines)):
                checked.append("force-fresh %r: breaches not named: %r" % (force, words))
        # A clean unconfined leg holds, and what another account or another tree's live process holds
        # is not charged to it.
        for path in shm.iterdir():
            path.unlink()
        unit_list.write_text("existing.service\n")
        result, lines = shards(leaky, "unconfined", ["01_clean", "05_tidy"], listed="01_clean,05_tidy", places=places,
                               units=listed_units, describe=lambda unit: "", extra=fixture_env)
        if result["failed"] or not any("isolation check held" in line for line in lines):
            checked.append("a clean leg did not hold: %r" % result["charged"])
        # The shared places of the real unconfined leg are the ones the specification names.
        real = {p["name"]: (str(p["path"]), p["rule"]) for p in RS.unconfined_places(top / "vs-fixture")}
        import pwd
        home = pwd.getpwuid(os.getuid()).pw_dir
        if real != {"systemd configuration": (home + "/.config/systemd/user", "strict"),
                    "runtime directory": ("/run/user/%d" % os.getuid(), "strict"),
                    "/dev/shm": ("/dev/shm", "strict"), "temporary directory": (str(top), "attributed"),
                    "owner cache": (home + "/.cache/veldo", "strict"),
                    "owner state": (home + "/.local/state/veldo", "strict")}:
            checked.append("the real shared places are %r" % real)
        expect("VELDO-0221 AC3 suite-shards/isolation-checked: " + "; ".join(checked), not checked)

        # An item is charged to the shard it can be tied to, and what cannot be the leg's is not.
        jobs = [{"name": "01_first", "index": 0}, {"name": "02_second", "index": 1}]
        base = top / "vs-attribution"
        (base / "001/h").mkdir(parents=True)
        place = top / "attribution-place"
        place.mkdir()
        (place / "plain").write_text("nothing here")
        (place / "refers").write_text("ExecStart=%s/001/h/bin/run\n" % base)
        os.symlink(base / "001/h", place / "link")
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
        holder = (held_by(dict(plain, HOME=str(top))), held_by(dict(plain, HOME=str(base / "001/h"))))
        by_unit = RS.attribute("unit", "run-u7.scope", None, base, jobs,
                               lambda unit: "WorkingDirectory=%s/000/t\n" % base)
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
                                "an inherited descriptor must be a pipe or a socket above the standard three",
                                "an inherited descriptor must be a pipe or a socket above the standard three"])


_veldo_0221()
