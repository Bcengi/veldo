"""VELDO-0358 brief B: the wall-clock census (AC6, AC7) and the end of VELDO-0223 (AC14).

Every row drives the real scripts/check_wallclock.py as a child over a fixture tree it writes, and
reads what the stage printed and how it exited. The fixture source texts below hold the sleeps the
census must find; they are the subject of this suite and are declared so in scripts/suites/wallclock.json.
No row of this suite sleeps, reads a clock or gives a timeout.

  census/each-rule              one site fixture per rule and per positional form is red with the
                                rule, the form and the site named; the allowed forms are green; a
                                fixture loaded by a computed path is in scope through the record
  census/lists-from-authority   the baseline shrinks without approval and never grows; exceptions
                                come from the authority alone; counts are compared, not presence
  census/stage-declared         the gate declares the stage and the scheduler accepts its node
  supersede/0223-not-claimable  the index, regenerated from the specification, shows VELDO-0223
                                not ready, and its History names what replaced it
  supersede/result-words-closed the gate prints GREEN, RED, NOT JUDGED and NOT STARTED and nothing
                                else, and no NOT JUDGED reason is about load
"""


def _v358_census():
    import importlib.util
    import json
    import re
    import shutil
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    tool = ROOT / "scripts" / "check_wallclock.py"
    verify = ROOT / "scripts" / "verify.sh"
    host = ROOT / "scripts" / "gate_host.py"
    superseded = ROOT / "specs" / "VELDO-0223-a-red-under-others-load-is-rerun-quietly-before-it-counts.md"

    def row(name, condition, detail=''):
        expect('VELDO-0358 ' + name + (': ' + str(detail)[:3000] if detail and not condition else ''), condition)

    def write(base, files):
        for rel, text in files.items():
            path = Path(base) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def lists(base, baseline=None, exceptions=()):
        """The two lists of a checkout; baseline None leaves the checkout without one."""
        files = {'scripts/suites/wallclock.json': json.dumps(
            {'schema': 'veldo.wallclock-exceptions/v1', 'entries': list(exceptions)})}
        if baseline is not None:
            files['scripts/suites/wallclock_baseline.json'] = json.dumps(
                {'schema': 'veldo.wallclock-baseline/v1', 'entries': list(baseline)})
        write(base, files)

    def entry(rel, text, function, count=1, rule='R1', **more):
        return dict({'file': rel, 'rule': rule, 'text': text, 'function': function, 'count': count}, **more)

    def census(candidate, authority, record=None):
        command = [sys.executable, '-I', '-S', str(tool), '--root', str(candidate), '--authority', str(authority)]
        if record is not None:
            command += ['--record', str(record)]
        done = subprocess.run(command, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        return done.returncode, done.stdout + done.stderr

    def named(out, error, rule, rel, *words):
        """Whether a line of the stage's output names this error, rule and file with every word."""
        return any(line.startswith('wallclock: %s %s ' % (error, rule)) and (' ' + rel + ':') in line
                   and all(word in line for word in words) for line in out.splitlines())

    with tempfile.TemporaryDirectory(prefix='v358-census-') as scratch:
        top = Path(scratch)
        # ---- AC6: one fixture per rule, per positional form, and the allowed forms -----------------
        sites = {
            # rel: (source, rule, words the red line must carry)
            'scripts/fx/rule_sleep.py': (
                'import time\n\n\ndef settle():\n    time.sleep(2)\n',
                'R1', ('call time.sleep', ':5 in settle', 'time.sleep(2)')),
            'scripts/fx/rule_sleep_aliased.py': (
                'from time import sleep as nap\n\n\ndef settle():\n    nap(2)\n',
                'R1', ('call time.sleep', ':5 in settle', 'nap(2)')),
            'scripts/fx/rule_sleep_imported_inline.py': (
                'def settle():\n    __import__("time").sleep(2)\n',
                'R1', ('call time.sleep', ':2 in settle')),
            'scripts/fx/rule_sleep_source.py': (
                'CHILD = "import time\\ntime.sleep(2)\\n"\n',
                'R1', ('sleep in a string', 'in <module>', 'time.sleep(2)')),
            'scripts/fx/rule_sleep_page.spec.ts': (
                "test('settles', async ({ page }) => {\n  await page.waitForTimeout(250);\n});\n",
                'R1', ('waitForTimeout', ':2 in')),
            'scripts/fx/rule_clock.py': (
                'import time\n\n\ndef stamp():\n    return time.monotonic()\n',
                'R2', ('read time.monotonic', ':5 in stamp')),
            'scripts/fx/rule_timeout.py': (
                'import subprocess\n\n\ndef child():\n    return subprocess.run(["true"], timeout=5)\n',
                'R3', ('keyword timeout 5', ':5 in child')),
            'scripts/fx/rule_timeout_light_child.py': (
                'import subprocess\nfrom waits import PROCESS_HANG_SECONDS\n\n\ndef child():\n'
                '    return subprocess.run(["git", "status"], timeout=PROCESS_HANG_SECONDS)\n',
                'R3', ('PROCESS_HANG_SECONDS on a child that is not heavy', ':6 in child')),
            'scripts/fx/rule_bound.py': (
                'def judge(elapsed):\n    return elapsed < 6\n',
                'R4', ('upper bound on the duration elapsed', ':2 in judge')),
            'scripts/fx/position_select.py': (
                'import select\n\n\ndef ready(reader):\n    return select.select([reader], [], [], 0.2)\n',
                'R3', ('select.select argument 3 0.2', ':5 in ready')),
            'scripts/fx/position_queue_get.py': (
                'import queue\n\n\ndef take():\n    inbox = queue.Queue()\n    return inbox.get(True, 5)\n',
                'R3', ('Queue.get argument 1 5', ':6 in take')),
            'scripts/fx/position_condition_wait_for.py': (
                'import threading\n\n\ndef held(ready):\n    gate = threading.Condition()\n'
                '    with gate:\n        return gate.wait_for(ready, 3)\n',
                'R3', ('Condition.wait_for argument 1 3', ':7 in held')),
            'scripts/fx/position_timer.py': (
                'import threading\n\n\ndef later(act):\n    return threading.Timer(2, act)\n',
                'R3', ('threading.Timer argument 0 2', ':5 in later')),
            'scripts/fx/position_sleep_command.py': (
                'import subprocess\n\n\ndef holder():\n    return subprocess.Popen(["sleep", "2"])\n',
                'R1', ('command list sleep', ':5 in holder')),
            'scripts/fx/position_thread_join.py': (
                'import threading\n\n\ndef finish(work):\n    worker = threading.Thread(target=work)\n'
                '    worker.start()\n    worker.join(5)\n',
                'R3', ('Thread.join argument 0 5', ':7 in finish')),
            'scripts/fx/position_unknown_receiver.py': (
                'def finish(worker):\n    worker.join(5)\n',
                'R3', ('method.join argument 0 5', ':2 in finish')),
        }
        allowed = {
            'scripts/fx/allowed.py': (
                'import os\nimport queue\nimport subprocess\nimport sys\nimport threading\n'
                'from waits import PROCESS_HANG_SECONDS, WAIT_HANG_SECONDS\n\n\n'
                'def forms(parts, a, b, d, k, elapsed, worker, inbox):\n'
                '    subprocess.run(["true"], timeout=0)\n'
                '    subprocess.run(["true"], timeout=None)\n'
                '    subprocess.run(["git", "status"], timeout=WAIT_HANG_SECONDS)\n'
                '    subprocess.run([sys.executable, "scripts/selftest.py"], timeout=PROCESS_HANG_SECONDS)\n'
                '    worker.join(WAIT_HANG_SECONDS)\n'
                '    worker.join(0)\n'
                '    inbox.get(False)\n'
                '    threading.Event().wait()\n'
                '    slow_enough = elapsed >= 2\n'
                '    return ", ".join(parts), os.path.join(a, b), d.get(k), d.get(k, 5), slow_enough\n'),
        }
        candidate, authority = top / 'rules' / 'candidate', top / 'rules' / 'authority'
        write(candidate, {rel: source for rel, (source, _, _) in sites.items()})
        write(candidate, allowed)
        lists(authority, baseline=[])
        code, out = census(candidate, authority)
        missed = [rel for rel, (_, rule, words) in sites.items() if not named(out, 'wallclock_site', rule, rel, *words)]
        spurious = [line for line in out.splitlines() if 'scripts/fx/allowed.py' in line]
        counted = len([line for line in out.splitlines() if line.startswith('wallclock: wallclock_site ')])
        each = code == 1 and not missed and not spurious and counted == len(sites)

        # The same fixtures are green under a baseline that lists them, so the reds above are the sites'.
        tool_module = importlib.util.spec_from_file_location('v358_check_wallclock', str(tool))
        census_module = importlib.util.module_from_spec(tool_module)
        tool_module.loader.exec_module(census_module)
        found, _ = census_module.census(candidate, {rel: set(census_module.RULES) for rel in list(sites) + list(allowed)})
        listed = [entry(s['file'], s['text'], s['function'], rule=s['rule'], **{'class': s['class']}) for s in found]
        lists(authority, baseline=listed)
        lists(candidate, baseline=listed)
        base_code, base_out = census(candidate, authority)
        baselined = base_code == 0 and 'wallclock: pass' in base_out and len(listed) == len(sites)

        # A fixture loaded by a computed path: no import statement names it, the record does.
        loaded = {
            'scripts/suites/900_fixture_loader.py':
                'import os\n\n\ndef load(root):\n'
                '    path = os.path.join(root, "proof", "FX-" + "0001", "load" + "ed.py")\n'
                '    exec(compile(open(path).read(), path, "exec"), {})\n',
            'proof/FX-0001/loaded.py': 'import time\n\n\ndef pace():\n    time.sleep(1)\n',
            'proof/FX-0001/unopened.py': 'import time\n\n\ndef pace():\n    time.sleep(9)\n',
        }
        candidate, authority = top / 'scope' / 'candidate', top / 'scope' / 'authority'
        write(candidate, loaded)
        write(authority, loaded)
        lists(authority, baseline=[])
        record = top / 'scope' / 'opened_files.json'
        record.write_text(json.dumps({'900_fixture_loader': [
            'proof/FX-0001/loaded.py', 'scripts/suites/900_fixture_loader.py']}))
        scope_code, scope_out = census(candidate, authority, record)
        computed = (scope_code == 1 and named(scope_out, 'wallclock_site', 'R1', 'proof/FX-0001/loaded.py', 'in pace')
                    and 'unopened.py' not in scope_out)
        # A file the candidate changed is in scope before any record has seen it.
        write(candidate, {'proof/FX-0001/unopened.py': 'import time\n\n\ndef pace():\n    time.sleep(8)\n'})
        changed_code, changed_out = census(candidate, authority, record)
        changed = changed_code == 1 and named(changed_out, 'wallclock_site', 'R1', 'proof/FX-0001/unopened.py')

        # The repository itself, against its own baseline and exceptions.
        repo_code, repo_out = census(ROOT, ROOT)
        repository = repo_code == 0 and 'wallclock: pass' in repo_out
        row('census/each-rule', each and baselined and computed and changed and repository,
            dict(missed=missed, spurious=spurious, counted=[counted, len(sites)], exit=code, baselined=[base_code, len(listed)],
                 computed=[scope_code, scope_out[-600:]], changed=[changed_code, changed_out[-400:]],
                 repository=[repo_code, repo_out[-1500:]], output=out[-1500:]))

        # ---- AC7: the lists are multisets, the exceptions are the authority's --------------------
        legacy = 'import time\n\n\ndef poll():\n    time.sleep(1)\n    time.sleep(3)\n'
        kept = 'import time\n\n\ndef hold():\n    time.sleep(5)\n'
        one, three = (entry('scripts/fx/legacy.py', 'time.sleep(%d)' % n, 'poll', **{'class': 'S1'}) for n in (1, 3))
        excepted = entry('scripts/fx/kept.py', 'time.sleep(5)', 'hold', kind='lower_bound',
                         reason='the fixture wait a lower bound reads', specification='VELDO-0358')

        def case(name, files, baseline, exceptions=(excepted,), authority_baseline=(one, three)):
            candidate, authority = top / 'lists' / name / 'candidate', top / 'lists' / name / 'authority'
            write(candidate, dict({'scripts/fx/legacy.py': legacy, 'scripts/fx/kept.py': kept}, **files))
            lists(candidate, baseline=baseline)
            lists(authority, baseline=authority_baseline, exceptions=exceptions)
            return census(candidate, authority)

        converted = 'import time\n\n\ndef poll():\n    time.sleep(3)\n'
        results = {
            'unchanged': case('unchanged', {}, [one, three]),
            'removed-and-lowered': case('lowered', {'scripts/fx/legacy.py': converted}, [three]),
            'added-with-own-entry': case(
                'added', {'scripts/fx/added.py': 'import time\n\n\ndef more():\n    time.sleep(7)\n'},
                [one, three, entry('scripts/fx/added.py', 'time.sleep(7)', 'more', **{'class': 'S1'})]),
            'removed-entry-left': case('left', {'scripts/fx/legacy.py': converted}, [one, three]),
            'duplicated-baselined-line': case(
                'duplicated', {'scripts/fx/legacy.py': legacy + '    time.sleep(3)\n'}, [one, three]),
            'copied-excepted-line': case('copied', {'scripts/fx/kept.py': kept + '    time.sleep(5)\n'}, [one, three]),
            'unknown-kind': case('kind', {}, [one, three], exceptions=(dict(excepted, kind='convenient'),)),
        }
        want = {
            'unchanged': lambda c, o: c == 0 and 'wallclock: pass' in o,
            'removed-and-lowered': lambda c, o: c == 0 and 'wallclock: pass' in o,
            'added-with-own-entry': lambda c, o: c == 1 and named(o, 'wallclock_site', 'R1', 'scripts/fx/added.py',
                                                                  '1 site(s), the authority allows 0'),
            'removed-entry-left': lambda c, o: c == 1 and '\nwallclock: wallclock_site ' not in o and any(
                line.startswith('wallclock: baseline_stale R1 ') and 'the baseline says 1, required 0' in line
                and 'time.sleep(1)' in line for line in o.splitlines()),
            'duplicated-baselined-line': lambda c, o: c == 1 and named(
                o, 'wallclock_site', 'R1', 'scripts/fx/legacy.py', '2 site(s), the authority allows 1', 'time.sleep(3)'),
            'copied-excepted-line': lambda c, o: c == 1 and named(
                o, 'wallclock_site', 'R1', 'scripts/fx/kept.py', '2 site(s), the authority allows 1', 'time.sleep(5)'),
            'unknown-kind': lambda c, o: c == 1 and 'list_refused' in o and "unknown kind 'convenient'" in o,
        }
        verdicts = {name: bool(want[name](*results[name])) for name in want}
        # Until the authority has a baseline, the stage reports and judges nothing.
        candidate, authority = top / 'lists' / 'bootstrap' / 'candidate', top / 'lists' / 'bootstrap' / 'authority'
        write(candidate, {'scripts/fx/legacy.py': legacy})
        lists(authority)
        boot_code, boot_out = census(candidate, authority)
        verdicts['report-mode'] = boot_code == 0 and 'report mode' in boot_out and 'R1 2' in boot_out
        row('census/lists-from-authority', all(verdicts.values()),
            dict(verdicts=verdicts, outputs={name: [results[name][0], results[name][1][-500:]]
                                             for name in want if not verdicts[name]}))

        # ---- the stage in the gate --------------------------------------------------------------
        gate_text = verify.read_text()
        graph = json.loads((ROOT / 'scripts' / 'gate_graph.json').read_text())
        node = graph['nodes'].get('wallclock') or {}
        schedule_spec = importlib.util.spec_from_file_location('v358_gate_schedule', str(ROOT / 'scripts' / 'gate_schedule.py'))
        schedule = importlib.util.module_from_spec(schedule_spec)
        schedule_spec.loader.exec_module(schedule)
        catalog = {}
        for name in re.search(r'ORDER="([^"]*)"', gate_text).group(1).replace('\\\n', ' ').split():
            match = re.search(r'^CHECK_%s="required:([^"]*)"' % name, gate_text, re.M)
            if match:
                catalog[name] = match.group(1)
        listing = ROOT / 'scripts' / 'gate_unconfined.json'
        legs = schedule.load_module('gate_legs').load(listing)[0] if listing.exists() else None
        try:
            schedule.read_graph(catalog, legs, ROOT / 'scripts' / 'gate_graph.json')
            refused = None
        except schedule.Refused as error:
            refused = str(error)
        engine_gate = (ROOT / 'engine' / 'scripts' / 'verify.sh').read_text()
        policy = (ROOT / '.veldo' / 'policy.yaml').read_text()
        protected = [path for path in ('scripts/check_wallclock.py', 'engine/scripts/check_wallclock.py',
                                       'scripts/suites/wallclock.json', 'scripts/suites/wallclock_baseline.json')
                     if '{path: "%s", floor: high}' % path not in policy]
        row('census/stage-declared',
            catalog.get('wallclock') == 'python3 scripts/check_wallclock.py'
            and 'export VELDO_GATE_AUTHORITY="$VELDO_AUTHORITY"' in gate_text
            and node.get('depends_on') == [] and node.get('writes_candidate') is False and refused is None
            and re.search(r'ORDER="[^"]*\bwallclock\b', engine_gate) is not None
            and re.search(r'(?m)^CHECK_wallclock="(?:na|required):', engine_gate) is not None
            and 'export VELDO_GATE_AUTHORITY="$VELDO_AUTHORITY"' in engine_gate
            and not protected
            and (ROOT / 'engine' / 'scripts' / 'check_wallclock.py').read_bytes()
            == (ROOT / 'scripts' / 'check_wallclock.py').read_bytes(),
            dict(catalog=catalog.get('wallclock'), node=node, refused=refused, unprotected=protected))

        # ---- AC14: VELDO-0223 cannot be claimed -------------------------------------------------
        fixture = top / 'supersede'
        (fixture / 'specs').mkdir(parents=True)
        shutil.copyfile(superseded, fixture / 'specs' / superseded.name)
        index_spec = importlib.util.spec_from_file_location('v358_update_index', str(ROOT / 'scripts' / 'update_index.py'))
        index = importlib.util.module_from_spec(index_spec)
        index_spec.loader.exec_module(index)
        index.SPECS, index.PLANS = fixture / 'specs', fixture / 'plans'
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            index.main(str(fixture / 'index.md'))

        def status(text):
            for line in text.splitlines():
                cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
                if cells and cells[0] == 'VELDO-0223':
                    return cells[2]
            return None

        derived, committed = status((fixture / 'index.md').read_text()), status((ROOT / 'specs' / 'index.md').read_text())
        text_0223 = superseded.read_text()
        history = text_0223.split('## History', 1)[1] if '## History' in text_0223 else ''
        text_0215 = (ROOT / 'specs' / 'VELDO-0215-measured-mutation-case-deadlines.md').read_text()
        history_0215 = text_0215.split('## History', 1)[1] if '## History' in text_0215 else ''
        row('supersede/0223-not-claimable',
            derived == 'blocked' and committed == 'blocked'
            and all(word in history for word in ('VELDO-0358', '42171', '2026-11-18', '42829', '2026-11-20'))
            and 'VELDO-0358' in history_0215 and 'no longer a verdict' in history_0215,
            dict(derived=derived, committed=committed, history=history[:300]))

        # ---- AC14: the gate's result words are a closed list ------------------------------------
        printed = verify.read_text() + '\n' + host.read_text()
        words = sorted(set(re.findall(r'GATE: ([A-Z]+(?: [A-Z]+)*)', printed)))
        reasons = re.findall(r'GATE: NOT JUDGED \(([^)]*)\)', printed)
        about_load = [reason for reason in reasons
                      if re.search(r'load|pressure|contention|contended|quiet', reason, re.I)]
        row('supersede/result-words-closed',
            words == ['GREEN', 'NOT JUDGED', 'NOT STARTED', 'RED'] and bool(reasons) and not about_load,
            dict(words=words, reasons=reasons))


_v358_census()
