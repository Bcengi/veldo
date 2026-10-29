"""VELDO-0188: the running factory starts a line for a project the moment the store records it, staffed from the
project's team or the default team, and stops the line of a closed project, with no reinstall and no restart.

Run: python3 scripts/selftest.py --suite 116_veldo_0188_project_lines

Uses shared ROOT, expect and __suite_file__. AC1 runs an installed authority service as a child process through
its installed executable and configuration, with real VELDO-0143 provisioning and VELDO-0161 adoption. Its
qualified fake Codex executable commits the first unit in each repository through the real account pool and
launch receiver. PID, process start time and installation digests remain unchanged until the explicit restart.
The commit and author checks adapt proof/VELDO-0143/round4/first-unit-for-0188.py.

The follow, staffing and closing rows also exercise Service and FactoryLoop directly on the signed VELDO-0152
fixture. These smaller rows expose exact pass boundaries, in-flight roles and refusal diagnostics. Their protocol
fake receiver and fixed account are explicit test seams. All mutations replace the same production copy in both
fixtures. Every process is joined before its temporary fixture is removed.
"""


def _v188_suite():
    import contextlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    import time

    # Literal anchors: the registered mutation driver substitutes one production copy here.
    PRODUCTION = {
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_team.py': ROOT / ".veldo" / "control_team.py",
        'control_factory_setup_dispatch.py': ROOT / ".veldo" / "control_factory_setup_dispatch.py",
    }
    PREFIX = 'VELDO-0188 '
    ROWS = ('follow/at-start', 'follow/new-project', 'follow/receiver-wait', 'follow/restart',
            'staff/project-team', 'staff/default-team', 'staff/new-revision', 'staff/refused-role',
            'staff/one-mapping', 'close/canceled', 'close/completed', 'close/removed', 'close/paused-kept',
            'observe/lines', 'lines/journal-only', 'close/guard', 'lines/paused-restart',
            'staff/configured-refusal', 'staff/missing-team', 'close/configured', 'lines/receiver-change',
            'lines/at-start', 'lines/new-project', 'lines/adopted-project', 'lines/restart')
    emitted, raised = set(), []

    def check(label, parts):
        """One row: every named part must hold. A part that raises while judging is a failed part."""
        emitted.add(label)
        failed = []
        for name, condition in parts:
            try:
                ok = bool(condition() if callable(condition) else condition)
            except Exception as error:  # noqa: BLE001 - a malformed answer is a failed part, never a raise
                ok, name = False, '%s (%s)' % (name, type(error).__name__)
            if not ok:
                failed.append(name)
        if failed:
            print('  %sdetail: %s: %s' % (PREFIX, label, '; '.join(failed)))
        expect(PREFIX + label, not failed)

    @contextlib.contextmanager
    def region(*labels):
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            __import__('traceback').print_exc()
            raised.append((labels[0], repr(error)))
            print('  %sdetail: %s did not run to its end: %r' % (PREFIX, labels[0], error))
            for label in labels:
                if label not in emitted:
                    check(label, [('region raised', False)])

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    helper = load('v188_fixture', Path(__suite_file__).resolve().parents[2] / 'proof/VELDO-0152/fixture.py')
    formats_f = load('v188_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    GIH = __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))
    HOST = 'fixture-host'
    AUTHOR = 'Fixture Identity <fixture@example.invalid>'

    with helper.fixture(ROOT, PRODUCTION) as f:
        base, mods, conn, S, CM, PJ, CT = f['base'], f['mods'], f['conn'], f['S'], f['CM'], f['PJ'], f['CT']
        DOMAIN, REPO, ids = f['DOMAIN'], f['REPO'], f['ids']
        sign_as, next_id, signed = f['sign_as'], f['next_id'], f['signed']
        SV = load('v188_service', mods / 'control_service.py')
        TR = load('v188_team_routes', mods / 'control_team_routes.py')
        CG = load('v188_config', mods / 'control_agent_config.py')
        RS = load('v188_readset', mods / 'control_readset.py')
        FSD = load('v188_setup_dispatch', mods / 'control_factory_setup_dispatch.py')

        def entity(eid):
            row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
            return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

        def git(path, *args):
            return subprocess.run(['git', '-C', str(path), '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
                                   *args], capture_output=True, text=True, check=True,
                                  env=dict(os.environ, GIT_AUTHOR_NAME='Seed', GIT_AUTHOR_EMAIL='seed@example.invalid',
                                           GIT_COMMITTER_NAME='Seed', GIT_COMMITTER_EMAIL='seed@example.invalid')
                                  ).stdout.strip()

        # THE FAKE ENGINE: it records its packet, commits in the workspace its argv names (an author planted in the
        # environment must be stripped by the launch) and, when the suite holds its unit, waits for the release.
        fake = base / 'fake-engine' / 'engine.py'
        fake.parent.mkdir()
        fake.write_text(formats_f.embed('''import json,os,subprocess,sys,time,traceback
from pathlib import Path
def failed(kind, value, trace):
    Path(sys.argv[2], 'error-%d.txt' % os.getpid()).write_text(''.join(traceback.format_exception(kind, value, trace)))
sys.excepthook = failed
def emit(event):
    print(json.dumps(complete_event(event)), flush=True)
if '--input-format' in sys.argv:
    opening = json.loads(sys.stdin.readline())
    emit({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': opening['request_id'],
          'response': {'account': {'subscriptionType': 'Claude Team', 'apiProvider': 'firstParty'}}}})
    packet = json.loads(json.loads(sys.stdin.readline())['message']['content'])
else:
    packet = json.load(sys.stdin)
workspace, out, adapter = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
payload = packet.get('payload') or {}
unit = payload.get('unit') or 'unknown'
hold = out / (unit + '.hold')
if hold.exists():
    (out / (unit + '.held')).write_text('held')
    ends = time.time() + 60
    while not (out / (unit + '.go')).exists() and time.time() < ends:
        time.sleep(0.05)
def git(*args):
    return subprocess.run(['git', '-C', workspace, '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', *args],
                          capture_output=True, text=True, check=True).stdout.strip()
head = git('rev-parse', 'HEAD')
made = git('commit-tree', head + '^{tree}', '-p', head, '-m', 'unit ' + unit)
(out / (unit + '.' + str(payload.get('operation')) + '.json')).write_text(json.dumps({
    'packet': packet, 'adapter': adapter, 'head': head, 'commit': made, 'workspace': workspace,
    'author': git('log', '-1', '--format=%an <%ae>', made), 'committer': git('log', '-1', '--format=%cn <%ce>', made)}))
emit({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'built'}],
      'usage': {'input_tokens': 2, 'output_tokens': 3}}})
emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'built',
      'usage': {'input_tokens': 2, 'output_tokens': 4}})
'''))
        out = base / 'engine-out'
        out.mkdir()
        signers = base / 'enrollment-signers'
        signers.write_text('')
        trust = base / 'host-trust.json'
        trust.write_text(json.dumps(dict(schema='veldo.host_trust/v1', host_identity=HOST,
                                         enrollment_signers=str(signers))))
        trust.chmod(0o600)
        receivers_dir = base / 'receivers'
        receivers_dir.mkdir()

        def adapters_for(workspace, engines, with_engine):
            found = {}
            for engine in engines:
                found[engine] = {'identity': 'reported', 'argv': [
                    sys.executable, '-B', str(mods / 'control_launch.py'), 'exec', sys.executable, '-B', str(fake),
                    os.path.realpath(str(workspace)), str(out), engine]}
                if with_engine:
                    found[engine]['engine'] = engine
            return found

        def receiver_files(name, repository, workspace, engines=('claude_code', 'codex')):
            """(installed, launch): the installation's receiver configuration of `repository`, whose adapters name
            their engines (what the line's staffing reads), and the one the Runner launches through, the same
            adapters with no engine binding."""
            paths = []
            for kind, with_engine in (('installed', True), ('launch', False)):
                path = receivers_dir / ('%s-%s.json' % (name, kind))
                path.write_text(json.dumps(dict(
                    store=str(f['db']), journal_key=str(f['keyfile']['authority']), principal='pm',
                    workspace=os.path.realpath(str(workspace)), host_trust=str(trust), domain=DOMAIN,
                    repository=repository, records=str(base / ('records-' + name)),
                    adapters=adapters_for(workspace, engines, with_engine))))
                path.chmod(0o600)
                paths.append(str(path))
            return paths

        # The repositories: the factory's (REPO) and one per project, each a real Git repository bound to the
        # store with its configured identity, with its first commit accepted.
        repos = {'factory': REPO, 'tide': 'repository-tide', 'cove': 'repository-cove', 'reef': 'repository-reef',
                 'shoal': 'repository-shoal', 'kelp': 'repository-kelp', 'dune': 'repository-dune'}
        workspaces = {}
        for name, repository in repos.items():
            ws = base / 'workspaces' / name
            ws.mkdir(parents=True)
            git(ws, 'init', '-q', '-b', 'main')
            (ws / 'README').write_text('%s\n' % name)
            git(ws, 'add', 'README')
            git(ws, 'commit', '-qm', 'first')
            workspaces[name] = ws
        GIH['bind_paths'](mods, conn, DOMAIN, {repos[n]: str(workspaces[n]) for n in repos})
        # Each repository's author configuration, written by the provisioner's own step (VELDO-0143) from the
        # identity the store binds to it: what a dispatch's commit is authored by once the launch strips the rest.
        GI = load('v188_git_identity', mods / 'control_git_identity.py')
        RC = load('v188_creation', mods / 'control_repository_creation.py')
        for name, repository in repos.items():
            RC.author({'directory': str(workspaces[name])}, GI.resolve(conn, DOMAIN, repository))
        revisions = RS.attach_revisions(S, conn, DOMAIN, {repos[n]: str(workspaces[n]) for n in repos})
        for name, repository in repos.items():
            revisions.accept('revision-188-' + name, repository, git(workspaces[name], 'rev-parse', 'HEAD'), 'pm',
                             signer='authority', sign=f['journal_sign'], authority_generation=1)
        conn.command_registry.pop('accept_revision', None)
        # Each repository's capability configurations, as a project's activation copies them (VELDO-0143).
        for name, repository in repos.items():
            if repository == REPO:
                continue
            CG.Configurations(S, conn, domain=DOMAIN, repository=repository, signer='authority',
                              sign=f['journal_sign']).save(
                dict(role='team-fixture', engine='claude_code', native_tools=[], mcp=[], skills=[], instructions=[],
                     settings={}), principal='steward', base=0, command_id=next_id('capability'))
        receivers = {name: receiver_files(name, repository, workspaces[name]) for name, repository in repos.items()}
        # The shoal installation runs Claude Code only, so a team role on Codex cannot be dispatched there.
        receivers['shoal'] = receiver_files('shoal', repos['shoal'], workspaces['shoal'], engines=('claude_code',))

        def project(op, name, **fields):
            if op != 'activate':
                fields['project_version'] = (entity('project:' + name) or {}).get('version')
            body = dict(ids, operation=op, project=name, principal='olga', command_id=next_id('pc'),
                        nonce=next_id('pn'), **fields)
            return f['projects'].apply(signed('olga', body))

        def activate(name):
            return project('activate', name, owner='olga', charter={'purpose': 'The %s project.' % name},
                           execution_repository=repos[name],
                           authority_policy={'team_amendment': ['project_owner'], 'admission': ['admission_authority']},
                           coordination_budget={'capacity': 5, 'invocations': 50, 'wall_seconds': 5000})

        def team_send(name, who, op, **fields):
            body = dict(ids, operation=op, project=name, principal=who, command_id=next_id('tc'), nonce=next_id('tn'),
                        **fields)
            return f['service'].apply(signed(who, body))

        def accept_team(name, value):
            """A project team revision through VELDO-0089: the PM's proposal, the owner's settled answer, amend."""
            record = CT.read(S, conn, name) or {}
            proposed = team_send(name, 'pm', 'propose', team_version=record.get('version', 0), team=value)
            if not proposed.get('ok'):
                return proposed
            record = CT.read(S, conn, name)
            rid, receipt = f['present'](next_id('TEAM'), CT.amendment_target(record), CT.amendment_brief(record))
            settled = f['answer'](receipt, 'accept', 'olga')
            if settled.get('outcome') != 'settled':
                return settled
            record = CT.read(S, conn, name)
            proposal = record.get('proposal') or {}
            return team_send(name, 'pm', 'amend', team_version=record['version'], revision=proposal.get('revision'),
                             digest=proposal.get('digest'), request=rid)

        def team_on(builder_engines=('claude_code',), builder='w-build'):
            workers = [builder] + [w for w in ('w-build', 'w-build2') if w != builder]
            return f['team'](implementation=f['role'](workers, 'implement', ('finding',), tuple(builder_engines)))

        # THE SERVICE: one process's Service and FactoryLoop, the work configuration naming the factory repository.
        def service_config(observations, served):
            return dict(domain_uuid=DOMAIN, store_uuid=ids['store_uuid'], principal='team-service', authority_generation=1,
                        repositories={repos[n]: [os.path.realpath(str(workspaces[n]))] for n in served},
                        journal_key=str(f['keyfile']['authority']), host_identity=HOST,
                        enrollment_signers=str(signers), store_path=str(f['db']), observations=str(observations),
                        receiver={'configs': {repos[n]: receivers[n][0] for n in served}})

        work_role = {'identity': 'w-build', 'adapter': 'claude_code', 'configuration': {'role': 'team-fixture', 'revision': 1},
                     'seconds': 100, 'payload': {'task': 'build the unit'}}
        work = {'schema': SV.WORK_SCHEMA, 'repositories': {REPO: {'builder': work_role, 'reviewers': [
            dict(work_role, identity='w-rev1', payload={'task': 'review the unit'})]}}}
        service = SV.Service(service_config(base / 'service.jsonl', ['factory']), conn)

        def take_on(name):
            """The repository taken on by this service, as Service._take_on records it (VELDO-0161 AC2): served, with
            its receiver configuration beside the installed one; nothing reinstalled, no loop rebuilt."""
            S.bind_repositories(conn, DOMAIN, {repos[name]: str(workspaces[name])})
            service.repositories[repos[name]] = [os.path.realpath(str(workspaces[name]))]
            service.config['receiver']['configs'][repos[name]] = receivers[name][0]
        launch_of = {}

        def fit_line(line):
            """The Runner of each line launches through the launch configuration of its repository (the same
            adapter names, no engine binding) on the fixture account; the account pool is not under test."""
            name = next(n for n, r in repos.items() if r == line.repository)
            line.runner.account = 'fixture-account'
            line.runner.receiver = (lambda contract, line=line, name=name:
                                    SV.L.invoke(receivers[name][1], contract, line.dispatches))
            for scope, subject in (('account', 'fixture-account'), ('project', name)):
                with contextlib.suppress(Exception):
                    line.reservations.configure('policy-188/%s/%s' % (scope, subject), scope, subject,
                                                dict(capacity=20, invocations=200, wall_seconds=50000),
                                                now=time.time())
            line.activate()

        class FittedLine(SV.Line):
            """Every line the loop builds, whenever it builds it, fitted as it is made (fit_line)."""
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                fit_line(self)
        SV.Line = FittedLine

        def fit(loop):
            return loop

        units = {}

        def unit_for(name, serial=1, holder='w-build'):
            """One READY unit of project `name` in its repository, claimed by its line's builder `holder`."""
            unit = '%s-%04d' % (name.upper(), serial)
            repository = repos[name]
            f['fixture'](unit, 'execution_unit', dict(
                state='READY', repository_uuid=repository, backlog_item_uuid='backlog:' + unit, requirements=[],
                eligible_holders=[holder], project=name, scope_digest='sha256:scope-' + unit, revision=1,
                depends_on=[], producer=holder))
            f['fixture']('backlog:' + unit, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=repository))
            f['fixture']('admission:' + unit, 'admission', dict(unit=unit, state='accepted',
                                                               scope_digest='sha256:scope-' + unit))
            body = dict(operation='claim', unit_id=unit, principal=holder, command_id=next_id('claim'),
                        nonce=next_id('claim-n'), generation=0, capabilities=[], domain_uuid=DOMAIN,
                        store_uuid=ids['store_uuid'], repository_uuid=repository)
            policies = loop.lines[REPO].reservations
            loop.lines[REPO].activate()
            with contextlib.suppress(Exception):
                policies.configure('policy-188/unit/' + unit, 'unit', unit,
                                   dict(capacity=5, invocations=50, wall_seconds=5000), now=time.time())
            claimed = service.receiver(repository).apply({'command': body, 'signature': sign_as(holder, S.canonical_bytes(body))})
            units[unit] = claimed
            return unit

        passes = []

        def journal_pass(loop):
            """One pass a journal advance woke (a commit's hint), as the serve loop runs it."""
            loop.wake('journal')
            report = loop.run() or {}
            fit(loop)
            passes.append(report)
            return report

        def offer_of(report, unit, station='build'):
            return next((o for o in report.get('offered') or [] if o.get('unit') == unit and o.get('station') == station), {})

        def finish(loop, report, unit, station='build'):
            """Wait for the unit's run to end and take its end in a run_end pass."""
            offer = offer_of(report, unit, station)
            line = loop.lines.get(offer.get('repository'))
            launch = line.runner.launches.get(offer.get('dispatch_id')) if line is not None else None
            if launch is not None:
                launch.wait(60)
                loop.saw_end(line, launch)
            done = loop.run() or {}
            passes.append(done)
            return done

        def result_of(unit, station='build'):
            path = out / ('%s.%s.json' % (unit, station))
            return json.loads(path.read_text()) if path.exists() else {}

        planted = {k: os.environ.get(k) for k in ('GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_COMMITTER_NAME',
                                                  'GIT_COMMITTER_EMAIL')}
        os.environ.update(GIT_AUTHOR_NAME='Planted Author', GIT_AUTHOR_EMAIL='planted@example.invalid',
                          GIT_COMMITTER_NAME='Planted Committer', GIT_COMMITTER_EMAIL='planted@example.invalid')
        try:
            # =========================================================================================================
            # AC1: a line for every project at run time
            # =========================================================================================================
            loop = None
            with region('follow/at-start'):
                default_saved = TR.TeamRoutes(f['service'], f['settlement'], f['presenter']).save_default(
                    f['team'](), 'olga', 0, next_id('default-team'), 'sha256:' + '0' * 64)
                loop = fit(SV.FactoryLoop(service, work))
                identity = (id(loop), os.getpid())
                check('follow/at-start', [
                    ('the default team is saved through its route', default_saved.get('outcome') == 'saved'),
                    ('the service starts with the factory project\'s line only', sorted(loop.lines) == [REPO]),
                    ('the loop status lists that line and its project',
                     list(loop.status()['lines']) == [REPO] and loop.status()['lines'][REPO].get('project') == 'factory')])

            with region('follow/new-project'):
                take_on('tide')
                activated = activate('tide')
                tide_unit = unit_for('tide')
                report = journal_pass(loop)
                line = loop.lines.get(repos['tide'])
                offer = offer_of(report, tide_unit)
                done = finish(loop, report, tide_unit)
                built = result_of(tide_unit)
                started = (report.get('lines') or {}).get('started') or []
                check('follow/new-project', [
                    ('the project is recorded ACTIVE on its own repository',
                     activated.get('ok') is True and (PJ.read(S, conn, 'tide') or {}).get('state') == 'ACTIVE'),
                    ('the pass its commit woke starts its line, in the same process and loop',
                     line is not None and (id(loop), os.getpid()) == identity
                     and any(s.get('project') == 'tide' and s.get('repository') == repos['tide'] for s in started)),
                    ('the line works in the project\'s repository through its own receiver configuration',
                     line is not None and line.workspace == os.path.realpath(str(workspaces['tide']))
                     and line.receiver_path == receivers['tide'][0] and line.gate.repository_uuid == repos['tide']),
                    ('the project\'s first unit is dispatched by that line in the same pass [%s]'
                     % {k: offer.get(k) for k in ('result', 'identity', 'adapter')},
                     units[tide_unit].get('ok') is True and offer.get('result') == 'accepted'
                     and offer.get('repository') == repos['tide']),
                    ('its build ran in the new repository and committed there',
                     built.get('workspace') == os.path.realpath(str(workspaces['tide']))
                     and (built.get('packet', {}).get('source') or {}).get('repository_uuid') == repos['tide']
                     and built.get('commit') and built.get('head') == git(workspaces['tide'], 'rev-parse', 'HEAD')),
                    ('its commit is authored and committed by the repository\'s identity alone, the planted author '
                     'stripped [%s | %s]' % (built.get('author'), built.get('committer')),
                     built.get('author') == built.get('committer') == AUTHOR),
                    ('the run ended and was settled', any(e.get('unit') == tide_unit and e.get('state') == 'exited'
                                                          for e in done.get('ended') or []))])

            with region('follow/receiver-wait'):
                # Activated while its repository has no receiver configuration here: refused by name, and every other
                # line serves; once the repository is taken on (VELDO-0161 AC2), the next woken pass starts it.
                S.bind_repositories(conn, DOMAIN, {repos['cove']: str(workspaces['cove'])})
                cove_activated = activate('cove')
                waiting = journal_pass(loop)
                cove_refusal = loop.status()['refused_lines'].get('cove')
                cove_waiting = (repos['cove'] not in loop.lines, loop.status()['line_counts']['waiting_receiver'])
                take_on('cove')
                cove_unit = unit_for('cove')
                taken = journal_pass(loop)
                cove_offer = offer_of(taken, cove_unit)
                finish(loop, taken, cove_unit)
                check('follow/receiver-wait', [
                    ('the project is activated on the adopted repository', cove_activated.get('ok') is True),
                    ('before its receiver configuration exists it is refused by name and gets no line [%s]' % cove_refusal,
                     cove_refusal == 'missing_authority:receiver:cove' and cove_waiting == (True, 1)
                     and not any(s.get('project') == 'cove' for s in (waiting.get('lines') or {}).get('started') or [])
                     and any(r.get('project') == 'cove' and r.get('refusal') == cove_refusal
                             for r in (waiting.get('lines') or {}).get('refused') or [])),
                    ('the pass after the take-on starts its line in the same loop',
                     repos['cove'] in loop.lines and (id(loop), os.getpid()) == identity
                     and any(s.get('project') == 'cove' for s in (taken.get('lines') or {}).get('started') or [])),
                    ('its first unit is dispatched in its repository',
                     cove_offer.get('result') == 'accepted' and result_of(cove_unit).get('workspace')
                     == os.path.realpath(str(workspaces['cove'])))])

            # =========================================================================================================
            # AC2: staffed from the project's team or the default team
            # =========================================================================================================
            with region('staff/project-team', 'staff/default-team', 'staff/new-revision'):
                take_on('reef')
                reef_activated = activate('reef')
                reef_team = accept_team('reef', team_on(('codex',), builder='w-build2'))
                # Its unit is claimed by its own builder, and held running while a new team revision is saved.
                reef_unit = unit_for('reef', holder='w-build2')
                (out / (reef_unit + '.hold')).write_text('hold')
                reef_pass = journal_pass(loop)
                reef_line = loop.lines.get(repos['reef'])
                staffed = (reef_line.roles if reef_line is not None else {})
                tide_roles = loop.lines[repos['tide']].roles if repos['tide'] in loop.lines else {}
                default_head = entity(TR.HEAD)['data']['revision']
                check('staff/project-team', [
                    ('the project\'s own team revision is current', reef_team.get('ok') is True
                     and (CT.read(S, conn, 'reef') or {}).get('revision') == 1),
                    ('its line\'s builder is its team\'s implementation role: its first worker on Codex, its engine [%s]'
                     % staffed.get('builder', {}).get('adapter'),
                     staffed.get('builder', {}).get('identity') == 'w-build2'
                     and staffed.get('builder', {}).get('adapter') == 'codex'),
                    ('its reviewer is its independent_review role\'s first worker on the role\'s first engine',
                     [r.get('identity') for r in staffed.get('reviewers') or []] == ['w-rev1']
                     and staffed['reviewers'][0].get('adapter') == 'claude_code'),
                    ('the line records the project team and its revision',
                     (reef_line.staffing if reef_line is not None else {}).get('team') == 'project'
                     and reef_line.staffing.get('team_revision') == 1)])
                check('staff/default-team', [
                    ('a project with no team of its own is staffed from the default team\'s current revision',
                     (loop.lines[repos['tide']].staffing or {}).get('team') == 'default'
                     and loop.lines[repos['tide']].staffing.get('team_revision') == default_head),
                    ('its builder is the default team\'s implementation role\'s first worker',
                     tide_roles.get('builder', {}).get('identity') == 'w-build')])
                reef_offer = offer_of(reef_pass, reef_unit)
                ends = time.time() + 30
                while not (out / (reef_unit + '.held')).exists() and time.time() < ends:
                    time.sleep(0.05)
                # The owner saves a second team revision whose builder runs on the other engine, Claude Code, while the
                # first build runs.
                reef_second = accept_team('reef', team_on(('claude_code',), builder='w-build2'))
                restaged = journal_pass(loop)
                running = reef_line.dispatches.record(reef_offer.get('dispatch_id')) if reef_offer.get('dispatch_id') else {}
                (out / (reef_unit + '.go')).write_text('go')
                finish(loop, reef_pass, reef_unit)
                reef_next = unit_for('reef', 2, holder='w-build2')
                next_pass = journal_pass(loop)
                next_offer = offer_of(next_pass, reef_next)
                finish(loop, next_pass, reef_next)
                check('staff/new-revision', [
                    ('the second revision is current', reef_second.get('ok') is True
                     and (CT.read(S, conn, 'reef') or {}).get('revision') == 2),
                    ('the pass its commit woke restages the line',
                     any(r.get('project') == 'reef' and r.get('team_revision') == 2
                         for r in (restaged.get('lines') or {}).get('restaged') or [])
                     and loop.lines[repos['reef']] is reef_line),
                    ('the run already dispatched keeps the roles it was dispatched with [%s]' % reef_offer.get('adapter'),
                     reef_offer.get('adapter') == 'codex'
                     and ((running or {}).get('contract') or {}).get('capability', {}).get('adapter') == 'codex'
                     and result_of(reef_unit).get('adapter') == 'codex'),
                    ('the next dispatch uses the new builder engine [%s]' % next_offer.get('adapter'),
                     next_offer.get('adapter') == 'claude_code' and next_offer.get('result') == 'accepted'
                     and result_of(reef_next).get('adapter') == 'claude_code')])

            with region('staff/refused-role'):
                take_on('shoal')
                shoal_activated = activate('shoal')
                shoal_team = accept_team('shoal', team_on(('codex',)))
                tide_more = unit_for('tide', 2)
                refused_pass = journal_pass(loop)
                check('staff/refused-role', [
                    ('the project and its team are current', shoal_activated.get('ok') is True and shoal_team.get('ok') is True),
                    ('a role the installation cannot dispatch leaves the project without a line, refused by name [%s]'
                     % loop.status()['refused_lines'].get('shoal'),
                     repos['shoal'] not in loop.lines
                     and loop.status()['refused_lines'].get('shoal') == 'invalid_input:line:role:adapter'
                     and any(r.get('project') == 'shoal' and r.get('refusal') == 'invalid_input:line:role:adapter'
                             for r in (refused_pass.get('lines') or {}).get('refused') or [])),
                    ('every other line serves in the same pass', offer_of(refused_pass, tide_more).get('result') == 'accepted'
                     and {repos['tide'], repos['reef'], repos['cove'], REPO} <= set(loop.lines))])
                finish(loop, refused_pass, tide_more)

            with region('staff/one-mapping'):
                fixture_team = f['team']()
                adapters = {'claude_code': {'engine': 'claude_code'}, 'codex': {'engine': 'codex'}}
                setup_work = FSD.work(REPO, fixture_team['roles'], {r: s['engines'][0] for r, s in fixture_team['roles'].items()})
                check('staff/one-mapping', [
                    ('setup\'s work configuration and the service\'s line roles come from the one mapping',
                     setup_work['repositories'][REPO] == SV.line_roles(fixture_team, adapters)),
                    ('each role carries exactly control_service\'s ROLE_FIELDS',
                     all(set(r) == set(SV.ROLE_FIELDS) for r in [setup_work['repositories'][REPO]['builder']]
                         + setup_work['repositories'][REPO]['reviewers']))])

            # =========================================================================================================
            # AC3: a closed project's line stops; a paused one keeps its line
            # =========================================================================================================
            with region('close/canceled', 'close/completed', 'close/removed', 'close/paused-kept'):
                take_on('kelp')
                take_on('dune')
                activate('kelp')
                activate('dune')
                prepared = journal_pass(loop)
                kelp_unit = unit_for('kelp')
                (out / (kelp_unit + '.hold')).write_text('hold')
                kelp_pass = journal_pass(loop)
                kelp_offer = offer_of(kelp_pass, kelp_unit)
                ends = time.time() + 30
                while not (out / (kelp_unit + '.held')).exists() and time.time() < ends:
                    time.sleep(0.05)
                kelp_line, dune_line = loop.lines.get(repos['kelp']), loop.lines.get(repos['dune'])
                canceled = project('cancel', 'kelp', reason='the owner closes it', disposition='nothing left open')
                completed = project('complete', 'dune')
                kelp_more = unit_for('kelp', 2)
                tide_third = unit_for('tide', 3)
                closing = journal_pass(loop)
                kept_while_running = repos['kelp'] in loop.lines
                dune_gone = repos['dune'] not in loop.lines
                (out / (kelp_unit + '.go')).write_text('go')
                ended = finish(loop, kelp_pass, kelp_unit)
                status = loop.status()
                check('close/canceled', [
                    ('the project is canceled with its build running', canceled.get('ok') is True
                     and kelp_offer.get('result') == 'accepted' and (PJ.read(S, conn, 'kelp') or {}).get('state') == 'CANCELED'),
                    ('from the pass its commit woke the line offers nothing and no re-run',
                     not offer_of(closing, kelp_more) and kelp_line is not None and getattr(kelp_line, 'closing', False)
                     and not [o for o in closing.get('offered') or [] if o.get('repository') == repos['kelp']]),
                    ('it stays in the loop while its run lasts', kept_while_running),
                    ('its run ends and is settled', any(e.get('unit') == kelp_unit for e in ended.get('ended') or []))])
                check('close/completed', [
                    ('the project with no run is completed', completed.get('ok') is True
                     and (PJ.read(S, conn, 'dune') or {}).get('state') == 'COMPLETED'),
                    ('its line leaves the loop at the pass its commit woke', dune_line is not None and dune_gone
                     and any(s.get('project') == 'dune' for s in (closing.get('lines') or {}).get('stopped') or [])),
                    ('a third project\'s unit is dispatched in the same pass', offer_of(closing, tide_third).get('result') == 'accepted')])
                check('close/removed', [
                    ('the canceled project\'s line leaves the loop once its run ended, its account slot free',
                     repos['kelp'] not in loop.lines and not kelp_line.runner.launches),
                    ('the loop status no longer lists either closed line',
                     repos['kelp'] not in status['lines'] and repos['dune'] not in status['lines']),
                    ('the loop counts its lines: the open projects\' and the factory\'s',
                     sorted(loop.lines) == sorted([REPO, repos['tide'], repos['cove'], repos['reef']]))])
                finish(loop, closing, tide_third)
                paused = project('pause', 'tide', reason='the owner pauses it', disposition='hold the rest')
                paused_pass = journal_pass(loop)
                resumed = project('resume', 'tide')
                tide_fourth = unit_for('tide', 4)
                resumed_pass = journal_pass(loop)
                check('close/paused-kept', [
                    ('a paused project keeps its line', paused.get('ok') is True and repos['tide'] in loop.lines
                     and not getattr(loop.lines[repos['tide']], 'closing', False)),
                    ('a resume needs no restart: its next unit is dispatched by the same loop',
                     resumed.get('ok') is True and offer_of(resumed_pass, tide_fourth).get('result') == 'accepted'
                     and (id(loop), os.getpid()) == identity)])
                finish(loop, resumed_pass, tide_fourth)

            with region('follow/restart'):
                before = {r: (getattr(l, 'project', None), l.receiver_path, json.dumps(l.roles, sort_keys=True))
                          for r, l in loop.lines.items()}
                # The restarted service serves again every repository it had taken on (VELDO-0161's take_on at the
                # start), with the same receiver configurations, and builds its loop from the store.
                again = SV.Service(dict(service.config, repositories=dict(service.repositories),
                                        observations=str(base / 'service-again.jsonl')), conn)
                restarted = SV.FactoryLoop(again, work)
                after = {r: (getattr(l, 'project', None), l.receiver_path, json.dumps(l.roles, sort_keys=True))
                         for r, l in restarted.lines.items()}
                check('follow/restart', [
                    ('a service started later builds the same lines from the store, with the same staffing',
                     before == after and len(after) == 4),
                    ('and the same refusals', restarted.status()['refused_lines'] == loop.status()['refused_lines'])])

            with region('observe/lines'):
                logged = [json.loads(x) for x in (base / 'service.jsonl').read_text().splitlines()]
                changes = [p.get('lines') for p in logged if p.get('operation') == 'loop_pass' and p.get('lines')]
                started_logged = [s for c in changes for s in c.get('started') or []]
                text = (base / 'service.jsonl').read_text()
                counts = loop.status()['line_counts']
                check('observe/lines', [
                    ('each line started is logged with its project, repository, team revision, receiver configuration, '
                     'pass and journal position',
                     any(s.get('project') == 'tide' and s.get('repository') == repos['tide'] and s.get('team') == 'default'
                         and s.get('team_revision') and s.get('receiver_config') == receivers['tide'][0]
                         for s in started_logged)
                     and all(isinstance(c.get('cause_pass'), int) for c in changes)
                     and all(isinstance(c.get('watermark'), int) for c in changes if c.get('started'))),
                    ('each refusal is logged by name', any(r.get('refusal') == 'missing_authority:receiver:cove'
                                                           for c in changes for r in c.get('refused') or [])),
                    ('the counts: lines started, restaged and stopped, and refusals by reason [%s]' % counts,
                     counts['started'] >= 5 and counts['restaged'] >= 1 and counts['stopped'] == 2
                     and counts['refused'].get('invalid_input:line:role:adapter', 0) == 1),
                    ('no key or signature is logged', 'PRIVATE KEY' not in text and 'SSH SIGNATURE' not in text)])
            with region('lines/journal-only'):
                take_on('dune')
                # A store change without a delivered journal wake must not change the set.
                project('activate', 'dune', owner='olga', charter={'purpose': 'again'},
                        execution_repository=repos['dune'],
                        authority_policy={'team_amendment': ['project_owner'], 'admission': ['admission_authority']},
                        coordination_budget={'capacity': 5, 'invocations': 50, 'wall_seconds': 5000})
                # Use a new project on the closed repository; activation of a completed name is refused.
                repos['timer'] = repos['dune']
                activated_timer = activate('timer')
                before_timer = set(loop.lines)
                loop.wake('account_reset')
                timer_pass = loop.run()
                same = set(loop.lines) == before_timer
                journal_pass(loop)
                check('lines/journal-only', [
                    ('a timer does not reconcile newly committed projects', activated_timer.get('ok') and same
                     and timer_pass['sources'] == ['account_reset'] and 'lines' not in timer_pass),
                    ('the journal wake does reconcile them', repos['timer'] in loop.lines)])
                del repos['timer']

            with region('close/guard'):
                guarded = loop.lines[REPO]
                original = {key: getattr(guarded, key) for key in ('assigned', 'next', 'wants_cycles')}
                visited = []
                try:
                    guarded.closing = True
                    guarded.wants_cycles = lambda: False
                    guarded.assigned = lambda: ['gate-would-admit']
                    guarded.next = lambda *args: visited.append(args[0])
                    guarded.run({'ended': [], 'released': [], 'provisioning': []}, [])
                finally:
                    guarded.closing = False
                    for key, value in original.items():
                        setattr(guarded, key, value)
                check('close/guard', [('a closing line never reaches a station, even with admissible work', not visited)])

            with region('lines/paused-restart'):
                paused = project('pause', 'tide', reason='restart paused', disposition='hold')
                journal_pass(loop)
                paused_loop = SV.FactoryLoop(service, work)
                check('lines/paused-restart', [('a paused project is rebuilt at startup', paused.get('ok')
                    and repos['tide'] in paused_loop.lines and not getattr(paused_loop.lines[repos['tide']], 'closing', False))])
                project('resume', 'tide')

            with region('lines/receiver-change'):
                old_line = loop.lines[REPO]
                changed = receivers_dir / 'factory-replaced.json'
                changed.write_text(Path(receivers['factory'][0]).read_text())
                service.config['receiver']['configs'][REPO] = str(changed)
                journal_pass(loop)
                journal_pass(loop)
                check('lines/receiver-change', [('a drained configured line is replaced and serves again',
                    REPO in loop.lines and loop.lines[REPO] is not old_line
                    and loop.lines[REPO].receiver_path == str(changed) and not getattr(loop.lines[REPO], 'closing', False))])

            with region('staff/configured-refusal'):
                # The configured repository must obey the same staffing rules as every other project.
                receiver = json.loads(changed.read_text())
                receiver['adapters'] = {}
                changed.write_text(json.dumps(receiver))
                journal_pass(loop)
                check('staff/configured-refusal', [('invalid roles remove a configured line too',
                    REPO not in loop.lines and loop.refused_lines.get('factory') == 'invalid_input:line:role:adapter')])
                changed.write_text(Path(receivers['factory'][0]).read_text())
                journal_pass(loop)

            with region('staff/missing-team'):
                # Delete fixture team records only for this negative authority test; restore them afterwards.
                reef_available = unit_for('reef', 3, holder='w-build2')
                saved_teams = list(conn.execute('SELECT * FROM entities WHERE id=?', (CT.team_id('factory'),)))
                saved_default = conn.execute('SELECT * FROM entities WHERE id=?', (TR.HEAD,)).fetchone()
                conn.execute('DELETE FROM entities WHERE id IN (?, ?)', (CT.team_id('factory'), TR.HEAD))
                missing_team_pass = journal_pass(loop)
                check('staff/missing-team', [('missing teams refuse configured and ordinary repositories by name [%s]' %
                    {key: missing_team_pass.get(key) for key in ('offered', 'refused', 'faults')},
                    REPO not in loop.lines and loop.refused_lines.get('factory') == 'missing_authority:team:factory'
                    and loop.refused_lines.get('tide') == 'missing_authority:team:tide'
                    and repos['reef'] in loop.lines and not getattr(loop.lines[repos['reef']], 'closing', False)
                    and offer_of(missing_team_pass, reef_available).get('result') == 'accepted')])
                for row in saved_teams + ([saved_default] if saved_default else []):
                    conn.execute('INSERT INTO entities VALUES (' + ','.join('?' for _ in row) + ')', tuple(row))
                finish(loop, missing_team_pass, reef_available)
                journal_pass(loop)

            with region('close/configured'):
                canceled_factory = project('cancel', 'factory', reason='done', disposition='nothing left')
                journal_pass(loop)
                check('close/configured', [('a closed configured project leaves loop and status',
                    canceled_factory.get('ok') and REPO not in loop.lines and REPO not in loop.status()['lines'])])
        finally:
            for k, v in planted.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            for loop_ in [x for x in (locals().get('loop'), locals().get('restarted')) if x is not None]:
                for line_ in loop_.lines.values():
                    for launch_ in list(line_.runner.launches.values()):
                        with contextlib.suppress(Exception):
                            launch_.stop('suite end')
                            launch_.wait(10)
    with region('lines/at-start', 'lines/new-project', 'lines/adopted-project', 'lines/restart'):
        load('v188_served', ROOT / 'proof/VELDO-0188/round2/served_scenario.py').run(ROOT, PRODUCTION, check)
    for label in ROWS:
        if label not in emitted:
            check(label, [('row ran', False)])


_v188_started = __import__('time').monotonic()
_v188_suite()
print('VELDO-0188 suite seconds: %.3f' % (__import__('time').monotonic() - _v188_started))
