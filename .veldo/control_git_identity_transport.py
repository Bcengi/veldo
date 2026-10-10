"""Identity-only Git transport and the shared creation/adoption owner check (VELDO-0153).

Only credential references enter argv. The helper resolves the value in its own process.
The trusted provisioner calls check_remote before creation/adoption and uses git_process's
identity profile for its pushes. No repository creation is implemented here.
"""
import importlib.util
import os
from pathlib import Path
import re
import shlex
import sys
from urllib.parse import urlsplit


class Refused(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def organ(name):
    spec = importlib.util.spec_from_file_location('identity_transport_' + name,
                                                Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_remote(record, remote, *, operation='push', repository=None, request=None, observe=None):
    """One owner check for push, remote creation and adoption. Never observes raw URLs."""
    event = dict(operation=operation, repository=repository, request=request,
                 identity=(record or {}).get('id'), remote_owner=None)
    try:
        if not record:
            raise Refused('missing_authority:repository_identity')
        if not isinstance(remote, str) or any(c.isspace() for c in remote):
            raise Refused('invalid_input:remote')
        if remote.startswith('git@github.com:'):
            remote = 'ssh://git@github.com/' + remote.split(':', 1)[1]
        try:
            url = urlsplit(remote)
            port = url.port
        except ValueError:
            raise Refused('invalid_input:remote') from None
        if (url.scheme not in ('https', 'ssh') or url.hostname != 'github.com'
                or url.hostname != record.get('remote_host') or url.password is not None
                or url.query or url.fragment or port not in (None, 443 if url.scheme == 'https' else 22)
                or url.username != (None if url.scheme == 'https' else 'git')):
            raise Refused('binding_mismatch:remote_host')
        match = re.fullmatch(r'/([A-Za-z0-9][A-Za-z0-9-]*)/([A-Za-z0-9_.-]+)', url.path)
        if not match or match[2] in ('.', '..', '.git'):
            raise Refused('invalid_input:remote')
        owner = match[1]
        event['remote_owner'] = owner
        if owner.casefold() != record['remote_owner'].casefold():
            raise Refused('binding_mismatch:remote_owner')
        result = dict(host=url.hostname, owner=owner, path=url.path.lstrip('/'), scheme=url.scheme)
    except Refused as error:
        if observe:
            observe(dict(event, outcome='refused', refusal=error.code))
        raise
    if observe:
        observe(dict(event, outcome='accepted'))
    return result


def credential(record):
    try:
        push = record['push_credential']
        reference = push['reference']
        if push['kind'] not in ('token', 'ssh') or not organ('control_git_identity').reference(reference):
            raise ValueError('reference')
        value = organ('secretref').resolve_for_runtime(
            reference, organ('control_credential_keystore').SecretService()).reveal()
        if any(c in value for c in '\r\n\x00'):
            raise ValueError('credential framing')
        return value
    except Exception:
        raise Refused('unavailable_service:push_credential') from None


def options(record, remote):
    """Config after environment isolation, before starting Git. No ambient fallback."""
    target = check_remote(record, remote)
    push = record.get('push_credential', {})
    value = credential(record)
    config = ['credential.helper=', 'credential.interactive=false', 'core.askPass=',
              'http.extraHeader=', 'http.followRedirects=false']
    if push.get('kind') == 'ssh':
        if target['scheme'] != 'ssh' or not os.path.isabs(value) or not Path(value).is_file():
            raise Refused('unavailable_service:push_credential')
        command = shlex.join(['/usr/bin/ssh', '-F', os.devnull, '-o', 'IdentitiesOnly=yes',
                              '-o', 'IdentityAgent=none', '-o', 'BatchMode=yes',
                              '-o', 'PasswordAuthentication=no', '-o', 'KbdInteractiveAuthentication=no',
                              '-i', value])
        config += ['core.sshCommand=' + command]
    else:
        if target['scheme'] != 'https':
            raise Refused('binding_mismatch:push_transport')
        helper = shlex.join([sys.executable, str(Path(__file__).resolve()),
                             push['reference'], target['host'], target['path']])
        config += ['credential.useHttpPath=true', 'credential.username=x-access-token',
                   'credential.helper=!' + helper]
    return [part for item in config for part in ('-c', item)]


def record_operations(conn, events):
    """Metadata-only operational log, separate from authority and credentials."""
    import json
    conn.execute('CREATE TABLE IF NOT EXISTS git_identity_operations (event TEXT NOT NULL)')
    conn.executemany('INSERT INTO git_identity_operations VALUES (?)',
                     [(json.dumps(event, sort_keys=True),) for event in events])


def metrics(conn):
    import json
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='git_identity_operations'").fetchone():
        return {}
    counts = {}
    for (data,) in conn.execute('SELECT event FROM git_identity_operations'):
        event = json.loads(data)
        row = counts.setdefault(event.get('identity'), {'pushes': 0, 'refusals': {}})
        if event['operation'] == 'push' and event['outcome'] == 'accepted':
            row['pushes'] += 1
        if event.get('refusal'):
            reason = event['refusal']
            row['refusals'][reason] = row['refusals'].get(reason, 0) + 1
    return counts


def helper(argv):
    """Git credential protocol. Get only, scoped to the checked host and path, never store."""
    if len(argv) != 4 or argv[-1] != 'get':
        return
    reference, host, path, _ = argv
    fields = dict(line.rstrip('\n').split('=', 1) for line in sys.stdin if '=' in line)
    if fields.get('protocol') != 'https' or fields.get('host') != host or fields.get('path') != path:
        print('quit=true\n')
        return
    try:
        value = credential({'push_credential': {'kind': 'token', 'reference': reference}})
    except Refused:
        print('quit=true\n')
        return
    print('username=x-access-token\npassword=' + value + '\n')


if __name__ == '__main__':
    helper(sys.argv[1:])
