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
import re
import secrets
import select
import subprocess
import sys
import time

import importlib.util
_spec = importlib.util.spec_from_file_location('effects', Path(__file__).with_name('control_effects.py'))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
_git_process = E.organ('git_process')

# Time limits. Every git step of a publication is bounded by the receiver's `git_step_seconds`,
# and the push by that bound for each destination it reaches. The supervisor never waits by a
# fixed total: the executor announces, before each stage, how long that stage may take, and
# the supervisor's limit follows it, so a slow multi-destination push is never killed after
# acceptance. `accept_seconds` bounds authentication and acceptance, before any announcement.
GIT_STEP_SECONDS = 20
ACCEPT_SECONDS = 30
STORE_MARGIN_SECONDS = 5


def _announce_nothing(seconds):
    pass


_announce = _announce_nothing


_SCHEME = re.compile(r'[A-Za-z][A-Za-z0-9+.-]*')
# A well-formed host as RFC 3986 writes one: an IP literal in brackets, or a registered name of
# unreserved characters, percent escapes and sub-delimiters. A scheme URL's authority may add a
# numeric port.
_HOST = r"(\[[0-9A-Fa-f:.]+\]|(?:[A-Za-z0-9._~!$&'()*+,;=-]|%[0-9A-Fa-f]{2})*)"
_AUTHORITY = re.compile(_HOST + r'(:[0-9]*)?')
_SCP_HOST = re.compile(_HOST)
UNPARSED = '<unparsed>'


def scrubbed_url(url):
    """A URL as it is recorded: parsed, never taken from git's display, and holding no user
    information, query, fragment or command text. Anything that does not parse into a
    well-formed host is over-scrubbed: what follows the scheme, or the whole address, becomes
    `<unparsed>`.

    `<transport>::<address>` is scrubbed in its address, recursively, and `ext::` (a command
    line, which can carry anything) keeps no command text. A scheme URL loses everything up to
    the last `@` of its authority (which ends at the first `/`, `?` or `#`, as git and RFC 3986
    read it) and, except a file URL, whose path git takes literally, its query and fragment; an
    authority that is not a well-formed host and port, or a path holding an `@`, is unparsed.
    An scp-style address ([user@]host:path, a `:` outside brackets before any `/`) loses
    everything up to the last `@` before its first `/`, and must then start with a well-formed
    host and its `:`. A local path is unchanged. Text git produced in no encoding is kept as
    escapes."""
    url = url.encode('utf-8', 'surrogateescape').decode('utf-8', 'backslashreplace')
    scheme = _SCHEME.match(url)
    if scheme and url.startswith('::', scheme.end()):
        if scheme.group().lower() == 'ext':
            return url[:scheme.end() + 2] + '<command>'
        return url[:scheme.end() + 2] + scrubbed_url(url[scheme.end() + 2:])
    if scheme and url.startswith('://', scheme.end()):
        prefix, rest = url[:scheme.end() + 3], url[scheme.end() + 3:]
        end = min([rest.find(c) for c in '/?#' if c in rest] or [len(rest)])
        host, tail = rest[:end].rpartition('@')[2], rest[end:]
        if scheme.group().lower() != 'file':
            tail = tail.partition('#')[0]
            tail = tail.partition('?')[0]
            if '@' in tail:
                return prefix + UNPARSED
        if not _AUTHORITY.fullmatch(host):
            return prefix + UNPARSED
        return prefix + host + tail
    depth, colon = 0, -1
    for i, c in enumerate(url):
        if c == '[':
            depth += 1
        elif c == ']':
            depth = max(depth - 1, 0)
        elif c == '/' and not depth:
            return url
        elif c == ':' and not depth:
            colon = i
            break
    if colon < 0:
        return url
    slash = url.find('/')
    rest = url[url.rfind('@', 0, len(url) if slash < 0 else slash) + 1:]
    depth = 0
    for i, c in enumerate(rest):
        if c == '[':
            depth += 1
        elif c == ']':
            depth = max(depth - 1, 0)
        elif c == ':' and not depth:
            return rest if _SCP_HOST.fullmatch(rest[:i]) else UNPARSED
    return UNPARSED


def receive(config, contract, accepted):
    receiver = config['receivers'][contract['target']]
    if receiver['kind'] != contract['kind']:
        raise E.Refused('scope-mismatch')
    binding = {f: accepted[f] for f in ('dispatch_id', 'target', 'request_digest')}
    if contract['kind'] == 'publication' and 'argv' not in receiver:
        payload = contract['payload']
        repo, remote, ref = receiver['repository'], receiver['remote'], receiver['ref']
        step = receiver.get('git_step_seconds', GIT_STEP_SECONDS)
        # Resolution: the tree check, the configuration guard and git's resolution.
        _announce(3 * step + STORE_MARGIN_SECONDS)
        def git(*args, profile='isolated', env=None, steps=1):
            # Output is decoded losslessly: a hook, a server or a ref name may emit any bytes.
            return _git_process.run(['git', '-C', repo, *args], capture_output=True, text=True,
                                    errors='surrogateescape', timeout=steps * step, profile=profile, env=env)
        def transport(*args, env=None, steps=1):
            # What reaches the remote, and every query deciding where it goes, sees what a plain
            # git push from this clone and this operator environment sees: global and system
            # configuration, credential helpers, rewrites, proxies and SSH/askpass variables.
            return git(*args, profile='network', env=env, steps=steps)
        def remote_refs(url):
            # Every advertised ref of one destination, HEAD and peeled tags included, plus each
            # symbolic ref's target; None when it cannot be listed.
            listed = transport('ls-remote', '--symref', url)
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
        # branches/ file of that name, pushurl fan-out, in any scope the push reads. Routing is
        # the operator's and is kept. WHERE it goes is git's own resolution of this push from
        # configuration, read before pushing and never from anything the push prints: `git
        # remote show -n` names every push URL of the remote git push would use, for a configured
        # remote and for a plain URL alike (`git remote get-url` answers only for remotes in the
        # clone's own file), without contacting any remote or running any hook. It reports one URL
        # per line, so a line break in the receiver's URL or in any configured URL would make two
        # URLs of one; such a configuration is refused before anything is pushed.
        if '\n' in remote:
            raise E.Refused('invalid-input')
        urls = transport('config', '-z', '--get-regexp',
                         r'^(remote\..*\.(url|pushurl)|url\..*\.(insteadof|pushinsteadof))$')
        if urls.returncode not in (0, 1) or any('\n' in entry.partition('\n')[2]
                                                for entry in urls.stdout.split('\0')):
            raise E.Refused('invalid-input')
        shown = transport('remote', 'show', '-n', '--', remote, env=dict(
            {k: v for k, v in os.environ.items() if k != 'LANGUAGE'}, LC_ALL='C'))
        head = '* remote ' + remote + '\n'
        lines = shown.stdout[len(head):].split('\n') if shown.stdout.startswith(head) else []
        pushed = []
        for line in lines[1:]:
            if not line.startswith('  Push  URL: '):
                break
            pushed.append(line[len('  Push  URL: '):])
        if (shown.returncode or not lines or not lines[0].startswith('  Fetch URL: ') or not pushed
                or lines[1 + len(pushed):2 + len(pushed)] != ['  HEAD branch: (not queried)']):
            raise E.Refused('invalid-input')
        # Each destination is listed by the URL git resolved for it, and `git ls-remote` resolves a
        # URL again through the whole remote lookup (a remote section named by it, a legacy
        # remotes/ file of that name, a further url.*.insteadOf). A destination that does not
        # resolve to itself would be listed somewhere the push never went, so it is refused by
        # name before anything is pushed; `--get-url` reads configuration only, no network.
        # From here each destination takes at most four steps: its self-resolution, its listing
        # before, its share of the push and its listing after.
        _announce(4 * step * len(pushed) + STORE_MARGIN_SECONDS)
        for url in pushed:
            itself = transport('ls-remote', '--get-url', '--', url)
            if itself.returncode or itself.stdout != url + '\n':
                raise E.Refused('rerouted-destination')
        # Each destination's state before the push, so its change can be judged after it. Nothing
        # is pushed unless every destination could be listed and holds the authorized ref at the
        # expected old state: the old tip, or absent when the all-zero id names a ref creation. A
        # refusal here is made before anything reaches a destination, and is reported by name.
        absent = set(payload['old_tip']) == {'0'}
        before = [remote_refs(url) for url in pushed]
        if any(state is None or (ref in state if absent else state.get(ref) != payload['old_tip'])
               for state in before):
            raise E.Refused('stale-subject')
        # An ordinary git push, so the clone's hooks, url.*.insteadOf rewrites, transports
        # (HTTP(S) included) and credential helpers behave exactly as configured. Only what
        # WIDENS a push is neutralized: an explicit URL and single refspec, no tag following
        # from the command line or config, no push options from any configuration scope (an
        # empty push.pushOption resets the list; on GitLab-style servers an option can open a
        # merge request or skip CI), no submodule recursion, and a lease on the old tip. What it
        # prints is diagnostic text only: a pre-push hook shares its standard output and a server
        # can shape its report, so nothing in it is evidence of where it went or whether it worked.
        push = transport('-c', 'push.followTags=false', '-c', 'push.pushOption=', 'push', '--porcelain',
                         '--no-follow-tags', '--recurse-submodules=no',
                         '--force-with-lease=' + ref + ':' + ('' if absent else payload['old_tip']),
                         remote, payload['commit'] + ':' + ref, steps=len(pushed))
        # Completion is read from each destination's actual state after the push. A destination
        # is `at-tip` when its advertised state is exactly the state before (checked above to
        # hold the expected old state) with the authorized ref, and any symbolic ref that targets
        # it, HEAD included, moved to the commit; `unreachable` when it cannot be listed after;
        # otherwise `not-at-tip` (rejected, reported under another ref, or anything else
        # changed). The effect is completed only when the push exited cleanly and every resolved
        # destination is at the tip.
        outcomes = []
        for url, state in zip(pushed, before):
            after = remote_refs(url)
            if after is None:
                outcomes.append('unreachable')
                continue
            expected = dict(state, **{ref: payload['commit']})
            expected.update({name[len('symref:'):]: payload['commit'] for name, target in state.items()
                             if name.startswith('symref:') and target == ref})
            outcomes.append('at-tip' if after == expected else 'not-at-tip')
        destination = {'authorized_url': scrubbed_url(remote),
                       'destinations': [{'url': scrubbed_url(url), 'outcome': outcome}
                                        for url, outcome in zip(pushed, outcomes)]}
        complete = push.returncode == 0 and all(outcome == 'at-tip' for outcome in outcomes)
        return dict(binding, status='completed' if complete else 'unknown', destination=destination,
                    evidence={'remote_commit': payload['commit'], 'tree': payload['tree']} if complete else None)
    # Only a service-selected adapter sees reusable authentication, on stdin. Its stdout
    # is never returned verbatim; only a bound digest enters the effect observation.
    credential = Path(receiver['credential_file']).read_text()
    packet = dict(binding, credential=credential, payload=contract['payload'])
    _announce(receiver.get('timeout', 20) + STORE_MARGIN_SECONDS)
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
            if accepted.get('status') == 'refused':
                return {'accepted': False, 'refusal': accepted['refusal'], 'result': accepted, 'metrics': E.metrics(conn)}
            return {'accepted': True, 'result': accepted, 'metrics': E.metrics(conn)}
        contract = accepted
        try:
            observation = receive(config, contract, accepted)
        except E.Refused as error:
            # A receiver refuses only before anything reaches a destination or an adapter, so the
            # refusal is conclusive: recorded as refused and reported by name, never as unknown.
            observation = dict(accepted, status='refused', refusal=error.code, evidence=None)
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            observation = dict(accepted, status='unknown', evidence=None)
        result = E.finish(conn, accepted, observation, journal)
        if result['status'] == 'refused':
            return {'accepted': False, 'refusal': result['refusal'], 'result': result, 'metrics': E.metrics(conn)}
        return {'accepted': True, 'result': result, 'metrics': E.metrics(conn)}
    except (E.Refused, E.S.StoreRefused) as error:
        return {'accepted': False, 'refusal': error.code, 'metrics': {'refused': 1}}
    except (ValueError, TypeError, KeyError):
        return {'accepted': False, 'refusal': 'invalid-input', 'metrics': {'refused': 1}}
    finally:
        conn.close()


def call(config_path, request, principal, connection_key):
    """Trusted supervisor-side adapter; config_path is never taken from worker JSON.

    The limit follows the executor: `accept_seconds` (configuration) for authentication and
    acceptance, then each window the executor announces for its next stage."""
    accept = json.loads(Path(config_path).read_text()).get('accept_seconds', ACCEPT_SECONDS)
    child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), str(config_path)],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    pending = b''
    def next_message(deadline):
        nonlocal pending
        while b'\n' not in pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([child.stdout], [], [], remaining)[0]:
                raise E.Refused('effect-service-unavailable')
            chunk = os.read(child.stdout.fileno(), 65536)
            if not chunk:
                raise E.Refused('effect-service-unavailable')
            pending += chunk
        line, _, pending = pending.partition(b'\n')
        return json.loads(line)
    try:
        challenge = next_message(time.monotonic() + 10)['challenge']
        message = E.SIG.canonical({'challenge': challenge, 'request_digest': E.SIG.digest(request)})
        signature = E.SIG.sign_bytes(connection_key, message, E.NAMESPACE) if connection_key else ''
        child.stdin.write((json.dumps({'request': request, 'principal': principal,
                                       'signature': signature}) + '\n').encode())
        child.stdin.close()
        deadline = time.monotonic() + accept
        while True:
            answer = next_message(deadline)
            if isinstance(answer, dict) and set(answer) == {'window_seconds'}:
                deadline = time.monotonic() + answer['window_seconds']
                continue
            break
        if child.wait(timeout=5):
            raise E.Refused('effect-service-unavailable')
        return answer
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)


def main():
    global _announce
    _announce = lambda seconds: print(json.dumps({'window_seconds': seconds}), flush=True)
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
