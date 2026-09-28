"""Allowlist scrub of the five authorized read-only local Tailscale captures (VELDO-0171 AC2).

    python3 -B proof/VELDO-0171/scrub_tailscale.py

Raw input stays outside the repository, in /home/dmitry/projects/veldo-live-captures/2026-09-27/tailscale/.
Dynamic map keys are values too. The captured outputs are kept as scrubbed; every state the suite's
stand-in replays beyond them is a listed field edit of the capture (field_edits), and no capability
field the CLI does not print is invented. The one parametric value is the loopback target of the status
after `serve --bg`: it is the target that invocation named (@TARGET@), since each suite run listens on a
port of its own.
"""
import json
from pathlib import Path
import re


SOURCE = Path('/home/dmitry/projects/veldo-live-captures/2026-09-27/tailscale')
DESTINATION = Path(__file__).with_name('tailscale-capture.json')
FIELDS = set('''Version TUN BackendState HaveNodeKey AuthURL TailscaleIPs Self
Health MagicDNSSuffix CurrentTailnet CertDomains ExtraRecords Peer User ClientVersion
ID NodeID PublicKey HostName DNSName OS UserID AllowedIPs Addrs CurAddr Relay PeerRelay
RxBytes TxBytes Created LastWrite LastSeen LastHandshake Online ExitNode ExitNodeOption
Active PeerAPIURL TaildropTarget NoFileSharingReason Capabilities CapMap InNetworkMap
InMagicSock InEngine KeyExpiry Name MagicDNSEnabled LoginName DisplayName ProfilePicURL
TCP Web HTTPS Handlers Proxy Foreground AllowFunnel OperatorUser'''.split())
STATES = {'Running', 'Stopped', 'NeedsLogin', 'NeedsMachineAuth', 'NoState', 'Starting'}


def scrub(value, field='', versions=()):
    if isinstance(value, dict):
        return {(key if key in FIELDS else '<string:%d>' % index):
                scrub(item, key, versions) for index, (key, item) in enumerate(value.items())}
    if isinstance(value, list):
        return [scrub(item, field, versions) for item in value]
    if isinstance(value, str):
        if field == 'BackendState' and value in STATES:
            return value
        if field == 'Version' and value in versions:
            return value
        return '<string>'
    if value is None or isinstance(value, bool):
        return value
    return 0.0 if isinstance(value, float) else 0


def strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, str):
        yield value


def main():
    raw_version = (SOURCE / 'version.stdout').read_text()
    version = raw_version.splitlines()[0].strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('unrecognized CLI version schema constant')
    raw = {name: json.loads((SOURCE / (name + '.stdout')).read_text())
           for name in ('status', 'serve-status', 'prefs')}
    help_text = (SOURCE / 'serve-help.stderr').read_text()
    def prefs_names(value):
        if isinstance(value, dict):
            return {k: (('<string>' if v else '') if k == 'OperatorUser' else prefs_names(v))
                    for k, v in value.items() if re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', k)}
        if isinstance(value, list):
            return [prefs_names(v) for v in value]
        return None
    versions = [version]
    # The status version can include a build suffix. Keep only the plain CLI
    # version constant; a status build identity is scrubbed like any other value.
    result = {
        'schema': 'veldo.tailscale_capture/v1',
        'date': '2026-09-27',
        'constant_allowlist': {'Version': versions, 'BackendState': sorted(STATES), 'protocol': ['https']},
        'field_allowlist': sorted(FIELDS),
        'scrub_rules': {
            'strings': '<string> unless the field and value are in constant_allowlist',
            'dynamic_keys': '<string:N> with N the map entry ordinal',
            'numbers': 'zero with the original numeric type',
            'booleans_and_null': 'unchanged',
            'version_output': 'first line is the CLI version; other lines are string placeholders'
        },
        'captured': {
            'version': '\n'.join([version] + ['<string>'] * (len(raw_version.splitlines()) - 1)) + '\n',
            **{name: scrub(value, versions=versions) for name, value in raw.items() if name != 'prefs'},
            'prefs': prefs_names(raw['prefs']),
            'serve-help': ('--bg\n' if '--bg' in help_text.split() else '')
        },
        'derived_states': [],
        'field_edits': [],
        'streams': {'version': 'stdout', 'status': 'stdout', 'serve-status': 'stdout', 'prefs': 'stdout', 'serve-help': 'stderr'},
        'capture_commands': ['version', 'status --json', 'serve status --json', 'debug prefs', 'serve --help']
    }
    # Every executable test state is a named edit of the scrubbed capture.
    edits = {
        'ready': [('status', ['Self', 'DNSName'], 'factory.invalid.'),
                  ('status', ['CertDomains'], ['factory.invalid']),
                  ('serve-status', [], {})],
        'operator': [('prefs', ['OperatorUser'], '')],
        'https': [('status', ['CertDomains'], [])],
        'persistence': [('serve-help', [], '')],
        'logged-out': [('status', ['BackendState'], 'NeedsLogin')],
        'served': [('serve-status', [], {'TCP': {'443': {'HTTPS': True}},
                    'Web': {'factory.invalid:443': {'Handlers': {'/': {'Proxy': '@TARGET@'}}}}})],
        'occupied': [('serve-status', [], {'TCP': {'443': {'HTTPS': True}},
                      'Web': {'factory.invalid:443': {'Handlers': {'/': {'Proxy': 'http://127.0.0.1:9'}}}}})]
    }
    import copy
    for name, changes in edits.items():
        state = copy.deepcopy(result['captured'] if name == 'ready' else result['derived_states'][0]['outputs'])
        listed = []
        for source, path, value in changes:
            parent = state
            for key in [source] + path[:-1] if path else []:
                parent = parent[key]
            key = path[-1] if path else source
            listed.append({'source': source, 'path': path, 'before': parent.get(key), 'after': value})
            parent[key] = value
        result['derived_states'].append({'name': name, 'base': 'captured' if name == 'ready' else 'ready', 'outputs': state})
        result['field_edits'].append({'state': name, 'edits': listed})
    result['scrub_rules']['prefs'] = 'Schema names only; OperatorUser presence as a string placeholder; every other leaf null'
    result['scrub_rules']['serve-help'] = 'Only the schema flag --bg, when listed; all prose discarded'
    result['state_rules'] = {
        'ready': 'the captured outputs with a tailnet name of the reserved .invalid domain, its certificate domain, '
                 'and no Serve mapping',
        'operator': 'ready without the operator setting', 'https': 'ready without a certificate domain',
        'persistence': 'ready whose serve help lists no --bg', 'logged-out': 'ready with a logged-out backend',
        'served': 'the Serve status after `serve --bg --https=443 <target>`; @TARGET@ is the target that invocation named',
        'occupied': 'ready with the name\'s HTTPS mapped to another loopback target'}
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    constants = FIELDS | STATES | set(versions) | {'https'} | set(k for k in strings(result['captured']['prefs']) if k != '<string>')
    # Literal substring checks cover every raw string value, and also dynamic
    # keys. Report counts only, never an identifying value.
    needles = {s for value in raw.values() for s in strings(value)} | set(raw_version.splitlines()) | {help_text}
    needles = {s for s in needles if len(s) > 3 and s not in constants}
    leaks = sum(s in text for s in needles)
    if leaks:
        raise ValueError('raw capture string survived: %d matches' % leaks)
    DESTINATION.write_text(text)
    print('Raw string overlap check: %d nonconstant strings, zero matches' % len(needles))


if __name__ == '__main__':
    main()
