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
outside every repository that renames a newly merged migration to the next free number. The authority is the real
SQLite control store with OpenSSH journal signatures: the units, their floor records handed off on their reviewed
commits (written by the setup principal, as the floor authority would write them), the project with its owner, the
VELDO-0064 inbox the owner's batch question is opened in and his own signed answer to it (the VELDO-0068
settlement the batch reads back), and the receipts the batch writes. The owner's command reaches the production
intake (control_intake) built with the production starter (control_batch_service) through both entrances: Telegram,
through a loopback Bot API serving getMe, getUpdates and sendMessage in the platform's documented shapes, the
production TelegramAcquisitionEdge and Acquirer; and the authenticated API's signed intake request, which the
project view's Start batch sends. The line that runs a requested batch is the production BatchLine. The other
approvals a unit needs are a callable, as before. Every gate run is counted by a logging `bash` first on PATH, which
records each start of a verifier in candidate mode. No engine runs, nothing logs in and no credential exists.
"""


def _v239_suite():
    import ast
    import contextlib
    import http.server
    import importlib.util
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import sys
    import tempfile
    import threading
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_batch.py': ROOT / ".veldo" / "control_batch.py",
        'control_intake.py': ROOT / ".veldo" / "control_intake.py",
        'control_batch_service.py': ROOT / ".veldo" / "control_batch_service.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_service_api.py': ROOT / ".veldo" / "control_service_api.py",
        'control_service_projects.py': ROOT / ".veldo" / "control_service_projects.py",
        'control_workflow_cycle_pm.py': ROOT / ".veldo" / "control_workflow_cycle_pm.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    ROWS = ('batch/renumber', 'batch/conflict', 'batch/hook-failed', 'batch/no-hook', 'batch/empty', 'batch/command',
            'gate/once', 'gate/inventory', 'land/together', 'land/local', 'land/stale', 'land/other-approval',
            'land/trunk-moved', 'single/unchanged', 'authority/unsettled-grant', 'authority/review-commit',
            'push/at-tip', 'push/at-watermark', 'push/elsewhere', 'wire/constructions', 'wire/telegram', 'wire/api',
            'wire/line')
    (BR, BC, BH, BN, BE, BM, GO, GI, LT, LL, LS, LO, LM, SU, AG, AR, PT, PW, PE, WC, WT, WA, WL) = ROWS
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
        CLM = load('v239_claims', mods / 'control_claim.py')
        S, CM, AC = CLM.S, CLM.CM, CLM.AC
        ENT = load('v239_entity', mods / 'entity_contract.py')
        INBOX = load('v239_inbox', mods / 'control_assignment.py')
        PROJ = load('v239_projection', mods / 'control_channel_projection.py')
        PRES = load('v239_presentation', mods / 'control_channel_presentation.py')
        ATTR = load('v239_attribution', mods / 'control_channel_attribution.py')
        IN = load('v239_intake', mods / 'control_intake.py')
        BS = load('v239_batch_service', mods / 'control_batch_service.py')
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

        # THE AUTHORITY: the real control store, its members and keys, the project and its owner, the inbox.
        keys = base / 'keys'
        keys.mkdir(mode=0o700)
        public = {}
        for who in ('authority', 'owner', 'colleague', 'api-edge', 'telegram-edge'):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v239-' + who, '-f', str(keys / who)],
                           check=True, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
            public[who] = (keys / (who + '.pub')).read_text().strip()

        def sign_as(who, message, namespace=AC.SIGNATURE_NAMESPACE):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / who), '-n', namespace], input=message,
                                  capture_output=True, check=True, timeout=30).stdout.decode()

        def journal_sign(message):
            return sign_as('authority', message, 'veldo-journal')

        def command_sign(message):
            return sign_as('authority', message)

        DOMAIN, REPO, STORE_UUID = 'batch-domain', 'batch-repo', 'batch-store'
        ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid=STORE_UUID)
        (base / 'authority').mkdir()
        conn = S.open_store(str(base / 'authority' / 'control.sqlite3'))
        restore.append(conn.close)
        serial = [0]

        def fixture(eid, kind, data):
            serial[0] += 1
            current = S.materialized_state(conn)['entities']
            S.execute(conn, dict(command_id='fixture-%d' % serial[0], principal='authority', operation='upsert_entity',
                                 parameters=dict(entity_id=eid, kind=kind, data=data),
                                 expected_versions={eid: current.get(eid, {}).get('version', 0)}, artifact_digests=[],
                                 nonce='fixture-n-%d' % serial[0]), 'authority', journal_sign, 1)

        for who, kind, scope in (('owner', 'person', [REPO, 'factory']), ('colleague', 'person', [REPO]),
                                 ('authority', 'service', ['*']), ('api-edge', 'service', ['*']),
                                 ('telegram-edge', 'service', [REPO])):
            fixture(who, 'membership', dict(principal_type=kind, roles=['project_owner'] if kind == 'person' else [],
                                            scope=scope, revoked_at=None, expires_at=None))
            if who != 'telegram-edge':
                fixture('key-' + who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
        fixture(AC.CHANNELS['telegram_chat']['edge_key_id'], 'verification_key',
                dict(principal='telegram-edge', public_key=public['telegram-edge'], effective_at=0))
        for name in ('fixture', 'second'):
            fixture('project:' + name, 'project', {'name': name, 'owner': 'owner', 'execution_repository': REPO,
                                                   'state': 'ACTIVE'})
        inbox = INBOX.Inbox(S, CM, CLM, ENT, conn, ids, 'authority', journal_sign)
        authority = BT.Authority(S, conn, inbox, domain=DOMAIN, repository=REPO, signer='authority', sign=journal_sign,
                                 command_sign=command_sign, store_uuid=STORE_UUID)

        def questions():
            """Every batch question the inbox holds: {subject digest: assignment record}."""
            prefix = INBOX.assignment_id(REPO, 'batch-approval-')
            return {json.loads(t)['subject']['digest']: json.loads(t) for (t,) in conn.execute(
                'SELECT data FROM entities WHERE substr(id, 1, ?) = ?', (len(prefix), prefix))}

        def answer(subject_digest, ruling='grant', who='owner'):
            """The owner's own signed answer to the batch question for one subject, through the inbox."""
            alias = BT.approval_alias(subject_digest)
            item = inbox.read(INBOX.assignment_id(REPO, alias)) or {'data': {}}
            serial[0] += 1
            body = dict(ids, operation='answer', alias=alias, principal=who, command_id='answer-%d' % serial[0],
                        nonce='answer-n-%d' % serial[0], request_version=item['data'].get('request_version'),
                        ruling=ruling)
            return inbox.apply({'command': body, 'signature': sign_as(who, S.canonical_bytes(body))})

        def stored_receipts(batch_id=None):
            return [r for r in authority.receipts() if batch_id is None or r.get('batch') == batch_id]

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
        reject = base / 'reject-push'
        hook_file.write_text('#!/bin/sh\nif [ -f %s ]; then cat >/dev/null; echo "rejected by the remote" >&2; exit 1; fi\n'
                             'cat >> %s\nexit 0\n' % (reject, received_log))
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

        def build(unit, files, on=None, project='fixture', reviewed=True):
            """One unit built in the caller's clone; its execution unit and, when reviewed, its floor record
            handed off on exactly that commit, in the store."""
            git(caller, 'checkout', '-q', '-B', 'build/' + unit, on or SEED)
            for path, body in files.items():
                (caller / path).parent.mkdir(parents=True, exist_ok=True)
                (caller / path).write_text(body)
            git(caller, 'add', '-A')
            git(caller, 'commit', '-q', '-m', 'Implement ' + unit, who=BUILDER)
            clock[0] += 10
            commit = git(caller, 'rev-parse', 'HEAD')
            fixture(unit, 'execution_unit', dict(state='READY', repository_uuid=REPO, project=project, revision=1))
            if reviewed:
                handoff(unit, commit)
            units[unit] = {'unit': unit, 'commit': commit}
            return units[unit]

        def handoff(unit, commit):
            fixture(BT.floor_id(REPO, unit), 'floor_unit', {
                'schema': 'veldo.floor/v1', 'unit': unit, 'domain': DOMAIN, 'repository': REPO, 'state': 'handoff',
                'attempt': 1, 'source': {'commit': commit}, 'handoff': {
                    'reviewers': ['reviewer-a'], 'required': 1, 'risk': 'standard', 'attempt': 1,
                    'source': {'commit': commit}}})

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
        build('UNIT-12', {'src/unit_12.py': 'OK = True\n'}, reviewed=False)
        build('UNIT-13', {'src/unit_13.py': 'OK = True\n'})
        build('UNIT-14', {'src/unit_14.py': 'OK = True\n'})
        build('UNIT-16', {'src/unit_16.py': 'OK = True\n'})
        build('UNIT-17', {'src/unit_17.py': 'OK = True\n'})
        # A caller's review state is not a review: UNIT-9 has none in the store.
        unreviewed = dict(build('UNIT-9', {'src/unit_9.py': 'OK = True\n'}, reviewed=False),
                          review={'state': 'passed', 'completed_at': 1})
        landed_before = build('UNIT-10', {'src/unit_10.py': 'OK = True\n'})
        fixture(BT.receipt_id('batch-earlier', 'UNIT-10'), BT.RECEIPT_KIND, {
            'schema': BT.RECEIPT_SCHEMA, 'fact': 'revision_landed', 'unit': 'UNIT-10', 'repository': REPO, 'revision': 1,
            'batch': 'batch-earlier', 'commit': landed_before['commit']})
        # UNIT-12's floor record is handed off on another commit than the one it is named with.
        handoff('UNIT-12', units['UNIT-13']['commit'])
        git(caller, 'checkout', '-q', '--detach', SEED)

        def batch(**options):
            told, returned = [], []
            options.setdefault('hook', HOOK)
            made = BT.Batch(caller, project='fixture', identity=LANDER, authority=authority,
                            records=str(base / 'records'), tell=lambda kind, payload: told.append((kind, payload)),
                            fix_round=lambda unit, reds: returned.append((unit, reds)), **options)
            made.told, made.returned = told, returned
            restore.append(made.discard)
            return made


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
        before, asked_before = gate_runs(), len(questions())
        b = batch()
        outcome = BT.run(b, [unreviewed, landed_before])
        check(BE, 'no reviewed unit: empty, no clone, no gate, nobody asked [%s]' % outcome['outcome'],
              outcome['outcome'] == 'empty' and 'clone' not in outcome['record'] and gate_runs() == before
              and len(questions()) == asked_before and b.gate_runs == 0 and outcome['record']['units'] == [])
        check(BE, 'the landed unit is landed by its receipt in the store, the unreviewed one has no review there',
              authority.landed('UNIT-10') and authority.review('UNIT-9') is None)

        # F2: a review in the store bound to another commit makes the unit ineligible; the store's review is the
        # only review.
        b = batch(hook=None)
        record = b.assemble([units['UNIT-12'], units['UNIT-13'], unreviewed])
        check(AR, 'a unit whose stored review is for another commit is not batched [%s]'
              % [u['unit'] for u in record['units']], [u['unit'] for u in record['units']] == ['UNIT-13'])
        check(AR, 'the review a unit carries in the batch is the store\'s, bound to its commit',
              record['units'][0]['review']['commit'] == units['UNIT-13']['commit']
              and record['units'][0]['review']['reviewers'] == ['reviewer-a'])
        check(AR, 'a batch without the store\'s authority cannot be built', raises(lambda: BT.Batch(
            caller, project='fixture', identity=LANDER, authority=types_namespace(review=lambda u: {'state': 'passed'}))))
        b.discard()

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
        green_digest = BT.digest(b.subject())
        check(GO, 'a green batch asks the owner once, in the inbox, for its subject',
              len(questions()) == asked_before + 1 and green_digest in questions()
              and questions()[green_digest]['owner'] == 'owner'
              and questions()[green_digest]['subject'] == {'kind': 'batch_approval', 'ref': b.record['id'],
                                                           'digest': green_digest})
        green_batch = b

        # AC2: gate/inventory. Two stages red; both in the inventory with their checks and units.
        before, asked_before = gate_runs(), len(questions())
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
              and sorted(u for u, _r in b.returned) == ['UNIT-4', 'UNIT-5'] and len(questions()) == asked_before)
        fixes = [json.loads(t) for (t,) in conn.execute("SELECT data FROM entities WHERE kind='batch_fix_round'")]
        check(GI, 'each fix round is recorded in the store with its reds [%s]' % [f['unit'] for f in fixes],
              sorted(f['unit'] for f in fixes if f['batch'] == b.record['id']) == ['UNIT-4', 'UNIT-5'])
        refused = b.land({'subject': b.subject(), 'subject_digest': BT.digest(b.subject())})
        check(GI, 'nothing of a red batch lands: missing_evidence:gate [%s]' % refused.get('refusal'),
              refused.get('refusal') == 'missing_evidence:gate' and remote_tip() == SEED)
        b.discard()

        # AC3: land/together. One approval, one compare-and-swap, a receipt per unit naming the batch.
        b = green_batch
        request = b.approval_request()
        # F2: a grant the caller builds from the batch's own subject, with no settlement, lands nothing.
        received_before, asked_before = len(received()), len(questions())
        forged = b.land({'subject': b.subject(), 'subject_digest': BT.digest(b.subject()), 'by': 'owner', 'at': 1})
        check(AG, 'a grant built from b.subject() without a settlement is refused [%s]' % forged.get('refusal'),
              forged.get('refusal') == 'missing_authority:approval/batch' and remote_tip() == SEED
              and len(received()) == received_before and stored_receipts(b.record['id']) == [])
        check(AG, 'the owner is not asked twice for the same subject', len(questions()) == asked_before)
        by_colleague = answer(request['subject_digest'], who='colleague')
        refused_again = b.land()
        check(AG, 'an answer by someone other than the owner is no settlement [%s %s]'
              % (by_colleague.get('reason'), refused_again.get('refusal')),
              refused_again.get('refusal') == 'missing_authority:approval/batch' and remote_tip() == SEED)
        check(LT, 'the approval shows every unit with its review, the renumber commits, the gate and the destination',
              [u['unit'] for u in request['units']] == ['UNIT-1', 'UNIT-2']
              and all(u['review']['state'] == 'passed' for u in request['units'])
              and [r['unit'] for r in request['renumber_commits'] if r['commit']] == ['UNIT-2']
              and request['gate']['green'] is True and request['gate']['observation']
              and request['destination'] == 'land_and_push' and 'land and push to origin' in request['brief']
              and request['subject']['tip'] == b.record['tip'])
        received_before = len(received())
        answered = answer(request['subject_digest'])
        landed = b.land()
        moves = received()[received_before:]
        check(LT, 'the trunk is at the batch tip, moved once from the watermark [%s %s]' % (landed.get('outcome'), moves),
              landed.get('ok') is True and remote_tip() == b.record['tip']
              and moves == [(SEED, b.record['tip'], 'refs/heads/main')])
        receipts = stored_receipts(b.record['id'])
        check(LT, 'the owner\'s own signed answer settled it [%s]' % answered, answered.get('ok') is True)
        check(LT, 'each unit has its revision_landed receipt naming the batch, in the store [%s]'
              % [r['unit'] for r in receipts],
              sorted(r['unit'] for r in receipts) == ['UNIT-1', 'UNIT-2']
              and all(r['fact'] == 'revision_landed' and r['batch'] == b.record['id'] and r['tip'] == b.record['tip']
                      and r['confirmed']['commit'] == b.record['tip'] and r['revision'] == 1 for r in receipts)
              and authority.landed('UNIT-1') and authority.landed('UNIT-2'))
        check(LT, 'the batch record ends landed with the approval and the receipts',
              json.loads((base / 'records' / (b.record['id'] + '.json')).read_text())['state'] == 'landed'
              and b.record['approval']['granted']['subject_digest'] == request['subject_digest']
              and b.record['approval']['granted']['by'] == 'owner')
        landed_tip = b.record['tip']
        b.discard()
        git(caller, 'fetch', '-q', 'origin')
        git(caller, 'update-ref', 'refs/heads/main', landed_tip)

        # AC3 under land_locally (VELDO-0235): the project repository's own main, nothing pushed.
        b = batch(destination='land_locally')
        outcome = BT.run(b, [units['UNIT-6'], units['UNIT-7']])
        received_before, origin_before = len(received()), remote_tip()
        answer(BT.digest(b.subject()))
        landed = b.land()
        check(LL, 'a local batch lands on the caller\'s main, nothing pushed [%s %s]'
              % (outcome['outcome'], landed.get('outcome')),
              landed.get('ok') is True and git(caller, 'rev-parse', 'refs/heads/main') == b.record['tip']
              and b.record['watermark'] == landed_tip and remote_tip() == origin_before
              and len(received()) == received_before and 'land locally on main' in b.approval_request()['brief']
              and not git(caller, 'for-each-ref', 'refs/veldo/batch/'))
        local_tip = b.record['tip']
        b.discard()
        git(caller, 'update-ref', 'refs/heads/main', landed_tip)

        # AC3: land/stale. The unit list changes after the grant: refused stale_subject:batch and asked again.
        # UNIT-6 and UNIT-7 landed locally above (and the trunk was put back), so two other units are batched here.
        b = batch()
        BT.run(b, [units['UNIT-16']])
        old = BT.digest(b.subject())
        answer(old)
        record = b.assemble([units['UNIT-16'], units['UNIT-17']])
        b.gate()
        asked_before, tip_before = len(questions()), remote_tip()
        refused = b.land()
        new = BT.digest(b.subject())
        check(LS, 'a settled grant bound to another unit list is refused stale_subject:batch [%s]' % refused.get('refusal'),
              refused.get('refusal') == 'stale_subject:batch' and remote_tip() == tip_before
              and b.record['state'] == 'green' and stored_receipts(b.record['id']) == [])
        check(LS, 'the owner is asked again, bound to the new tip and unit list',
              len(questions()) == asked_before + 1 and new in questions() and b.subject()['units'] == [
                  ['UNIT-16', units['UNIT-16']['commit']], ['UNIT-17', units['UNIT-17']['commit']]] and new != old)
        forged = {'subject': dict(b.subject(), tip=SEED), 'subject_digest': BT.digest(dict(b.subject(), tip=SEED))}
        check(LS, 'a grant bound to another tip is refused too',
              b.land(forged).get('refusal') == 'stale_subject:batch' and remote_tip() == tip_before)
        answer(new)

        # AC3: another approval a unit needs (a protected path) is still asked; the batch approval never replaces it.
        b.requirements = lambda unit: (['missing_authority:protected_path/' + unit['unit']]
                                       if unit['unit'] == 'UNIT-17' else [])
        refused = b.land()
        check(LO, 'a unit lacking its own approval stops the whole batch [%s]' % refused.get('refusal'),
              refused.get('refusal') == 'missing_authority:protected_path/UNIT-17' and remote_tip() == tip_before
              and stored_receipts(b.record['id']) == [])
        b.requirements = lambda unit: []
        b.discard()

        # AC3: land/trunk-moved. The trunk moves after the watermark: re-merge, re-run the hook, re-gate, ask again.
        b = batch()
        BT.run(b, [units['UNIT-8'], units['UNIT-11']])
        first_request = BT.digest(b.subject())
        answer(first_request)
        git(pusher, 'fetch', '-q', 'origin')
        git(pusher, 'checkout', '-q', '-B', 'main', 'origin/main')
        (pusher / 'migrations' / '039_other.sql').write_text('-- another factory\n')
        git(pusher, 'add', '-A')
        git(pusher, 'commit', '-q', '-m', 'Another factory lands')
        git(pusher, 'push', '-q', 'origin', 'main')
        moved = remote_tip()
        moved_result = b.land()
        check(LM, 'a trunk moved after the watermark ends the batch trunk_moved, nothing forced [%s]'
              % moved_result.get('outcome'), moved_result.get('outcome') == 'trunk_moved' and remote_tip() == moved)
        check(PE, 'the trunk found elsewhere after the push is a moved trunk, found and recorded [%s]'
              % moved_result.get('found'), moved_result.get('found') == moved and b.record['state'] == 'trunk_moved'
              and b.record['landing']['found'] == moved and stored_receipts(b.record['id']) == [])
        runs_before, asked_before = gate_runs(), len(questions())
        again = b.reland()
        migrations = files_at(b.clone, b.record['tip'], 'migrations') if b.record.get('tip') else []
        check(LM, 're-landed on the new trunk: re-merged, hook re-run, gated again, asked again [%s %s]'
              % (again.get('ok'), migrations),
              again.get('ok') is True and b.record['watermark'] == moved and gate_runs() - runs_before == 1
              and 'migrations/040_payments.sql' in migrations and len(questions()) == asked_before + 1
              and b.record['follows'] is not None)
        check(LM, 'the old grant does not land the re-landed batch', b.land().get(
            'refusal') == 'stale_subject:batch' and remote_tip() == moved)
        answer(BT.digest(b.subject()))
        final = b.land()
        check(LM, 'the fresh grant lands it [%s]' % final.get('outcome'),
              final.get('ok') is True and remote_tip() == b.record['tip'])
        b.discard()
        metrics = BT.metrics(json.loads(p.read_text()) for p in sorted((base / 'records').glob('*.json')))
        check(LM, 'metrics count batches by outcome and left-out units by reason [%s]' % metrics['left_out_by_reason'],
              metrics['batches'].get('landed') == 3 and metrics['left_out_by_reason'].get('conflict') == 1
              and metrics['left_out_by_reason'].get('hook_failed:renumber') == 1)

        # F3: after the push the trunk is read with no expectation and classified by what was found there.
        git(caller, 'fetch', '-q', 'origin')
        b = batch(hook=None)
        BT.run(b, [units['UNIT-13']])
        answer(BT.digest(b.subject()))
        real_git, failed_reads = b._git, []

        def unreadable(times):
            def git_boundary(repo, *args, **kw):
                if args and args[0] == 'ls-remote' and len(failed_reads) < times:
                    failed_reads.append(args)
                    return types_namespace(returncode=128, stdout='', stderr='fatal: the remote hung up')
                return real_git(repo, *args, **kw)
            return git_boundary
        b._git = unreadable(2)
        unread = b.land()
        b._git = real_git
        check(PT, 'a push followed by a trunk that cannot be read is unknown by name, no receipts yet [%s]'
              % unread.get('refusal'), unread.get('refusal') == 'unknown_outcome:batch/trunk'
              and remote_tip() == b.record['tip'] and b.record['state'] == 'green'
              and stored_receipts(b.record['id']) == [])
        again = b.land()
        check(PT, 'landing again finds the trunk at the tip and lands, with the receipts [%s]' % again.get('outcome'),
              again.get('ok') is True and remote_tip() == b.record['tip']
              and [r['unit'] for r in stored_receipts(b.record['id'])] == ['UNIT-13'])
        b.discard()
        b = batch(hook=None)
        BT.run(b, [units['UNIT-14']])
        answer(BT.digest(b.subject()))
        failed_reads[:] = []
        b._git = unreadable(1)
        once = b.land()
        check(PT, 'a push whose first read fails and second finds the tip lands with the receipts [%s]'
              % once.get('outcome'), once.get('ok') is True and len(failed_reads) == 1
              and [r['unit'] for r in stored_receipts(b.record['id'])] == ['UNIT-14'])
        b._git = real_git
        b.discard()
        # A push the remote rejects (not the lease) leaves the trunk at the watermark: a push failure by name.
        build('UNIT-15', {'src/unit_15.py': 'OK = True\n'})
        b = batch(hook=None)
        BT.run(b, [units['UNIT-15']])
        answer(BT.digest(b.subject()))
        watermark = remote_tip()
        reject.write_text('rejected\n')
        rejected = b.land()
        reject.unlink()
        check(PW, 'a rejected push with the trunk still at the watermark is a push failure, not trunk_moved [%s]'
              % rejected.get('refusal'), rejected.get('refusal') == 'unavailable_service:git/push'
              and rejected.get('outcome') == 'refused' and remote_tip() == watermark
              and b.record['state'] == 'green' and stored_receipts(b.record['id']) == [])
        retried = b.land()
        check(PW, 'the same batch lands once the remote accepts [%s]' % retried.get('outcome'),
              retried.get('ok') is True and remote_tip() == b.record['tip'])
        b.discard()

        # F1: every production construction of Intake passes the production batch starter.
        constructions = []
        for path in sorted(mods.glob('*.py')):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Call) and (getattr(node.func, 'attr', None) == 'Intake'
                                                   or getattr(node.func, 'id', None) == 'Intake'):
                    given = {k.arg: ast.unparse(k.value) for k in node.keywords}
                    constructions.append((path.name, node.lineno, given.get('batches') or ''))
        wired_files = sorted({name for name, _line, value in constructions})
        check(WC, 'the intake is built in the three production places [%s]' % wired_files,
              wired_files == ['control_service_api.py', 'control_service_projects.py', 'control_workflow_cycle_pm.py'])
        check(WC, 'every one passes the batch starter [%s]' % constructions,
              constructions and all("('control_batch_service').starter(" in value for _n, _l, value in constructions))
        scaffold = load('v239_scaffold_installed', mods / 'init_scaffold.py')
        check(WC, 'the installer lays the batch modules every intake loads',
              '.veldo/control_batch.py' in scaffold._FILES and '.veldo/control_batch_service.py' in scaffold._FILES)

        # F1: the owner's /batch <project> through the production intake, from Telegram and from the API.
        git(caller, 'fetch', '-q', 'origin')
        build('S-1', {'migrations/037_second.sql': '-- second\n', 'src/s_1.py': 'OK = True\n'}, on=remote_tip(),
              project='second')
        build('S-2', {'migrations/037_more.sql': '-- more\n', 'src/s_2.py': 'OK = True\n'}, on=remote_tip(),
              project='second')
        git(caller, 'checkout', '-q', '--detach', remote_tip())
        git(caller, 'update-ref', 'refs/heads/main', remote_tip())
        bot = {'token': 'batch-bot', 'bot': {'id': 8239000001, 'is_bot': True, 'first_name': 'Factory',
                                             'username': 'factory_batch_bot'},
               'updates': [], 'next': 7000, 'update_next': 500000000, 'chats': {}, 'sent': []}
        people = {'owner': 6239001, 'colleague': 6239002}
        for who, chat in people.items():
            bot['chats'][chat] = {'id': chat, 'type': 'private', 'first_name': who.title()}
            fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                    dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                         revoked_at=None))

        class BotApi(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
                body = json.loads(raw) if raw else {}
                token, _, method = self.path.partition('/bot')[2].partition('/')
                if token != bot['token']:
                    return self.reply(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
                if method == 'getMe':
                    return self.reply(200, {'ok': True, 'result': dict(bot['bot'], can_join_groups=True,
                                                                       can_read_all_group_messages=False,
                                                                       supports_inline_queries=False)})
                if method == 'getUpdates':
                    offset = body.get('offset') or 0
                    bot['updates'] = [u for u in bot['updates'] if u['update_id'] >= offset]
                    return self.reply(200, {'ok': True, 'result': bot['updates'][:body.get('limit') or 100]})
                if method == 'sendMessage':
                    bot['sent'].append(body)
                    bot['next'] += 1
                    chat = bot['chats'].get(body.get('chat_id')) or {'id': body.get('chat_id'), 'type': 'private'}
                    return self.reply(200, {'ok': True, 'result': {'message_id': bot['next'], 'from': bot['bot'],
                                                                   'chat': chat, 'date': 1790200000,
                                                                   'text': body.get('text')}})
                return self.reply(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

            def reply(self, code, value):
                payload = json.dumps(value).encode()
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), BotApi)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        restore.append(server.shutdown)
        url = 'http://127.0.0.1:%d' % server.server_address[1]
        presenter = PRES.Presenter(S, CM, PROJ, inbox, PRES.TelegramPresentationEdge(PROJ, url, bot['token']), conn,
                                   'authority', journal_sign, assignment=INBOX)
        acquirer = ATTR.Acquirer(S, CM, PROJ, PRES, presenter, ATTR.TelegramAcquisitionEdge(PROJ, url, bot['token']),
                                 conn, 'authority', journal_sign, 'telegram-edge',
                                 lambda message: sign_as('telegram-edge', message))
        # Built as every production intake is: the store's projects and the production batch starter.
        intake = IN.Intake(S, CM, AC, acquirer, conn, domain=DOMAIN, projects=lambda: IN.store_projects(conn),
                           api_edge='api-edge', journal_signer='authority', sign=journal_sign,
                           asker=PRES.TelegramPresentationEdge(PROJ, url, bot['token']),
                           batches=BS.starter(S, conn, domain=DOMAIN, signer='authority', sign=journal_sign))

        def telegram(who, text):
            bot['next'] += 1
            bot['update_next'] += 1
            chat = bot['chats'][people[who]]
            held = {'message_id': bot['next'], 'from': {'id': chat['id'], 'is_bot': False, 'first_name': who.title()},
                    'chat': dict(chat), 'date': 1790200000 + bot['next'], 'text': text}
            bot['updates'].append({'update_id': bot['update_next'], 'message': held})
            acquired = acquirer.acquire()
            # take_telegram answers every kept update in update order: this message's answer is the last.
            taken = intake.take_telegram()
            mine = [a for a in acquired if a.get('update_id') == bot['update_next']]
            return taken[-1:] if mine and taken else [{'outcome': 'missing', 'acquired': acquired, 'taken': taken}]

        def proposals():
            return conn.execute("SELECT COUNT(*) FROM entities WHERE kind='intake_proposal'").fetchone()[0]

        def batch_requests():
            return {i: json.loads(t) for i, t in conn.execute("SELECT id, data FROM entities WHERE kind='batch_request'")}

        proposals_before = proposals()
        by_owner = telegram('owner', '/batch second')
        requests_now = batch_requests()
        started_request = next(iter(requests_now.values()), {})
        check(WT, 'the owner\'s Telegram /batch second starts a batch request, not a proposal [%s]' % by_owner,
              len(by_owner) == 1 and by_owner[0].get('outcome') == 'batch' and by_owner[0].get('batch_outcome') ==
              'requested' and len(requests_now) == 1 and proposals() == proposals_before)
        check(WT, 'the request names the project, the owner and the store\'s eligible units with their commits [%s]'
              % started_request.get('units'), started_request.get('project') == 'second'
              and started_request.get('principal') == 'owner' and started_request.get('units') == [
                  {'unit': 'S-1', 'commit': units['S-1']['commit']}, {'unit': 'S-2', 'commit': units['S-2']['commit']}])
        by_colleague = telegram('colleague', '/batch second')
        check(WT, 'a colleague\'s /batch is refused as not the owner and starts nothing [%s]' % by_colleague,
              len(by_colleague) == 1 and by_colleague[0].get('batch_outcome') == 'refused'
              and by_colleague[0].get('reason') == 'missing_authority:batch/owner'
              and len(batch_requests()) == 1 and proposals() == proposals_before)

        line = BS.BatchLine(S, conn, domain=DOMAIN, repository=REPO,
                            land={'repository': str(caller), 'trunk': 'main', 'remote': 'origin'}, signer='authority',
                            sign=journal_sign, command_sign=command_sign, inbox=lambda: inbox, identity=LANDER,
                            store_uuid=STORE_UUID, hook=HOOK)
        restore.append(lambda: [held.discard() for held in line.held.values()])
        first_pass = line.pass_once()
        request_after = batch_requests()
        rid = next(iter(request_after))
        awaiting = request_after[rid]
        check(WL, 'the line assembles, renumbers, gates once and asks the owner [%s]' % first_pass,
              [p['state'] for p in first_pass] == ['awaiting_approval'] and awaiting['tip']
              and len(awaiting['inventory'] or []) == 0 and line.held[rid].record['hook_runs'][-1]['renamed'] == [
                  {'old': 'migrations/037_more.sql', 'new': 'migrations/%03d_more.sql' % (
                      max(int(n.split('/')[-1][:3]) for n in files_at(caller, remote_tip(), 'migrations')) + 2)}]
              and BT.digest(line.held[rid].subject()) in questions())
        check(WL, 'nothing lands while the owner has not answered', [p['state'] for p in line.pass_once()] == [
            'awaiting_approval'] and remote_tip() != awaiting['tip'])
        answer(BT.digest(line.held[rid].subject()))
        tip_expected = awaiting['tip']
        second_pass = line.pass_once()
        check(WL, 'his settled grant lands the batch on the next pass, receipts in the store [%s]' % second_pass,
              [p['state'] for p in second_pass] == ['landed'] and remote_tip() == tip_expected
              and sorted(r['unit'] for r in stored_receipts(awaiting['batch'])) == ['S-1', 'S-2']
              and batch_requests()[rid]['state'] == 'landed' and authority.landed('S-1'))

        git(caller, 'fetch', '-q', 'origin')
        build('S-3', {'src/s_3.py': 'OK = True\n'}, on=remote_tip(), project='second')
        git(caller, 'checkout', '-q', '--detach', remote_tip())

        def api_request(principal, text, request_id):
            body = {'schema': 'veldo.intake_api_request/v1', 'domain': DOMAIN, 'request_id': request_id,
                    'edge': 'api-edge', 'principal': principal, 'text': text, 'project': None, 'clarifies': None}
            return intake.receive('api_request', {'request': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))})

        proposals_before = proposals()
        by_api = api_request('owner', '/batch second', 'req-batch-1')
        api_rid = BS.request_id('req-batch-1')
        api_request_record = batch_requests().get(api_rid) or {}
        check(WA, 'the project view\'s /batch second through the API starts a batch request, not a proposal [%s]'
              % by_api, by_api.get('outcome') == 'batch' and by_api.get('batch_outcome') == 'requested'
              and proposals() == proposals_before)
        check(WA, 'a landed unit is not batched again: only the new unit is in it [%s]' % api_request_record.get('units'),
              api_request_record.get('units') == [{'unit': 'S-3', 'commit': units['S-3']['commit']}])
        repeated = api_request('owner', '/batch second', 'req-batch-1')
        not_owner = api_request('colleague', '/batch second', 'req-batch-2')
        check(WA, 'a repeated request starts nothing again; a colleague is refused [%s %s]' % (repeated, not_owner),
              repeated.get('repeated') is True and not_owner.get('reason') == 'missing_authority:batch/owner'
              and BS.request_id('req-batch-2') not in batch_requests() and proposals() == proposals_before)
        line.pass_once()
        answer(BT.digest(line.held[api_rid].subject()))
        landed_by_api = line.pass_once()
        check(WA, 'the line lands the API-started batch on the owner\'s answer [%s]' % landed_by_api,
              [p['state'] for p in landed_by_api] == ['landed'] and
              [r['unit'] for r in stored_receipts(batch_requests()[api_rid]['batch'])] == ['S-3'])

        # AC4: single-unit landing never reads or writes a batch record.
        for name in ('lander.py', 'control_landing.py', 'control_landing_station.py'):
            text = (mods / name).read_text()
            check(SU, '%s does not route through the batch' % name,
                  'control_batch' not in text and 'veldo.batch/v1' not in text)
        check(SU, 'every batch record is one this suite made [%s]' % local_tip[:12],
              all(json.loads(p.read_text())['project'] == 'fixture' for p in (base / 'records').glob('*.json')))

    def types_namespace(**fields):
        return __import__('types').SimpleNamespace(**fields)

    def raises(call):
        try:
            call()
        except Exception:  # noqa: BLE001 - any refusal counts
            return True
        return False

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
