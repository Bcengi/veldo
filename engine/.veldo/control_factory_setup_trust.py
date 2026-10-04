"""VELDO-0170: repair receiver host trust from the installation, as one setup re-run step."""
import json
from pathlib import Path


def inspect(installed, EL, Refused):
    """Read only, before any setup write. Trust comes from installed ingress, never a setup flag."""
    path = EL.host_trust_path()
    ingress = installed.get('channel_ingress')
    try:
        if ingress:
            path = json.loads(Path(ingress).read_text()).get('host_trust') or path
        trust = EL.load_host_trust(path)
    except (OSError, ValueError, EL.Stopped):
        trust = None
    if trust is None:
        raise Refused('host_trust_required', 'no installed host trust loads')
    if trust.host_identity != installed.get('host_identity'):
        raise Refused('host_trust_required:host_identity', 'installed trust belongs to another host')
    configs = {}
    for repository, filename in sorted((installed.get('receiver') or {}).get('configs', {}).items()):
        try:
            held = json.loads(Path(filename).read_text())
        except (OSError, ValueError):
            held = None
        if not isinstance(held, dict):
            raise Refused('invalid_input:state_root:differs:' + filename, 'receiver configuration cannot be read')
        configs[filename] = (repository, held)
    return {'trust': str(path), 'host_identity': trust.host_identity, 'configs': configs}


def validate(step, installed, receivers, differs):
    """Compare the installer rendering, excluding only trust and keys an older installer lacked."""
    template = next(iter(receivers.values()))
    for path, (repository, held) in step['configs'].items():
        expected = dict(template, repository=repository,
                        workspace=installed['repositories'][repository][0])
        # Adapters are owner configuration, not setup arguments. The existing engine upgrade
        # preserves them; this step must render the same configured workers, never empty defaults.
        expected['adapters'] = held.get('adapters')
        expected.pop('host_trust', None)
        actual = dict(held)
        actual.pop('host_trust', None)
        if 'state_root' not in actual:
            expected.pop('state_root', None)
        if 'runs' in actual:
            expected['runs'] = actual['runs']
        # The records preflight checks these values and plans their additive repair.
        for key in ('records', 'record_hint_service'):
            actual.pop(key, None)
            expected.pop(key, None)
        if actual != expected:
            raise differs(path)


def apply(step, API):
    """Only add the missing key, replacing the whole file at 0600. Keep current bytes untouched."""
    added, current = [], []
    for path in step['configs']:
        held = json.loads(Path(path).read_text())
        if not held.get('host_trust'):
            held['host_trust'] = step['trust']
            API.replace_file(path, API.text(held), 0o600)
            added.append(path)
        else:
            current.append(path)
    return {'step': 'receiver_host_trust', 'outcome': 'done' if added else 'already_done',
            'host_trust': step['trust'], 'host_identity': step['host_identity'],
            'added': added, 'current': current,
            'metrics': {'added': len(added), 'current': len(current)}}
