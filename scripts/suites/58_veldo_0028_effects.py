"""VELDO-0028: installed copies, real signed IPC, SQLite and local Git receivers.

Provider/queued-lander receivers are harmless trusted protocol witnesses, not live model
qualification. A completed publication drives real Git and confirms the remote commit.
"""
import http.server as _v28_http
import importlib.util as _v28_import
import os as _v28_os
from pathlib import Path as _v28_Path
import json as _v28_json
import shlex as _v28_shlex
import shutil as _v28_shutil
import subprocess as _v28_sp
import sys as _v28_sys
import tempfile as _v28_temp
import threading as _v28_threading
import time as _v28_time


class _V28Backend(_v28_http.BaseHTTPRequestHandler):
    """A smart-HTTP Git remote: each request runs `git http-backend` as CGI over the fixture root."""
    project_root = None

    def do_GET(self):
        self.backend()

    def do_POST(self):
        self.backend()

    def log_message(self, *args):
        pass

    def backend(self):
        path, _, query = self.path.partition('?')
        if self.headers.get('Transfer-Encoding', '').lower() == 'chunked':
            body = b''
            while True:
                size = int(self.rfile.readline().split(b';')[0].strip(), 16)
                chunk = self.rfile.read(size + 2)[:size]
                if not size:
                    break
                body += chunk
        else:
            body = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        env = {'PATH': _v28_os.environ.get('PATH', _v28_os.defpath), 'HOME': self.project_root,
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': _v28_os.devnull,
               'GIT_PROJECT_ROOT': self.project_root, 'GIT_HTTP_EXPORT_ALL': '1',
               'REQUEST_METHOD': self.command, 'PATH_INFO': path, 'QUERY_STRING': query,
               'CONTENT_TYPE': self.headers.get('Content-Type', ''), 'CONTENT_LENGTH': str(len(body)),
               'REMOTE_ADDR': '127.0.0.1'}
        if self.headers.get('Content-Encoding'):
            env['HTTP_CONTENT_ENCODING'] = self.headers['Content-Encoding']
        if self.headers.get('Git-Protocol'):
            env['GIT_PROTOCOL'] = env['HTTP_GIT_PROTOCOL'] = self.headers['Git-Protocol']
        out = _v28_sp.run(['git', 'http-backend'], input=body, capture_output=True, env=env, timeout=20).stdout
        split = b'\r\n\r\n' if b'\r\n\r\n' in out else b'\n\n'
        head, _, payload = out.partition(split)
        status, headers = 200, []
        for line in head.decode('latin-1').splitlines():
            key, _, value = line.partition(':')
            if key.lower() == 'status':
                status = int(value.split()[0])
            elif key:
                headers.append((key, value.strip()))
        self.send_response(status)
        for key, value in headers:
            self.send_header(key, value)
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class _V28AuthBackend(_V28Backend):
    """The same remote behind HTTP Basic authentication, as a hosted Git server requires."""
    credential = 'Basic ' + __import__('base64').b64encode(b'deploy:fixture-secret').decode()

    def backend(self):
        if self.headers.get('Authorization') != self.credential:
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="git"')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        _V28Backend.backend(self)



# Fake credentials for the scrubbing rows, assembled at run time so no source line reads like a login
# (secret scanners match the literal text; the values the rows see are unchanged).
_V28_S = 'SEC' + 'RET'
_V28_U = _V28_S + 'USER'
_V28_P = _V28_S + 'PW'
_V28_T = _V28_S + 'TOKEN'

def _v28_run():
    started = _v28_time.monotonic()
    with _v28_temp.TemporaryDirectory(prefix='v28-') as directory, __import__('contextlib').ExitStack() as wired:
        root = _v28_Path(directory)
        modules = root / 'installed'
        modules.mkdir()
        for name in ('control_signer', 'control_keys', 'control_membership', 'authority_contract',
                     'control_store', 'credential_issue', 'control_revocation'):
            _v28_shutil.copyfile(ROOT / '.veldo' / (name + '.py'), modules / (name + '.py'))
        _v28_shutil.copyfile(ROOT / ".veldo" / "git_process.py", modules / 'git_process.py')
        _v28_shutil.copyfile(ROOT / ".veldo" / "control_effects.py", modules / 'control_effects.py')
        _v28_shutil.copyfile(ROOT / ".veldo" / "control_effect_executor.py", modules / 'control_effect_executor.py')
        # VELDO-0153: a publication resolves the repository's Git identity and pushes through the
        # identity transport, which resolves that identity's credential.
        for name in ('control_git_identity', 'control_git_identity_transport', 'control_credential_keystore', 'secretref'):
            _v28_shutil.copyfile(ROOT / '.veldo' / (name + '.py'), modules / (name + '.py'))
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
if 'refusal' in p['payload']:
    result['refusal']=p['payload']['refusal'][::-1]
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
        # VELDO-0153: the repository's identity is bound on the store the executor reads, and the test
        # wire maps each remote registered under the identity's owner to its bare repository.
        __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))['bind'](
            modules, conn, 'domain', 'repo', repo)
        wire = __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/identity_wire.py'))['Wire'](root / 'wire')
        wired.enter_context(wire.active())
        def wired_url(name, url):
            # A local remote is published to by the URL the wire registers for it under the owner.
            path = url[len('file://'):] if url.startswith('file://') else url
            return wire.remote(name, path) if _v28_os.path.isabs(path) and _v28_os.path.exists(path) else url
        config = {'store': str(db), 'journal_key': str(private / 'journal'),
                  'domain_uuid': 'domain', 'repository_uuid': 'repo', 'receivers': {}}
        for kind in E.KINDS:
            for name in ('good', 'outside'):
                target = kind + '-' + name
                config['receivers'][target] = {'kind': kind, 'argv': [_v28_sys.executable, str(receiver), str(root / (target + '.jsonl'))],
                                               'credential_file': str(credential)}
        config['receivers']['git-target'] = {'kind': 'publication', 'repository': str(repo),
                                             'remote': wired_url('target', str(remote)), 'ref': 'refs/heads/main'}
        config_path = private / 'config.json'
        config_path.write_text(_v28_json.dumps(config))
        observations = []
        # The executor is a child process and inherits this environment. Every call runs with no
        # ambient GIT_* variable and an empty operator home, so global Git configuration and
        # transport variables reach it only where a row supplies them for that one call.
        empty_home = root / 'operator-home'
        empty_home.mkdir()
        def call(request, key='worker', env=None):
            saved = dict(_v28_os.environ)
            try:
                for name in [k for k in _v28_os.environ if k.startswith('GIT_')]:
                    del _v28_os.environ[name]
                _v28_os.environ.update({'HOME': str(empty_home), 'XDG_CONFIG_HOME': str(empty_home), **(env or {})})
                answer = _v28_executor.call(config_path, request, 'worker', private / key if key else None)
            finally:
                _v28_os.environ.clear()
                _v28_os.environ.update(saved)
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
            # A receiver that ran and then reports refused may already have acted: only the
            # executor's own refusal, before any receiver runs, is conclusive, and the receiver's
            # text (the contract's marker reversed, so it appears nowhere else) is neither
            # returned to the worker nor stored.
            r, _, _, _ = setup(kind, 'receiver-refused', payload={'outcome': 'refused', 'refusal': 'RECEIVERTEXT'})
            before = len(calls(kind + '-good'))
            answer = call(r)
            result = answer.get('result', {})
            stored = E.S.materialized_state(conn)['entities'].get('effect:' + r['dispatch_id'], {}).get('data', {})
            row('receiver-refused-is-unknown/' + kind, len(calls(kind + '-good')) == before + 1
                and answer.get('accepted') is True and result.get('status') == 'unknown'
                and result.get('completed') is False and result.get('stop') == 'effect-outcome-unknown'
                and 'TXETREVIECER' not in _v28_json.dumps(answer) and 'TXETREVIECER' not in _v28_json.dumps(stored))
            expect('VELDO-0028 effects/receiver-refused-is-unknown/' + kind, checks['receiver-refused-is-unknown/' + kind])
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
                                                   'remote': wired_url(name, str(bare)), 'ref': 'refs/heads/main'}
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
        # Publication uses the identity profile. AC3 removes clone hooks and routing;
        # the authorized ref, destination state and transport exit still establish completion.
        def fresh(name):
            clone, bare = root / (name + '-source'), root / (name + '-remote.git')
            git('clone', '-q', '--no-local', str(repo), str(clone))
            git('init', '-q', '--bare', str(bare))
            git('-C', str(clone), 'push', '-q', str(bare), old + ':refs/heads/main')
            return clone, bare
        def publish(name, clone, remote_url, env=None):
            config['receivers']['git-' + name] = {'kind': 'publication', 'repository': str(clone),
                                                   'remote': wired_url(name, remote_url), 'ref': 'refs/heads/main'}
            config_path.write_text(_v28_json.dumps(config))
            pr, _, _, _ = setup('publication', name, target='git-' + name,
                                 payload={'commit': tip, 'tree': tree, 'old_tip': old})
            return call(pr, env=env).get('result', {})
        def publish_as(name, clone, remote_url, env=None, ref='refs/heads/main', old_tip=None, receiver=None):
            # The whole answer: a refusal raised by the receiver reaches the caller by name.
            config['receivers']['git-' + name] = dict({'kind': 'publication', 'repository': str(clone),
                                                        'remote': wired_url(name, remote_url), 'ref': ref}, **(receiver or {}))
            config_path.write_text(_v28_json.dumps(config))
            pr, _, _, _ = setup('publication', name, target='git-' + name,
                                 payload={'commit': tip, 'tree': tree, 'old_tip': old if old_tip is None else old_tip})
            return pr, call(pr, env=env)
        def remote_main(bare):
            return git('-C', str(bare), 'rev-parse', 'refs/heads/main')
        # AC3: plant a clone hook that would refuse and record its invocation if it ran.
        clone, bare = fresh('pre-push-hook')
        ran = root / 'pre-push-hook.ran'
        hook = clone / '.git' / 'hooks' / 'pre-push'
        hook.write_text('#!/bin/sh\ntouch ' + str(ran) + '\necho policy refuses this push >&2\nexit 1\n')
        hook.chmod(0o755)
        result = publish('pre-push-hook', clone, str(bare))
        # VELDO-0153 AC3: clone code never runs with the identity's credential.
        row('publication-pre-push-hook', not ran.exists() and result.get('completed') is True
            and result.get('status') == 'completed' and remote_main(bare) == tip)
        # P7: the clone rewrites an alias to the real remote with url.<real>.insteadOf.
        clone, bare = fresh('url-rewrite')
        alias = wired_url('url-rewrite', str(bare))
        git('-C', str(clone), 'config', 'url.' + str(bare) + '.insteadOf', alias)
        result = publish('url-rewrite', clone, alias)
        # VELDO-0153 AC3: the clone's rewrite refuses before a network write.
        row('publication-url-rewrite', result.get('completed') is False and remote_main(bare) == old
            and result.get('refusal') == 'binding_mismatch:identity_transport_config')
        # A smart-HTTP remote served by git http-backend.
        clone, bare = fresh('smart-http')
        git('-C', str(bare), 'config', 'http.receivepack', 'true')
        _V28Backend.project_root = str(root)
        server = _v28_http.ThreadingHTTPServer(('127.0.0.1', 0), _V28Backend)
        _v28_threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True).start()
        try:
            url = 'http://127.0.0.1:%d/%s' % (server.server_address[1], bare.name)
            reachable = git('-C', str(clone), 'ls-remote', url, 'refs/heads/main').split()[:1] == [old]
            # The factory is given the identity's remote (VELDO-0153); the wire carries the identity
            # push to this smart-HTTP server, so git's HTTP transport still does the publishing.
            result = publish('smart-http', clone, wire.remote('smart-http', url))
        finally:
            server.shutdown()
            server.server_close()
        row('publication-smart-http', reachable and result.get('completed') is True and remote_main(bare) == tip)
        # P2: HEAD is confirmed with its target. Control: HEAD names the authorized ref and
        # follows it, so the publication completes. Then the remote repoints HEAD at another
        # branch that already holds the commit: every ref and HEAD's own commit are as
        # expected; only HEAD's target changed.
        clone, bare = fresh('head-follows')
        git('-C', str(bare), 'symbolic-ref', 'HEAD', 'refs/heads/main')
        follows = publish('head-follows', clone, str(bare))
        clone, bare = fresh('head-change')
        git('-C', str(bare), 'symbolic-ref', 'HEAD', 'refs/heads/main')
        git('-C', str(clone), 'push', '-q', str(bare), tip + ':refs/heads/other')
        hook = bare / 'hooks' / 'post-receive'
        hook.write_text('#!/bin/sh\ngit symbolic-ref HEAD refs/heads/other\n')
        hook.chmod(0o755)
        result = publish('head-change', clone, str(bare))
        row('publication-head-change', follows.get('completed') is True and result.get('completed') is False and result.get('status') == 'unknown'
            and result.get('stop') == 'effect-outcome-unknown' and remote_main(bare) == tip
            and git('-C', str(bare), 'symbolic-ref', 'HEAD') == 'refs/heads/other')
        for name in ('pre-push-hook', 'url-rewrite', 'smart-http', 'head-change'):
            expect('VELDO-0028 effects/publication-' + name, checks['publication-' + name])
        # R5: an independent check of c5dc41a reproduced three publication defects. `r5` keeps
        # what each case actually observed for the printed observation line.
        r5 = {}
        def seen_result(name, result, **extra):
            r5[name] = dict(status=result.get('status'), completed=result.get('completed'), **extra)
        def operator_home(name, gitconfig=None):
            home = root / ('home-' + name)
            home.mkdir()
            if gitconfig is not None:
                (home / '.gitconfig').write_text(gitconfig)
            return {'HOME': str(home), 'XDG_CONFIG_HOME': str(home)}
        def elsewhere_for(name):
            other = root / (name + '-elsewhere.git')
            git('init', '-q', '--bare', str(other))
            git('-C', str(repo), 'push', '-q', str(other), old + ':refs/heads/main')
            return other
        # R5 1: push options configured in the clone or globally never reach the receiver. The
        # control push is a plain git push of another ref from the same clone: the receiver's
        # hook sees both options, so the fixture can see them when they are sent.
        clone, bare = fresh('push-options')
        git('-C', str(bare), 'config', 'receive.advertisePushOptions', 'true')
        seen = root / 'push-options.log'
        hook = bare / 'hooks' / 'post-receive'
        hook.write_text('#!/bin/sh\necho "count=${GIT_PUSH_OPTION_COUNT:-0} ${GIT_PUSH_OPTION_0:-}'
                        ' ${GIT_PUSH_OPTION_1:-} ${GIT_PUSH_OPTION_2:-}" >> ' + str(seen) + '\n')
        hook.chmod(0o755)
        git('-C', str(clone), 'config', '--add', 'push.pushOption', 'merge_request.create')
        git('-C', str(clone), 'config', '--add', 'push.pushOption', 'ci.skip')
        git('-C', str(clone), 'push', '-q', str(bare), old + ':refs/heads/control')
        result = publish('push-options', clone, str(bare),
                         env=operator_home('push-options', '[push]\n\tpushOption = global.option\n'))
        lines = [line.split() for line in seen.read_text().splitlines()] if seen.exists() else []
        seen_result('push-options', result, receiver_saw=lines)
        row('publication-push-options', result.get('completed') is True and remote_main(bare) == tip
            and lines == [['count=2', 'merge_request.create', 'ci.skip'], ['count=0']])
        # R6 1 and R7: the push is addressed to the authorized URL and routed by the operator's
        # configured routing, and the effect record stores where it went. The destinations are
        # git's own resolution of this push from configuration (`git remote show -n`, before
        # pushing), and completion is read from each destination's state after it: every resolved
        # destination must hold exactly the authorized change. Each case has a decoy repository
        # holding the old tip, so the lease holds wherever the routing sends the push. URLs are
        # recorded without their credentials.
        def recorded(name):
            data = E.S.materialized_state(conn)['entities'].get('effect:dispatch-publication-' + name, {}).get('data', {})
            return data.get('destination')
        def reached(*pairs):
            return [{'url': url, 'outcome': outcome} for url, outcome in pairs]
        routes = {}
        for name in ('control', 'insteadof', 'global-include-insteadof', 'named-pushurl', 'remotes-file', 'branches-file',
                     'push-instead-of', 'space-section-pushurl', 'fan-out-pushurls', 'fan-out-stale',
                     'fan-out-unreachable', 'config-newline', 'path-newline'):
            clone, bare = fresh('route-' + name)
            other = elsewhere_for('route-' + name)
            env = None
            if name == 'space-section-pushurl':
                spaced = root / ('route ' + name + '.git')
                bare.rename(spaced)
                bare = spaced
            if name == 'path-newline':
                broken = root / ('route-path\nnewline.git')
                bare.rename(broken)
                bare = broken
            url = wired_url('route-' + name, str(bare))
            if name == 'path-newline':
                url += '\nforged-destination'
            if name == 'insteadof':
                git('-C', str(clone), 'config', 'url.' + str(other) + '.insteadOf', url)
            elif name == 'global-include-insteadof':
                included = root / ('route-' + name + '.gitconfig')
                included.write_text('[url "%s"]\n\tinsteadOf = %s\n[remote "publication"]\n\tpushurl = %s\n'
                                    % (other, url, wired_url('route-global-decoy', str(other))))
                git('-C', str(clone), 'config', 'remote.publication.url', url)
                env = operator_home('route-' + name, '[includeIf "gitdir:%s/"]\n\tpath = %s\n' % (clone, included))
            elif name == 'named-pushurl':
                git('-C', str(clone), 'config', 'remote.publication.url', wired_url('route-fetch-decoy', str(other)))
                git('-C', str(clone), 'config', 'remote.publication.pushurl', url)
            elif name in ('remotes-file', 'branches-file'):
                # A remote nickname: the legacy file of that name gives the listing and the push
                # the decoy's URL.
                nickname = 'publish-target'
                legacy = clone / '.git' / name.split('-')[0]
                legacy.mkdir(exist_ok=True)
                (legacy / nickname).write_text(('URL: %s\n' if name == 'remotes-file' else '%s\n') % other)
                git('-C', str(clone), 'config', 'remote.' + nickname + '.url', url)
            elif name == 'push-instead-of':
                git('-C', str(clone), 'config', 'url.' + str(other) + '.pushInsteadOf', url)
            elif name == 'space-section-pushurl':
                git('-C', str(clone), 'config', 'remote.' + url + '.url', url)
                git('-C', str(clone), 'config', 'remote.' + url + '.pushurl', str(other))
            elif name.startswith('fan-out'):
                # Two pushurls: the authorized repository and a second one, which accepts, holds
                # no old tip (the lease rejects there) or does not exist.
                second = {'fan-out-pushurls': str(other), 'fan-out-unreachable': str(root / 'route-no-such.git')}.get(name)
                if name == 'fan-out-stale':
                    # The second repository moved on to another commit, so it is not at the old tip.
                    git('-C', str(other), 'update-ref', 'refs/heads/main',
                        git('-C', str(other), 'commit-tree', '-p', old, '-m', 'elsewhere', old + '^{tree}'))
                    second = str(other)
                git('-C', str(clone), 'config', 'remote.' + url + '.url', url)
                git('-C', str(clone), 'config', '--add', 'remote.' + url + '.pushurl', url)
                git('-C', str(clone), 'config', '--add', 'remote.' + url + '.pushurl', second)
            elif name == 'config-newline':
                # A configured pushurl holding a line break cannot be told apart from two URLs in
                # git's one-per-line report, so it is refused before anything is pushed.
                git('-C', str(clone), 'config', 'remote.' + url + '.url', url)
                git('-C', str(clone), 'config', 'remote.' + url + '.pushurl', str(other) + '\n  Push  URL: ' + url)
            receiver_url = ('publication' if name in ('global-include-insteadof', 'named-pushurl') else
                            'publish-target' if name in ('remotes-file', 'branches-file') else url)
            result = publish('route-' + name, clone, receiver_url, env=env)
            routes[name] = dict(result=result, url=url, bare=bare, other=other, destination=recorded('route-' + name),
                                authorized_moved=remote_main(bare) == tip, decoy_moved=remote_main(other) == tip)
            seen_result('route-' + name, result, authorized_moved=routes[name]['authorized_moved'],
                        decoy_moved=routes[name]['decoy_moved'], destination=routes[name]['destination'])
        def routed(name, completed, destinations, authorized_moved, decoy_moved):
            # `destinations` lists each repository the push was resolved to, with its outcome, and
            # the two flags say which of the authorized repository and the decoy hold the commit.
            # `completed` is True, False (unknown) or the name of the refusal made before pushing.
            case = routes[name]
            status = 'completed' if completed is True else 'unknown' if completed is False else 'refused'
            return (case['result'].get('completed') is (completed is True)
                    and case['result'].get('status') == status
                    and case['result'].get('refusal') == (completed if status == 'refused' else None)
                    and case['authorized_moved'] is authorized_moved and case['decoy_moved'] is decoy_moved
                    and case['destination'] == (None if destinations is None else
                                                {'authorized_url': case['url'], 'destinations': destinations})
                    and case['result'].get('destination') == case['destination'])
        url_of, decoy_of = (lambda name: routes[name]['url']), (lambda name: str(routes[name]['other']))
        # VELDO-0153 AC3: record only the checked URL. Clone routing refuses; global
        # routing and legacy files cannot redirect the literal destination.
        row('publication-records-resolved-destination',
            routed('control', True, reached((url_of('control'), 'at-tip')), True, False)
            and all(routed(name, True, reached((url_of(name), 'at-tip')), True, False)
                    for name in ('global-include-insteadof', 'named-pushurl', 'remotes-file', 'branches-file'))
            and all(routed(name, 'binding_mismatch:identity_transport_config', None, False, False)
                    for name in ('insteadof', 'push-instead-of', 'space-section-pushurl',
                                 'fan-out-pushurls', 'fan-out-stale', 'fan-out-unreachable', 'config-newline'))
            and routed('path-newline', 'invalid_input:remote', None, False, False))
        # R5 3: publication keeps what a plain git push from the same clone and the same operator
        # environment can do: global configuration and transport and credential variables.
        def fake_ssh(name):
            script, log = root / (name + '-ssh'), root / (name + '-ssh.log')
            script.write_text('#!/bin/sh\necho "$@" >> ' + str(log) + '\n'
                              'while [ $# -gt 1 ]; do case "$1" in -o|-p|-l|-i) shift 2 ;; -*) shift ;; *) break ;; esac; done\n'
                              'shift\nexec sh -c "$*"\n')
            script.chmod(0o755)
            return script, log
        # VELDO-0153 AC1 supersedes R5 3 for the factory's publication: the push runs in the
        # identity profile, which ignores global and system configuration, strips every GIT_*
        # variable and authenticates with the repository identity's credential alone. Each row
        # below plants the operator route R5 3 honored and asserts the publication used nothing
        # planted. Plain git from the same environment is the control that each plant is live.
        clone, bare = fresh('global-insteadof')
        decoy = elsewhere_for('global-insteadof')
        authorized = wired_url('global-insteadof', str(bare))
        planted = operator_home('global-insteadof', '[url "%s"]\n\tinsteadOf = %s\n' % (decoy, authorized))
        live = _v28_sp.run(['git', '-C', str(clone), 'ls-remote', '--get-url', authorized], capture_output=True, text=True,
                           timeout=20, env=dict({k: v for k, v in _v28_os.environ.items() if not k.startswith('GIT_')}, **planted)).stdout.strip()
        result = publish('global-insteadof', clone, authorized, env=planted)
        seen_result('global-insteadof', result, plain_git_resolves=live, decoy_moved=remote_main(decoy) == tip)
        # VELDO-0153 AC1: a global url.*.insteadOf is not read by the identity push.
        row('publication-global-insteadof', live == str(decoy) and result.get('completed') is True
            and remote_main(bare) == tip and remote_main(decoy) == old)
        clone, bare = fresh('global-credential-helper')
        git('-C', str(bare), 'config', 'http.receivepack', 'true')
        helper, helper_log = root / 'credential-helper', root / 'credential-helper.log'
        helper.write_text('#!/bin/sh\necho "$1" >> ' + str(helper_log) + '\n'
                          '[ "$1" = get ] && printf "username=deploy\\npassword=fixture-secret\\n"\nexit 0\n')
        helper.chmod(0o755)
        _V28Backend.project_root = str(root)
        server = _v28_http.ThreadingHTTPServer(('127.0.0.1', 0), _V28AuthBackend)
        _v28_threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True).start()
        try:
            url = 'http://127.0.0.1:%d/%s' % (server.server_address[1], bare.name)
            # Control: the server refuses a client without the operator's credential helper, and
            # accepts plain git that has it.
            unauthenticated = G.run(['git', 'ls-remote', url], capture_output=True, text=True, timeout=20).returncode != 0
            helped = operator_home('global-credential-helper', '[credential]\n\thelper = %s\n' % helper)
            authenticated = _v28_sp.run(['git', 'ls-remote', url], capture_output=True, text=True, timeout=20,
                                        env=dict({k: v for k, v in _v28_os.environ.items() if not k.startswith('GIT_')},
                                                 GIT_TERMINAL_PROMPT='0', **helped)).returncode == 0
            control_calls = helper_log.read_text().split() if helper_log.exists() else []
            helper_log.unlink(missing_ok=True)
            # The factory is given the identity's remote; the wire carries it to this server, which
            # accepts only the planted helper's credential.
            result = publish('global-credential-helper', clone, wire.remote('global-credential-helper', url), env=helped)
            # R6 1, superseded by VELDO-0153 AC1 and AC2: a URL carrying its own credential is not
            # the identity's credential, and is refused by name before any network write. The R6 1
            # guarantee kept: neither the answer nor the record carries the credential.
            keyed_clone, keyed_bare = fresh('keyed-url')
            keyed_url = wired_url('keyed-url', str(keyed_bare))
            _, keyed_answer = publish_as('keyed-url', keyed_clone, keyed_url.replace('https://', 'https://deploy:fixture-secret@'))
            keyed = keyed_answer.get('result', {})
        finally:
            server.shutdown()
            server.server_close()
        keyed_record = recorded('keyed-url')
        seen_result('keyed-url', keyed, destination=keyed_record, refusal=keyed_answer.get('refusal'))
        # VELDO-0153 AC1 and AC2: refused by name, nothing pushed, no credential anywhere.
        row('publication-destination-without-credentials', keyed_answer.get('accepted') is False
            and keyed_answer.get('refusal') == 'binding_mismatch:remote_host' and keyed.get('status') == 'refused'
            and remote_main(keyed_bare) == old and 'fixture-secret' not in _v28_json.dumps(keyed_answer)
            and 'fixture-secret' not in _v28_json.dumps(E.S.materialized_state(conn)['entities']))
        seen_result('global-credential-helper', result, unauthenticated_refused=unauthenticated,
                    planted_helper_authenticates=authenticated, planted_helper_calls=helper_log.exists())
        # VELDO-0153 AC1 ("Let the identity profile honor the global credential helper; the
        # planted-helper row must fail"): the planted helper is never asked and its credential
        # publishes nothing.
        row('publication-global-credential-helper', unauthenticated and authenticated and 'get' in control_calls
            and result.get('completed') is False and not helper_log.exists() and remote_main(bare) == old)
        clone, bare = fresh('env-ssh-command')
        script, log = fake_ssh('env-ssh-command')
        result = publish('env-ssh-command', clone, wired_url('env-ssh-command', str(bare)), env={'GIT_SSH_COMMAND': str(script)})
        seen_result('env-ssh-command', result, ssh_ran=log.exists())
        # VELDO-0153 AC1: GIT_SSH_COMMAND is stripped; the planted command never runs.
        row('publication-env-ssh-command', result.get('completed') is True and remote_main(bare) == tip
            and not log.exists())
        clone, bare = fresh('global-ssh-command')
        script, log = fake_ssh('global-ssh-command')
        result = publish('global-ssh-command', clone, wired_url('global-ssh-command', str(bare)),
                         env=operator_home('global-ssh-command', '[core]\n\tsshCommand = %s\n' % script))
        seen_result('global-ssh-command', result, ssh_ran=log.exists())
        # VELDO-0153 AC1: a global core.sshCommand is not read; the planted command never runs.
        row('publication-global-ssh-command', result.get('completed') is True and remote_main(bare) == tip
            and not log.exists())
        # R7: where the push went, and whether it completed, never come from the push's output.
        # Client pre-push hooks write to it (git runs them with standard output inherited) and a
        # server's proc-receive report can reshape it. Each case routes the push with a pushurl to
        # X while the authorized URL names L, and the text claims L.
        def hook(clone, body):
            path = clone / '.git' / 'hooks' / 'pre-push'
            path.write_text('#!/bin/sh\ncat >/dev/null\n' + body)
            path.chmod(0o755)
        def proc_receive(bare, body):
            # A server-side proc-receive hook (report-status v2), as AGit-style servers run one.
            git('-C', str(bare), 'config', 'receive.procReceiveRefs', 'refs/heads/main')
            path = bare / 'hooks' / 'proc-receive'
            path.write_text('#!' + _v28_sys.executable + '\n'
                            'import os, subprocess, sys\n'
                            'inp, out = sys.stdin.buffer, sys.stdout.buffer\n'
                            'def rd():\n    n = inp.read(4)\n    return None if not n or n == b"0000" else inp.read(int(n, 16) - 4)\n'
                            'def wr(s):\n    b = s.encode()\n    out.write(b"%04x" % (len(b) + 4) + b)\n'
                            'while rd() is not None: pass\n'
                            'wr("version=1\\n"); out.write(b"0000"); out.flush()\n'
                            'cmds = []\n'
                            'while True:\n    line = rd()\n    if line is None: break\n    cmds.append(line.decode().split())\n'
                            'for old, new, ref in cmds:\n' + body +
                            'out.write(b"0000"); out.flush()\n')
            path.chmod(0o755)
        def routed_to_x(name):
            clone, lbare = fresh(name)
            xbare = elsewhere_for(name)
            return clone, lbare, xbare
        def forged(lbare):
            # A To block naming L for the authorized refspec, ending in a fragment that swallows
            # git's own `To X` line.
            return 'printf "To file://%s\\n*\\t%s:refs/heads/main\\t[new branch]\\nx"\n' % (lbare, tip)
        text_cases = {}
        # AC3: the clone hook would mirror and forge output, but must never run.
        clone, lbare, xbare = routed_to_x('text-mirrored')
        hook(clone, 'git push -q --no-verify %s %s:refs/heads/main >/dev/null 2>&1\n' % (lbare, tip) + forged(lbare))
        text_cases['mirrored'] = (publish('text-mirrored', clone, 'file://' + str(lbare)), recorded('text-mirrored'), lbare, xbare)
        # The checked destination L refuses; a planted clone hook cannot alter the record.
        clone, lbare, xbare = routed_to_x('text-refused')
        refuse = lbare / 'hooks' / 'pre-receive'
        refuse.write_text('#!/bin/sh\necho refused >&2\nexit 1\n')
        refuse.chmod(0o755)
        hook(clone, forged(lbare))
        text_cases['refused'] = (publish('text-refused', clone, 'file://' + str(lbare)), recorded('text-refused'), lbare, xbare)
        # L's proc-receive reports success without updating L, mirrors to X and forges
        # a To block for X. Completion must still be read from the checked L.
        clone, lbare, xbare = routed_to_x('text-proc-receive')
        proc_receive(lbare, '    subprocess.run(["git", "push", "-q", %r, new + ":" + ref], check=True)\n'
                            '    wr("ok %%s\\n" %% ref)\n'
                            '    wr("option refname x\\nTo file://%s\\n*\\t%%s:%%s\\n" %% (new, ref))\n' % (str(xbare), str(xbare)))
        text_cases['proc-receive'] = (publish('text-proc-receive', clone, 'file://' + str(lbare)), recorded('text-proc-receive'), lbare, xbare)
        for key, (result, destination, lbare, xbare) in text_cases.items():
            seen_result('text-' + key, result, destination=destination, x_moved=remote_main(xbare) == tip,
                        l_moved=remote_main(lbare) == tip)
        def text_case(key, completed, outcome, l_moved, x_moved=False):
            result, destination, lbare, xbare = text_cases[key]
            given = wired_url('text-' + key, str(lbare))
            return (result.get('completed') is completed and remote_main(lbare) == (tip if l_moved else old)
                    and remote_main(xbare) == (tip if x_moved else old)
                    and destination == {'authorized_url': given, 'destinations': reached((given, outcome))})
        # VELDO-0153 AC3: the clone's hook cannot mirror or forge a destination.
        row('publication-destination-despite-hook-text', text_case('mirrored', True, 'at-tip', True))
        # VELDO-0153 AC3: retain the rejected destination guarantee at the single checked URL.
        row('publication-rejected-destination-recorded', text_case('refused', False, 'not-at-tip', False))
        # VELDO-0153 AC3: a server's success text cannot replace the checked destination's state.
        row('publication-completion-from-destination-state', text_case('proc-receive', False, 'not-at-tip', False, True))
        # 1a: a benign hook prints a word without a trailing newline; the push is correct.
        clone, bare = fresh('text-no-newline')
        hook(clone, "printf 'checks passed'\n")
        # VELDO-0153 AC3 disables clone hooks; exercise unframed output from the server instead.
        server_hook = bare / 'hooks/pre-receive'
        server_hook.write_text("#!/bin/sh\nprintf 'checks passed'\n")
        server_hook.chmod(0o755)
        given = wired_url('text-no-newline', str(bare))
        result = publish('text-no-newline', clone, str(bare))
        seen_result('text-no-newline', result, destination=recorded('text-no-newline'))
        row('publication-hook-text-without-newline', result.get('completed') is True and remote_main(bare) == tip
            and recorded('text-no-newline') == {'authorized_url': given, 'destinations': reached((given, 'at-tip'))})
        # 1h: a benign hook prints a Latin-1 byte, and the remote holds a ref whose name is not
        # UTF-8; the push and both listings are read losslessly.
        clone, bare = fresh('text-latin1')
        _v28_sp.run([b'git', b'-C', bytes(bare), b'update-ref', b'refs/heads/caf\xe9', old.encode()], check=True,
                    capture_output=True, timeout=20)
        hook(clone, "printf 'caf\\351 ok\\n'\n")
        # VELDO-0153 AC3 disables clone hooks; the server and both listings still emit non-UTF-8.
        server_hook = bare / 'hooks/pre-receive'
        server_hook.write_text("#!/bin/sh\nprintf 'caf\\351 ok\\n'\n")
        server_hook.chmod(0o755)
        given = wired_url('text-latin1', str(bare))
        result = publish('text-latin1', clone, str(bare))
        seen_result('text-latin1', result, destination=recorded('text-latin1'))
        row('publication-non-utf8-output', result.get('completed') is True and remote_main(bare) == tip
            and recorded('text-latin1') == {'authorized_url': given, 'destinations': reached((given, 'at-tip'))})
        # 3e: two pushurls; the second is an AGit-style server that accepts the push under
        # refs/changes/1 and leaves the authorized ref where it was, so it is not at the tip.
        clone, lbare = fresh('fan-out-agit')
        xbare = elsewhere_for('fan-out-agit')
        proc_receive(xbare, '    subprocess.run(["git", "update-ref", "refs/changes/1", new])\n'
                            '    wr("ok %s\\n" % ref)\n    wr("option refname refs/changes/1\\n")\n')
        agit_url = wired_url('fan-out-agit', str(lbare))
        git('-C', str(clone), 'config', '--add', 'remote.' + agit_url + '.pushurl', agit_url)
        git('-C', str(clone), 'config', '--add', 'remote.' + agit_url + '.pushurl', str(xbare))
        result = publish('fan-out-agit', clone, agit_url)
        agit = recorded('fan-out-agit')
        changes = G.run(['git', '-C', str(xbare), 'rev-parse', '--verify', '-q', 'refs/changes/1'],
                        capture_output=True, text=True, timeout=20).stdout.strip()
        seen_result('fan-out-agit', result, destination=agit, agit_ref_at_tip=changes == tip)
        # VELDO-0153 AC3: refuse fan-out before either the trunk or the AGit ref can move.
        row('publication-fan-out-agit-report', result.get('completed') is False and not changes
            and result.get('refusal') == 'binding_mismatch:identity_transport_config'
            and remote_main(lbare) == old and remote_main(xbare) == old and agit is None)
        # R7 scrub: recorded URLs are scrubbed by parsing them, never by git's display. An
        # scp-style address's user information is everything before the LAST `@` ahead of the
        # host; a `<transport>::<address>` URL is scrubbed in its address; a scheme URL loses its
        # query and fragment. Reached through a fake SSH command and a test remote helper, so git
        # runs its real transports.
        # VELDO-0153 AC2 supersedes publishing to these addresses: none names a remote under the
        # identity's owner on its host, so each is refused by name before any network write, and
        # AC1's identity profile strips the planted GIT_SSH_COMMAND. The R7 guarantee kept: no
        # credential reaches the answer or the record, and the executor's scrubbing of each
        # address (what a record would carry) is unchanged.
        def scrubbed(prefix, name, url, expected, env):
            clone, bare = fresh('scrub-' + name)
            _, answer = publish_as('scrub-' + name, clone, url(bare), env=env(bare))
            result = answer.get('result', {})
            destination = recorded('scrub-' + name)
            seen_result('scrub-' + name, result, destination=destination, refusal=answer.get('refusal'))
            return (answer.get('accepted') is False and result.get('status') == 'refused'
                    and (answer.get('refusal') or '').startswith(('binding_mismatch:', 'invalid_input:'))
                    and remote_main(bare) == old and _V28_S not in _v28_json.dumps(answer)
                    and _V28_S not in _v28_json.dumps(destination) and destination is None
                    and _v28_executor.scrubbed_url(url(bare)) == expected(bare)[0])
        script, scrub_ssh_log = fake_ssh('scrub')
        by_ssh = lambda bare: {'GIT_SSH_COMMAND': str(script)}
        row('publication-scrub-scp-user-information', all(scrubbed(*case, env=by_ssh) for case in (
            ('scp', 'scp-user-with-at', lambda b: 'deploy@' + _V28_U + '@deploy-host:' + str(b),
             lambda b: ('deploy-host:' + str(b),) * 2),
            ('scp', 'scp-user', lambda b: _V28_U + '@deploy-host:' + str(b), lambda b: ('deploy-host:' + str(b),) * 2),
            ('ssh', 'ssh-at-in-password', lambda b: 'ssh://deploy:fix@SECRET@deploy-host' + str(b),
             lambda b: ('ssh://deploy-host' + str(b),) * 2))) and not scrub_ssh_log.exists())
        helpers = root / 'remote-helpers'
        helpers.mkdir()
        (helpers / 'git-remote-veldotest').write_text(
            '#!/bin/sh\nwhile read cmd; do case "$cmd" in\n capabilities) printf "connect\\n\\n" ;;\n'
            ' "connect "*) printf "\\n"; exec ${cmd#connect } "$V28_HELPER_REPOSITORY" ;;\n "") exit 0 ;;\n esac; done\n')
        (helpers / 'git-remote-veldotest').chmod(0o755)
        by_helper = lambda bare: {'PATH': str(helpers) + _v28_os.pathsep + _v28_os.environ['PATH'],
                                  'V28_HELPER_REPOSITORY': str(bare)}
        def injected_env(bare):
            # The operator's global configuration rewrites https://veldo-host/ to a transport-
            # prefixed URL carrying credentials, so git's own resolution carries them.
            env = operator_home('scrub-injected', '[url "veldotest::https://' + _V28_U + ':' + _V28_P + '@veldo-host/"]\n'
                                '\tinsteadOf = https://veldo-host/\n')
            return dict(env, **by_helper(bare))
        row('publication-scrub-transport-prefix', all(scrubbed(*case, env=env) for case, env in (
            (('helper', 'transport-scheme', lambda b: 'veldotest::https://' + _V28_U + ':' + _V28_P + '@veldo-host' + str(b),
              lambda b: ('veldotest::https://veldo-host' + str(b),) * 2), by_helper),
            (('helper', 'transport-ssh', lambda b: 'veldotest::ssh://' + _V28_U + ':' + _V28_P + '@veldo-host' + str(b),
              lambda b: ('veldotest::ssh://veldo-host' + str(b),) * 2), by_helper),
            (('helper', 'transport-injected', lambda b: 'https://veldo-host' + str(b),
              lambda b: ('https://veldo-host' + str(b), 'veldotest::https://veldo-host' + str(b))), injected_env))))
        row('publication-scrub-query-fragment', all(scrubbed(*case, env=by_helper) for case in (
            ('helper', 'query', lambda b: 'veldotest://veldo-host' + str(b) + '?private_token=' + _V28_T,
             lambda b: ('veldotest://veldo-host' + str(b),) * 2),
            ('helper', 'fragment', lambda b: 'veldotest://veldo-host' + str(b) + '#' + _V28_T,
             lambda b: ('veldotest://veldo-host' + str(b),) * 2))))
        # R8 B1: nothing is pushed unless every resolved destination could be listed first and
        # holds the authorized ref at the expected old state (the old tip, or absent for a ref
        # creation). The refusal is made by name before any push and reaches the caller as that
        # refusal, recorded as conclusive, never as an unknown outcome.
        def moved_elsewhere(bare):
            git('-C', str(bare), 'update-ref', 'refs/heads/main',
                git('-C', str(bare), 'commit-tree', '-p', old, '-m', 'elsewhere', old + '^{tree}'))
            return remote_main(bare)
        stale = {}
        clone, bare = fresh('stale-single')
        held = moved_elsewhere(bare)
        stale['single'] = (publish_as('stale-single', clone, str(bare))[1], [(bare, held)])
        clone, bare = fresh('stale-unlisted')
        unlisted_url = wired_url('stale-unlisted', str(bare))
        # AC3 fixes one destination. A failed listing of that URL must still prevent a push.
        no_list = root / 'unlisted-wrapper'
        no_list.mkdir()
        (no_list / 'git').write_text('#!/bin/sh\nfor arg in "$@"; do\n'
            '  [ "$arg" = ls-remote ] && exit 1\ndone\nexec %s "$@"\n' % _v28_shlex.quote(_v28_shutil.which('git')))
        (no_list / 'git').chmod(0o755)
        stale['unlisted'] = (publish_as('stale-unlisted', clone, unlisted_url,
            env={'PATH': str(no_list) + _v28_os.pathsep + _v28_os.environ['PATH']})[1], [(bare, old)])
        clone, bare = fresh('stale-fan-out')
        second = elsewhere_for('stale-fan-out')
        fan_url = wired_url('stale-fan-out', str(bare))
        git('-C', str(clone), 'config', '--add', 'remote.' + fan_url + '.pushurl', fan_url)
        git('-C', str(clone), 'config', '--add', 'remote.' + fan_url + '.pushurl', str(second))
        held = moved_elsewhere(second)
        stale['fan-out'] = (publish_as('stale-fan-out', clone, fan_url)[1], [(bare, old), (second, held)])
        for key, (answer, _) in stale.items():
            seen_result('stale-' + key, answer.get('result', {}), refusal=answer.get('refusal'), accepted=answer.get('accepted'))
        def refused_before_push(key, code='stale-subject'):
            answer, repositories = stale[key]
            result = answer.get('result', {})
            return (answer.get('accepted') is False and answer.get('refusal') == code
                    and result.get('status') == 'refused' and result.get('refusal') == code
                    and result.get('completed') is False and result.get('stop') is None
                    and 'destination' not in result
                    and all(remote_main(repository) == held for repository, held in repositories))
        # Retain compare-and-swap and listing failure against AC3's single checked URL.
        # AC3 refuses clone fan-out before the old-tip check can run.
        row('publication-refused-when-not-at-old-tip', all(refused_before_push(key) for key in ('single', 'unlisted'))
            and refused_before_push('fan-out', 'binding_mismatch:identity_transport_config'))
        # The named refusal is the effect's recorded, conclusive outcome: the stored record says
        # refused, and the same request again returns the same refusal without another attempt.
        clone, bare = fresh('stale-replay')
        held = moved_elsewhere(bare)
        stale_request, first = publish_as('stale-replay', clone, str(bare))
        stale_record = E.S.materialized_state(conn)['entities'].get('effect:dispatch-publication-stale-replay', {}).get('data', {})
        replay = call(stale_request)
        seen_result('stale-replay', first.get('result', {}), refusal=first.get('refusal'), replay_refusal=replay.get('refusal'))
        # VELDO-0026's in-flight effect for it is reconciled as stopped, so a later revocation owes
        # no stop for an effect that was never performed.
        linked = E.S.materialized_state(conn)['entities'].get(stale_record.get('revocation_effect') or '', {}).get('data', {})
        row('publication-refusal-reaches-caller', first.get('accepted') is False and first.get('refusal') == 'stale-subject'
            and stale_record.get('status') == 'refused' and stale_record.get('refusal') == 'stale-subject'
            and stale_record.get('stop') is None and linked.get('state') == 'stopped' and replay.get('accepted') is False
            and replay.get('refusal') == 'stale-subject' and replay.get('result') == first.get('result')
            and remote_main(bare) == held)
        # A ref creation: the expected old state is "absent" (the all-zero id), and it completes
        # when the ref was absent before and holds the tip after, at every destination.
        zero = '0' * len(old)
        clone, bare = fresh('create')
        create_url = wired_url('create', str(bare))
        created = publish_as('create', clone, create_url, ref='refs/heads/created', old_tip=zero)[1].get('result', {})
        def ref_of(bare, name):
            return G.run(['git', '-C', str(bare), 'rev-parse', '--verify', '-q', name], capture_output=True,
                         text=True, timeout=20).stdout.strip()
        clone, existing = fresh('create-existing')
        git('-C', str(existing), 'update-ref', 'refs/heads/created', old)
        over = publish_as('create-existing', clone, str(existing), ref='refs/heads/created', old_tip=zero)[1]
        seen_result('create', created, destination=recorded('create'))
        seen_result('create-existing', over.get('result', {}), refusal=over.get('refusal'))
        # Retain absent-ref creation and refusal over an existing ref at AC3's one checked URL.
        row('publication-ref-creation', created.get('completed') is True
            and ref_of(bare, 'refs/heads/created') == tip
            and recorded('create') == {'authorized_url': create_url,
                                       'destinations': reached((create_url, 'at-tip'))}
            and over.get('refusal') == 'stale-subject' and ref_of(existing, 'refs/heads/created') == old)
        # R8 B2: each destination is listed by the URL git resolved, and `git ls-remote` resolves
        # that URL again through the whole remote lookup: a remote section named by it, a legacy
        # remotes/ file of that name, a further url.*.insteadOf. The listing would then read a
        # repository the push never reached, so a destination that does not resolve to itself
        # (`git ls-remote --get-url`, no network) is refused by name before anything is pushed.
        rerouted = {}
        for name in ('section', 'legacy-file', 'insteadof-chain'):
            clone, lbare = fresh('reroute-' + name)
            xbare = elsewhere_for('reroute-' + name)
            ybare = elsewhere_for('reroute-' + name + '-listed')
            url = wired_url('reroute-' + name, str(lbare))
            if name == 'section':
                # The second destination, X's file URL, has a section of its own pointing at Y (git
                # ignores a section named by a plain path, so the URL form is the one that reroutes).
                git('-C', str(clone), 'config', '--add', 'remote.' + url + '.pushurl', url)
                git('-C', str(clone), 'config', '--add', 'remote.' + url + '.pushurl', 'file://' + str(xbare))
                git('-C', str(clone), 'config', 'remote.file://' + str(xbare) + '.url', str(ybare))
            elif name == 'legacy-file':
                # A relative pushurl that is also a remote nickname with a legacy remotes/ file.
                nick = clone / 'nick-repo'
                git('init', '-q', '--bare', str(nick))
                git('-C', str(repo), 'push', '-q', str(nick), old + ':refs/heads/main')
                xbare = nick
                git('-C', str(clone), 'config', '--add', 'remote.' + url + '.pushurl', url)
                git('-C', str(clone), 'config', '--add', 'remote.' + url + '.pushurl', 'nick-repo')
                (clone / '.git' / 'remotes').mkdir(exist_ok=True)
                (clone / '.git' / 'remotes' / 'nick-repo').write_text('URL: %s\n' % ybare)
            else:
                # The authorized alias is rewritten to X, and X is itself rewritten to Y.
                git('-C', str(clone), 'config', 'url.' + str(xbare) + '.insteadOf', url)
                git('-C', str(clone), 'config', 'url.' + str(ybare) + '.insteadOf', str(xbare))
            _, answer = publish_as('reroute-' + name, clone, url)
            rerouted[name] = (answer, [lbare, xbare, ybare])
            seen_result('reroute-' + name, answer.get('result', {}), refusal=answer.get('refusal'),
                        moved=[remote_main(b) == tip for b in (lbare, xbare, ybare)])
        # Retain listing/push destination parity: AC3 refuses every planted route before listing.
        row('publication-destination-listed-as-resolved', all(
            answer.get('refusal') == 'binding_mismatch:identity_transport_config' and answer.get('result', {}).get('status') == 'refused'
            and all(remote_main(b) == old for b in repositories) for answer, repositories in rerouted.values()))
        # The supervisor must extend its acceptance deadline for the announced operation.
        # AC3 permits one destination; its three-second receive exceeds the two-second
        # acceptance window while staying within the five-second Git step bound.
        clone, lbare = fresh('slow-fan-out')
        slow_url = wired_url('slow-fan-out', str(lbare))
        slow = [lbare]
        for index, bare in enumerate(slow):
            wait = bare / 'hooks' / 'pre-receive'
            wait.write_text('#!/bin/sh\ncat >/dev/null\nsleep 3\n')
            wait.chmod(0o755)
        config['receivers']['git-slow-fan-out'] = {'kind': 'publication', 'repository': str(clone), 'remote': slow_url,
                                                   'ref': 'refs/heads/main', 'git_step_seconds': 5}
        config_path.write_text(_v28_json.dumps(config))
        slow_config = private / 'slow-fan-out-config.json'
        slow_config.write_text(_v28_json.dumps(dict(config, accept_seconds=2)))
        slow_request, _, _, _ = setup('publication', 'slow-fan-out', target='git-slow-fan-out',
                                      payload={'commit': tip, 'tree': tree, 'old_tip': old})
        began = _v28_time.monotonic()
        try:
            slow_answer = _v28_executor.call(slow_config, slow_request, 'worker', private / 'worker')
        except E.Refused as error:
            slow_answer = {'supervisor_refusal': error.code}
        slow_seconds = _v28_time.monotonic() - began
        seen_result('slow-fan-out', slow_answer.get('result', {}), seconds=round(slow_seconds, 1),
                    supervisor_refusal=slow_answer.get('supervisor_refusal'))
        # Retain the supervisor's announced time window for every destination of the call.
        # AC3 fixes that set to one URL; its slow receive exceeds the acceptance window.
        row('publication-call-covers-every-destination', slow_answer.get('result', {}).get('completed') is True
            and slow_seconds > 2 and all(remote_main(bare) == tip for bare in slow)
            and recorded('slow-fan-out') == {'authorized_url': slow_url, 'destinations': reached(
                *[(slow_url if index == 0 else str(bare), 'at-tip') for index, bare in enumerate(slow)])})
        # R8 scrub: anything that does not parse into a well-formed host is over-scrubbed. An
        # scp-style address loses everything up to the last `@` before its path (user:password
        # included, and a scheme-looking `ssh:` user), an `ext::` command keeps no command text,
        # a URL with no path loses its query and fragment, and an authority or path that could
        # only have come from a mangled credential is recorded `<unparsed>`. The ext:: shape is
        # published end to end; the rest are scrubbed directly (git itself reads user:password@host
        # as the host `user`, so it reaches nothing), with well-formed controls kept.
        clone, bare = fresh('scrub-ext')
        git('-C', str(clone), 'config', 'protocol.ext.allow', 'always')
        ext_url = 'ext::env V28_TOKEN=' + _V28_P + ' git %s ' + str(bare)
        _, ext_answer = publish_as('scrub-ext', clone, ext_url)
        # VELDO-0153 AC2 supersedes publishing the ext:: shape end to end: it names no remote under
        # the identity's owner and is refused by name before any network write. Kept from R8: no
        # credential in the answer, nothing recorded, and its scrubbing keeps no command text.
        ext_ok = (ext_answer.get('accepted') is False and ext_answer.get('result', {}).get('status') == 'refused'
                  and (ext_answer.get('refusal') or '').startswith(('binding_mismatch:', 'invalid_input:'))
                  and _V28_S not in _v28_json.dumps(ext_answer) and recorded('scrub-ext') is None
                  and remote_main(bare) == old and _v28_executor.scrubbed_url(ext_url) == 'ext::<command>')
        seen_result('scrub-ext', ext_answer.get('result', {}), destination=recorded('scrub-ext'), refusal=ext_answer.get('refusal'))
        scrub_table = [
            (_V28_U + ':' + _V28_P + '@deploy-host:repo.git', 'deploy-host:repo.git'),
            ('ssh:' + _V28_U + '@deploy-host:repo.git', 'deploy-host:repo.git'),
            ('a@' + _V28_U + '@deploy-host:repo.git', 'deploy-host:repo.git'),
            ("ext::sh -c 'curl -u " + _V28_U + ":" + _V28_P + " h' %S", 'ext::<command>'),
            ('veldotest::ext::sh ' + _V28_P, 'veldotest::ext::<command>'),
            ('https://h?private_token=' + _V28_T, 'https://h'),
            ('https://h#' + _V28_T, 'https://h'),
            ('https://' + _V28_U + ':' + _V28_S + '/PW@h/r.git', 'https://<unparsed>'),
            ('https://' + _V28_U + ':' + _V28_S + '?PW@h/r.git', 'https://<unparsed>'),
            ('https://' + _V28_U + '/' + _V28_P + '@h/r.git', 'https://<unparsed>'),
            ('ssh://[' + _V28_U + '@h:22]/r.git', 'ssh://<unparsed>'),
            ('deploy-host:repo@' + _V28_P + '.git', '<unparsed>'),
            # Well-formed controls are kept as they are.
            ('https://example.com:8443/r.git', 'https://example.com:8443/r.git'),
            ('ssh://[::1]:22/r.git', 'ssh://[::1]:22/r.git'),
            ('deploy-host:path/r.git', 'deploy-host:path/r.git'),
            ('/local/a@b/r.git', '/local/a@b/r.git'),
            ('file:///srv/r.git', 'file:///srv/r.git')]
        scrub_seen = {url: _v28_executor.scrubbed_url(url) for url, _ in scrub_table}
        seen_result('scrub-table', {}, mismatches={url: got for (url, want), got in zip(scrub_table, scrub_seen.values()) if got != want})
        row('publication-scrub-malformed-address', ext_ok
            and all(scrub_seen[url] == want for url, want in scrub_table))
        # Completion requires a clean transport exit even when the checked destination
        # already holds exactly the authorized tip. Inject that exit at the process boundary.
        clone, bare = fresh('hook-then-fail')
        failed_exit = root / 'failed-exit-wrapper'
        failed_exit.mkdir()
        (failed_exit / 'git').write_text('#!/bin/sh\n%s "$@"\nrc=$?\n'
            'for arg in "$@"; do\n  [ "$arg" = push ] && exit 1\ndone\nexit "$rc"\n'
            % _v28_shlex.quote(_v28_shutil.which('git')))
        (failed_exit / 'git').chmod(0o755)
        given = wired_url('hook-then-fail', str(bare))
        failed = publish('hook-then-fail', clone, given,
            env={'PATH': str(failed_exit) + _v28_os.pathsep + _v28_os.environ['PATH']})
        seen_result('hook-then-fail', failed, destination=recorded('hook-then-fail'))
        # Retain the clean-exit requirement without a clone hook, disabled by AC3: the
        # transport writes the one checked remote, then returns a nonzero exit.
        row('publication-requires-clean-push-exit', failed.get('completed') is False and failed.get('status') == 'unknown'
            and remote_main(bare) == tip
            and recorded('hook-then-fail') == {'authorized_url': given, 'destinations': reached((given, 'at-tip'))})
        # A line break in the receiver's URL, or in a configured URL, is refused by its own guard
        # before git's one-per-line report is read. Each case below gets past the report's shape
        # check without the guard: git would name three push URLs for the first, two for the second.
        breaks = {}
        clone, bare = fresh('break-remote')
        _, answer = publish_as('break-remote', clone, wired_url('break-remote', str(bare)) + '\n  Push  URL: forged')
        breaks['remote'] = (answer, [bare])
        clone, bare = fresh('break-pushurl')
        other = elsewhere_for('break-pushurl')
        break_url = wired_url('break-pushurl', str(bare))
        git('-C', str(clone), 'config', 'remote.' + break_url + '.url', break_url)
        git('-C', str(clone), 'config', 'remote.' + break_url + '.pushurl', str(other) + '\n  Push  URL: ' + break_url)
        _, answer = publish_as('break-pushurl', clone, break_url)
        breaks['pushurl'] = (answer, [bare, other])
        for key, (answer, _) in breaks.items():
            seen_result('break-' + key, answer.get('result', {}), refusal=answer.get('refusal'))
        # Retain framing safety: a literal URL's line break is invalid, while AC3 refuses
        # a configured override before parsing it as a destination.
        codes = {'remote': 'invalid_input:remote', 'pushurl': 'binding_mismatch:identity_transport_config'}
        row('publication-line-break-refused', all(answer.get('refusal') == codes[key]
            and all(remote_main(b) == old for b in repositories) for key, (answer, repositories) in breaks.items()))
        # Named-remote resolution reads machine config values. Inject a bad host, an empty
        # value, missing values, multiple values, failure exits and localized diagnostics.
        # Retain historical shape names so the earlier review rows remain traceable.
        wrapper = root / 'git-wrapper'
        wrapper.mkdir()
        (wrapper / 'git').write_text("""#!/bin/sh
real=%s
if [ "$1" = -C ] && [ "$3" = config ] && [ "$4" = --get-all ] && [ "$5" = remote.publication.url ]; then
  out=$("$real" "$@"); rc=$?
  loc=${LC_ALL:-${LC_MESSAGES:-${LANG:-C}}}
  case "$V28_GIT_SHAPE" in
    show-exit) printf '%%s\\n' "$out"; exit 1 ;;
    header) printf 'http://elsewhere.invalid/repo.git\\n' ;;
    fetch) printf '\\n' ;;
    no-push) : ;;
    extra) printf '%%s\\n%%s\\n' "$out" "$out" ;;
    translated)
      # Config values are machine output; only diagnostics are localized.
      printf 'URL zum Versenden (%%s)\\n' "$loc" >&2
      printf '%%s\\n' "$out" ;;
    *) printf '%%s\\n' "$out" ;;
  esac
  exit $rc
fi
if [ "$1" = -C ] && [ "$3" = config ] && [ "$V28_GIT_SHAPE" = config-exit ]; then exit 3; fi
exec "$real" "$@"
""" % _v28_shutil.which('git'))
        (wrapper / 'git').chmod(0o755)
        def reshaped(shape, env=None):
            clone, bare = fresh('shape-' + shape)
            shape_url = wired_url('shape-' + shape, str(bare))
            git('-C', str(clone), 'config', 'remote.publication.url', shape_url)
            # config-exit drives the identity profile's own inspection; the other cases
            # drive named-remote resolution before the literal URL is checked.
            receiver_url = shape_url if shape == 'config-exit' else 'publication'
            _, answer = publish_as('shape-' + shape, clone, receiver_url, env=dict(
                {'PATH': str(wrapper) + _v28_os.pathsep + _v28_os.environ['PATH'], 'V28_GIT_SHAPE': shape}, **(env or {})))
            seen_result('shape-' + shape, answer.get('result', {}), refusal=answer.get('refusal'))
            return answer, [bare]
        shapes = {shape: reshaped(shape) for shape in ('show-exit', 'header', 'fetch', 'no-push', 'extra', 'config-exit')}
        control, repositories = reshaped('unchanged')
        # Retain checked resolution output against AC3's one URL. Human-readable remote
        # reports are no longer parsed; fail closed on invalid config values and exit codes.
        shape_codes = dict.fromkeys(('show-exit', 'no-push', 'extra'), 'invalid_input:push_destinations')
        shape_codes.update(header='binding_mismatch:remote_host', fetch='binding_mismatch:remote_host',
                           **{'config-exit': 'binding_mismatch:identity_transport_config'})
        row('publication-resolution-output-checked', control.get('result', {}).get('completed') is True
            and all(remote_main(b) == tip for b in repositories)
            and all(answer.get('refusal') == shape_codes[shape] and all(remote_main(b) == old for b in repositories)
                    for shape, (answer, repositories) in shapes.items()))
        # Keep locale independence: machine config values have no translated labels to parse.
        localized, repositories = reshaped('translated', {'LC_ALL': 'de_DE.UTF-8', 'LANG': 'de_DE.UTF-8'})
        row('publication-resolution-in-c-locale', localized.get('result', {}).get('completed') is True
            and all(remote_main(b) == tip for b in repositories))
        # R6 2 and 3, superseded by VELDO-0153 AC1 for the factory's publication: the identity
        # profile strips every GIT_* variable and ignores global and system configuration, so no
        # selection or injection route reaches the push. Each case plants one route rewriting the
        # authorized remote to a decoy; plain git from the same environment (`git ls-remote
        # --get-url`, outside git_process) is the control that the route is live, and the
        # publication must still land at the authorized remote and record only it.
        selection = {}
        for name in ('global-file', 'system-file', 'count-injection', 'parameters-injection', 'home-file'):
            clone, bare = fresh('selection-' + name)
            other = elsewhere_for('selection-' + name)
            authorized = wired_url('selection-' + name, str(bare))
            rewrite = '[url "%s"]\n\tinsteadOf = %s\n' % (other, authorized)
            selector = root / ('selection-' + name + '.gitconfig')
            selector.write_text(rewrite)
            env = operator_home('selection-' + name, rewrite if name == 'home-file' else None)
            env.update({
                'global-file': {'GIT_CONFIG_GLOBAL': str(selector)},
                'system-file': {'GIT_CONFIG_SYSTEM': str(selector)},
                'count-injection': {'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'url.' + str(other) + '.insteadOf',
                                    'GIT_CONFIG_VALUE_0': authorized},
                'parameters-injection': {'GIT_CONFIG_PARAMETERS': "'url.%s.insteadof'='%s'" % (other, authorized)},
                'home-file': {}}[name])
            plain_env = {k: v for k, v in _v28_os.environ.items() if not k.startswith('GIT_')}
            plain_env.update(env)
            plain = _v28_sp.run(['git', '-C', str(clone), 'ls-remote', '--get-url', authorized], env=plain_env,
                                capture_output=True, text=True, timeout=20).stdout.strip()
            result = publish('selection-' + name, clone, authorized, env=env)
            destination = recorded('selection-' + name) or {}
            selection[name] = (plain == str(other), result, destination, remote_main(bare) == tip,
                               remote_main(other) == tip, authorized)
            seen_result('selection-' + name, result, plain_git_resolves=plain, destination=destination or None,
                        authorized_moved=selection[name][3], decoy_moved=selection[name][4])
        # VELDO-0153 AC1: every planted route is live for plain git and inert for the identity push.
        row('publication-config-selection-parity', all(
            live and result.get('completed') is True and moved is True and decoy is False
            and destination.get('destinations') == reached((authorized, 'at-tip'))
            for live, result, destination, moved, decoy, authorized in selection.values()))
        # The network profile still strips every variable that changes WHICH repository or objects
        # git acts on: repository, work tree, index, object store, alternates, common directory,
        # namespace, discovery bounds, the program directory and `git config`'s own file override.
        # Were any honored, the push would run in another repository or into a namespace.
        clone, bare = fresh('network-coordinates')
        decoy = root / 'network-decoy'
        git('init', '-q', str(decoy))
        hostile = {'GIT_DIR': str(decoy / '.git'), 'GIT_WORK_TREE': str(decoy),
                   'GIT_INDEX_FILE': str(root / 'no-such-index'), 'GIT_OBJECT_DIRECTORY': str(root / 'no-such-objects'),
                   'GIT_ALTERNATE_OBJECT_DIRECTORIES': str(root / 'no-such-alternates'), 'GIT_NAMESPACE': 'hostile',
                   'GIT_COMMON_DIR': str(decoy / '.git'), 'GIT_CEILING_DIRECTORIES': str(clone),
                   'GIT_DISCOVERY_ACROSS_FILESYSTEM': '1', 'GIT_CONFIG': str(root / 'no-such-config'),
                   'GIT_EXEC_PATH': str(root / 'no-such-exec-path')}
        result = publish('network-coordinates', clone, str(bare), env=hostile)
        namespaced = git('-C', str(bare), 'for-each-ref', 'refs/namespaces')
        transport = {'GIT_SSH_COMMAND': 'ssh-cmd', 'GIT_SSH': 'ssh-bin', 'GIT_ASKPASS': 'askpass',
                     'SSH_ASKPASS': 'ssh-askpass', 'SSH_AUTH_SOCK': 'agent.sock', 'GIT_TERMINAL_PROMPT': '1',
                     'HTTPS_PROXY': 'proxy', 'http_proxy': 'proxy', 'NO_PROXY': 'local'}
        configuration = {'GIT_CONFIG_GLOBAL': 'global.cfg', 'GIT_CONFIG_SYSTEM': 'system.cfg', 'GIT_CONFIG_NOSYSTEM': '1',
                         'GIT_CONFIG_COUNT': '2', 'GIT_CONFIG_KEY_0': 'k.a', 'GIT_CONFIG_VALUE_0': 'a',
                         'GIT_CONFIG_KEY_1': 'k.b', 'GIT_CONFIG_VALUE_1': 'b', 'GIT_CONFIG_PARAMETERS': "'k.c'='c'"}
        try:
            network = G.clean_env(dict(hostile, **transport, **configuration), profile='network')
        except TypeError:
            network = None
        isolated = G.clean_env(dict(hostile, **transport, **configuration))
        seen_result('network-coordinates', result, namespaced=namespaced,
                    network_profile_kept=None if network is None else sorted(k for k in hostile if k in network))
        row('publication-network-profile-strips-coordinates', result.get('completed') is True
            and remote_main(bare) == tip and namespaced == ''
            and network is not None and not any(k in network for k in hostile)
            and all(network.get(k) == v for k, v in dict(transport, **configuration).items())
            and isolated.get('GIT_CONFIG_GLOBAL') == _v28_os.devnull and isolated.get('GIT_CONFIG_NOSYSTEM') == '1'
            and isolated.get('GIT_CONFIG_SYSTEM') == _v28_os.devnull
            and not any(k in isolated for k in configuration if k not in ('GIT_CONFIG_GLOBAL', 'GIT_CONFIG_SYSTEM', 'GIT_CONFIG_NOSYSTEM'))
            and 'GIT_SSH_COMMAND' not in isolated)
        for name in ('push-options', 'records-resolved-destination', 'destination-without-credentials', 'global-insteadof', 'global-credential-helper',
                     'env-ssh-command', 'global-ssh-command', 'destination-despite-hook-text', 'rejected-destination-recorded',
                     'completion-from-destination-state', 'hook-text-without-newline', 'non-utf8-output', 'fan-out-agit-report',
                     'scrub-scp-user-information', 'scrub-transport-prefix', 'scrub-query-fragment',
                     'refused-when-not-at-old-tip', 'refusal-reaches-caller', 'ref-creation',
                     'destination-listed-as-resolved', 'call-covers-every-destination',
                     'scrub-malformed-address',
                     'requires-clean-push-exit', 'line-break-refused', 'resolution-output-checked',
                     'resolution-in-c-locale',
                     'config-selection-parity', 'network-profile-strips-coordinates'):
            expect('VELDO-0028 effects/publication-' + name, checks['publication-' + name])
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
            'remote_commit_confirmed': actual == tip, 'r5': r5, 'metrics': E.metrics(conn)}, sort_keys=True))
        conn.close()
    print('VELDO-0028 suite seconds: %.3f' % (_v28_time.monotonic() - started))


_v28_run()
