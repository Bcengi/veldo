"""VELDO-0027: real keys outside a disposable Git repository; real store and pipes.

Run: python3 scripts/selftest.py --suite 56_veldo_0027_signing
Mutation workers substitute only the two production-module paths below. The suite,
assertion observer, requests, keys and expectations are outside the mutated subject.
No private bytes, public key blobs or signatures are printed or retained in proof.
"""
import copy as _v27_copy
import importlib.util as _v27_import
import json as _v27_json
import os as _v27_os
from pathlib import Path as _v27_Path
import shutil as _v27_shutil
import signal as _v27_signal
import stat as _v27_stat
import subprocess as _v27_sp
import sys as _v27_sys
import tempfile as _v27_temp
import time as _v27_time
import threading as _v27_threading


def _v27_load(name, path):
    spec = _v27_import.spec_from_file_location(name, path)
    mod = _v27_import.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_v27_started = _v27_time.monotonic()
with _v27_temp.TemporaryDirectory(prefix='v27-') as _v27_directory:
    _v27_root = _v27_Path(_v27_directory)
    _v27_modules = _v27_root / 'installed'
    _v27_modules.mkdir()
    for _v27_module in ('authority_contract', 'control_membership', 'control_store', 'git_process'):
        _v27_shutil.copyfile(ROOT / '.veldo' / (_v27_module + '.py'), _v27_modules / (_v27_module + '.py'))
    _v27_shutil.copyfile(ROOT / ".veldo" / "control_signer.py", _v27_modules / 'control_signer.py')
    _v27_shutil.copyfile(ROOT / ".veldo" / "control_keys.py", _v27_modules / 'control_keys.py')
    _v27_signer = _v27_load('v27_signer', _v27_modules / 'control_signer.py')
    _v27_keys, _v27_store = _v27_signer.K, _v27_signer.S
    _v27_mem, _v27_ac = _v27_keys.CM, _v27_keys.AC
    _git_process = _v27_load('v27_git_process', _v27_modules / 'git_process.py')
    _v27_repo = _v27_root / 'repository'
    _v27_repo.mkdir()
    _git_process.run(['git', 'init', '-q', str(_v27_repo)], check=True, capture_output=True)
    _v27_keydir = _v27_root / 'private'
    _v27_keydir.mkdir()
    _v27_public = {}
    for _v27_name in ('owner', 'edge-telegram', 'edge-jira', 'edge-cli', 'evidence', 'rotated', 'branch', 'tg-auth', 'jira-auth', 'cli-auth', 'ev-auth', 'race-key', 'race-next', 'kill-rotated'):
        _v27_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'test', '-f', str(_v27_keydir / _v27_name)],
                    check=True, capture_output=True, timeout=10)
        _v27_public[_v27_name] = ' '.join((_v27_keydir / (_v27_name + '.pub')).read_text().split()[:2])
    _v27_db = _v27_root / 'control.sqlite3'
    _v27_conn = _v27_store.open_store(str(_v27_db))
    _v27_mem.attach(_v27_store)
    _v27_keys.attach(_v27_store)
    _v27_ids = {'domain_uuid': 'v27-domain', 'repository_uuid': 'v27-repo', 'store_uuid': 'v27-store'}
    _v27_projection = _v27_repo / '.veldo/keys/allowed_signers'
    _v27_config = _v27_root / 'authority.json'
    _v27_config.write_text(_v27_json.dumps({'store': str(_v27_db), 'repository': str(_v27_repo),
                                          'allowed_signers': str(_v27_projection), 'key_directory': str(_v27_keydir)}))
    _v27_number = 0
    _v27_results = []
    _v27_rows = []

    def _v27_expect(row, condition):
        _v27_rows.append(row)
        expect('VELDO-0027 ' + row, condition)

    def _v27_state():
        return _v27_mem.authority_state(_v27_store, _v27_conn)

    def _v27_sign(name, message, namespace=None):
        return _v27_signer.sign_bytes(_v27_keydir / name, message, namespace or _v27_ac.SIGNATURE_NAMESPACE)

    _v27_journal = ('owner', lambda message: _v27_sign('owner', message))

    def _v27_command(operation, params):
        global _v27_number
        _v27_number += 1
        return {'command_id': 'v27-' + str(_v27_number), 'principal': 'owner', 'operation': operation,
                'target': 'authority', 'parameters': params, 'artifact_digests': [], 'expected_versions': {},
                'nonce': 'v27-nonce-' + str(_v27_number)}

    def _v27_envelope(command):
        state = _v27_state()
        return dict(_v27_ids, schema=_v27_ac.ENVELOPE_SCHEMA, command_id=command['command_id'],
                    principal='owner', request_revision=1, nonce=command['nonce'], expires_at=_v27_time.time() + 600,
                    membership_version=state['membership_version'], delegation_version=state['delegation_version'],
                    command_digest=_v27_ac.canonical_command_digest(command))

    def _v27_admin(operation, params, key='owner', projection=None):
        command = _v27_command(operation, params)
        envelope = _v27_envelope(command)
        signature = _v27_sign(key, _v27_ac.canonical_envelope_bytes(envelope))
        if operation in _v27_keys.OPERATIONS:
            result = _v27_keys.admit(_v27_store, _v27_conn, envelope, command, signature, _v27_ids,
                                     _v27_journal, projection or _v27_projection)
            _v27_keys.publish(_v27_store, _v27_conn, _v27_projection)
            return result
        return _v27_mem.admit(_v27_store, _v27_conn, envelope, command, signature, _v27_ids,
                             _v27_time.time(), journal_signer=_v27_journal)

    _v27_admin('enroll_principal', {'principal': 'owner', 'principal_type': 'person',
                                   'roles': ['membership_steward', 'project_owner'], 'scope': '*',
                                   'public_key': _v27_public['owner'], 'independence_group': 'owner'})
    _v27_keys.publish(_v27_store, _v27_conn, _v27_projection)
    _v27_channels = {'telegram_chat': ('edge-telegram', 'tg-auth'), 'jira': ('edge-jira', 'jira-auth'),
                     'signed_cli': ('edge-cli', 'cli-auth'), 'evidence': ('evidence', 'ev-auth')}
    for _v27_channel, (_v27_kid, _v27_auth) in _v27_channels.items():
        _v27_admin('register_signing_key', {'key_id': _v27_kid, 'channel': _v27_channel,
                                          'public_key': _v27_public[_v27_kid], 'connection_public_key': _v27_public[_v27_auth]})
        if _v27_channel != 'evidence':
            _v27_admin('grant_delegation', {'id': 'delegation-' + _v27_channel, 'principal': 'owner', 'channel': _v27_channel,
                                           'assertion_kinds': list(_v27_ac.ASSERTION_KINDS), 'authority_scope': ['project'],
                                           'request_version': 1, 'presentation_version': 1,
                                           'expires_at': _v27_time.time() + 600, 'edge_key_id': _v27_kid})
    # The projection is committed and then changed on a REAL conflicting worker branch
    # in the disposable repository only. The real worktree/branch is never touched.
    _git_process.run(['git', '-C', str(_v27_repo), 'add', '.'], check=True, capture_output=True)
    _git_process.run(['git', '-C', str(_v27_repo), 'commit', '-qm', 'Accepted public projection'],
                     identity=('Signing fixture', 'signing@example.invalid'), check=True, capture_output=True)
    _git_process.run(['git', '-C', str(_v27_repo), 'checkout', '-qb', 'worker'], check=True, capture_output=True)
    _v27_projection.write_text(_v27_projection.read_text().replace(_v27_public['owner'], _v27_public['branch']))
    _git_process.run(['git', '-C', str(_v27_repo), 'commit', '-qam', 'Worker substitutes owner verification key'],
                     identity=('Signing fixture', 'signing@example.invalid'), check=True, capture_output=True)
    _v27_branch_projection = _v27_root / 'worker-allowed-signers'
    _v27_branch_projection.write_bytes(_v27_projection.read_bytes())
    _v27_keys.publish(_v27_store, _v27_conn, _v27_projection)

    def _v27_signer_pids():
        found = set()
        for path in _v27_Path('/proc').glob('[0-9]*/cmdline'):
            try:
                if str(_v27_modules / 'control_signer.py').encode() in path.read_bytes().split(b'\0'):
                    found.add(int(path.parent.name))
            except (OSError, ProcessLookupError):
                pass
        return found

    _v27_before_pids = _v27_signer_pids()
    _v27_observed_pids, _v27_observed_sockets = set(), set()
    _v27_observer_stop = _v27_threading.Event()

    def _v27_observe_processes():
        while not _v27_observer_stop.is_set():
            pids = _v27_signer_pids()
            _v27_observed_pids.update(pids)
            for pid in pids:
                try:
                    children = _v27_Path('/proc', str(pid), 'task', str(pid), 'children').read_text().split()
                    for child in [str(pid)] + children:
                        for fd in _v27_Path('/proc', child, 'fd').iterdir():
                            try:
                                target = _v27_os.readlink(fd)
                                if target.startswith('socket:'):
                                    inode = target[8:-1]
                                    # Observe endpoints, not libc's short-lived unbound
                                    # name-service probes inside the system ssh-keygen.
                                    # Any named UNIX endpoint or listening descriptor fails.
                                    unix = _v27_Path('/proc/net/unix').read_text().splitlines()[1:]
                                    for line in unix:
                                        fields = line.split()
                                        if fields[6] == inode and (len(fields) > 7 or fields[3] == '00010000'):
                                            _v27_observed_sockets.add(target)
                                    for table in ('tcp', 'tcp6', 'udp', 'udp6'):
                                        for line in _v27_Path('/proc/net', table).read_text().splitlines()[1:]:
                                            if line.split()[9] == inode:
                                                _v27_observed_sockets.add(target)
                            except OSError:
                                pass
                except OSError:
                    pass
            _v27_observer_stop.wait(0.003)

    _v27_observer = _v27_threading.Thread(target=_v27_observe_processes, daemon=True)
    _v27_observer.start()

    def _v27_call(request, authenticated='telegram_chat'):
        kid, auth = _v27_channels.get(authenticated, (None, None))
        result = _v27_signer.call(_v27_config, request, kid, _v27_keydir / auth if auth else None)
        _v27_results.append(result)
        return result

    def _v27_source(channel, kind='acknowledgement', overrides=None):
        global _v27_number
        _v27_number += 1
        kid = _v27_channels[channel][0]
        payload = {'type': 'assertion', 'actor': 'owner', 'actor_kind': 'person', 'principal': 'owner',
                   'contract_digest': _v27_signer.digest({'contract': 1}), 'source_digest': _v27_signer.digest({'message': 1}),
                   'presentation_digest': _v27_signer.digest({'presentation': 1}), 'presentation_id': 'p1',
                   'presentation_version': 1, 'request_version': 1, 'authority_scope': 'project',
                   'channel': channel, 'edge_key_id': kid, 'assertion_kind': kind,
                   'attribution': {f: True if f.endswith('_verified') else 'source-1'
                                   for f in _v27_ac.CHANNELS[channel]['attribution']}}
        if channel == 'signed_cli':
            cmd = _v27_command('answer', {'ruling': 'approve'})
            env = _v27_envelope(cmd)
            payload['personal_command'] = {'command': cmd, 'envelope': env,
                                           'signature': _v27_sign('owner', _v27_ac.canonical_envelope_bytes(env))}
        payload.update(overrides or {})
        identity = 'source-' + str(_v27_number)
        _v27_signer.record(_v27_store, _v27_conn, identity, 'edge_source', payload, _v27_journal)
        return {'operation': 'sign_receipt', 'channel': channel, 'edge_key_id': kid, 'source_id': identity,
                'delegation_id': 'delegation-' + channel, 'delegation_version': _v27_state()['delegation_version'], 'payload': payload}

    _v27_controls = {}
    for _v27_channel in ('telegram_chat', 'jira', 'signed_cli'):
        for _v27_kind in _v27_ac.ASSERTION_KINDS:
            _v27_req = _v27_source(_v27_channel, _v27_kind)
            _v27_result = _v27_call(_v27_req, _v27_channel)
            _v27_controls[_v27_channel, _v27_kind] = (_v27_req, _v27_result)
            _v27_expect('signing/kind/' + _v27_channel + '/' + _v27_kind,
                         _v27_result['accepted'] and _v27_keys.verify(_v27_state(), _v27_result))
    _v27_tg = _v27_controls['telegram_chat', 'acknowledgement'][0]
    _v27_jira = _v27_controls['jira', 'acknowledgement'][0]
    _v27_cross = _v27_call(_v27_jira)
    _v27_expect('signing/cross-channel', _v27_cross.get('refusal') == 'channel-mismatch' and not _v27_cross['accepted'])
    _v27_expect('signing/channel-comes-from-the-connection',
                 all(_v27_controls[c, 'acknowledgement'][1]['accepted'] and
                     _v27_keys.verify(_v27_state(), _v27_controls[c, 'acknowledgement'][1]) for c in ('telegram_chat', 'jira'))
                 and _v27_channels['telegram_chat'][0] != _v27_channels['jira'][0]
                 and _v27_cross.get('refusal') == 'channel-mismatch')
    _v27_bad_key = _v27_call(dict(_v27_tg, edge_key_id='edge-jira'))
    _v27_expect('signing/key-comes-from-the-channel', _v27_bad_key.get('refusal') == 'channel-mismatch')
    for _v27_case, _v27_request, _v27_authenticated, _v27_refusal in (
        ('unauthenticated', _v27_tg, None, 'unauthenticated-channel'),
        ('key-path', dict(_v27_tg, key_path=str(_v27_keydir / 'edge-telegram')), 'telegram_chat', 'key-path'),
        ('arbitrary', dict(_v27_tg, operation='sign_bytes', bytes='arbitrary'), 'telegram_chat', 'forbidden-arbitrary-signing'),
        ('membership', dict(_v27_tg, operation='enroll_principal'), 'telegram_chat', 'forbidden-arbitrary-signing'),
        ('unknown-kind', _v27_source('telegram_chat', 'invented'), 'telegram_chat', 'unknown-assertion-kind')):
        _v27_expect('signing/' + _v27_case, _v27_call(_v27_request, _v27_authenticated).get('refusal') == _v27_refusal)
    for _v27_case, _v27_changes, _v27_refusal in (
        ('absent', {'delegation_id': None}, 'delegation-refused'),
        ('stale', {'delegation_version': 0}, 'stale-delegation')):
        _v27_expect('signing/delegation/' + _v27_case, _v27_call(dict(_v27_tg, **_v27_changes)).get('refusal') == _v27_refusal)
    # Wrong-principal and revoked delegations are stored, not invented request flags.
    _v27_bad_data = dict(next(d for d in _v27_state()['delegations'] if d['channel'] == 'telegram_chat'))
    for _v27_case, _v27_changes in (('wrong-principal', {'principal': 'someone-else'}), ('revoked', {'revoked_at': _v27_time.time()})):
        _v27_signer.record(_v27_store, _v27_conn, 'delegation-' + _v27_case, 'delegation',
                           dict(_v27_bad_data, **_v27_changes), _v27_journal)
        _v27_expect('signing/delegation/' + _v27_case,
                     _v27_call(dict(_v27_tg, delegation_id='delegation-' + _v27_case)).get('refusal') == 'delegation-refused')
    _v27_expect('signing/delegation/valid-control', _v27_call(_v27_tg)['accepted'])

    for _v27_field in ('platform_message_id', 'sender_id', 'platform_timestamp'):
        _v27_attribution = dict(_v27_tg['payload']['attribution'])
        del _v27_attribution[_v27_field]
        _v27_missing = _v27_source('telegram_chat', overrides={'attribution': _v27_attribution})
        _v27_answer = _v27_call(_v27_missing)
        _v27_expect('signing/attribution/' + _v27_field, _v27_answer.get('refusal') == 'missing-attribution')
    _v27_text = _v27_source('telegram_chat', overrides={'attribution': {}, 'text': 'approve'})
    _v27_expect('signing/text-only', _v27_call(_v27_text).get('refusal') == 'missing-attribution')
    _v27_cli = _v27_source('signed_cli', overrides={'personal_command': {}})
    _v27_expect('signing/attribution/personal-signature', _v27_call(_v27_cli, 'signed_cli').get('refusal') == 'missing-attribution')
    for _v27_field in ('contract_digest', 'source_digest', 'presentation_digest', 'actor', 'actor_kind', 'principal'):
        _v27_changed = _v27_copy.deepcopy(_v27_tg)
        _v27_changed['payload'][_v27_field] = 'corrupt'
        _v27_expect('signing/bound/' + _v27_field, _v27_call(_v27_changed).get('refusal') == 'provenance-mismatch')

    _v27_provenance = {'contract_digest': _v27_signer.digest({'contract': 1}), 'actor': 'agent-run-1', 'actor_kind': 'agent_run',
                       'source_digest': _v27_signer.digest({'input': 1}), 'presentation_digest': _v27_signer.digest({'presentation': 1})}
    _v27_capture, _v27_out, _v27_err = _v27_signer.capture(
        _v27_store, _v27_conn, 'captured', [_v27_sys.executable, '-c', 'import sys; sys.stdout.buffer.write(b"observed"); sys.exit(3)'],
        _v27_provenance, _v27_journal)
    _v27_evidence = {'operation': 'sign_receipt', 'channel': 'evidence', 'edge_key_id': 'evidence', 'source_id': 'captured', 'payload': _v27_capture}
    _v27_receipt = _v27_call(_v27_evidence, 'evidence')
    _v27_verify_code = """import sys,json
sys.path.insert(0,sys.argv[1]); import control_signer as C
config=json.load(open(sys.argv[2])); conn=C.S.open_store(config['store'])
print(json.dumps(C.K.verify(C.CM.authority_state(C.S,conn),json.load(sys.stdin))))
conn.close()
"""
    _v27_verified = _v27_sp.run([_v27_sys.executable, '-B', '-c', _v27_verify_code, str(_v27_modules), str(_v27_config)],
                               input=_v27_json.dumps(_v27_receipt), capture_output=True, text=True, timeout=10)
    _v27_expect('signing/captured-observation', _v27_receipt['accepted'] and _v27_capture['exit_code'] == 3
                 and _v27_out == b'observed' and _v27_err == b'' and _v27_verified.returncode == 0 and _v27_json.loads(_v27_verified.stdout) is True)
    for _v27_field in ('stdout_digest', 'stderr_digest', 'executable_digest', 'invocation', 'exit_code', 'pid'):
        _v27_corrupt_capture = _v27_copy.deepcopy(_v27_evidence)
        _v27_corrupt_capture['payload'][_v27_field] = 'corrupt'
        _v27_expect('signing/observation-bound/' + _v27_field,
                     _v27_call(_v27_corrupt_capture, 'evidence').get('refusal') == 'provenance-mismatch')
    for _v27_field in _v27_receipt.get('envelope', {}):
        _v27_tampered = _v27_copy.deepcopy(_v27_receipt)
        _v27_tampered['envelope'][_v27_field] = 'changed' if _v27_tampered['envelope'][_v27_field] is None else None
        _v27_expect('signing/receipt-bound/' + _v27_field, not _v27_keys.verify(_v27_state(), _v27_tampered))
    _v27_assertion = dict(_v27_provenance, type='assertion', statement='The task succeeded')
    _v27_signer.record(_v27_store, _v27_conn, 'agent-statement', 'agent_assertion', _v27_assertion, _v27_journal)
    _v27_assert_req = dict(_v27_evidence, source_id='agent-statement', payload=_v27_assertion)
    _v27_assert_result = _v27_call(_v27_assert_req, 'evidence')
    _v27_expect('signing/assertion-control', _v27_assert_result['accepted'] and _v27_assert_result['envelope']['payload']['type'] == 'assertion')
    _v27_expect('signing/assertion-relabel', _v27_call(dict(_v27_assert_req, payload=dict(_v27_assertion, type='observation')), 'evidence').get('refusal') == 'assertion-is-not-observation')

    # Reopen the store, then try a command carrying a valid signature by the
    # branch-added key and otherwise-current owner envelope. No exception is a
    # passing mutation detection: refusals are caught and asserted by exact code.
    _v27_conn.close()
    _v27_conn = _v27_store.open_store(str(_v27_db))
    try:
        _v27_admin('retire_signing_key', {'key_id': 'edge-cli'}, key='branch', projection=_v27_branch_projection)
        _v27_branch_code = 'accepted'
    except _v27_keys.Refused as _v27_error:
        _v27_branch_code = _v27_error.code
    _v27_expect('signing/branch-key', _v27_branch_code in ('projection-mismatch', 'command-authentication'))

    _v27_before = _v27_call(_v27_evidence, 'evidence')
    _v27_admin('rotate_signing_key', {'key_id': 'rotated', 'channel': 'evidence', 'public_key': _v27_public['rotated'],
                                    'connection_public_key': _v27_public['ev-auth']})
    _v27_channels['evidence'] = ('rotated', 'ev-auth')
    _v27_evidence['edge_key_id'] = 'rotated'
    _v27_after = _v27_call(_v27_evidence, 'evidence')
    _v27_expect('signing/rotation', _v27_before['accepted'] and _v27_after['accepted'] and
                 _v27_keys.verify(_v27_state(), _v27_before) and _v27_keys.verify(_v27_state(), _v27_after, fresh=True)
                 and not _v27_keys.verify(_v27_state(), _v27_before, fresh=True))
    _v27_admin('retire_signing_key', {'key_id': 'rotated'})
    _v27_retired = _v27_call(_v27_evidence, 'evidence')
    _v27_expect('signing/retirement', not _v27_retired['accepted'] and _v27_keys.verify(_v27_state(), _v27_after)
                 and not _v27_keys.verify(_v27_state(), _v27_after, fresh=True))
    _v27_admin('revoke_signing_key', {'key_id': 'rotated'})
    _v27_revoked = _v27_call(_v27_evidence, 'evidence')
    _v27_expect('signing/revocation', not _v27_revoked['accepted'] and _v27_keys.verify(_v27_state(), _v27_after)
                 and not _v27_keys.verify(_v27_state(), _v27_after, fresh=True))

    _v27_transition_code = """import sys,json
sys.path.insert(0,sys.argv[1]); import control_signer as C
config=json.load(open(sys.argv[2])); packet=json.loads(sys.argv[3])
conn=C.S.open_store(config['store']); C.K.attach(C.S)
js=('owner',lambda m: C.sign_bytes(__import__('pathlib').Path(config['key_directory'])/'owner',m,C.AC.SIGNATURE_NAMESPACE))
print('ready',flush=True); sys.stdin.readline()
r=C.K.admit(C.S,conn,packet['envelope'],packet['command'],packet['signature'],packet['ids'],js,config['allowed_signers'])
print(json.dumps(r),flush=True)
if packet.get('kill_boundary'): sys.stdin.readline()
C.K.publish(C.S,conn,config['allowed_signers']); conn.close()
"""

    def _v27_transition_child(operation, params, kill_boundary=False):
        command = _v27_command(operation, params)
        envelope = _v27_envelope(command)
        packet = {'command': command, 'envelope': envelope, 'ids': _v27_ids,
                  'signature': _v27_sign('owner', _v27_ac.canonical_envelope_bytes(envelope)), 'kill_boundary': kill_boundary}
        child = _v27_sp.Popen([_v27_sys.executable, '-B', '-c', _v27_transition_code,
                              str(_v27_modules), str(_v27_config), _v27_json.dumps(packet)],
                             stdin=_v27_sp.PIPE, stdout=_v27_sp.PIPE, stderr=_v27_sp.PIPE, text=True)
        assert child.stdout.readline().strip() == 'ready'
        return child

    _v27_admin('register_signing_key', {'key_id': 'race-key', 'channel': 'evidence',
                                      'public_key': _v27_public['race-key'], 'connection_public_key': _v27_public['ev-auth']})
    _v27_channels['evidence'] = ('race-key', 'ev-auth')
    _v27_evidence['edge_key_id'] = 'race-key'
    _v27_race_before = _v27_call(_v27_evidence, 'evidence')
    _v27_rotation = _v27_transition_child('rotate_signing_key', {'key_id': 'race-next', 'channel': 'evidence',
                                                              'public_key': _v27_public['race-next'], 'connection_public_key': _v27_public['ev-auth']})
    _v27_rotation.stdin.write('go\n')
    _v27_rotation.stdin.flush()
    _v27_raced = _v27_call(_v27_evidence, 'evidence')
    _v27_rotation_out, _v27_rotation_err = _v27_rotation.communicate(timeout=10)
    _v27_race_state = _v27_state()
    _v27_expect('signing/rotation-race', _v27_rotation.returncode == 0 and
                 (_v27_keys.verify(_v27_race_state, _v27_raced) if _v27_raced['accepted'] else
                  _v27_raced.get('refusal') in ('revoked-key', 'channel-mismatch', 'projection-mismatch'))
                 and _v27_keys.verify(_v27_race_state, _v27_race_before)
                 and not _v27_keys.verify(_v27_race_state, _v27_race_before, fresh=True))
    _v27_channels['evidence'] = ('race-next', 'ev-auth')
    _v27_evidence['edge_key_id'] = 'race-next'
    _v27_race_after = _v27_call(_v27_evidence, 'evidence')
    _v27_expect('signing/race-new-key', _v27_race_after['accepted'] and _v27_keys.verify(_v27_state(), _v27_race_after))
    _v27_crash_rotation = _v27_transition_child('rotate_signing_key', {
        'key_id': 'kill-rotated', 'channel': 'evidence', 'public_key': _v27_public['kill-rotated'],
        'connection_public_key': _v27_public['ev-auth']}, kill_boundary=True)
    _v27_crash_rotation.stdin.write('go\n'); _v27_crash_rotation.stdin.flush()
    _v27_rotation_commit = _v27_json.loads(_v27_crash_rotation.stdout.readline())
    _v27_rotation_snapshot = _v27_keys.entries(_v27_state())
    _v27_crash_rotation.kill(); _v27_crash_rotation.communicate(timeout=10)
    _v27_channels['evidence'] = ('kill-rotated', 'ev-auth')
    _v27_evidence['edge_key_id'] = 'kill-rotated'
    _v27_conn.close(); _v27_conn = _v27_store.open_store(str(_v27_db))
    _v27_unpublished = _v27_call(_v27_evidence, 'evidence')
    _v27_keys.publish(_v27_store, _v27_conn, _v27_projection)
    _v27_published = _v27_call(_v27_evidence, 'evidence')
    _v27_expect('signing/kill-after-rotation', _v27_rotation_commit['committed'] and
                 _v27_crash_rotation.returncode == -_v27_signal.SIGKILL and
                 _v27_keys.entries(_v27_state()) == _v27_rotation_snapshot and
                 _v27_unpublished.get('refusal') == 'projection-mismatch' and _v27_published['accepted'] and
                 _v27_keys.verify(_v27_state(), _v27_race_after) and not _v27_keys.verify(_v27_state(), _v27_race_after, fresh=True))
    _v27_race_after = _v27_published
    for _v27_operation in ('retire_signing_key', 'revoke_signing_key'):
        _v27_crasher = _v27_transition_child(_v27_operation, {'key_id': 'kill-rotated'}, kill_boundary=True)
        _v27_crasher.stdin.write('go\n'); _v27_crasher.stdin.flush()
        _v27_committed = _v27_json.loads(_v27_crasher.stdout.readline())
        _v27_at_commit = _v27_keys.entries(_v27_state())
        _v27_crasher.kill()
        _v27_crasher.communicate(timeout=10)
        _v27_conn.close()
        _v27_conn = _v27_store.open_store(str(_v27_db))
        _v27_keys.publish(_v27_store, _v27_conn, _v27_projection)
        _v27_after_kill = _v27_call(_v27_evidence, 'evidence')
        _v27_expect('signing/kill-after-' + _v27_operation,
                     _v27_committed['committed'] and _v27_crasher.returncode == -_v27_signal.SIGKILL and
                     _v27_keys.entries(_v27_state()) == _v27_at_commit and
                     _v27_after_kill.get('refusal') == 'revoked-key' and
                     _v27_keys.verify(_v27_state(), _v27_race_after) and
                     not _v27_keys.verify(_v27_state(), _v27_race_after, fresh=True))

    # Observation apparatus inspects the production child PIDs after joining and
    # the entire disposable run for listener/socket/pid artifacts and private bytes.
    _v27_observer_stop.set()
    _v27_observer.join(timeout=5)
    _v27_expect('signing/process-count-and-listeners', not _v27_observer.is_alive() and bool(_v27_observed_pids)
                 and _v27_signer_pids() == _v27_before_pids and not _v27_observed_sockets)
    _v27_expect('signing/children-exit', bool(_v27_results) and all(not _v27_Path('/proc', str(r['signer_pid'])).exists() for r in _v27_results))
    _v27_artifacts = [p for p in _v27_root.rglob('*') if p.is_file() and not p.is_relative_to(_v27_keydir)]
    _v27_private_bytes = [(_v27_keydir / n).read_bytes() for n in _v27_public]
    _v27_outputs = _v27_json.dumps(_v27_results).encode()
    _v27_expect('signing/no-key-leaks', all(k not in _v27_outputs and all(k not in p.read_bytes() for p in _v27_artifacts) for k in _v27_private_bytes))
    _v27_expect('signing/no-socket-or-pidfile', all(not _v27_stat.S_ISSOCK(p.stat().st_mode) and p.suffix != '.pid' for p in _v27_root.rglob('*')))
    _v27_conn.close()
    _v27_universe = _v27_json.loads((ROOT / 'proof/VELDO-0027/universe.json').read_text())
    _v27_declared = {r for rows in _v27_universe['criteria'].values() for r in rows}
    _v27_expect('signing/universe', set(_v27_rows) == _v27_declared and set(_v27_ac.ASSERTION_KINDS) == {'decision_answer', 'assignment_acceptance', 'review_disposition', 'acknowledgement'}
                 and len(_v27_controls) == 12 and len(_v27_rows) == len(set(_v27_rows)))
_v27_elapsed = _v27_time.monotonic() - _v27_started
print('VELDO-0027 suite: %d rows, %.3fs' % (len(_v27_rows), _v27_elapsed))
