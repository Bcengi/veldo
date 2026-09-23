"""Trusted Effect Executor: authenticated pipe IPC, configured store, private receivers.

Install config, credentials and this executable outside worker clones. The supervisor owns
this process and its pipes; workers cannot select config, executable, receiver or credential
path. No listener, recovery loop, worker launch, capability filtering or paid model API.
Provider receivers are trusted subscription-CLI adapters with a JSON observation protocol.
Publication uses the configured trusted clone and the exact accepted commit/ref/old tip.
"""
import json
import os
from pathlib import Path
import secrets
import select
import subprocess
import sys

import importlib.util
_spec = importlib.util.spec_from_file_location('effects', Path(__file__).with_name('control_effects.py'))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
_git_process = E.organ('git_process')


def receive(config, contract, accepted):
    receiver = config['receivers'][contract['target']]
    if receiver['kind'] != contract['kind']:
        raise E.Refused('scope-mismatch')
    binding = {f: accepted[f] for f in ('dispatch_id', 'target', 'request_digest')}
    if contract['kind'] == 'publication' and 'argv' not in receiver:
        payload = contract['payload']
        repo, remote, ref = receiver['repository'], receiver['remote'], receiver['ref']
        def git(*args):
            return _git_process.run(['git', '-C', repo, *args], capture_output=True, text=True, timeout=20)
        def remote_refs():
            # Every advertised ref, HEAD and peeled tags included, plus each symbolic ref's target.
            listed = git('ls-remote', '--symref', remote)
            if listed.returncode:
                return None
            refs = {}
            for line in listed.stdout.splitlines():
                value, name = line.split('\t', 1)
                if value.startswith('ref: '):
                    refs['symref:' + name] = value[len('ref: '):]
                else:
                    refs[name] = value
            return refs
        tree = git('rev-parse', payload['commit'] + '^{tree}')
        if tree.returncode or tree.stdout.strip() != payload['tree']:
            raise E.Refused('missing-evidence')
        # The receiver names a URL, never a remote of the clone, and the push must reach exactly
        # that URL. Git resolves a push destination by name first. A remote section named
        # exactly by the URL, in any configuration scope, brings its pushurl,
        # refspecs and mirror setting (a pushurl alone is enough); a legacy remotes/ or branches/
        # file of that name replaces the URL for the listing and the push alike; a pushInsteadOf
        # prefix of the URL rewrites the push only. Each could send the commit somewhere the
        # authorization does not name, so each is refused before anything is pushed. Names are
        # compared exactly, never as whitespace-separated words.
        listed = git('config', '-z', '--list')
        if listed.returncode:
            raise E.Refused('invalid-input')
        for key, _, value in (entry.partition('\n') for entry in listed.stdout.split('\0') if entry):
            if key.startswith('remote.') and key[len('remote.'):key.rindex('.')] == remote:
                raise E.Refused('invalid-input')
            if key.startswith('url.') and key.endswith('.pushinsteadof') and remote.startswith(value):
                raise E.Refused('invalid-input')
        if '/' not in remote and remote not in ('', '.', '..'):
            for legacy in ('remotes/', 'branches/'):
                path = git('rev-parse', '--git-path', legacy + remote)
                if path.returncode or (Path(repo) / path.stdout.strip()).exists():
                    raise E.Refused('invalid-input')
        before = remote_refs()
        if before is None or before.get(ref) != payload['old_tip']:
            raise E.Refused('stale-subject')
        # An ordinary git push, so the clone's hooks, url.*.insteadOf rewrites, transports
        # (HTTP(S) included) and credential helpers behave exactly as configured. Only what
        # WIDENS a push is neutralized: an explicit URL and single refspec, no tag following
        # from the command line or config, no push options from any configuration scope (an
        # empty push.pushOption resets the list; on GitLab-style servers an option can open a
        # merge request or skip CI), no submodule recursion, and a lease on the old tip.
        push = git('-c', 'push.followTags=false', '-c', 'push.pushOption=', 'push',
                   '--no-follow-tags', '--recurse-submodules=no',
                   '--force-with-lease=' + ref + ':' + payload['old_tip'],
                   remote, payload['commit'] + ':' + ref)
        # Completion is exactly one remote change: the authorized ref (and any symbolic ref
        # that targets it, HEAD included) moved to the commit; every other entry is unchanged.
        after = remote_refs()
        expected = dict(before, **{ref: payload['commit']})
        expected.update({name[len('symref:'):]: payload['commit'] for name, target in before.items()
                         if name.startswith('symref:') and target == ref})
        complete = push.returncode == 0 and after is not None and after == expected
        return dict(binding, status='completed' if complete else 'unknown',
                    evidence={'remote_commit': payload['commit'], 'tree': payload['tree']} if complete else None)
    # Only a service-selected adapter sees reusable authentication, on stdin. Its stdout
    # is never returned verbatim; only a bound digest enters the effect observation.
    credential = Path(receiver['credential_file']).read_text()
    packet = dict(binding, credential=credential, payload=contract['payload'])
    proc = subprocess.run(receiver['argv'], input=json.dumps(packet), capture_output=True,
                          text=True, timeout=receiver.get('timeout', 20),
                          env={'PATH': os.defpath, 'LANG': 'C.UTF-8'})
    if proc.returncode:
        return dict(binding, status='unknown')
    return json.loads(proc.stdout)


def execute(config, request, principal, challenge, signature):
    if not isinstance(request, dict):
        return {'accepted': False, 'refusal': 'invalid-input'}
    if not Path(config['store']).is_file():
        return {'accepted': False, 'refusal': 'effect-service-unavailable'}
    conn = E.S.open_store(config['store'])
    try:
        state = E.S.materialized_state(conn)['entities']
        E.authenticate(state, principal, challenge, request, signature)
        config = dict(config, _auth_versions={k: e['version'] for k, e in state.items()
                                             if e['kind'] in ('membership', 'verification_key')})
        journal = ('effect-executor', lambda data: E.SIG.sign_bytes(config['journal_key'], data, 'veldo-journal'))
        operation = request.get('operation')
        if operation == 'issue':
            issuer = E.organ('credential_issue').ProtectedIssuer(E, conn, config, journal)
            return issuer.issue(principal, request)
        if operation != 'execute':
            raise E.Refused('credential-access-refused')
        accepted, fresh = E.accept(conn, config, principal, request, journal)
        if not fresh:
            return {'accepted': True, 'result': accepted, 'metrics': E.metrics(conn)}
        contract = accepted
        try:
            observation = receive(config, contract, accepted)
        except (OSError, ValueError, KeyError, E.Refused, subprocess.TimeoutExpired):
            observation = dict(accepted, status='unknown', evidence=None)
        result = E.finish(conn, accepted, observation, journal)
        return {'accepted': True, 'result': result, 'metrics': E.metrics(conn)}
    except (E.Refused, E.S.StoreRefused) as error:
        return {'accepted': False, 'refusal': error.code, 'metrics': {'refused': 1}}
    except (ValueError, TypeError, KeyError):
        return {'accepted': False, 'refusal': 'invalid-input', 'metrics': {'refused': 1}}
    finally:
        conn.close()


def call(config_path, request, principal, connection_key):
    """Trusted supervisor-side adapter; config_path is never taken from worker JSON."""
    child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), str(config_path)],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        if not select.select([child.stdout], [], [], 10)[0]:
            raise E.Refused('effect-service-unavailable')
        challenge = json.loads(child.stdout.readline())['challenge']
        message = E.SIG.canonical({'challenge': challenge, 'request_digest': E.SIG.digest(request)})
        signature = E.SIG.sign_bytes(connection_key, message, E.NAMESPACE) if connection_key else ''
        output, _ = child.communicate(json.dumps({'request': request, 'principal': principal,
                                                'signature': signature}) + '\n', timeout=50)
        if child.returncode:
            raise E.Refused('effect-service-unavailable')
        return json.loads(output)
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)


def main():
    try:
        config = json.loads(Path(sys.argv[1]).read_text())
        challenge = secrets.token_hex(32)
        print(json.dumps({'challenge': challenge}), flush=True)
        if not select.select([sys.stdin], [], [], 10)[0]:
            raise E.Refused('unauthenticated-worker')
        packet = json.loads(sys.stdin.buffer.readline(1024 * 1024))
        result = execute(config, packet['request'], packet.get('principal'), challenge, packet.get('signature', ''))
    except (OSError, ValueError, TypeError, KeyError, E.Refused, subprocess.TimeoutExpired):
        result = {'accepted': False, 'refusal': 'effect-service-unavailable'}
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
