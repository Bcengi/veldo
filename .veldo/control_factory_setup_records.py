#!/usr/bin/env python3
"""VELDO-0167: shared record storage and additive configuration on factory setup.

Check all files before writing. Existing JSON bytes outside this step's missing or null
keys are preserved, including their formatting. The subscriber registry belongs only to
control_service_api; receivers know just the authority socket.
"""
import json
import os
from pathlib import Path
import re
import stat


def directory(root, differs, write=False):
    path = Path(root) / 'records'
    if path.exists():
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise differs(str(path))
        return False
    if write:
        path.mkdir(mode=0o700)
        path.chmod(0o700)
    return True


def keys(root, socket):
    return {'records': str(Path(root) / 'records'), 'record_hint_service': socket}


def patch(path, expected, owned, differs):
    """Return state, resulting bytes and added key names; inspect without writing."""
    path = Path(path)
    if not path.exists():
        return 'absent', json.dumps(expected, indent=1, sort_keys=True) + '\n', list(owned)
    try:
        info = path.lstat()
        text = path.read_text()
        held = json.loads(text)
    except (OSError, ValueError):
        raise differs(str(path)) from None
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600
            or not isinstance(held, dict)):
        raise differs(str(path))
    merged = dict(held)
    added = []
    for key, value in owned.items():
        if held.get(key) is None:
            merged[key] = value
            added.append(key)
    if merged != expected:
        raise differs(str(path))
    for key in added:
        if key in held:
            pattern = r'("' + re.escape(key) + r'"\s*:\s*)null\b'
            text, count = re.subn(pattern, lambda m: m[1] + json.dumps(owned[key]), text)
            if count != 1:
                raise differs(str(path))
        else:
            end = text.rfind('}')
            at = len(text[:end].rstrip())
            text = text[:at] + ',\n ' + json.dumps(key) + ': ' + json.dumps(owned[key]) + text[at:]
    return ('upgrade' if added else 'equal'), text, added


def prepare(root, installed, receivers, api, service_text, differs):
    directory(root, differs)
    owned = keys(root, installed['socket'])
    files = []
    for path, expected in sorted(receivers.items()):
        # Earlier engine keys are added by the engine upgrade before this step writes.
        try:
            held = json.loads(Path(path).read_text())
        except (OSError, ValueError):
            raise differs(str(path)) from None
        if not isinstance(held, dict):
            raise differs(str(path))
        expected = {k: v for k, v in expected.items() if k in held or k not in ('host_trust', 'state_root')}
        if 'runs' in held:
            expected['runs'] = str(Path(installed['store_path']).parent / 'runs')
        expected.update(owned)
        state, text, added = patch(path, expected, owned, differs)
        files.append((path, expected, owned, state, text, added))
    api_states = {}
    for name in ('service_config', 'installed_service_config'):
        expected = json.loads(service_text)
        own = {k: expected[k] for k in ('records',) if k in expected}
        state, text, added = patch(api[name], expected, own, differs)
        api_states[name] = state
        files.append((api[name], expected, own, state, text, added))
    return dict(root=root, files=files, api_states=api_states)


def apply(plan, differs):
    made = directory(plan['root'], differs, write=True)
    reports = [dict(step='records_directory', outcome='done' if made else 'already_done',
                    records=str(Path(plan['root']) / 'records'))]
    for path, expected, own, state, text, added in plan['files']:
        if state == 'upgrade':
            # An engine upgrade can have added its keys since preflight; retain them too.
            current = json.loads(Path(path).read_text())
            expected = dict(current, **own)
            state, text, added = patch(path, expected, own, differs)
        if state == 'upgrade':
            temporary = str(path) + '.records-new'
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as handle:
                handle.write(text)
            os.replace(temporary, path)
        reports.append(dict(step='record_configuration', path=str(path), keys=sorted(own), added=added,
                            outcome='already_done' if state == 'equal' else 'done'))
    return reports


def fresh(service_config, root, differs):
    installed = json.loads(Path(service_config).read_text())
    own = keys(root, installed['socket'])
    files = []
    for path in sorted(installed['receiver']['configs'].values()):
        expected = dict(json.loads(Path(path).read_text()), **own)
        state, text, added = patch(path, expected, own, differs)
        files.append((path, expected, own, state, text, added))
    return apply(dict(root=root, files=files), differs)
