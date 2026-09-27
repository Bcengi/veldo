"""Allowlist scrub of the three authorized local Tailscale captures.

Raw input stays outside the repository. Dynamic map keys are values too.
This records captured states only; it does not invent capability fields.
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
TCP Web HTTPS Handlers Proxy Foreground AllowFunnel'''.split())
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
           for name in ('status', 'serve-status')}
    versions = [version]
    # The status version can include a build suffix. Keep only the plain CLI
    # version constant; a status build identity is scrubbed like any other value.
    result = {
        'schema': 'veldo.tailscale_capture/v1',
        'date': '2026-09-27',
        'constant_allowlist': {'Version': versions, 'BackendState': sorted(STATES)},
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
            **{name: scrub(value, versions=versions) for name, value in raw.items()}
        },
        'derived_states': [],
        'field_edits': [],
        'blocker': 'Neither captured JSON output exposes the operator setting or a background-persistence capability. No derived refusal or post-write state has been fabricated.'
    }
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    constants = FIELDS | STATES | set(versions)
    # Literal substring checks cover every raw string value, and also dynamic
    # keys. Report counts only, never an identifying value.
    needles = {s for value in raw.values() for s in strings(value)} | set(raw_version.splitlines())
    needles = {s for s in needles if len(s) > 3 and s not in constants}
    leaks = sum(s in text for s in needles)
    if leaks:
        raise ValueError('raw capture string survived: %d matches' % leaks)
    DESTINATION.write_text(text)
    print('Raw string overlap check: %d nonconstant strings, zero matches' % len(needles))


if __name__ == '__main__':
    main()
