"""VELDO-0028: installed copies, real signed IPC, SQLite and local Git receivers.

Provider/queued-lander receivers are harmless trusted protocol witnesses, not live model
qualification. A completed publication drives real Git and confirms the remote commit.
"""
import importlib.util as _v28_import
from pathlib import Path as _v28_Path
import json as _v28_json
import shutil as _v28_shutil
import subprocess as _v28_sp
import sys as _v28_sys
import tempfile as _v28_temp
import time as _v28_time


def _v28_run():
    started = _v28_time.monotonic()
    with _v28_temp.TemporaryDirectory(prefix='v28-') as directory:
        root = _v28_Path(directory)
        modules = root / 'installed'
        modules.mkdir()
        for name in ('control_signer', 'control_keys', 'control_membership', 'authority_contract',
                     'control_store', 'git_process', 'credential_issue', 'control_revocation'):
            _v28_shutil.copyfile(ROOT / '.veldo' / (name + '.py'), modules / (name + '.py'))
        _v28_shutil.copyfile(ROOT / ".veldo" / "control_effects.py", modules / 'control_effects.py')
        _v28_shutil.copyfile(ROOT / ".veldo" / "control_effect_executor.py", modules / 'control_effect_executor.py')
        _v28_executor_spec = _v28_import.spec_from_file_location('v28_executor', modules / 'control_effect_executor.py')
        _v28_executor = _v28_import.module_from_spec(_v28_executor_spec)
        _v28_executor_spec.loader.exec_module(_v28_executor)
        E, G = _v28_executor.E, _v28_executor._git_process
        private = root / 'private'
        private.mkdir(mode=0o700)
        for name in ('journal', 'worker', 'stranger'):
            _v28_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / name)],
                        check=True, capture_output=True, timeout=10)
        credential = private / 'provider-auth'
        credential.write_text('fixture authentication material\n')
        credential.chmod(0o600)
        db = root / 'control.sqlite3'
        conn = E.S.open_store(str(db))
        journal = ('owner', lambda data: E.SIG.sign_bytes(private / 'journal', data, 'veldo-journal'))
        count = 0
        def put(identity, kind, data, store=None):
            nonlocal count
            count += 1
            store = store or conn
            old = E.S.materialized_state(store)['entities'].get(identity, {}).get('version', 0)
            return E.S.execute(store, {'command_id': 'setup-' + str(count), 'principal': 'owner',
                'operation': 'upsert_entity', 'parameters': {'entity_id': identity, 'kind': kind, 'data': data},
                'expected_versions': {identity: old}, 'artifact_digests': [], 'nonce': 'setup-' + str(count)},
                journal[0], journal[1], 1)
        # Accepted membership and contract records are the narrow upstream fixture seam.
        # No worker IPC operation can write any of these entities.
        put('worker', 'membership', {'principal_type': 'agent_run', 'roles': ['builder'],
                                    'scope': ['repo'], 'revoked_at': None, 'expires_at': None})
        put('worker-key', 'verification_key', {'principal': 'worker', 'public_key':
            ' '.join((private / 'worker.pub').read_text().split()[:2]), 'effective_at': 0,
            'retired_at': None, 'revoked_at': None})
        receiver = private / 'receiver.py'
        receiver.write_text('''import json,sys
from pathlib import Path
p=json.load(sys.stdin)
with Path(sys.argv[1]).open('a') as f:
    f.write(json.dumps({k:p[k] for k in ('dispatch_id','target','request_digest')})+'\\n')
result={k:p[k] for k in ('dispatch_id','target','request_digest')}
result.update(status=p['payload'].get('outcome','completed'),evidence={'observed':True})
if p['payload'].get('misbind'):
    result['dispatch_id']='foreign-dispatch'
print(json.dumps(result))
''')
        repo, remote = root / 'source', root / 'remote.git'
        def git(*args):
            return G.run(['git', *args], check=True, capture_output=True, text=True,
                         identity=('Effect fixture', 'effect@example.invalid')).stdout.strip()
        git('init', '-q', str(repo))
        git('init', '-q', '--bare', str(remote))
        (repo / 'file').write_text('old\n')
        git('-C', str(repo), 'add', 'file')
        git('-C', str(repo), 'commit', '-qm', 'old')
        old = git('-C', str(repo), 'rev-parse', 'HEAD')
        git('-C', str(repo), 'push', str(remote), 'HEAD:refs/heads/main')
        (repo / 'file').write_text('tested\n')
        git('-C', str(repo), 'commit', '-qam', 'tested')
        tip = git('-C', str(repo), 'rev-parse', 'HEAD')
        tree = git('-C', str(repo), 'rev-parse', 'HEAD^{tree}')
        config = {'store': str(db), 'journal_key': str(private / 'journal'),
                  'domain_uuid': 'domain', 'repository_uuid': 'repo', 'receivers': {}}
        for kind in E.KINDS:
            for name in ('good', 'outside'):
                target = kind + '-' + name
                config['receivers'][target] = {'kind': kind, 'argv': [_v28_sys.executable, str(receiver), str(root / (target + '.jsonl'))],
                                               'credential_file': str(credential)}
        config['receivers']['git-target'] = {'kind': 'publication', 'repository': str(repo),
                                             'remote': str(remote), 'ref': 'refs/heads/main'}
        config_path = private / 'config.json'
        config_path.write_text(_v28_json.dumps(config))
        observations = []
        def call(request, key='worker'):
            answer = _v28_executor.call(config_path, request, 'worker', private / key if key else None)
            observations.append(answer)
            return answer
        def setup(kind, name, outcome='completed', target=None, payload=None):
            cid = kind + '-' + name
            contract = dict(domain_uuid='domain', repository_uuid='repo', unit='unit-' + cid,
                station='build', sandbox='sandbox-' + cid, dispatch_id='dispatch-' + cid,
                kind=kind, target=target or kind + '-good', worker='worker', status='accepted',
                deadline=_v28_time.time() + 600, permission_id='permit-' + cid,
                payload=payload or {'outcome': outcome})
            if kind == 'publication':
                contract['payload'] = dict(commit=tip, tree=tree, old_tip=old, **contract['payload']) if 'commit' not in contract['payload'] else contract['payload']
            put(cid, 'effect_contract', contract)
            entry = E.S.materialized_state(conn)['entities'][cid]
            permission = dict(contract_digest=entry['digest'], authorized=True, obligations=[],
                expires_at=_v28_time.time() + 600, subscription_allowed=True, remaining_calls=2,
                gate_passed=True, gate_tree=contract['payload'].get('tree'), review_passed=True,
                reviewer='independent-reviewer', reviewer_group='review-group', worker_group='build-group', approval_current=True)
            put(contract['permission_id'], 'effect_permission', permission)
            request = {f: contract[f] for f in E.BINDINGS}
            request.update(contract_id=cid, operation='issue')
            issued = call(request)
            request.update(operation='execute', handle=issued.get('handle', 'missing'))
            return request, issued, contract, permission
        def calls(target):
            path = root / (target + '.jsonl')
            return [_v28_json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
        checks = {}
        def row(name, condition):
            checks[name] = bool(condition)
        for kind in E.KINDS:
            req, issued, contract, permit = setup(kind, 'scope')
            outside = dict(req, target=kind + '-outside')
            denied = call(outside)
            binding = issued.get('binding', {})
            binding_ok = (all(binding.get(f) == contract[f] for f in E.BINDINGS)
                and binding.get('contract_id') == req['contract_id']
                and binding.get('contract_digest') == E.S.materialized_state(conn)['entities'][req['contract_id']]['digest']
                and binding.get('contract_version') == 1 and binding.get('worker') == 'worker')
            rejects = []
            for field in ('unit', 'station', 'sandbox', 'domain_uuid', 'repository_uuid', 'dispatch_id'):
                rejects.append(call(dict(req, **{field: 'foreign'})).get('accepted') is False)
            expired_req, _, expired_contract, expired_permit = setup(kind, 'expired')
            hid = 'handle:' + E.SIG.digest(expired_req['handle'])
            data = E.S.materialized_state(conn)['entities'][hid]['data']
            put(hid, 'effect_handle', dict(data, expires_at=0))
            expired = call(expired_req)
            row('scope/' + kind, binding_ok and denied.get('accepted') is False and all(rejects)
                and len(calls(kind + '-outside')) == 0 and expired.get('accepted') is False
                and binding.get('expires_at', 1e100) <= contract['deadline'] + 900)
            before = len(calls(kind + '-good'))
            first, second = call(req), call(req)
            changed = call(dict(req, content='changed'))
            records = E.S.materialized_state(conn)
            effect = records['entities'].get('effect:' + req['dispatch_id'], {}).get('data', {})
            uses = conn.execute('SELECT count(*) FROM nonces WHERE nonce=?', ('handle:' + E.SIG.digest(req['handle']),)).fetchone()[0]
            accepts = conn.execute("SELECT count(*) FROM journal WHERE transition LIKE ? AND transition LIKE ?",
                                   ('%protected_effect%', '%' + req['dispatch_id'] + '%')).fetchone()[0]
            row('nonce/' + kind, first.get('accepted') is True and first == second
                and changed.get('refusal') == 'request-content-conflict' and uses == 1
                and len(calls(kind + '-good')) - before == 1 and accepts == 2
                and effect.get('request_digest') == E.SIG.digest(req))
            statuses = []
            for outcome in ('accepted', 'completed', 'unknown'):
                r, _, _, _ = setup(kind, outcome, outcome)
                before = len(calls(kind + '-good'))
                a, b = call(r), call(r)
                result = a.get('result', {})
                statuses.append(a == b and len(calls(kind + '-good')) == before + 1
                    and result.get('status') == outcome and result.get('completed') == (outcome == 'completed')
                    and result.get('dispatch_id') == r['dispatch_id'] and result.get('target') == r['target']
                    and result.get('request_digest') == E.SIG.digest(r)
                    and result.get('stop') == {'accepted': 'effect-pending', 'completed': None, 'unknown': 'effect-outcome-unknown'}[outcome])
            r, _, _, _ = setup(kind, 'misbound', payload={'misbind': True})
            wrong = call(r).get('result', {})
            row('completion/' + kind, all(statuses) and wrong.get('status') == 'unknown'
                and wrong.get('completed') is False and wrong.get('stop') == 'effect-outcome-unknown')
            # Current authority and evidence must fail before receiver invocation.
            r, _, c, p = setup(kind, 'authority')
            before = len(calls(kind + '-good'))
            put(c['permission_id'], 'effect_permission', dict(p, authorized=False))
            missing = call(r)
            put(c['permission_id'], 'effect_permission', dict(p, **({'remaining_calls': 0} if kind == 'provider' else {'reviewer': 'worker'})))
            boundary = call(r)
            row('current-authority/' + kind, missing.get('accepted') is False and boundary.get('accepted') is False
                and len(calls(kind + '-good')) == before)
        r, _, _, _ = setup('publication', 'real-git', target='git-target',
                            payload={'commit': tip, 'tree': tree, 'old_tip': old})
        landed = call(r)
        actual = git('ls-remote', str(remote), 'refs/heads/main').split()[0]
        row('real-publication', landed.get('result', {}).get('completed') is True and actual == tip and call(r) == landed)
        # R2: the trusted clone's own configuration widens an ordinary push (followTags with
        # an annotated tag on the tip, push.default=matching with another branch), and a
        # remote hook changes a second ref. Publication sends exactly the authorized ref, and
        # completion is claimed only when that ref is the one remote change.
        def remote_refs(path):
            listed = git('ls-remote', '--refs', str(path))
            return {name: sha for sha, name in (line.split('\t', 1) for line in listed.splitlines())}
        published = {}
        for name in ('exact-ref', 'side-effect'):
            clone, bare = root / (name + '-source'), root / (name + '-remote.git')
            git('clone', '-q', '--no-local', str(repo), str(clone))
            git('init', '-q', '--bare', str(bare))
            git('-C', str(clone), 'push', '-q', str(bare), old + ':refs/heads/main')
            git('-C', str(clone), 'config', 'push.followTags', 'true')
            git('-C', str(clone), 'config', 'push.default', 'matching')
            git('-C', str(clone), 'branch', 'unauthorized-branch', tip)
            git('-C', str(clone), 'tag', '-a', 'release-not-authorized', '-m', 'not in the contract', tip)
            if name == 'side-effect':
                hook = bare / 'hooks' / 'post-receive'
                hook.write_text('#!/bin/sh\ngit update-ref refs/tags/receiver-side-effect ' + old + '\n')
                hook.chmod(0o755)
            config['receivers']['git-' + name] = {'kind': 'publication', 'repository': str(clone),
                                                   'remote': str(bare), 'ref': 'refs/heads/main'}
            config_path.write_text(_v28_json.dumps(config))
            r, _, _, _ = setup('publication', name, target='git-' + name,
                                payload={'commit': tip, 'tree': tree, 'old_tip': old})
            widened = (git('-C', str(clone), 'config', 'push.followTags') == 'true'
                and git('-C', str(clone), 'cat-file', '-t', 'release-not-authorized') == 'tag')
            published[name] = (widened, call(r).get('result', {}), remote_refs(bare))
        widened, result, refs = published['exact-ref']
        row('publication-exact-ref', widened and result.get('completed') is True
            and result.get('status') == 'completed' and refs == {'refs/heads/main': tip})
        widened, result, refs = published['side-effect']
        row('publication-confirms-one-change', widened and result.get('completed') is False
            and result.get('status') == 'unknown' and result.get('stop') == 'effect-outcome-unknown'
            and refs == {'refs/heads/main': tip, 'refs/tags/receiver-side-effect': old})
        for name in ('publication-exact-ref', 'publication-confirms-one-change'):
            expect('VELDO-0028 effects/' + name, checks[name])
        row('authenticated-ipc', call(r, 'stranger').get('accepted') is False and call(r, None).get('accepted') is False)
        row('worker-credential-read', call({'operation': 'read_credential', 'path': str(credential)}).get('refusal') == 'credential-access-refused'
            and credential.read_text() not in _v28_json.dumps(observations)
            and 'PRIVATE KEY' not in _v28_json.dumps(observations))
        # The store's accepted authorization, handle consumption and effect acceptance
        # share one signed journal transaction; inspect the actual persisted signature.
        journal_rows = E.S.export_journal(conn)
        signed = journal_rows[-1]
        key = ' '.join((private / 'journal.pub').read_text().split()[:2])
        ok, _ = E.AC.ssh_keygen_verify(E.S.journal_signed_bytes(signed), signed['signature'],
            E.AC.allowed_signers_line('effect-executor', key, 'veldo-journal'), 'effect-executor', 'veldo-journal')
        row('signed-store', ok and E.metrics(conn)['pending'] >= 4)
        # R1: real authorization revocation after issuance, including a first ledger
        # insertion between the acceptance preflight and its SQLite transaction.
        R = E.organ('control_revocation')
        R.attach(E.S)
        for kind in E.KINDS:
            for timing in ('committed', 'before-transaction'):
                req, issued, contract, permit = setup(kind, 'revoked-' + timing)
                copy_path = root / (kind + '-' + timing + '.sqlite3')
                revoked_conn = E.S.open_store(str(copy_path))
                conn.backup(revoked_conn)
                isolated = dict(config, store=str(copy_path))
                isolated_path = private / 'revoked-config.json'
                isolated_path.write_text(_v28_json.dumps(isolated))
                before_calls = len(calls(kind + '-good'))
                def revoke():
                    now = _v28_time.time()
                    R.execute(E.S, revoked_conn, dict(command_id='revoke-worker', principal='owner',
                        operation='revoke_authorization', parameters=dict(principal='worker', at=now,
                            reason='operator withdrew authorization', revoked_by='owner'),
                        expected_versions={}, artifact_digests=[], nonce='revoke-worker'), journal, now)
                original = E.transact
                reissued = {'refusal': 'revoked'}
                if timing == 'committed':
                    revoke()
                    answer = _v28_executor.call(isolated_path, req, 'worker', private / 'worker')
                    # A committed revocation also refuses a new handle for the same contract.
                    reissued = _v28_executor.call(isolated_path, {f: v for f, v in dict(req, operation='issue').items()
                                                                  if f != 'handle'}, 'worker', private / 'worker')
                else:
                    def interleave(c, operation, *args):
                        if operation == 'accept_protected_effect':
                            revoke()
                        return original(c, operation, *args)
                    E.transact = interleave
                    challenge = 'revocation-interleave'
                    signature = E.SIG.sign_bytes(private / 'worker', E.SIG.canonical(
                        dict(challenge=challenge, request_digest=E.SIG.digest(req))), E.NAMESPACE)
                    try:
                        answer = _v28_executor.execute(isolated, req, 'worker', challenge, signature)
                    finally:
                        E.transact = original
                state = E.S.materialized_state(revoked_conn)
                refused = (issued.get('accepted') is True
                    and R.is_revoked(E.S, revoked_conn, 'worker', _v28_time.time())
                    and answer.get('accepted') is False and reissued.get('refusal') == 'revoked'
                    and len(calls(kind + '-good')) == before_calls
                    and 'effect:' + req['dispatch_id'] not in state['entities']
                    and 'handle:' + E.SIG.digest(req['handle']) not in state['nonces']
                    and state['entities'][contract['permission_id']]['data'] == permit)
                row('revocation-' + timing + '/' + kind, refused)
                expect('VELDO-0028 effects/revocation-' + timing + '/' + kind, refused)
                revoked_conn.close()
        # R3: revocation reaches every protected effect through VELDO-0026's own ledger. Each
        # scenario runs on an isolated copy of the store so the revocation stays local to it.
        def isolate(tag):
            path = root / (tag + '.sqlite3')
            copy = E.S.open_store(str(path))
            conn.backup(copy)
            isolated_path = private / (tag + '-config.json')
            isolated_path.write_text(_v28_json.dumps(dict(config, store=str(path))))
            return copy, isolated_path
        def revoke_on(store, principal, at, command_id):
            R.execute(E.S, store, dict(command_id=command_id, principal='owner', operation='revoke_authorization',
                parameters=dict(principal=principal, at=at, reason='operator withdrew authorization', revoked_by='owner'),
                expected_versions={}, artifact_digests=[], nonce=command_id), journal, _v28_time.time())
        def unused(store, request):
            state = E.S.materialized_state(store)
            return ('effect:' + request['dispatch_id'] not in state['entities']
                    and 'handle:' + E.SIG.digest(request['handle']) not in state['nonces'])
        for kind in E.KINDS:
            # A: an effect the receiver accepted and has not finished is IN FLIGHT when its worker
            # is revoked; one that completed with evidence is not.
            pending, _, _, _ = setup(kind, 'in-flight', 'accepted')
            settled, _, _, _ = setup(kind, 'settled', 'completed')
            store, isolated_path = isolate(kind + '-in-flight')
            ran = [_v28_executor.call(isolated_path, r, 'worker', private / 'worker').get('result', {}) for r in (pending, settled)]
            revoke_on(store, 'worker', _v28_time.time(), 'revoke-in-flight')
            closure = R.closure_status(E.S, store, 'worker')
            stops = R.pending_stop_obligations(E.S, store)
            recorded = E.S.materialized_state(store)['entities']
            # The copy also holds this worker's earlier pending effects; judge the two named here.
            link, done = (recorded.get('effect:' + r['dispatch_id'], {}).get('data', {}).get('revocation_effect') for r in (pending, settled))
            in_flight = closure.get('in_flight', [])
            row('revocation-in-flight/' + kind, ran[0].get('stop') == 'effect-pending' and ran[1].get('completed') is True
                and closure.get('revoked') is True and closure.get('effective') is False
                and link is not None and link in in_flight and done is not None and done not in in_flight
                and [data.get('effect') for _, data in stops if data.get('effect') in (link, done)] == [link])
            expect('VELDO-0028 effects/revocation-in-flight/' + kind, checks['revocation-in-flight/' + kind])
            store.close()
            # B: a committed ledger revocation dated ahead of the executor's clock applies from
            # its commit: neither a new handle nor the already issued one is honored.
            req, issued, contract, permit = setup(kind, 'future-dated')
            store, isolated_path = isolate(kind + '-future-dated')
            before_calls = len(calls(kind + '-good'))
            revoke_on(store, 'worker', _v28_time.time() + 3600, 'revoke-future-dated')
            reissue = {f: v for f, v in dict(req, operation='issue').items() if f != 'handle'}
            answers = [_v28_executor.call(isolated_path, r, 'worker', private / 'worker') for r in (reissue, req)]
            row('revocation-future-dated/' + kind, issued.get('accepted') is True
                and [a.get('refusal') for a in answers] == ['revoked', 'revoked']
                and len(calls(kind + '-good')) == before_calls and unused(store, req)
                and E.S.materialized_state(store)['entities'][contract['permission_id']]['data'] == permit)
            expect('VELDO-0028 effects/revocation-future-dated/' + kind, checks['revocation-future-dated/' + kind])
            store.close()
        # E: a review by a principal the ledger revoked satisfies nothing; a fresh permission
        # naming a current reviewer is the fresh authorization and publishes.
        req, _, contract, permit = setup('publication', 'revoked-reviewer')
        store, isolated_path = isolate('revoked-reviewer')
        before_calls = len(calls('publication-good'))
        revoke_on(store, permit['reviewer'], _v28_time.time(), 'revoke-reviewer')
        refused = _v28_executor.call(isolated_path, req, 'worker', private / 'worker')
        refused_clean = len(calls('publication-good')) == before_calls and unused(store, req)
        put(contract['permission_id'], 'effect_permission', dict(permit, reviewer='current-reviewer'), store)
        fresh = _v28_executor.call(isolated_path, req, 'worker', private / 'worker')
        row('publication-revoked-reviewer', refused.get('refusal') == 'revoked-reviewer' and refused_clean
            and fresh.get('result', {}).get('completed') is True and len(calls('publication-good')) == before_calls + 1)
        expect('VELDO-0028 effects/publication-revoked-reviewer', checks['publication-revoked-reviewer'])
        store.close()
        # Linux custody witness: this isolated probe can execute but cannot read private
        # service files. Provisioning this boundary for real workers belongs to W26.
        probe = '''import ctypes,sys
lib=ctypes.CDLL(None,use_errno=True)
a=ctypes.c_uint64(4)
fd=lib.syscall(444,ctypes.byref(a),8,0)
if fd<0 or lib.prctl(38,1,0,0,0)!=0 or lib.syscall(446,fd,0)!=0:
 sys.exit(2)
try:
 open(sys.argv[1]).read()
except PermissionError:
 print('read-denied')
else:
 print('read-allowed')
'''
        denied = _v28_sp.run([_v28_sys.executable, '-c', probe, str(credential)],
                             capture_output=True, text=True, timeout=10)
        checks['worker-credential-read'] &= denied.returncode == 0 and denied.stdout.strip() == 'read-denied'
        for kind in E.KINDS:
            checks['scope/' + kind] &= checks['current-authority/' + kind] and checks['authenticated-ipc'] and checks['worker-credential-read']
            checks['nonce/' + kind] &= checks['signed-store']
            if kind == 'publication':
                checks['completion/' + kind] &= checks['real-publication']
            for criterion in ('scope', 'nonce', 'completion'):
                name = criterion + '/' + kind
                expect('VELDO-0028 effects/' + name, checks[name])
        print('VELDO-0028 observations: ' + _v28_json.dumps({'checks': checks,
            'provider_calls': len(calls('provider-good')), 'publication_calls': len(calls('publication-good')),
            'out_of_scope_calls': len(calls('provider-outside')) + len(calls('publication-outside')),
            'remote_commit_confirmed': actual == tip, 'metrics': E.metrics(conn)}, sort_keys=True))
        conn.close()
    print('VELDO-0028 suite seconds: %.3f' % (_v28_time.monotonic() - started))


_v28_run()
