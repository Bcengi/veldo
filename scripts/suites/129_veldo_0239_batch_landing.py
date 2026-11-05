"""VELDO-0239: several reviewed units of a project are assembled onto trunk in one candidate, colliding migrations
are renumbered by the project's own hook, the candidate is gated once with every red inventoried, and all land
together on one owner approval.

Run: python3 scripts/selftest.py --suite 129_veldo_0239_batch_landing

Only shared ROOT, expect and launcher_fds are consumed. One temporary tree holds the installed .veldo copy every
organ loads, with this change's production modules (PRODUCTION) laid over it, so a registered mutation of any of
them reaches every row. Real throughout: Git (a scaffolded seed whose canonical gate is its own scripts/verify.sh
with two fixture stages, unit and integration; a disposable bare origin whose pre-receive hook records every
receive; the caller's clone the units are built in and whose local main a local landing moves), the batch's
isolated clone, VELDO-0058's installed gate in candidate mode, and the project's renumber hook, a fixture script
outside every repository that renames a newly merged migration to the next free number. The units' reviews, the
owner's approval answers and the other approvals a unit needs are fixture records handed to the batch. Every gate
run is counted by a logging `bash` first on PATH, which records each start of a verifier in candidate mode. No engine
runs, nothing logs in and no credential exists.
"""


def _v239_suite():
    import contextlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_batch.py': ROOT / ".veldo" / "control_batch.py",
        'control_intake.py': ROOT / ".veldo" / "control_intake.py",
    }
    ROWS = ('batch/renumber', 'batch/conflict', 'batch/hook-failed', 'batch/no-hook', 'batch/empty', 'batch/command',
            'gate/once', 'gate/inventory', 'land/together', 'land/local', 'land/stale', 'land/other-approval',
            'land/trunk-moved', 'single/unchanged')
    (BR, BC, BH, BN, BE, BM, GO, GI, LT, LL, LS, LO, LM, SU) = ROWS
    rows = {name: [] for name in ROWS}
    started = time.monotonic()

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    restore = []

    def exercise(base):
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copyfile(ROOT / '.veldo' / 'policy.yaml', mods / 'policy.yaml')
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        GP = load('v239_git', mods / 'git_process.py')
        IS = load('v239_scaffold', mods / 'init_scaffold.py')
        BT = load('v239_batch', mods / 'control_batch.py')
        OWNER = ('Owner', 'owner@example.invalid')
        BUILDER = ('Builder', 'builder@example.invalid')
        LANDER = ('Lander', 'lander@example.invalid')
        clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        clean.update(PYTHONDONTWRITEBYTECODE='1', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                     GIT_TERMINAL_PROMPT='0')

        def git(repo, *args, who=OWNER):
            r = GP.run(['git', '-C', str(repo), *args], capture_output=True, text=True, identity=who,
                       stdin=subprocess.DEVNULL, timeout=120)
            if r.returncode:
                raise RuntimeError('git %s: %s' % (' '.join(args[:3]), r.stderr.strip()[:300]))
            return r.stdout.strip()

        def files_at(repo, commit, directory):
            out = git(repo, 'ls-tree', '-r', '--name-only', commit, '--', directory)
            return sorted(line for line in out.splitlines() if line)

        gate_log = base / 'gate-runs.log'
        gate_log.write_text('')

        def gate_text(text):
            def declare(match):
                if match.group(1) == 'unit':
                    return 'CHECK_unit="required:python3 -B check_unit.py"'
                if match.group(1) == 'integration':
                    return 'CHECK_integration="required:python3 -B check_integration.py"'
                return 'CHECK_%s="na:fixture"' % match.group(1)
            return re.sub(r'(?m)^CHECK_([A-Za-z0-9_]+)=".*"$', declare, text)

        # The seed: a scaffolded repository whose own gate runs two fixture stages.
        seed = base / 'seed'
        seed.mkdir()
        GP.run(['git', 'init', '-q', '-b', 'main', str(seed)], check=True, capture_output=True)
        IS.scaffold(str(seed), templates=str(ROOT / 'engine'))
        (seed / 'scripts' / 'verify.sh').write_text(gate_text((seed / 'scripts' / 'verify.sh').read_text()))
        (seed / '.gitignore').write_text('__pycache__/\n')
        (seed / 'check_unit.py').write_text('\n'.join([
            'import pathlib, re, sys',
            'bad = []',
            'numbers = {}',
            "for p in sorted(pathlib.Path('migrations').glob('*.sql')):",
            "    numbers.setdefault(p.name.split('_', 1)[0], []).append('migrations/' + p.name)",
            'for number, names in sorted(numbers.items()):',
            '    if len(names) > 1:',
            "        bad.append('duplicate migration %s: %s' % (number, ' '.join(names)))",
            "for p in sorted(pathlib.Path('src').glob('*.py')):",
            "    if 'OK = True' not in p.read_text():",
            "        bad.append('src/%s is not OK' % p.name)",
            'for line in bad:',
            "    print('FAIL: ' + line)",
            "print('green' if not bad else 'red')",
            'sys.exit(1 if bad else 0)', '']))
        (seed / 'check_integration.py').write_text('\n'.join([
            'import pathlib, sys',
            "bad = ['src/%s breaks the integration' % p.name for p in sorted(pathlib.Path('src').glob('*.py'))",
            "       if 'INTEGRATION_BREAK' in p.read_text()]",
            'for line in bad:',
            "    print('FAIL: ' + line)",
            'sys.exit(1 if bad else 0)', '']))
        (seed / 'src').mkdir()
        (seed / 'src' / 'README').write_text('fixture sources\n')
        (seed / 'migrations').mkdir()
        for number, name in (('035', 'start'), ('036', 'accounts')):
            (seed / 'migrations' / ('%s_%s.sql' % (number, name))).write_text('-- %s\n' % name)
        (seed / 'README.md').write_text('fixture\nline two\n')
        subprocess.run([sys.executable, '-B', 'scripts/update_index.py'], cwd=str(seed), check=True,
                       capture_output=True, timeout=60, env=clean)
        git(seed, 'add', '-A')
        git(seed, 'commit', '-q', '-m', 'Fixture repository')
        first = git(seed, 'rev-parse', 'HEAD')
        subprocess.run(['bash', 'scripts/verify.sh'], cwd=str(seed), capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, env=clean, timeout=300, pass_fds=launcher_fds())
        git(seed, 'add', '--', '.veldo/last_verify', '.veldo/events.jsonl')
        git(seed, 'commit', '-q', '-m', 'Gate stamp for ' + first[:12])
        SEED = git(seed, 'rev-parse', 'HEAD')

        # Every gate run is counted by a logging `bash` first on PATH: control_verification starts the installed
        # verifier as `bash <verify.sh> --candidate <root> --sink <dir>`, before the gate confines its checks.
        logging_dir = base / 'logging-bash'
        logging_dir.mkdir()
        (logging_dir / 'bash').write_text('#!/bin/sh\ncase " $* " in *" --candidate "*) echo "$*" >> %s ;; esac\n'
                                          'exec %s "$@"\n' % (gate_log, shutil.which('bash')))
        (logging_dir / 'bash').chmod(0o755)
        saved_path = os.environ.get('PATH', '')
        os.environ['PATH'] = str(logging_dir) + os.pathsep + saved_path
        restore.append(lambda: os.environ.__setitem__('PATH', saved_path))

        # The origin: a bare repository whose pre-receive hook records every receive.
        bare = base / 'origin.git'
        received_log = base / 'received.log'
        GP.run(['git', 'clone', '-q', '--bare', str(seed), str(bare)], check=True, capture_output=True)
        git(bare, 'config', 'gc.auto', '0')
        hook_file = bare / 'hooks' / 'pre-receive'
        hook_file.write_text('#!/bin/sh\ncat >> %s\nexit 0\n' % received_log)
        hook_file.chmod(0o755)
        received_log.write_text('')
        caller, pusher = base / 'caller', base / 'pusher'
        for clone in (caller, pusher):
            GP.run(['git', 'clone', '-q', str(bare), str(clone)], check=True, capture_output=True)
            git(clone, 'config', 'gc.auto', '0')

        def received():
            return [tuple(line.split()) for line in received_log.read_text().splitlines() if line.strip()]

        def remote_tip():
            return git(bare, 'rev-parse', 'refs/heads/main')

        def gate_runs():
            return len([line for line in gate_log.read_text().splitlines() if line.strip()])

        # The project's renumber hook: outside every repository, named to the batch as the project's file names it.
        hooks = base / 'hooks'
        hooks.mkdir()
        (hooks / 'renumber.py').write_text('\n'.join([
            'import os, subprocess, sys',
            'watermark, merge = sys.argv[1], sys.argv[2]',
            "added = subprocess.run(['git', 'diff', '--name-only', '--diff-filter=A', merge + '^1', merge],",
            "                       capture_output=True, text=True, check=True).stdout.split()",
            "names = sorted(os.listdir('migrations'))",
            'for path in added:',
            "    if not path.startswith('migrations/') or not path.endswith('.sql'):",
            '        continue',
            "    name = path.split('/', 1)[1]",
            "    number, rest = name.split('_', 1)",
            "    others = [n for n in names if n != name and n.split('_', 1)[0] == number]",
            '    if others:',
            "        free = max(int(n.split('_', 1)[0]) for n in names) + 1",
            "        new = '%03d_%s' % (free, rest)",
            "        os.rename(os.path.join('migrations', name), os.path.join('migrations', new))",
            '        names = sorted(os.listdir("migrations"))',
            '']))
        (hooks / 'failing.py').write_text('import sys\nprint("the hook refuses")\nsys.exit(3)\n')
        HOOK = [sys.executable, '-B', str(hooks / 'renumber.py')]
        FAILING_HOOK = [sys.executable, '-B', str(hooks / 'failing.py')]

        # The units, each built on the seed in the caller's clone, each one commit.
        clock = [1000.0]
        units = {}

        def build(unit, files, on=None):
            git(caller, 'checkout', '-q', '-B', 'build/' + unit, on or SEED)
            for path, body in files.items():
                (caller / path).parent.mkdir(parents=True, exist_ok=True)
                (caller / path).write_text(body)
            git(caller, 'add', '-A')
            git(caller, 'commit', '-q', '-m', 'Implement ' + unit, who=BUILDER)
            clock[0] += 10
            units[unit] = {'unit': unit, 'commit': git(caller, 'rev-parse', 'HEAD'),
                           'review': {'state': 'passed', 'completed_at': clock[0], 'reviewer': 'reviewer-a'},
                           'landed': False}
            return units[unit]

        build('UNIT-1', {'migrations/037_users.sql': '-- users\n', 'src/unit_1.py': 'OK = True\n',
                         'README.md': 'fixture\nline two, unit one\n'})
        build('UNIT-2', {'migrations/037_orders.sql': '-- orders\n', 'src/unit_2.py': 'OK = True\n'})
        build('UNIT-3', {'src/unit_3.py': 'OK = True\n', 'README.md': 'fixture\nline two, unit three\n'})
        build('UNIT-4', {'src/unit_4.py': 'OK = False\n'})
        build('UNIT-5', {'src/unit_5.py': 'OK = True\nINTEGRATION_BREAK = 1\n'})
        build('UNIT-6', {'src/unit_6.py': 'OK = True\n'})
        build('UNIT-7', {'src/unit_7.py': 'OK = True\n'})
        build('UNIT-8', {'src/unit_8.py': 'OK = True\n'})
        build('UNIT-11', {'migrations/037_payments.sql': '-- payments\n', 'src/unit_11.py': 'OK = True\n'})
        unreviewed = dict(build('UNIT-9', {'src/unit_9.py': 'OK = True\n'}), review={'state': 'requested'})
        landed_before = dict(build('UNIT-10', {'src/unit_10.py': 'OK = True\n'}), landed=True)
        git(caller, 'checkout', '-q', '--detach', SEED)

        def batch(**options):
            told, asked, returned, receipts = [], [], [], []
            options.setdefault('hook', HOOK)
            made = BT.Batch(caller, project='fixture', identity=LANDER,
                            records=str(base / 'records'), tell=lambda kind, payload: told.append((kind, payload)),
                            ask=asked.append, fix_round=lambda unit, reds: returned.append((unit, reds)),
                            receipt=receipts.append, **options)
            made.told, made.asked, made.returned, made.receipts = told, asked, returned, receipts
            restore.append(made.discard)
            return made

        def grant_for(request):
            return {'subject': request['subject'], 'subject_digest': request['subject_digest'], 'by': 'owner',
                    'at': clock[0]}


        # AC1: batch/renumber. Two units add migration 037; the project's hook renumbers the second to 038.
        b = batch()
        record = b.assemble([units['UNIT-2'], units['UNIT-1'], unreviewed, landed_before])
        tip = record.get('tip')
        migrations = files_at(b.clone, tip, 'migrations') if tip else []
        check(BR, 'the batch took the reviewed, unlanded units in review-completion order [%s]'
              % [u['unit'] for u in record['units']], [u['unit'] for u in record['units']] == ['UNIT-1', 'UNIT-2'])
        check(BR, 'the batch tip holds 037 and 038, no two 037 [%s]' % migrations,
              'migrations/037_users.sql' in migrations and 'migrations/038_orders.sql' in migrations
              and len([m for m in migrations if m.startswith('migrations/037_')]) == 1)
        runs = record['hook_runs']
        second = next((h for h in runs if h['unit'] == 'UNIT-2'), {})
        check(BR, 'the hook ran after each merge with the watermark and the merge commit [%s]'
              % [(h['unit'], h['exit']) for h in runs],
              [h['unit'] for h in runs] == ['UNIT-1', 'UNIT-2'] and all(h['exit'] == 0 for h in runs)
              and all(h['hook'] == HOOK for h in runs))
        check(BR, 'the hook\'s change is its own recorded renumber commit with the rename [%s]' % second.get('renamed'),
              second.get('commit') and second.get('renamed') == [
                  {'old': 'migrations/037_orders.sql', 'new': 'migrations/038_orders.sql'}]
              and git(b.clone, 'rev-parse', second['commit'] + '^1') == second.get('merge')
              and next(u for u in record['units'] if u['unit'] == 'UNIT-2')['renumber'] == second['commit'])
        check(BR, 'the first unit\'s hook run changed nothing and made no commit',
              next((h for h in runs if h['unit'] == 'UNIT-1'), {}).get('commit') is None)
        stored = json.loads((base / 'records' / (record['id'] + '.json')).read_text())
        check(BR, 'the batch record holds project, watermark, units with their reviewed commits, hook runs and tip',
              stored['project'] == 'fixture' and stored['watermark'] == SEED and stored['tip'] == tip
              and [u['commit'] for u in stored['units']] == [units['UNIT-1']['commit'], units['UNIT-2']['commit']]
              and len(stored['hook_runs']) == 2)
        check(BR, 'the caller\'s main and the origin are untouched by assembly',
              git(caller, 'rev-parse', 'refs/heads/main') == SEED and remote_tip() == SEED)
        b.discard()

        # AC1: batch/conflict. A third unit conflicting with the first is left out; the other two are in.
        b = batch()
        record = b.assemble([units['UNIT-1'], units['UNIT-2'], units['UNIT-3']])
        check(BC, 'the conflicting unit is left out by name [%s]' % record['left_out'],
              [(x['unit'], x['reason']) for x in record['left_out']] == [('UNIT-3', 'conflict:UNIT-3')])
        check(BC, 'the other two are in the batch [%s]' % [u['unit'] for u in record['units']],
              [u['unit'] for u in record['units']] == ['UNIT-1', 'UNIT-2'] and record['state'] == 'assembled')
        tip_files = files_at(b.clone, record['tip'], 'src')
        check(BC, 'nothing of the left-out unit is in the tip [%s]' % tip_files,
              'src/unit_3.py' not in tip_files and 'src/unit_1.py' in tip_files and 'src/unit_2.py' in tip_files)
        b.discard()

        # A failing hook leaves the unit just merged out; the batch goes on.
        b = batch(hook=FAILING_HOOK)
        record = b.assemble([units['UNIT-6']])
        check(BH, 'a hook exiting non-zero leaves the unit out as hook_failed:renumber [%s]' % record['left_out'],
              [(x['unit'], x['reason']) for x in record['left_out']] == [('UNIT-6', 'hook_failed:renumber:UNIT-6')]
              and record['hook_runs'][0]['exit'] == 3 and record['state'] == 'empty')
        b.discard()

        # A project with no hook merges with no renumbering.
        b = batch(hook=None)
        record = b.assemble([units['UNIT-6'], units['UNIT-7']])
        check(BN, 'no hook: both merged, no hook run, no renumber commit [%s]' % record['hook_runs'],
              record['hook_runs'] == [] and [u['unit'] for u in record['units']] == ['UNIT-6', 'UNIT-7']
              and all(u['renumber'] is None for u in record['units']))
        b.discard()

        # A batch with no reviewed unit is empty and runs nothing.
        before = gate_runs()
        b = batch()
        outcome = BT.run(b, [unreviewed, landed_before])
        check(BE, 'no reviewed unit: empty, no clone, no gate, nobody asked [%s]' % outcome['outcome'],
              outcome['outcome'] == 'empty' and 'clone' not in outcome['record'] and gate_runs() == before
              and b.asked == [] and b.gate_runs == 0 and outcome['record']['units'] == [])

        # The owner's command: /batch <project>, from Telegram or the UI's project view.
        check(BM, 'the command names its project', BT.batch_command('/batch fixture') == 'fixture'
              and BT.batch_command('/batch@factory_bot fixture ') == 'fixture')
        check(BM, 'anything else is not the command', BT.batch_command('/batch') is None
              and BT.batch_command('please /batch fixture') is None and BT.batch_command('/batch a b') is None
              and BT.batch_command('/batches fixture') is None)
        IN = load('v239_intake', mods / 'control_intake.py')
        started_batches = []
        taken = IN.Intake.batch_started(types_namespace(batches=lambda **kw: started_batches.append(kw) or
                                                        {'outcome': 'green', 'batch': 'batch-x'}),
                                        {'text': '/batch fixture', 'principal': 'owner', 'source_kind': 'telegram_message',
                                         'source_id': 'telegram:1:2:3'})
        check(BM, 'intake hands the owner\'s /batch to the batch starter and writes no proposal [%s]' % taken,
              taken and taken.get('outcome') == 'batch' and started_batches == [
                  {'project': 'fixture', 'principal': 'owner', 'source': 'telegram:1:2:3'}])
        ordinary = IN.Intake.batch_started(types_namespace(batches=lambda **kw: started_batches.append(kw)),
                                           {'text': 'please build a thing', 'principal': 'owner',
                                            'source_kind': 'telegram_message', 'source_id': 'telegram:1:2:4'})
        check(BM, 'an ordinary message is not taken as a batch', ordinary is None and len(started_batches) == 1)

        # AC2: gate/once. One gate run per batch.
        before = gate_runs()
        b = batch()
        outcome = BT.run(b, [units['UNIT-1'], units['UNIT-2']])
        check(GO, 'the batch was gated once, by the project\'s own gate, and is green [%s %s %s]'
              % (outcome['outcome'], gate_runs() - before, (outcome['record']['gate'] or {}).get('terminal')),
              outcome['outcome'] == 'green' and gate_runs() - before == 1 and b.gate_runs == 1
              and (outcome['record']['gate'] or {}).get('commit') == outcome['record']['tip'])
        check(GO, 'every declared stage is in the observation, green [%s]' % outcome['record']['gate']['stages'],
              {s['stage']: s['result'] for s in outcome['record']['gate']['stages']} == {
                  'unit': 'pass', 'integration': 'pass'})
        check(GO, 'a green batch asks the owner once', len(b.asked) == 1)
        green_batch = b

        # AC2: gate/inventory. Two stages red; both in the inventory with their checks and units.
        before = gate_runs()
        b = batch()
        outcome = BT.run(b, [units['UNIT-4'], units['UNIT-5'], units['UNIT-6']])
        inventory = outcome['record']['inventory'] or []
        stages = {s['stage']: s['result'] for s in outcome['record']['gate']['stages']}
        check(GI, 'the batch is red and was gated once [%s %s]' % (outcome['outcome'], gate_runs() - before),
              outcome['outcome'] == 'red' and gate_runs() - before == 1 and b.gate_runs == 1)
        check(GI, 'both red stages are in the inventory with their checks and units [%s]' % inventory,
              {'stage': 'unit', 'check': 'src/unit_4.py is not OK', 'units': ['UNIT-4']} in inventory
              and {'stage': 'integration', 'check': 'src/unit_5.py breaks the integration', 'units': ['UNIT-5']}
              in inventory and stages.get('unit') == 'FAIL' and stages.get('integration') == 'FAIL')
        check(GI, 'the inventory went to the owner and into the record; each named unit returned to its fix round [%s]'
              % [u for u, _r in b.returned],
              [k for k, _p in b.told] == ['inventory'] and b.told[0][1]['inventory'] == inventory
              and sorted(u for u, _r in b.returned) == ['UNIT-4', 'UNIT-5'] and b.asked == [])
        refused = b.land({'subject': b.subject(), 'subject_digest': BT.digest(b.subject())})
        check(GI, 'nothing of a red batch lands: missing_evidence:gate [%s]' % refused.get('refusal'),
              refused.get('refusal') == 'missing_evidence:gate' and remote_tip() == SEED)
        b.discard()

        # AC3: land/together. One approval, one compare-and-swap, a receipt per unit naming the batch.
        b = green_batch
        request = b.asked[0]
        check(LT, 'the approval shows every unit with its review, the renumber commits, the gate and the destination',
              [u['unit'] for u in request['units']] == ['UNIT-1', 'UNIT-2']
              and all(u['review']['state'] == 'passed' for u in request['units'])
              and [r['unit'] for r in request['renumber_commits'] if r['commit']] == ['UNIT-2']
              and request['gate']['green'] is True and request['gate']['observation']
              and request['destination'] == 'land_and_push' and 'land and push to origin' in request['brief']
              and request['subject']['tip'] == b.record['tip'])
        received_before = len(received())
        landed = b.land(grant_for(request))
        moves = received()[received_before:]
        check(LT, 'the trunk is at the batch tip, moved once from the watermark [%s %s]' % (landed.get('outcome'), moves),
              landed.get('ok') is True and remote_tip() == b.record['tip']
              and moves == [(SEED, b.record['tip'], 'refs/heads/main')])
        check(LT, 'each unit has its revision_landed receipt naming the batch [%s]' % [r['unit'] for r in b.receipts],
              [r['unit'] for r in b.receipts] == ['UNIT-1', 'UNIT-2']
              and all(r['fact'] == 'revision_landed' and r['batch'] == b.record['id'] and r['tip'] == b.record['tip']
                      and r['confirmed']['commit'] == b.record['tip'] for r in b.receipts))
        check(LT, 'the batch record ends landed with the approval and the receipts',
              json.loads((base / 'records' / (b.record['id'] + '.json')).read_text())['state'] == 'landed'
              and b.record['approval']['granted']['subject_digest'] == request['subject_digest'])
        landed_tip = b.record['tip']
        b.discard()
        git(caller, 'fetch', '-q', 'origin')
        git(caller, 'update-ref', 'refs/heads/main', landed_tip)

        # AC3 under land_locally (VELDO-0235): the project repository's own main, nothing pushed.
        b = batch(destination='land_locally')
        outcome = BT.run(b, [units['UNIT-6'], units['UNIT-7']])
        received_before, origin_before = len(received()), remote_tip()
        landed = b.land(grant_for(b.asked[0])) if b.asked else {}
        check(LL, 'a local batch lands on the caller\'s main, nothing pushed [%s %s]'
              % (outcome['outcome'], landed.get('outcome')),
              landed.get('ok') is True and git(caller, 'rev-parse', 'refs/heads/main') == b.record['tip']
              and b.record['watermark'] == landed_tip and remote_tip() == origin_before
              and len(received()) == received_before and 'land locally on main' in b.asked[0]['brief']
              and not git(caller, 'for-each-ref', 'refs/veldo/batch/'))
        local_tip = b.record['tip']
        b.discard()
        git(caller, 'update-ref', 'refs/heads/main', landed_tip)

        # AC3: land/stale. The unit list changes after the grant: refused stale_subject:batch and asked again.
        b = batch()
        BT.run(b, [units['UNIT-6']])
        old = grant_for(b.asked[0])
        record = b.assemble([units['UNIT-6'], units['UNIT-7']])
        b.gate()
        asked_before, tip_before = len(b.asked), remote_tip()
        refused = b.land(old)
        check(LS, 'a grant bound to another unit list is refused stale_subject:batch [%s]' % refused.get('refusal'),
              refused.get('refusal') == 'stale_subject:batch' and remote_tip() == tip_before
              and b.record['state'] == 'green' and b.receipts == [])
        check(LS, 'the owner is asked again, bound to the new tip and unit list',
              len(b.asked) == asked_before + 1 and b.asked[-1]['subject']['units'] == [
                  ['UNIT-6', units['UNIT-6']['commit']], ['UNIT-7', units['UNIT-7']['commit']]]
              and b.asked[-1]['subject_digest'] != old['subject_digest'])
        forged = dict(grant_for(b.asked[-1]), subject=dict(b.asked[-1]['subject'], tip=SEED))
        check(LS, 'a grant bound to another tip is refused too',
              b.land(forged).get('refusal') == 'stale_subject:batch' and remote_tip() == tip_before)

        # AC3: another approval a unit needs (a protected path) is still asked; the batch approval never replaces it.
        b.requirements = lambda unit: (['missing_authority:protected_path/' + unit['unit']]
                                       if unit['unit'] == 'UNIT-7' else [])
        refused = b.land(grant_for(b.asked[-1]))
        check(LO, 'a unit lacking its own approval stops the whole batch [%s]' % refused.get('refusal'),
              refused.get('refusal') == 'missing_authority:protected_path/UNIT-7' and remote_tip() == tip_before
              and b.receipts == [])
        b.requirements = lambda unit: []
        b.discard()

        # AC3: land/trunk-moved. The trunk moves after the watermark: re-merge, re-run the hook, re-gate, ask again.
        b = batch()
        BT.run(b, [units['UNIT-8'], units['UNIT-11']])
        first_request = b.asked[0]
        git(pusher, 'fetch', '-q', 'origin')
        git(pusher, 'checkout', '-q', '-B', 'main', 'origin/main')
        (pusher / 'migrations' / '039_other.sql').write_text('-- another factory\n')
        git(pusher, 'add', '-A')
        git(pusher, 'commit', '-q', '-m', 'Another factory lands')
        git(pusher, 'push', '-q', 'origin', 'main')
        moved = remote_tip()
        moved_result = b.land(grant_for(first_request))
        check(LM, 'a trunk moved after the watermark ends the batch trunk_moved, nothing forced [%s]'
              % moved_result.get('outcome'), moved_result.get('outcome') == 'trunk_moved' and remote_tip() == moved)
        runs_before = gate_runs()
        again = b.reland()
        migrations = files_at(b.clone, b.record['tip'], 'migrations') if b.record.get('tip') else []
        check(LM, 're-landed on the new trunk: re-merged, hook re-run, gated again, asked again [%s %s]'
              % (again.get('ok'), migrations),
              again.get('ok') is True and b.record['watermark'] == moved and gate_runs() - runs_before == 1
              and 'migrations/040_payments.sql' in migrations and len(b.asked) == 2
              and b.record['follows'] is not None)
        check(LM, 'the old grant does not land the re-landed batch', b.land(grant_for(first_request)).get(
            'refusal') == 'stale_subject:batch' and remote_tip() == moved)
        final = b.land(grant_for(b.asked[-1]))
        check(LM, 'the fresh grant lands it [%s]' % final.get('outcome'),
              final.get('ok') is True and remote_tip() == b.record['tip'])
        b.discard()
        metrics = BT.metrics(json.loads(p.read_text()) for p in sorted((base / 'records').glob('*.json')))
        check(LM, 'metrics count batches by outcome and left-out units by reason [%s]' % metrics['left_out_by_reason'],
              metrics['batches'].get('landed') == 3 and metrics['left_out_by_reason'].get('conflict') == 1
              and metrics['left_out_by_reason'].get('hook_failed:renumber') == 1)

        # AC4: single-unit landing never reads or writes a batch record.
        for name in ('lander.py', 'control_landing.py', 'control_landing_station.py'):
            text = (mods / name).read_text()
            check(SU, '%s does not route through the batch' % name,
                  'control_batch' not in text and 'veldo.batch/v1' not in text)
        check(SU, 'every batch record is one this suite made [%s]' % local_tip[:12],
              all(json.loads(p.read_text())['project'] == 'fixture' for p in (base / 'records').glob('*.json')))

    def types_namespace(**fields):
        return __import__('types').SimpleNamespace(**fields)

    try:
        fast = None
        try:
            os.rmdir(tempfile.mkdtemp(prefix='fast-probe-', dir='/dev/shm'))
            fast = '/dev/shm'
        except OSError:
            pass
        with tempfile.TemporaryDirectory(prefix='v239-', dir=fast) as directory:
            try:
                exercise(Path(directory))
            finally:
                for undo in restore:
                    undo()
    except Exception as error:  # noqa: BLE001
        if os.environ.get('VELDO_0239_DETAILS'):
            __import__('traceback').print_exc()
        for row in ROWS:
            check(row, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:300]), False)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0239_DETAILS'):
                print('  VELDO-0239 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0239 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0239 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0239 suite seconds: %.3f' % (time.monotonic() - started))


_v239_suite()
