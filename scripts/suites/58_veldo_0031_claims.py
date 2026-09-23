"""Real signed clone clients, IPC receiver, SQLite state and Git refs for VELDO-0031.

Three criterion rows collect all observations, including negative requests. Mutation
workers replace a production file copied below, never assertions or fixture input.
The real lander is driven with its existing claims_root injection; no remote push
is performed (the remote is a disposable local bare repository).
"""
import importlib.util as _v31_import
import json as _v31_json
import multiprocessing as _v31_mp
import os as _v31_os
from pathlib import Path as _v31_Path
import shutil as _v31_shutil
import subprocess as _v31_sp
import tempfile as _v31_temp
import time as _v31_time


def _v31_load(name, path):
    spec = _v31_import.spec_from_file_location(name, path)
    mod = _v31_import.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_v31_start = _v31_time.monotonic()
with _v31_temp.TemporaryDirectory(prefix='v31-') as _v31_dir:
    _v31_base = _v31_Path(_v31_dir)
    _v31_modules = _v31_base / '.veldo'
    _v31_modules.mkdir()
    for _v31_name in ('claim', 'control_store', 'control_membership', 'authority_contract',
                      'control_client', 'control_enrollment', 'git_process', 'lander', 'policy_check'):
        _v31_shutil.copyfile(ROOT / '.veldo' / (_v31_name + '.py'), _v31_modules / (_v31_name + '.py'))
    _v31_shutil.copyfile(ROOT / ".veldo" / "control_claim.py", _v31_modules / 'control_claim.py')
    _v31_shutil.copyfile(ROOT / ".veldo" / "control_claim_client.py", _v31_modules / 'control_claim_client.py')
    _v31_C = _v31_load('claims31', _v31_modules / 'control_claim.py')
    _v31_CC = _v31_load('client31', _v31_modules / 'control_claim_client.py')
    _v31_G = _v31_load('git31', _v31_modules / 'git_process.py')
    _v31_S, _v31_AC = _v31_C.S, _v31_C.AC
    _v31_CL = _v31_C.CL
    _v31_E, _v31_IPC = _v31_CC.E, _v31_CC.IPC
    _v31_keys = _v31_base / 'keys'
    _v31_keys.mkdir()
    _v31_public = {}
    for _v31_w in ('owner', 'worker-a', 'worker-b'):
        _v31_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(_v31_keys / _v31_w)],
                    check=True, capture_output=True, timeout=10)
        _v31_public[_v31_w] = (_v31_keys / (_v31_w + '.pub')).read_text().strip()

    def _v31_sign(who, message):
        return _v31_sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(_v31_keys / who),
                           '-n', _v31_AC.SIGNATURE_NAMESPACE], input=message, capture_output=True,
                          check=True, timeout=10).stdout.decode()

    def _v31_verify(message, signature):
        return any(_v31_AC.ssh_keygen_verify(message, signature,
                   _v31_AC.allowed_signers_line(w, public), w)[0] for w, public in _v31_public.items())

    def _v31_git(repo, *args):
        return _v31_G.check_output(['git', '-C', str(repo), *args], text=True, stderr=_v31_sp.DEVNULL)

    _v31_origin = _v31_base / 'origin'
    _v31_origin.mkdir()
    _v31_git(_v31_origin, 'init', '-q')
    _v31_G.run(['git', '-C', str(_v31_origin), 'commit', '-q', '--allow-empty', '-m', 'fixture'],
              identity=('Fixture', 'fixture@example.invalid'), check=True)
    _v31_remote = _v31_base / 'remote.git'
    _v31_G.run(['git', 'clone', '-q', '--bare', str(_v31_origin), str(_v31_remote)], check=True)
    _v31_repos = []
    _v31_db = _v31_base / 'authority/control.sqlite3'
    _v31_ids = dict(domain_uuid='claims-domain', store_uuid='claims-store', repository_uuid='claims-repository')
    for _v31_n in ('a', 'b'):
        _v31_repo = _v31_base / _v31_n
        _v31_G.run(['git', 'clone', '-q', str(_v31_remote), str(_v31_repo)], check=True)
        _v31_E.enroll(str(_v31_repo), _v31_ids['domain_uuid'], _v31_ids['store_uuid'], str(_v31_db),
                      'test-host', 1, lambda m: _v31_sign('owner', m), 'owner', _v31_time.time(),
                      repository_uuid=_v31_ids['repository_uuid'])
        _v31_repos.append(_v31_repo)
    _v31_conn = _v31_S.open_store(str(_v31_db))
    _v31_serial = 0

    def _v31_write(eid, kind, data):
        global _v31_serial
        _v31_serial += 1
        entity = _v31_S.materialized_state(_v31_conn)['entities'].get(eid, {})
        return _v31_S.execute(_v31_conn, dict(command_id='fixture-' + str(_v31_serial), principal='owner',
            operation='upsert_entity', parameters=dict(entity_id=eid, kind=kind, data=data),
            expected_versions={eid: entity.get('version', 0)}, artifact_digests=[], nonce='fixture-' + str(_v31_serial)),
            'owner', lambda m: _v31_sign('owner', m), 1)

    for _v31_w in ('worker-a', 'worker-b'):
        _v31_write(_v31_w, 'membership', dict(principal_type='agent_run', roles=[], scope='*'))
        _v31_write('key-' + _v31_w, 'verification_key', dict(principal=_v31_w,
                    public_key=_v31_public[_v31_w], effective_at=0))
    _v31_write('backlog', 'backlog_item', dict(state='PRIORITIZED', repository_uuid=_v31_ids['repository_uuid']))
    for _v31_unit in ('unit', '__land_lock__', 'capability-unit'):
        _v31_write(_v31_unit, 'execution_unit', dict(state='READY', repository_uuid=_v31_ids['repository_uuid'],
                    backlog_item_uuid='backlog', requirements=['mac'] if _v31_unit == 'capability-unit' else [],
                    eligible_holders=['worker-a', 'worker-b']))
    _v31_ctx = _v31_mp.get_context('fork')
    _v31_stop, _v31_ready = _v31_ctx.Event(), _v31_ctx.Event()
    _v31_address = _v31_IPC.socket_path_for(_v31_E.read_binding(str(_v31_repos[0])))
    _v31_audit = _v31_base / 'observations.json'

    def _v31_server():
        conn = _v31_S.open_store(str(_v31_db))
        receiver = _v31_C.Receiver(conn, _v31_ids, 'owner', lambda m: _v31_sign('owner', m))
        authority = _v31_IPC.Authority(_v31_ids['store_uuid'], _v31_ids['domain_uuid'], str(_v31_db),
                                     _v31_E, _v31_verify, 'test-host', receiver.apply)
        srv = _v31_IPC.bind(_v31_address)
        srv.settimeout(.05)
        _v31_ready.set()
        try:
            while not _v31_stop.is_set():
                try:
                    _v31_IPC.serve_one(srv, authority)
                except TimeoutError:
                    pass
        finally:
            _v31_audit.write_text(_v31_json.dumps(dict(rows=receiver.observations, counts=receiver.counts,
                                                      pending=list(receiver.pending()))))
            srv.close()
            conn.close()

    _v31_server_proc = _v31_ctx.Process(target=_v31_server)
    _v31_server_proc.start()
    if not _v31_ready.wait(10):
        raise RuntimeError('claim service did not start')
    _v31_clients = [_v31_CC.Client(r, w, lambda m, w=w: _v31_sign(w, m), _v31_verify, 'test-host')
                    for r, w in zip(_v31_repos, ('worker-a', 'worker-b'))]
    _v31_checks = {1: [], 2: [], 3: []}

    def _v31_check(ac, label, condition):
        _v31_checks[ac].append((label, bool(condition)))

    def _v31_request(client, op, unit='unit', generation=0, capabilities=()):
        try:
            return client.request(op, unit, generation, capabilities)
        except _v31_CC.CL.ClaimStopped as exc:
            return {'ok': False, 'reason': exc.reason}

    try:
        # Invalid aliases are rejected before client artifacts or authority writes.
        _v31_before = _v31_S.materialized_state(_v31_conn)
        for _v31_bad in ('bad/unit', 'bad unit', '', 31):
            _v31_invalid = False
            try:
                _v31_clients[0].request('claim', _v31_bad)
            except _v31_CC.CL.UnitIdError:
                _v31_invalid = True
            _v31_check(1, 'invalid-alias-' + repr(_v31_bad), _v31_invalid)
        _v31_check(1, 'aliases-no-state', _v31_S.materialized_state(_v31_conn) == _v31_before)
        _v31_local = _v31_sp.run([__import__('sys').executable, '-B', '-c',
            "import importlib.util; s=importlib.util.spec_from_file_location('claim', " + repr(str(_v31_modules / 'claim.py')) +
            "); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "m.claim('unit', 'worker-a')"], cwd=_v31_repos[0], capture_output=True, text=True, timeout=10)
        _v31_check(1, 'enrolled-default-stops', _v31_local.returncode != 0 and 'authority_required' in _v31_local.stderr)
        # A repository whose Git FAILS cannot be concluded unenrolled: the enrollment lives inside it.
        # Driven from the repository root and from a subdirectory, for a failing Git and for no git
        # executable at all; a directory in no repository keeps the pre-factory behavior (the Git
        # failure propagates as before). The temporary base must itself be in no repository.
        _v31_os = __import__('os')
        _v31_gp = importlib.util.module_from_spec(importlib.util.spec_from_file_location('v31_gp', str(_v31_modules / 'git_process.py')))
        _v31_gp.__spec__.loader.exec_module(_v31_gp)
        _v31_bases = [b for b in (__import__('tempfile').gettempdir(), '/tmp', '/var/tmp')
                      if _v31_os.path.isdir(b) and not _v31_gp.claims_a_repository(b)]
        _v31_tmp = __import__('tempfile').mkdtemp(prefix='v31-authority-', dir=(_v31_bases or [None])[0])
        _v31_broken = _v31_os.path.join(_v31_tmp, 'broken')
        _v31_sp.run(['git', 'init', '-q', _v31_broken], check=True, capture_output=True)
        _v31_os.mkdir(_v31_os.path.join(_v31_broken, 'sub'))
        with open(_v31_os.path.join(_v31_broken, '.git', 'config'), 'w') as _v31_cfg:
            _v31_cfg.write('[[[ this is not a git config\n')
        _v31_healthy = _v31_os.path.join(_v31_tmp, 'healthy')
        _v31_sp.run(['git', 'init', '-q', _v31_healthy], check=True, capture_output=True)
        _v31_unreadable = _v31_os.path.join(_v31_tmp, 'unreadable')
        _v31_sp.run(['git', 'init', '-q', _v31_unreadable], check=True, capture_output=True)
        _v31_control = _v31_os.path.join(_v31_unreadable, '.git', 'veldo', 'control')
        _v31_os.makedirs(_v31_control)
        with open(_v31_os.path.join(_v31_control, 'enrollment.json'), 'w') as _v31_cfg:
            _v31_cfg.write('{}\n')
        _v31_plain = _v31_os.path.join(_v31_tmp, 'plain')
        _v31_os.mkdir(_v31_plain)
        _v31_nogit = _v31_os.path.join(_v31_tmp, 'nogit-bin')
        _v31_os.mkdir(_v31_nogit)
        _v31_env = {k: v for k, v in _v31_os.environ.items() if not k.startswith(('GIT_', 'VELDO_'))}
        _v31_default = ("import importlib.util; s=importlib.util.spec_from_file_location('claim', " + repr(str(_v31_modules / 'claim.py')) +
                        "); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.claim('unit', 'worker-a'))")

        def _v31_run(cwd, **extra):
            return _v31_sp.run([__import__('sys').executable, '-B', '-c', _v31_default], cwd=cwd,
                               capture_output=True, text=True, timeout=30, env=dict(_v31_env, **extra))

        # A separate enrolled ledger for the spelling shapes, so the shared fixtures stay untouched.
        _v31_enrolled_repo = _v31_os.path.join(_v31_tmp, 'enrolled')
        _v31_sp.run(['git', 'init', '-q', _v31_enrolled_repo], check=True, capture_output=True)
        _v31_enrolled_ledger = _v31_os.path.join(_v31_enrolled_repo, '.git', 'veldo')
        _v31_os.makedirs(_v31_os.path.join(_v31_enrolled_ledger, 'control'))
        with open(_v31_os.path.join(_v31_enrolled_ledger, 'control', 'enrollment.json'), 'w') as _v31_cfg:
            _v31_cfg.write('{}\n')
        _v31_linked_root = _v31_os.path.join(_v31_tmp, 'linked-runs')
        _v31_os.makedirs(_v31_linked_root)
        _v31_os.makedirs(_v31_os.path.join(_v31_enrolled_ledger, 'claims'), exist_ok=True)
        _v31_os.symlink(_v31_os.path.join(_v31_enrolled_ledger, 'claims'), _v31_os.path.join(_v31_linked_root, 'claims'))
        _v31_os.chmod(_v31_control, 0)
        try:
            _v31_runs = {'broken': _v31_run(_v31_broken), 'broken-sub': _v31_run(_v31_os.path.join(_v31_broken, 'sub')),
                         'no-git': _v31_run(_v31_healthy, PATH=_v31_nogit), 'plain': _v31_run(_v31_plain),
                         'env-override': _v31_run(_v31_repos[0], VELDO_RUNS_ROOT=_v31_os.path.join(_v31_tmp, 'elsewhere')),
                         'unreadable-control': _v31_run(_v31_unreadable),
                         'override-into-enrolled-from-plain': _v31_run(
                             _v31_plain, VELDO_RUNS_ROOT=_v31_sp.run(['git', '-C', str(_v31_repos[0]), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                                                                     capture_output=True, text=True, check=True).stdout.strip() + '/veldo'),
                         'ghost-dotdot-into-enrolled': _v31_run(
                             _v31_plain, VELDO_RUNS_ROOT=_v31_enrolled_ledger + '/ghost/..'),
                         'symlinked-claims-into-enrolled': _v31_run(_v31_plain, VELDO_RUNS_ROOT=_v31_linked_root),
                         'empty-root-with-override': _v31_sp.run([__import__('sys').executable, '-B', '-c',
                             _v31_default.replace("m.claim('unit', 'worker-a')", "m.claim('unit', 'worker-a', root='')")],
                             cwd=_v31_repos[0], capture_output=True, text=True, timeout=30,
                             env=dict(_v31_env, VELDO_RUNS_ROOT=_v31_os.path.join(_v31_tmp, 'elsewhere'))),
                         'vanished-cwd': _v31_sp.run([__import__('sys').executable, '-B', '-c',
                             "import os, tempfile; d = tempfile.mkdtemp(dir=" + repr(_v31_tmp) + "); os.chdir(d); os.rmdir(d); " + _v31_default],
                             cwd=_v31_plain, capture_output=True, text=True, timeout=30,
                             env=dict(_v31_env, VELDO_RUNS_ROOT=_v31_os.path.join(_v31_tmp, 'elsewhere')))}
        finally:
            _v31_os.chmod(_v31_control, 0o755)
            __import__('shutil').rmtree(_v31_tmp, ignore_errors=True)

        def _v31_stopped(name, reason):
            run = _v31_runs[name]
            return run.returncode != 0 and ('claim stopped: ' + reason) in run.stderr

        _v31_check(1, 'git-failure-in-a-repository-stops',
                   bool(_v31_bases) and _v31_stopped('broken', 'enrollment_unanswerable')
                   and _v31_stopped('broken-sub', 'enrollment_unanswerable')
                   and _v31_stopped('no-git', 'enrollment_unanswerable')
                   and _v31_runs['plain'].returncode != 0 and 'CalledProcessError' in _v31_runs['plain'].stderr
                   and 'claim stopped' not in _v31_runs['plain'].stderr)
        _v31_check(1, 'enrollment-read-never-fails-open',
                   _v31_stopped('env-override', 'authority_required')
                   and _v31_stopped('override-into-enrolled-from-plain', 'authority_required')
                   and _v31_stopped('ghost-dotdot-into-enrolled', 'authority_required')
                   and _v31_stopped('symlinked-claims-into-enrolled', 'authority_required')
                   and _v31_stopped('empty-root-with-override', 'authority_required')
                   and _v31_stopped('vanished-cwd', 'enrollment_unanswerable')
                   and (_v31_os.geteuid() == 0 or _v31_stopped('unreadable-control', 'enrollment_unanswerable')))
        _v31_backlog_data = _v31_S.materialized_state(_v31_conn)['entities']['backlog']['data']
        _v31_write('backlog', 'backlog_item', dict(_v31_backlog_data, state='ADMITTED'))
        _v31_check(1, 'priority-required', _v31_request(_v31_clients[0], 'claim')['reason'] == 'not_admitted')
        _v31_write('backlog', 'backlog_item', _v31_backlog_data)
        _v31_queue, _v31_go = _v31_ctx.Queue(), _v31_ctx.Event()

        def _v31_race(index):
            _v31_go.wait(5)
            _v31_queue.put((index, _v31_request(_v31_clients[index], 'claim')))

        _v31_children = [_v31_ctx.Process(target=_v31_race, args=(i,)) for i in range(2)]
        for _v31_p in _v31_children:
            _v31_p.start()
        _v31_go.set()
        _v31_results = [_v31_queue.get(timeout=15) for _ in range(2)]
        for _v31_p in _v31_children:
            _v31_p.join(5)
            if _v31_p.is_alive():
                _v31_p.terminate()
                _v31_p.join()
                raise RuntimeError('clone client did not finish')
        _v31_winners = [i for i, r in _v31_results if r['ok']]
        _v31_check(1, 'one-owner', len(_v31_winners) == 1)
        _v31_winner = _v31_winners[0] if _v31_winners else 0
        _v31_owner, _v31_other = _v31_clients[_v31_winner], _v31_clients[1 - _v31_winner]
        _v31_cid = _v31_C.claim_id(_v31_ids['repository_uuid'], 'unit')
        _v31_state = _v31_S.materialized_state(_v31_conn)['entities']
        _v31_claim = _v31_state.get(_v31_cid, {}).get('data', {})
        _v31_generation = _v31_claim.get('generation', 1)
        _v31_entries = [r for r in _v31_S.export_journal(_v31_conn) if _v31_cid in r['transition']]
        _v31_check(1, 'stored-activation', _v31_state['unit']['data']['state'] == 'CLAIMED'
                    and _v31_state['backlog']['data']['state'] == 'ACTIVE'
                    and _v31_claim.get('holder') == _v31_owner.principal)
        _v31_check(1, 'atomic-journal', len(_v31_entries) == 1
                    and set(_v31_entries[0]['transition']) == {_v31_cid, 'unit', 'backlog'})
        _v31_check(1, 'capability', _v31_request(_v31_owner, 'claim', 'capability-unit')['reason'] == 'capability')
        # All holder/generation combinations reach the real receiver for every operation.
        for _v31_op in ('renew', 'release', 'use'):
            for _v31_client, _v31_gen, _v31_reason in (
                    (_v31_other, _v31_generation, 'not_owner'),
                    (_v31_owner, _v31_generation + 9, 'stale_generation'),
                    (_v31_other, _v31_generation + 9, 'not_owner')):
                _v31_result = _v31_request(_v31_client, _v31_op, generation=_v31_gen)
                _v31_check(2, _v31_op + '-' + _v31_reason, not _v31_result['ok'] and _v31_result['reason'] == _v31_reason)
        for _v31_op in ('renew', 'use', 'release'):
            _v31_check(2, 'current-' + _v31_op, _v31_request(_v31_owner, _v31_op, generation=_v31_generation)['ok'])
        _v31_check(3, 'unowned-use', _v31_request(_v31_other, 'use', generation=_v31_generation)['reason'] == 'unowned')
        _v31_result = _v31_request(_v31_owner, 'claim')
        _v31_check(2, 'generation-increases', _v31_result.get('claim', {}).get('generation') == _v31_generation + 1)
        _v31_check(2, 'old-generation-after-release',
                    _v31_request(_v31_owner, 'use', generation=_v31_generation)['reason'] == 'stale_generation')
        _v31_unit_data = _v31_S.materialized_state(_v31_conn)['entities']['unit']['data']
        for _v31_phase in ('DISPATCHING', 'RUNNING', 'VERIFYING', 'REVIEWING', 'READY_TO_LAND', 'LANDING'):
            _v31_write('unit', 'execution_unit', dict(_v31_unit_data, state=_v31_phase))
            _v31_check(2, 'protected-use-' + _v31_phase,
                        _v31_request(_v31_owner, 'use', generation=_v31_generation + 1)['ok'])
            _v31_check(2, 'stale-use-' + _v31_phase,
                        _v31_request(_v31_owner, 'use', generation=_v31_generation)['reason'] == 'stale_generation')
        _v31_write('unit', 'execution_unit', _v31_unit_data)
        _v31_member = _v31_S.materialized_state(_v31_conn)['entities'][_v31_owner.principal]['data']
        _v31_write(_v31_owner.principal, 'membership', dict(_v31_member, revoked_at=0))
        for _v31_op in ('claim', 'renew', 'release', 'use'):
            _v31_check(2, 'revoked-' + _v31_op,
                        _v31_request(_v31_owner, _v31_op, generation=_v31_generation + 1)['reason'] == 'not_authorized')
        _v31_write(_v31_owner.principal, 'membership', _v31_member)
        _v31_original_sign = _v31_other.sign
        _v31_other.sign = _v31_owner.sign
        _v31_check(2, 'signature-binds-holder',
                    _v31_request(_v31_other, 'use', generation=_v31_generation + 1)['reason'] == 'not_authorized')
        _v31_other.sign = _v31_original_sign
        _v31_write('unit', 'execution_unit', dict(_v31_unit_data, state='COMPLETED'))
        _v31_check(2, 'terminal-use-stops',
                    _v31_request(_v31_owner, 'use', generation=_v31_generation + 1)['reason'] == 'ownership_uncertain')
        _v31_check(2, 'terminal-release-stops',
                    _v31_request(_v31_owner, 'release', generation=_v31_generation + 1)['reason'] == 'ownership_uncertain')
        # An actual caller of the existing Lander must stop without retry or touching refs.
        _v31_L = _v31_load('lander31', ROOT / '.veldo/lander.py')
        _v31_land_client = _v31_clients[0]
        _v31_land_cid = _v31_C.claim_id(_v31_ids['repository_uuid'], '__land_lock__')
        _v31_calls = []

        class _v31_Ops:
            def sync_main(self):
                _v31_calls.append('sync')
                return {'ok': True}

            def reconcile(self, unit):
                return {'ok': True}

            def gate(self):
                return {'ok': True}

            def finalize(self, unit):
                _v31_calls.append('finalize')
                # A local bare fixture stands in for the remote; write real refs only here.
                _v31_git(_v31_repos[0], 'update-ref', 'refs/heads/landed', 'HEAD')
                _v31_git(_v31_remote, 'update-ref', 'refs/heads/landed', 'HEAD')
                return {'ok': True}

        def _v31_refs():
            return [_v31_git(r, 'show-ref') for r in (*_v31_repos, _v31_remote)]

        _v31_land = _v31_L.Lander('worker-a', _v31_Ops(), claims_root=_v31_land_client,
                                  lock_timeout=.02, poll=.005, hb_interval=60)
        _v31_check(3, 'unowned-landing', _v31_land.land()['ok'] and _v31_calls == ['sync', 'finalize'])
        _v31_calls.clear()
        _v31_other.request('claim', '__land_lock__')
        _v31_ref_before = _v31_refs()
        _v31_check(3, 'owned-landing', not _v31_land.land()['ok'] and not _v31_calls and _v31_refs() == _v31_ref_before)
        _v31_check(3, 'known-owner', _v31_land_client.holder('__land_lock__') == _v31_other.principal)
        for _v31_scenario, _v31_fields, _v31_reason in (
                ('uncertain', {'state': 'uncertain'}, 'ownership_uncertain'),
                ('detector', {'state': 'owned', 'heartbeat_at': '2999-01-01T00:00:00Z'}, 'unanswerable'),
                ('stale', {'state': 'owned', 'heartbeat_at': '2000-01-01T00:00:00Z'}, 'ownership_uncertain')):
            _v31_cur = _v31_S.materialized_state(_v31_conn)['entities'][_v31_land_cid]['data']
            _v31_cur.update(_v31_fields)
            _v31_write(_v31_land_cid, 'claim', _v31_cur)
            _v31_state_before = _v31_S.materialized_state(_v31_conn)
            _v31_result = _v31_request(_v31_land_client, 'claim', '__land_lock__')
            _v31_check(3, _v31_scenario + '-claim', not _v31_result['ok'] and _v31_result['reason'] == _v31_reason)
            _v31_stopped = None
            try:
                _v31_land.land()
            except _v31_CC.CL.ClaimStopped as exc:
                _v31_stopped = exc.reason
            _v31_check(3, _v31_scenario + '-landing-stop', _v31_stopped == _v31_reason and not _v31_calls)
            _v31_check(3, _v31_scenario + '-unchanged', _v31_refs() == _v31_ref_before
                        and _v31_S.materialized_state(_v31_conn) == _v31_state_before)
            _v31_check(3, _v31_scenario + '-holder',
                        _v31_request(_v31_land_client, 'inspect', '__land_lock__')['reason'] == _v31_reason)
        _v31_check(1, 'no-clone-ledgers', all(not (r / '.git/veldo/claims').exists()
                    and not (r / '.git/veldo/control/control.sqlite3').exists() for r in _v31_repos))
    finally:
        _v31_stop.set()
        _v31_server_proc.join(10)
        if _v31_server_proc.is_alive():
            _v31_server_proc.terminate()
            _v31_server_proc.join()
            raise RuntimeError('claim receiver did not stop')
        _v31_conn.close()
    _v31_log = _v31_json.loads(_v31_audit.read_text())
    _v31_check(2, 'receiver-reached', all(any(r['operation'] == op and r['reason'] == 'stale_generation'
                for r in _v31_log['rows']) for op in ('renew', 'release', 'use')))
    _v31_check(3, 'observability', _v31_log['counts']['accepted'] > 0 and _v31_log['counts']['refused'] > 0
                and bool(_v31_log['pending']) and all(r['domain_uuid'] == _v31_ids['domain_uuid'] for r in _v31_log['rows']))
    _v31_check(3, 'unavailable', _v31_request(_v31_clients[0], 'claim')['reason'] == 'authority_unavailable')
    for _v31_ac, _v31_row in ((1, 'claims/atomic-activation'), (2, 'claims/current-generation'), (3, 'claims/uncertainty-stop')):
        expect('VELDO-0031 AC%d %s' % (_v31_ac, _v31_row), all(ok for _, ok in _v31_checks[_v31_ac]))
        print('  VELDO-0031 observations AC%d: %s' % (_v31_ac, _v31_json.dumps(_v31_checks[_v31_ac])))
print('  VELDO-0031 suite seconds: %.3f' % (_v31_time.monotonic() - _v31_start))
