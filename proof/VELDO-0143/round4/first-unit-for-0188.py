"""VELDO-0143 round 4: the row activation/first-unit, moved out of suite 110 to seed VELDO-0188's row.

This file seeds VELDO-0188 AC1's new-project row and is not run by any suite. The owner moved the observation "the
first unit dispatched in the new repository with the identity as author" from VELDO-0143 AC3 to VELDO-0188 AC1
(Telegram 36153, approved by 36156 "ok 0143"): a factory runs only its first line's cycles until VELDO-0188, and
VELDO-0188 depends on VELDO-0143.

REGION below holds the region of scripts/suites/110_veldo_0143_new_project.py at 91b9291c (lines 1724 to 1864),
unchanged, as text so this file compiles: it is a fragment of that suite's _v143_suite() and runs only inside it,
on its fixture's names (base, f, mods, conn, service, work, wire, provision, own_decision, judged, record, tip,
sign_as, next_id, SV, PP, PJ, S and the rest). Its setup and the activation/line-from-pass row stay in suite 110;
the first-unit parts are what VELDO-0188's row needs: the fake engine that commits in the new repository's
workspace, the installed receiver configuration pointed at it, the unit claimed on the new line, the loop's pass
with an author planted in the environment, and the four parts of the check.
"""

REGION = r"""
            with region('activation/first-unit'):
                # AC3's observation (VELDO-0143 F5): once the pass activates a new project with the factory loop
                # attached, the loop gains the repository's line from that pass, and the first unit offered on it is
                # dispatched through that line's Runner in the new repository, its commit authored by the identity
                # alone. The engine is a fake printing the installed CLI's output shape; it commits in the workspace
                # its argv names (a reported adapter runs with no clone), with an author planted in its environment
                # that the launch must strip.
                formats_f = load('v143_fake_formats_unit', ROOT / 'proof/VELDO-0172/fake_formats.py')
                built = base / 'unit-build.json'
                build_fake = base / 'unit-fake' / 'claude'
                build_fake.parent.mkdir()
                build_fake.write_text(formats_f.embed('''import json,subprocess,sys
from pathlib import Path
def emit(event):
    print(json.dumps(complete_event(event)), flush=True)
if '--input-format' in sys.argv:
    opening = json.loads(sys.stdin.readline())
    emit({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': opening['request_id'],
          'response': {'account': {'subscriptionType': 'Claude Team', 'apiProvider': 'firstParty'}}}})
    packet = json.loads(json.loads(sys.stdin.readline())['message']['content'])
else:
    packet = json.load(sys.stdin)
workspace = sys.argv[1]
def git(*args):
    return subprocess.run(['git', '-C', workspace, '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', *args],
                          capture_output=True, text=True, check=True).stdout.strip()
head = git('rev-parse', 'HEAD')
made = git('commit-tree', head + '^{tree}', '-p', head, '-m', 'the first unit')
Path(sys.argv[2]).write_text(json.dumps({'packet': packet, 'head': head, 'commit': made,
                                         'author': git('log', '-1', '--format=%an <%ae>', made),
                                         'committer': git('log', '-1', '--format=%cn <%ce>', made)}))
emit({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'built'}],
      'usage': {'input_tokens': 2, 'output_tokens': 3}}})
emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'built',
      'usage': {'input_tokens': 2, 'output_tokens': 4}})
'''))
                unit_signers = base / 'unit-enrollment-signers'
                unit_signers.write_text('')
                unit_trust = base / 'unit-host-trust.json'
                unit_trust.write_text(json.dumps(dict(schema='veldo.host_trust/v1', host_identity=HOST,
                                                      enrollment_signers=str(unit_signers))))
                unit_trust.chmod(0o600)
                fjord_dir = projects_root['personal'] / 'fjord'
                # The installed receiver configuration every taken-on repository's is derived from (the last row,
                # so no other row reads it again): its engine is the fake, run in the new repository.
                receiver_config.write_text(json.dumps(dict(
                    json.loads(receiver_config.read_text()), journal_key=str(f['keyfile']['authority']),
                    host_trust=str(unit_trust), adapters={'claude': {'identity': 'reported', 'argv': [
                        sys.executable, '-B', str(mods / 'control_launch.py'), 'exec', sys.executable, '-B',
                        str(build_fake), os.path.realpath(str(fjord_dir)), str(built)]}})))
                # The factory loop runs as the scheduling service's principal (reservation_service), as the pm row's.
                unit_service = SV.Service(dict(service.config, principal='team-service',
                                               repositories={REPO: [str(base / 'workspace')]},
                                               observations=str(base / 'unit-service.jsonl'),
                                               receiver={'configs': {REPO: str(receiver_config)}}), conn)
                unit_service.channel = service.channel
                unit_loop = SV.FactoryLoop(unit_service, work)
                decision_u1, _, _ = own_decision('fjord')
                fjord_repo = PP.read(conn, decision_u1)['proposal']['repository']
                saved_loop, service.loop = service.loop, unit_loop
                try:
                    with fenced(wire):
                        fjord = provision(decision_u1, send=judged(service))
                    fjord_pass = service.new_project_pass()
                finally:
                    service.loop = saved_loop
                tline = unit_loop.lines.get(fjord_repo)
                check('activation/line-from-pass', [
                    ('the pass that activates the new project, with the factory loop attached, gives the loop its line',
                     fjord.get('state') == 'active' and (PJ.read(S, conn, 'fjord') or {}).get('state') == 'ACTIVE'
                     and any(e.get('decision') == decision_u1 and e.get('outcome') == 'activated'
                             and e.get('line') == fjord_repo for e in fjord_pass)),
                    ('that line works in the new repository, through its own receiver configuration, with the roles of '
                     'the loop\'s first line',
                     tline is not None and tline.workspace == os.path.realpath(str(fjord_dir))
                     and tline.gate.repository_uuid == fjord_repo and tline.roles == work['repositories'][REPO])])
                # The new line's project cycles beside another line's on the service's one connection (VELDO-0154):
                # the refusal, by name, that the loop's pass records only as unknown_outcome:Refused.
                PMu = load('v143_pm_unit', mods / 'control_workflow_cycle_pm.py')
                try:
                    PMu.from_line(tline) if tline is not None else None
                    cycles_refusal = None
                except Exception as error:  # noqa: BLE001 - named in the row
                    cycles_refusal = '%s: %s' % (getattr(error, 'code', type(error).__name__), str(error)[:200])
                unit = 'FJORD-0001'
                if tline is not None:
                    f['fixture'](unit, 'execution_unit', dict(
                        state='READY', repository_uuid=fjord_repo, backlog_item_uuid='backlog:' + unit, requirements=[],
                        eligible_holders=['w-build'], project='fjord', scope_digest='sha256:scope-' + unit, revision=1,
                        depends_on=[], producer='w-build'))
                    f['fixture']('backlog:' + unit, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=fjord_repo))
                    f['fixture']('admission:' + unit, 'admission', dict(unit=unit, state='accepted',
                                                                        scope_digest='sha256:scope-' + unit))
                    tline.runner.account = 'fixture-account'
                    for scope, subject in (('account', 'fixture-account'), ('project', 'fjord'), ('unit', unit)):
                        with contextlib.suppress(Exception):
                            tline.reservations.configure('policy-143-unit/' + subject, scope, subject,
                                                         dict(capacity=5, invocations=100, wall_seconds=5000),
                                                         now=time.time())
                    body_u = dict(operation='claim', unit_id=unit, principal='w-build', command_id=next_id('claim'),
                                  nonce=next_id('claim-n'), generation=0, capabilities=[], domain_uuid=DOMAIN,
                                  store_uuid=ids['store_uuid'], repository_uuid=fjord_repo)
                    claimed = service.receiver(fjord_repo).apply(
                        {'command': body_u, 'signature': sign_as('w-build', S.canonical_bytes(body_u))})
                    planted = {k: os.environ.get(k) for k in ('GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL')}
                    os.environ.update(GIT_AUTHOR_NAME='Planted Author', GIT_AUTHOR_EMAIL='planted@example.invalid')
                    try:
                        unit_loop.wake('journal')
                        unit_report = unit_loop.run() or {}
                        offer = next((o for o in unit_report.get('offered') or []
                                      if o.get('unit') == unit and o.get('station') == 'build'), {})
                        if offer.get('dispatch_id') in tline.runner.launches:
                            tline.runner.wait(tline.runner.launches[offer['dispatch_id']], timeout=60)
                    finally:
                        for k, v in planted.items():
                            if v is None:
                                os.environ.pop(k, None)
                            else:
                                os.environ[k] = v
                else:
                    claimed, unit_report, offer = {}, {}, {}
                out = json.loads(built.read_text()) if built.exists() else {}
                if not out:
                    for name_u, value_u in (('claim', claimed.get('ok')), ('offered', unit_report.get('offered')),
                                            ('refused', unit_report.get('refused')),
                                            ('faults', unit_report.get('faults'))):
                        print('  %sdetail: first unit %s: %s' % (PREFIX, name_u, json.dumps(value_u, default=str)[:900]))
                check('activation/first-unit', [
                    ('the new line\'s project cycles run beside another line\'s on the service\'s connection [%s]'
                     % cycles_refusal, tline is not None and cycles_refusal is None
                     and not any(fault.get('repository') == fjord_repo for fault in unit_report.get('faults') or [])),
                    ('the first unit is offered on that line and dispatched through its Runner [%s]'
                     % {k: offer.get(k) for k in ('station', 'identity', 'result', 'dispatch_id')},
                     claimed.get('ok') is True and offer.get('result') == 'accepted' and offer.get('identity') == 'w-build'
                     and offer.get('repository') == fjord_repo),
                    ('the dispatch is in the new repository: its packet names it and its build follows its commit',
                     (out.get('packet', {}).get('source') or {}).get('repository_uuid') == fjord_repo
                     and out.get('head') == tip(fjord_dir, 'HEAD') == (record(fjord_repo) or {}).get('base_commit')),
                    ('its commit is authored and committed by the identity alone, an author planted in the environment '
                     'stripped [%s | %s]' % (out.get('author'), out.get('committer')),
                     out.get('author') == out.get('committer') == 'Olga Personal <personal@example.invalid>')])
"""
