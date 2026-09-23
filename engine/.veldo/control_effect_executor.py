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


def displayed_url(url):
    """The URL exactly as git displays it in push output (transport_anonymize_url): a local path
    is unchanged; otherwise everything up to the first `@` is dropped, from a scheme URL when that
    `@` comes before the path, and from an scp-style address when a `:` follows it. A porcelain
    `To` line carries this form, so the listing's resolution is compared in it."""
    at, colon, slash = url.find('@'), url.find(':'), url.find('/')
    if at < 0 or colon < 0 or 0 <= slash < colon:
        return url
    rest, end = url[at + 1:], url.find('://')
    if end < 0:
        return rest if ':' in rest else url
    if not all(c in '+.-' or (c.isascii() and c.isalnum()) for c in url[:end]):
        return url
    if 0 <= url.find('/', end + 3) < at:
        return url
    return url[:end + 3] + rest


def anonymous_url(url):
    """A displayed URL as it is recorded: a scheme URL also loses any user information git's
    display leaves (a password holding an unencoded `@`). Recorded URLs never carry credentials."""
    scheme, separator, rest = url.partition('://')
    if not separator or not scheme or not all(c in '+.-' or (c.isascii() and c.isalnum()) for c in scheme):
        return url
    authority, slash, path = rest.partition('/')
    return scheme + separator + authority.rpartition('@')[2] + slash + path


def receive(config, contract, accepted):
    receiver = config['receivers'][contract['target']]
    if receiver['kind'] != contract['kind']:
        raise E.Refused('scope-mismatch')
    binding = {f: accepted[f] for f in ('dispatch_id', 'target', 'request_digest')}
    if contract['kind'] == 'publication' and 'argv' not in receiver:
        payload = contract['payload']
        repo, remote, ref = receiver['repository'], receiver['remote'], receiver['ref']
        def git(*args, profile='isolated'):
            return _git_process.run(['git', '-C', repo, *args], capture_output=True, text=True, timeout=20,
                                    profile=profile)
        def transport(*args):
            # What reaches the remote, and every query deciding where it goes, sees what a plain
            # git push from this clone and this operator environment sees: global and system
            # configuration, credential helpers, rewrites, proxies and SSH/askpass variables.
            return git(*args, profile='network')
        def remote_refs():
            # Every advertised ref, HEAD and peeled tags included, plus each symbolic ref's target.
            listed = transport('ls-remote', '--symref', remote)
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
        # The push is addressed to the receiver's URL and routed as the operator configured it:
        # url.*.insteadOf and pushInsteadOf rewrites, a remote section or a legacy remotes/ or
        # branches/ file of that name, in any scope the push reads. Routing is the operator's and
        # is kept; the effect record stores where it went instead. `listed` is where the remote's
        # state is read before and after the push, the listing's own resolution of the URL.
        resolved = transport('ls-remote', '--get-url', remote)
        if resolved.returncode:
            raise E.Refused('invalid-input')
        listed = resolved.stdout.strip()
        before = remote_refs()
        if before is None or before.get(ref) != payload['old_tip']:
            raise E.Refused('stale-subject')
        # An ordinary git push, so the clone's hooks, url.*.insteadOf rewrites, transports
        # (HTTP(S) included) and credential helpers behave exactly as configured. Only what
        # WIDENS a push is neutralized: an explicit URL and single refspec, no tag following
        # from the command line or config, no push options from any configuration scope (an
        # empty push.pushOption resets the list; on GitLab-style servers an option can open a
        # merge request or skip CI), no submodule recursion, and a lease on the old tip.
        push = transport('-c', 'push.followTags=false', '-c', 'push.pushOption=', 'push', '--porcelain',
                         '--no-follow-tags', '--recurse-submodules=no',
                         '--force-with-lease=' + ref + ':' + payload['old_tip'],
                         remote, payload['commit'] + ':' + ref)
        # Where the push went is git's own account: for each repository it pushed to, a porcelain
        # `To <url>` line followed by git's status line for this one refspec. A pre-push hook
        # writes to the same stream (git runs it with standard output inherited), so a `To` line
        # counts only when that status line follows it; a hook's own text or its own push of
        # another refspec is never taken for a destination.
        refspec = payload['commit'] + ':' + ref
        lines = push.stdout.splitlines()
        pushed = [line[len('To '):] for line, status in zip(lines, lines[1:])
                  if line.startswith('To ') and len(status.split('\t')) == 3
                  and len(status.split('\t')[0]) == 1 and status.split('\t')[1] == refspec]
        # Compared as git displays them, recorded without credentials.
        reached = pushed == [displayed_url(listed)]
        destination = {'authorized_url': anonymous_url(displayed_url(remote)),
                       'listed_url': anonymous_url(displayed_url(listed)),
                       'pushed_urls': [anonymous_url(url) for url in pushed]}
        # Completion is exactly one remote change, observed where the push went: the push reached
        # one repository, the one the listing reads, and there the authorized ref (and any symbolic
        # ref that targets it, HEAD included) moved to the commit; every other entry is unchanged.
        # A route that sends the push somewhere the listing does not read cannot be confirmed.
        after = remote_refs()
        expected = dict(before, **{ref: payload['commit']})
        expected.update({name[len('symref:'):]: payload['commit'] for name, target in before.items()
                         if name.startswith('symref:') and target == ref})
        complete = (push.returncode == 0 and reached
                    and after is not None and after == expected)
        return dict(binding, status='completed' if complete else 'unknown', destination=destination,
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
