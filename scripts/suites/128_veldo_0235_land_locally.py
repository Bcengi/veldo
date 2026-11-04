"""VELDO-0235: each project has a landing destination, land and push or land locally, so a repository that never
pushes can run through the factory.

Run: python3 scripts/selftest.py --suite 128_veldo_0235_land_locally

Only shared ROOT, expect and launcher_fds are consumed. One temporary tree holds the installed .veldo copy every
organ loads, with this change's production modules (PRODUCTION) laid over it, so a registered mutation of any of
them reaches every row. Real throughout: Git (a scaffolded seed whose canonical gate is its own scripts/verify.sh
with one fixture check, a disposable bare origin whose pre-receive hook records every receive, the caller's clone
the builds are made in and whose local main a local landing moves, and the VELDO-0028 effect executor's
publication clone), the SQLite store with OpenSSH journal, command and effect-connection signatures, the
VELDO-0076 project service with the owner's signed commands, the land station (VELDO-0148) running the lander's
disposable candidate, VELDO-0058's installed gate, VELDO-0057's Landing and the executor process. The units, the
floor handoffs and the approvals are fixture records written with the store's generic command, and the
authority's candidate policy is a fixture that accepts, as in VELDO-0057's suite. Every Git started by name
goes through a logging `git` first on PATH (in front of VELDO-0153's identity wire, which maps the origin's
GitHub URL to the bare repository), so a row reads every push, fetch and ls-remote any process ran. The owner's
re-land grant brief is the service's own Line.grant over a recording inbox. No engine runs, nothing logs in and
no credential exists.
"""


def _v235_suite():
    import contextlib
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import stat
    import subprocess
    import sys
    import tempfile
    import time
    import types

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_project.py': ROOT / ".veldo" / "control_project.py",
        'control_landing.py': ROOT / ".veldo" / "control_landing.py",
        'control_landing_station.py': ROOT / ".veldo" / "control_landing_station.py",
        'lander.py': ROOT / ".veldo" / "lander.py",
        'control_effect_executor.py': ROOT / ".veldo" / "control_effect_executor.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    ROWS = ('destination/default-push', 'destination/owner-sets', 'destination/refused', 'local/lands',
            'local/trunk-moved', 'bound/brief', 'bound/destination-changed', 'push/unchanged')
    DP, DS, DR, LL, LM, BB, BC, PU = ROWS
    rows = {name: [] for name in ROWS}
    started = time.monotonic()

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def sha(body):
        return 'sha256:' + hashlib.sha256(body).hexdigest()

    fast = None
    try:
        os.rmdir(tempfile.mkdtemp(prefix='fast-probe-', dir='/dev/shm'))
        fast = '/dev/shm'
    except OSError:
        pass

    def exercise(base, wired):
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copyfile(ROOT / '.veldo' / 'policy.yaml', mods / 'policy.yaml')
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        S = load('v235_store', mods / 'control_store.py')
        SIG = load('v235_signer', mods / 'control_signer.py')
        GP = load('v235_git', mods / 'git_process.py')
        IS = load('v235_scaffold', mods / 'init_scaffold.py')
        FX = load('v235_executor', mods / 'control_effect_executor.py')
        CM = load('v235_membership', mods / 'control_membership.py')
        AC = CM.AC
        PJ = load('v235_project', mods / 'control_project.py')
        LD = load('v235_lander', mods / 'lander.py')
        LG = load('v235_landing', mods / 'control_landing.py')
        LS = load('v235_station', mods / 'control_landing_station.py')
        CS = load('v235_service', mods / 'control_service.py')
        DOMAIN, REPO = 'domain-235', 'repository-235'
        ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='store-235')
        OWNER = ('Owner', 'owner@example.invalid')
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

        def blob(repo, commit, path):
            r = GP.run(['git', '-C', str(repo), 'cat-file', 'blob', '%s:%s' % (commit, path)], capture_output=True)
            return None if r.returncode else r.stdout

        def gate_text(text):
            def declare(match):
                if match.group(1) == 'unit':
                    return 'CHECK_unit="required:python3 -B check.py"'
                return 'CHECK_%s="na:fixture"' % match.group(1)
            return re.sub(r'(?m)^CHECK_([A-Za-z0-9_]+)=".*"$', declare, text)

        # The units: one per scenario, each of its own project.
        PUSHED, LOCAL, MOVED, SWITCH, SET = ('VELDO-96%02d' % n for n in range(1, 6))
        UNITS = (PUSHED, LOCAL, MOVED, SWITCH, SET)
        PROJECT = {PUSHED: 'pushed', LOCAL: 'local', MOVED: 'local', SWITCH: 'switch', SET: 'pushset'}

        seed = base / 'seed'
        seed.mkdir()
        GP.run(['git', 'init', '-q', '-b', 'main', str(seed)], check=True, capture_output=True)
        IS.scaffold(str(seed), templates=str(ROOT / 'engine'))
        (seed / 'scripts' / 'verify.sh').write_text(gate_text((seed / 'scripts' / 'verify.sh').read_text()))
        (seed / '.gitignore').write_text('__pycache__/\n')
        (seed / 'check.py').write_text('\n'.join([
            'import pathlib, sys',
            "bad = [p.name for p in sorted(pathlib.Path('src').glob('*.py')) if 'OK = True' not in p.read_text()]",
            "print('red: %s' % bad if bad else 'green')",
            'sys.exit(1 if bad else 0)', '']))
        (seed / 'src').mkdir()
        (seed / 'src' / 'README').write_text('fixture sources\n')
        (seed / 'README.md').write_text('fixture\n')
        for sid in UNITS:
            (seed / 'specs' / ('%s-destination-fixture.md' % sid)).write_text('\n'.join([
                '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Destination fixture unit', 'status: ready',
                'risk: standard', 'owner: dmitry', 'human_approval: required', 'lane: standalone',
                'protected_paths: []', 'acceptance_criteria:', '  - id: AC1', '    text: The unit check passes.',
                'required_evidence: [unit]', 'rollback: git revert', '---', '', '## Intent', '', 'Fixture.', '']))
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

        # The origin: a bare repository whose pre-receive hook records every receive.
        bare = base / 'origin.git'
        received_log = base / 'received.log'
        GP.run(['git', 'clone', '-q', '--bare', str(seed), str(bare)], check=True, capture_output=True)
        git(bare, 'config', 'gc.auto', '0')
        git(bare, 'config', 'receive.autogc', 'false')
        hook = bare / 'hooks' / 'pre-receive'
        hook.write_text('#!/bin/sh\ncat >> %s\nexit 0\n' % received_log)
        hook.chmod(0o755)
        received_log.write_text('')
        caller, publisher = base / 'caller', base / 'publisher'
        for clone in (caller, publisher):
            GP.run(['git', 'clone', '-q', str(bare), str(clone)], check=True, capture_output=True)
            git(clone, 'config', 'gc.auto', '0')
        wire = __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/identity_wire.py'))['Wire'](base / 'wire')
        url = wire.remote('origin', bare)
        for clone in (caller, publisher):
            git(clone, 'remote', 'set-url', 'origin', url)
        wired.enter_context(wire.active())

        # The logging Git: first on PATH, in front of the wire's, for every process started from here on.
        logging_dir, git_log = base / 'logging-git', base / 'git-invocations.log'
        logging_dir.mkdir()
        following = shutil.which('git')
        # A process that cannot write the log (the gate's confinement) still runs Git. Candidate workspaces are the
        # lander's default (the system temporary directory): the candidate's confinement grants nothing in /dev/shm.
        (logging_dir / 'git').write_text('#!/bin/sh\n{ printf \'%%s\\037\' "$@"; printf \'\\n\'; } >> %s 2>/dev/null\n'
                                         'exec %s "$@"\n' % (git_log, following))
        (logging_dir / 'git').chmod(0o755)
        git_log.write_text('')
        saved_path = os.environ.get('PATH', '')
        os.environ['PATH'] = str(logging_dir) + os.pathsep + saved_path
        wired.callback(os.environ.__setitem__, 'PATH', saved_path)

        def invocations():
            return [line.split('\x1f')[:-1] for line in git_log.read_text().splitlines()]

        def command_of(argv):
            i = 0
            while i < len(argv):
                if argv[i] in ('-C', '-c'):
                    i += 2
                elif argv[i].startswith('-'):
                    i += 1
                else:
                    return argv[i]
            return None

        def remote_commands(since):
            return [a for a in invocations()[since:] if command_of(a) in ('push', 'fetch', 'ls-remote')]

        def received():
            return [tuple(line.split()) for line in received_log.read_text().splitlines() if line.strip()]

        def snapshot(top):
            seen = {}
            for directory, dirs, files in os.walk(str(top)):
                for name in dirs + files:
                    path = os.path.join(directory, name)
                    info = os.lstat(path)
                    digest = None
                    if stat.S_ISREG(info.st_mode):
                        with open(path, 'rb') as handle:
                            digest = hashlib.sha256(handle.read()).hexdigest()
                    seen[path] = (stat.S_IMODE(info.st_mode), digest)
            return seen

        def remote_tip():
            return git(bare, 'rev-parse', 'refs/heads/main')

        def local_tip():
            return git(caller, 'rev-parse', 'refs/heads/main')

        builds = {}

        def build(unit):
            git(caller, 'checkout', '-q', '-B', 'build/' + unit, SEED)
            source = 'src/%s.py' % unit.replace('-', '_').lower()
            (caller / source).write_text('OK = True\nUNIT = %r\n' % unit)
            git(caller, 'add', '-A')
            git(caller, 'commit', '-q', '-m', 'Implement ' + unit, who=LANDER)
            implementation = git(caller, 'rev-parse', 'HEAD')
            manifest = {'schema': 'veldo.proof/v1', 'spec_id': unit, 'producer': 'builder-a', 'commit': implementation,
                        'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [
                            {'type': 'unit', 'path': source, 'digest': sha((caller / source).read_bytes())}]}],
                        'checks': [{'name': 'unit', 'status': 'passed'}], 'rollback': 'git revert'}
            (caller / 'proof' / unit).mkdir(parents=True, exist_ok=True)
            (caller / 'proof' / unit / 'manifest.json').write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
            git(caller, 'add', '--', 'proof/' + unit)
            git(caller, 'commit', '-q', '-m', 'Proof for ' + unit, who=LANDER)
            evidence = git(caller, 'rev-parse', 'HEAD')
            builds[unit] = {'branch': 'build/' + unit, 'implementation': implementation, 'evidence': evidence,
                            'proof': sha(blob(caller, evidence, 'proof/%s/manifest.json' % unit))}

        for sid in UNITS:
            build(sid)
        # The caller's checkout is detached, so moving its local main moves no working tree.
        git(caller, 'checkout', '-q', '--detach', SEED)

        # The authority: the store, its keys, the lander's and the station's memberships, the owner and another person.
        private = base / 'private'
        private.mkdir(mode=0o700)
        public = {}
        for who in ('journal', 'landing', 'olga', 'pete'):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', who, '-f', str(private / who)],
                           check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
            public[who] = ' '.join((private / (who + '.pub')).read_text().split()[:2])
        db = base / 'authority' / 'control.sqlite3'
        db.parent.mkdir()
        writer = S.open_store(str(db))
        wired.callback(writer.close)
        __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))['bind'](
            mods, writer, DOMAIN, REPO, caller, LANDER)
        serial = [0]

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        def sign_as(who, message):
            # Never the SSH agent: the identity wire's fence records any contact with it.
            quiet = {k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')}
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(private / who), '-n', AC.SIGNATURE_NAMESPACE],
                                  input=message, capture_output=True, check=True, timeout=20, env=quiet).stdout.decode()

        def row(identity):
            found = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': found[0], 'version': found[1], 'digest': found[2], 'data': json.loads(found[3])} if found else None

        def put(identity, kind, data):
            serial[0] += 1
            current = row(identity)
            return S.execute(writer, dict(command_id='fixture-%d' % serial[0], principal='authority',
                                          operation='upsert_entity', nonce='fixture-%d' % serial[0], artifact_digests=[],
                                          expected_versions={identity: current['version'] if current else 0},
                                          parameters=dict(entity_id=identity, kind=kind, data=data)), 'authority', sign, 1)

        def journal_head():
            return writer.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]

        put('landing', 'membership', {'principal_type': 'service', 'roles': ['lander'], 'scope': [REPO],
                                      'revoked_at': None, 'expires_at': None})
        put('landing-key', 'verification_key', {'principal': 'landing', 'public_key': public['landing'],
                                                'effective_at': 0, 'retired_at': None, 'revoked_at': None})
        put('authority', 'membership', {'principal_type': 'service', 'roles': [], 'scope': [REPO],
                                        'revoked_at': None, 'expires_at': None})
        put('olga', 'membership', {'principal_type': 'person', 'roles': ['project_owner'],
                                   'scope': sorted(set(PROJECT.values())), 'revoked_at': None, 'expires_at': None})
        put('pete', 'membership', {'principal_type': 'person', 'roles': ['project_owner'], 'scope': ['elsewhere'],
                                   'revoked_at': None, 'expires_at': None})
        for who in ('olga', 'pete'):
            put('key-' + who, 'verification_key', {'principal': who, 'public_key': public[who], 'effective_at': 0})
        put('authority:' + DOMAIN, 'authority', {'state': 'active', 'generation': 1})
        for sid in UNITS:
            put(sid, 'execution_unit', {'state': 'READY', 'repository_uuid': REPO, 'revision': 1, 'project': PROJECT[sid],
                                        'backlog_item_uuid': 'backlog:' + sid, 'requirements': [], 'depends_on': [],
                                        'approvals_required': ['owner'] if sid == SWITCH else []})
            put(LS.floor_id(REPO, sid), 'floor_unit', {
                'unit': sid, 'state': 'handoff', 'attempt': 1, 'reviews': [], 'findings': {},
                'source': {'commit': builds[sid]['evidence']}, 'proof': {'digest': builds[sid]['proof']},
                'handoff': {'reviewers': ['reviewer-b'], 'required': 1, 'risk': 'standard', 'attempt': 1,
                            'source': {'commit': builds[sid]['evidence']}, 'proof': {'digest': builds[sid]['proof']}}})

        # The project service and the owner's signed commands.
        projects = PJ.Projects(S, CM, writer, ids, 'authority', sign, stop=lambda dispatch, reason: True)

        def packet(who, op, name, signer=None, **extra):
            serial[0] += 1
            body = dict(ids, operation=op, project=name, principal=who, command_id='pc-%d' % serial[0],
                        nonce='pn-%d' % serial[0], **extra)
            return {'command': body, 'signature': sign_as(signer or who, S.canonical_bytes(body))}

        def project(name):
            return PJ.read(S, writer, name)

        def activate(name):
            return projects.apply(packet('olga', 'activate', name, owner='olga',
                                         charter={'purpose': 'Land %s.' % name}, execution_repository=REPO,
                                         authority_policy={'grooming': ['project_owner']},
                                         coordination_budget={'capacity': 2, 'invocations': 20, 'wall_seconds': 600}))

        def set_destination(name, value, who='olga', signer=None):
            return projects.apply(packet(who, 'set_landing_destination', name, signer,
                                         project_version=(project(name) or {}).get('version'), landing_destination=value))

        for name in sorted(set(PROJECT.values())):
            activated = activate(name)
            if not activated.get('ok'):
                raise RuntimeError('activation of %s: %s' % (name, activated.get('reason')))

        # The land station, as every factory land runs, with the fixture candidate policy.
        effects_path = private / 'effects.json'
        effects_path.write_text(json.dumps({
            'store': str(db), 'journal_key': str(private / 'journal'), 'domain_uuid': DOMAIN, 'repository_uuid': REPO,
            'receivers': {'git-origin': {'kind': 'publication', 'repository': str(publisher), 'remote': url,
                                         'ref': 'refs/heads/main'}}}))
        events_root = base / 'events'
        (events_root / '.veldo').mkdir(parents=True)
        for folder in ('claims', 'observations'):
            (base / folder).mkdir()
        LAND = {'repository': str(caller), 'trunk': 'main', 'remote': 'origin', 'effects': str(effects_path),
                'target': 'git-origin', 'principal': 'landing', 'connection_key': str(private / 'landing'),
                'events_root': str(events_root), 'claims': str(base / 'claims'),
                'observations': str(base / 'observations')}
        empty_home = base / 'operator-home'
        empty_home.mkdir()
        calls = []

        def effect_call(config, request, principal, key):
            calls.append((request.get('operation'), request.get('dispatch_id')))
            saved = dict(os.environ)
            try:
                for name in [k for k in os.environ if k.startswith('GIT_')]:
                    del os.environ[name]
                os.environ.update({'HOME': str(empty_home), 'XDG_CONFIG_HOME': str(empty_home)})
                return FX.call(config, request, principal, key)
            finally:
                os.environ.clear()
                os.environ.update(saved)

        events = []
        station = LS.LandStation(S, writer, domain=DOMAIN, repository=REPO, land=LAND, principal='authority',
                                 signer='authority', sign=sign, call=effect_call, observe=events.append)
        asked, hooks = [], {}

        def authority_policy(unit, candidate):
            asked.append((unit.get('spec'), (candidate or {}).get('commit')))
            return {'ok': True, 'refusals': []}
        original_ops = station._ops

        def fixture_ops(evidence):
            ops = original_ops(evidence)
            ops.policy = authority_policy
            finalize = ops.finalize

            def before_finalize(unit):
                hook = hooks.pop((unit or {}).get('spec'), None)
                if hook is not None:
                    hook(ops)
                return finalize(unit)
            ops.finalize = before_finalize
            return ops
        station._ops = fixture_ops

        def land(sid, follows=None):
            try:
                return station.land(sid, evidence=builds[sid]['evidence'], holder='builder-a', generation=1,
                                    follows=follows)
            except LS.Refused as error:
                return {'state': 'not_opened', 'refusal': error.code, 'unit': sid}

        def effect(dispatch):
            found = row('effect:' + str(dispatch))
            return found['data'] if found and found['kind'] == 'protected_effect' else None

        def receipts(sid):
            return [json.loads(data) for (data,) in writer.execute("SELECT data FROM entities WHERE kind='completion_receipt'")
                    if json.loads(data).get('fact') == 'revision_landed' and (json.loads(data).get('subject') or {}).get('id') == sid]

        def shipped(sid):
            path = events_root / '.veldo' / 'events.jsonl'
            lines = [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []
            return [e for e in lines if e.get('type') == 'spec.shipped' and e.get('spec_id') == sid]

        def candidate_of(record):
            return (record.get('candidate') or {}).get('commit')

        # ---- AC1: a project record without the field lands and pushes, and is never rewritten for it -----------------
        held = project('pushed')
        check(DP, 'the record has no landing_destination and reads as land_and_push [%s]'
              % PJ.landing_destination(held), 'landing_destination' not in held
              and PJ.landing_destination(held) == 'land_and_push')
        since, before_received = len(invocations()), len(received())
        landed = land(PUSHED)
        after = project('pushed')
        check(DP, 'its land dispatch ran under land_and_push and landed [%s %s %s]'
              % (landed.get('destination'), landed.get('state'), landed.get('refusal')),
              landed.get('destination') == 'land_and_push' and landed.get('state') == 'landed')
        check(DP, 'the land published: the origin\'s main is the candidate, received once [%s]' % received()[before_received:],
              remote_tip() == candidate_of(landed)
              and [r[1:] for r in received()[before_received:]] == [(candidate_of(landed), 'refs/heads/main')])
        check(DP, 'the record is never rewritten for the field: same version, still no field',
              after.get('version') == held.get('version') and 'landing_destination' not in after)
        push_record = landed

        # ---- AC1: the owner's signed command sets it; any other value, an unsigned or another principal's is refused --
        head, version = journal_head(), project('local').get('version')
        refusals = []
        for label, attempt, code in (
                ('another value', lambda: set_destination('local', 'land_remote'), 'invalid_input:landing_destination'),
                ('a value of another type', lambda: set_destination('local', None), 'invalid_input:landing_destination'),
                ('signed by another key', lambda: set_destination('local', 'land_locally', signer='pete'), 'not_authorized'),
                ('another principal', lambda: set_destination('local', 'land_locally', who='pete'), 'not_authorized:scope'),
                ('an unsigned command', lambda: projects.apply({'command': dict(ids, operation='set_landing_destination',
                                                                                project='local', principal='olga',
                                                                                command_id='pc-unsigned', nonce='pn-unsigned',
                                                                                project_version=version,
                                                                                landing_destination='land_locally'),
                                                                'signature': ''}), 'not_authorized')):
            answer = attempt()
            refusals.append((label, answer.get('reason')))
            check(DR, '%s is refused as %s [%s]' % (label, code, answer.get('reason')),
                  answer.get('ok') is False and answer.get('reason') == code)
        check(DR, 'nothing was written: the journal head and the record version are unchanged',
              journal_head() == head and project('local').get('version') == version
              and 'landing_destination' not in project('local'))
        answer = set_destination('local', 'land_locally')
        local = project('local')
        history = local.get('landing_destination_history') or []
        observed = projects.observations[-1]
        check(DS, 'the owner\'s signed set_landing_destination is accepted [%s]' % answer.get('reason'),
              answer.get('ok') is True and local.get('landing_destination') == 'land_locally')
        check(DS, 'the record names the change: old and new value, the owner and his command id [%s]' % history,
              len(history) == 1 and history[0].get('previous') == 'land_and_push'
              and history[0].get('landing_destination') == 'land_locally' and history[0].get('by') == 'olga'
              and history[0].get('command_id') == observed.get('command_id'))
        check(DS, 'the observation names the project, the old and new value and the command id [%s]'
              % {k: observed.get(k) for k in ('project', 'previous', 'landing_destination', 'command_id')},
              observed.get('project') == 'project:local' and observed.get('previous') == 'land_and_push'
              and observed.get('landing_destination') == 'land_locally' and observed.get('outcome') == 'accepted')
        check(DS, 'it is not a lifecycle edge: the state and its history are unchanged',
              local.get('state') == 'ACTIVE' and len(local.get('history') or []) == 1)

        # ---- AC2: land locally moves the local main and pushes nothing ----------------------------------------------
        bare_before, since, calls_before = snapshot(bare), len(invocations()), len(calls)
        wire_before = len(wire.log.read_text().splitlines()) if wire.log.is_file() else 0
        watermark = local_tip()
        landed = land(LOCAL)
        remote_cmds = remote_commands(since)
        mine = effect(landed.get('dispatch_id')) or {}
        check(LL, 'the land dispatch ran under land_locally and landed [%s %s %s]'
              % (landed.get('destination'), landed.get('state'), landed.get('refusal')),
              landed.get('destination') == 'land_locally' and landed.get('state') == 'landed'
              and landed.get('destination_command') == history[0].get('command_id'))
        check(LL, 'the caller\'s local main is the candidate, moved from the watermark [%s %s]'
              % (watermark[:12], local_tip()[:12]), local_tip() == candidate_of(landed) and landed.get('watermark') == watermark)
        confirmed = [(r.get('publication_receipt') or {}).get('remote_confirmation') or {} for r in receipts(LOCAL)]
        check(LL, 'the revision_landed receipt is committed, confirmed by the local ref now [%s]' % confirmed,
              len(confirmed) == 1 and confirmed[0].get('commit') == local_tip()
              and confirmed[0].get('ref') == 'refs/heads/main' and confirmed[0].get('destination') == 'land_locally')
        check(LL, 'the VELDO-0051 projection derives spec.shipped from it [%s]' % shipped(LOCAL),
              len(shipped(LOCAL)) == 1 and shipped(LOCAL)[0].get('commit') == local_tip())
        check(LL, 'the publication records the trunk ref, the old tip and the new tip it moved [%s]'
              % {k: mine.get(k) for k in ('status', 'destination_kind', 'local', 'evidence')},
              mine.get('status') == 'completed' and mine.get('destination_kind') == 'land_locally'
              and (mine.get('local') or {}).get('ref') == 'refs/heads/main'
              and (mine.get('evidence') or {}).get('old_tip') == watermark
              and (mine.get('evidence') or {}).get('new_tip') == local_tip())
        check(LL, 'the bare origin is byte for byte unchanged', snapshot(bare) == bare_before)
        check(LL, 'the logging Git shows no push, fetch or ls-remote [%s]' % remote_cmds[:3], not remote_cmds)
        check(LL, 'the effect executor was never called and no identity transport ran (no push credential read)',
              len(calls) == calls_before
              and (len(wire.log.read_text().splitlines()) if wire.log.is_file() else 0) == wire_before)
        status = station.status().get('destinations') or {}
        check(LL, 'the station counts landings by destination and outcome [%s]' % status,
              (status.get('land_locally') or {}).get('landed') == 1 and (status.get('land_and_push') or {}).get('landed') == 1)

        # ---- AC2: a local main moved after the watermark is refused, never overwritten, and re-landed --------------
        moved = {}

        def move_local(ops):
            tip = local_tip()
            env = dict(clean, GIT_AUTHOR_NAME='Mover', GIT_AUTHOR_EMAIL='mover@example.invalid',
                       GIT_COMMITTER_NAME='Mover', GIT_COMMITTER_EMAIL='mover@example.invalid')
            commit = subprocess.run(['git', '-C', str(caller), 'commit-tree', tip + '^{tree}', '-p', tip, '-m',
                                     'Another commit on the local main'], capture_output=True, text=True, env=env,
                                    check=True).stdout.strip()
            git(caller, 'update-ref', 'refs/heads/main', commit, tip)
            moved['commit'] = commit
        hooks[MOVED] = move_local
        bare_before = snapshot(bare)
        refused = land(MOVED)
        mine = effect(refused.get('dispatch_id')) or {}
        check(LM, 'the land ends trunk_moved, the publication refused before the swap [%s %s %s]'
              % (refused.get('state'), refused.get('refusal'), mine.get('refusal')),
              refused.get('state') == 'trunk_moved' and mine.get('status') == 'refused'
              and mine.get('refusal') == 'stale-subject')
        check(LM, 'the moved local main is kept, never overwritten [%s]' % (refused.get('observed') or {}),
              moved.get('commit') and local_tip() == moved['commit']
              and (refused.get('observed') or {}).get('tip') == moved['commit']
              and (refused.get('observed') or {}).get('watermark') == refused.get('watermark'))
        relanded = land(MOVED, follows=refused.get('dispatch_id'))
        check(LM, 'the re-land under VELDO-0148 lands on the moved main [%s %s]'
              % (relanded.get('state'), relanded.get('refusal')),
              relanded.get('state') == 'landed' and relanded.get('follows') == refused.get('dispatch_id')
              and relanded.get('watermark') == moved.get('commit') and local_tip() == candidate_of(relanded)
              and GP.run(['git', '-C', str(caller), 'merge-base', '--is-ancestor', moved.get('commit') or 'HEAD',
                          local_tip()], capture_output=True).returncode == 0)
        check(LM, 'the bare origin is still unchanged', snapshot(bare) == bare_before)

        # ---- AC3: the owner's brief names the destination in words ----------------------------------------------
        briefs = []

        def brief_of(last):
            fake = types.SimpleNamespace(
                repository=REPO, station=types.SimpleNamespace(land_config=dict(LAND)),
                service=types.SimpleNamespace(inbox=lambda repository: types.SimpleNamespace(read=lambda aid: None)),
                open_question=lambda inbox, alias, unit, brief, choices, subject, key: (
                    briefs.append(brief) or ('olga', {'ok': True})))
            CS.Line.grant(fake, last.get('unit'), last, {'asked': [], 'awaiting': [], 'stopped': [], 'refused': []})
            return briefs[-1] if briefs else ''
        push_brief = brief_of({'unit': PUSHED, 'dispatch_id': 'dispatch/x/land-1', 'destination': 'land_and_push',
                               'watermark': SEED, 'subject': {'tree': 't', 'source': 's', 'proof': 'p',
                                                              'approvals': ['owner']}})
        local_brief = brief_of({'unit': LOCAL, 'dispatch_id': 'dispatch/y/land-1', 'destination': 'land_locally',
                                'watermark': SEED, 'subject': {'tree': 't', 'source': 's', 'proof': 'p',
                                                               'destination': 'land_locally', 'approvals': ['owner']}})
        check(BB, 'a land_and_push grant brief says "land and push to origin" [%s]' % push_brief[-120:],
              'Destination: land and push to origin.' in push_brief)
        check(BB, 'a land_locally grant brief says "land locally on main, nothing pushed" [%s]' % local_brief[-120:],
              'Destination: land locally on main, nothing pushed.' in local_brief)
        check(BB, 'the words are control_landing\'s own',
              LG.destination_words('land_and_push', 'origin', 'main') == 'land and push to origin'
              and LG.destination_words('land_locally', 'origin', 'main') == 'land locally on main, nothing pushed')

        # ---- AC3 (declared falsifier): the destination changed after the grant refuses and asks again --------------
        dry = LD.GitLandOps(caller, builds[SWITCH]['branch'], trunk='main', remote='origin', push=False,
                            policy=authority_policy, domain=DOMAIN, repository=REPO, identity_conn=writer,
                            observations=base / 'observations')
        try:
            dry.sync_main()
            dry.reconcile({'spec': SWITCH})
            tree = (dry.record() or {}).get('tree')
        finally:
            dry.discard()
        put('approval:%s:owner' % SWITCH, 'approval', {
            'unit': SWITCH, 'name': 'owner', 'revision': 1, 'state': 'granted',
            'subject': {'tree': tree, 'source': builds[SWITCH]['evidence'], 'proof': builds[SWITCH]['proof'],
                        'dependencies': {}}})
        changed = set_destination('switch', 'land_locally')
        bare_before, main_before = snapshot(bare), local_tip()
        waiting = land(SWITCH)
        subject = waiting.get('subject') or {}
        check(BC, 'the destination is changed after the grant [%s]' % changed.get('reason'), changed.get('ok') is True)
        check(BC, 'the land is refused as stale_subject:landing/destination and awaits a fresh grant [%s %s]'
              % (waiting.get('state'), waiting.get('refusals')),
              waiting.get('state') == 'awaiting_approval' and waiting.get('refusals') == ['stale_subject:landing/destination'])
        check(BC, 'nothing landed: the local main and the bare origin are unchanged',
              local_tip() == main_before and snapshot(bare) == bare_before and not receipts(SWITCH))
        check(BC, 'the exact subject a fresh grant binds names land_locally and the re-merged tree [%s]'
              % {k: subject.get(k) for k in ('destination', 'tree', 'approvals')},
              subject.get('destination') == 'land_locally' and subject.get('tree') == tree
              and subject.get('approvals') == ['owner'])
        asked_brief = brief_of(waiting)
        check(BC, 'the owner is asked again, the brief naming the destination [%s]' % asked_brief[-100:],
              'Destination: land locally on main, nothing pushed.' in asked_brief)
        granted = station.grant(SWITCH, station.record(waiting['dispatch_id']), owner='olga', basis={'answer': 'grant'})
        fresh = (row(granted[0]) or {}).get('data') or {} if granted else {}
        check(BC, 'his grant binds the destination [%s]' % (fresh.get('subject') or {}).get('destination'),
              (fresh.get('subject') or {}).get('destination') == 'land_locally')
        relanded = land(SWITCH, follows=waiting['dispatch_id'])
        check(BC, 'the land after his grant lands locally [%s %s]' % (relanded.get('state'), relanded.get('refusal')),
              relanded.get('state') == 'landed' and relanded.get('destination') == 'land_locally'
              and local_tip() == candidate_of(relanded) and snapshot(bare) == bare_before)

        # ---- AC4: land and push, set or absent, is today's: contract, push, remote re-read and receipt -------------
        set_answer = set_destination('pushset', 'land_and_push')
        since, before_received = len(invocations()), len(received())
        landed = land(SET)
        cmds = [command_of(a) for a in remote_commands(since)]
        check(PU, 'the owner may set land_and_push, and that land runs under it and lands [%s %s %s]'
              % (set_answer.get('reason'), landed.get('state'), landed.get('refusal')),
              set_answer.get('ok') is True and landed.get('destination') == 'land_and_push'
              and landed.get('state') == 'landed')
        for label, record in (('set', landed), ('absent', push_record)):
            dispatch = record.get('dispatch_id')
            contract = (row('contract/' + str(dispatch)) or {}).get('data') or {}
            published = effect(dispatch) or {}
            receipt = next((r for r in receipts(record.get('unit')) if (r.get('publication_receipt') or {}).get(
                'dispatch_id') == dispatch), {})
            confirmation = (receipt.get('publication_receipt') or {}).get('remote_confirmation') or {}
            check(PU, '%s: the VELDO-0028 effect contract is today\'s shape [%s]' % (label, sorted(contract)),
                  sorted(contract) == sorted(['domain_uuid', 'repository_uuid', 'unit', 'station', 'sandbox', 'dispatch_id',
                                              'kind', 'target', 'worker', 'status', 'deadline', 'permission_id', 'payload'])
                  and sorted(contract.get('payload') or {}) == ['commit', 'old_tip', 'revision', 'tree']
                  and contract.get('target') == 'git-origin')
            check(PU, '%s: the executor published it, every destination at the tip [%s]'
                  % (label, published.get('destination')), published.get('status') == 'completed'
                  and 'destination_kind' not in published
                  and [d.get('outcome') for d in (published.get('destination') or {}).get('destinations') or []] == ['at-tip'])
            check(PU, '%s: the receipt\'s confirmation is the remote\'s own answer [%s]' % (label, sorted(confirmation)),
                  sorted(confirmation) == ['commit', 'read_at', 'ref', 'remote']
                  and confirmation.get('commit') == candidate_of(record))
        check(PU, 'the set land pushed and re-read the remote: the origin received it, the log shows fetch, ls-remote and '
              'push [%s]' % sorted(set(cmds)), remote_tip() == candidate_of(landed)
              and [r[1:] for r in received()[before_received:]] == [(candidate_of(landed), 'refs/heads/main')]
              and {'fetch', 'ls-remote', 'push'} <= set(cmds))

    try:
        with tempfile.TemporaryDirectory(prefix='v235-', dir=fast) as directory, contextlib.ExitStack() as wired:
            exercise(Path(directory), wired)
    except Exception as error:  # noqa: BLE001
        for row in ROWS:
            check(row, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:300]), False)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0235_DETAILS'):
                print('  VELDO-0235 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0235 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0235 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0235 suite seconds: %.3f' % (time.monotonic() - started))


_v235_suite()
