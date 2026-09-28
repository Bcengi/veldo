"""A stand-in Tailscale CLI replaying the scrubbed read-only capture of proof/VELDO-0171/tailscale-capture.json.

Loaded by path by the suites that run veldo factory setup (73_veldo_0139_factory_setup,
74_veldo_0140_standing_delegation, 85_veldo_0171_setup_api), so no suite reaches the host's real Tailscale.
`stand_in(capture, python)` writes an executable in a 0700 directory of its own and returns a StandIn:
its `path` is what the suite gives setup as the one system location to look at. For the state it is set
to (one of the capture's derived_states: ready, operator, https, persistence, logged-out, occupied), it
prints exactly that state's outputs for the five read-only commands the capture was taken with
(`version`, `status --json`, `serve status --json`, `debug prefs`, `serve --help`, the last on the error
stream as the real CLI prints it). `serve --bg --https=443 <target>` from the ready state succeeds and
afterwards `serve status --json` prints the capture's `served` state with @TARGET@ that target; `funnel`
is logged and answered like it, so a check that setup never ran Funnel can only be the invocation log's.
Anything else exits 2. Every invocation is appended to a log in a second 0700 directory the stand-in's
path does not reveal (outside setup's reach), which the suite reads after setup exits.
"""
import json
import os
from pathlib import Path
import shutil
import tempfile

_SCRIPT = '''#!%(python)s -B
import json
import sys
CAPTURE, STATE, LOG = %(capture)r, %(state)r, %(log)r
argv = sys.argv[1:]
with open(LOG, 'a') as handle:
    handle.write(json.dumps(argv) + '\\n')
with open(CAPTURE) as handle:
    capture = json.load(handle)
with open(STATE) as handle:
    state = json.load(handle)
states = {s['name']: s['outputs'] for s in capture['derived_states']}
outputs = states[state['state']]
serve_status = outputs['serve-status']
if state.get('target') is not None:
    serve_status = json.loads(json.dumps(states['served']['serve-status']).replace('@TARGET@', state['target']))


def emit(value):
    sys.stdout.write(value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True) + '\\n')


if argv == ['version']:
    emit(outputs['version'])
elif argv == ['status', '--json']:
    emit(outputs['status'])
elif argv == ['debug', 'prefs']:
    emit(outputs['prefs'])
elif argv == ['serve', '--help']:
    sys.stderr.write(outputs['serve-help'])
elif argv == ['serve', 'status', '--json']:
    emit(serve_status)
elif argv[:1] in (['serve'], ['funnel']) and '--bg' in argv and len(argv) == 4 and argv[2] == '--https=443':
    if state['state'] != 'ready' or state.get('target') not in (None, argv[3]):
        sys.exit(1)
    state['target'] = argv[3]
    with open(STATE, 'w') as handle:
        json.dump(state, handle)
else:
    sys.exit(2)
'''


class StandIn:
    def __init__(self, capture, python, state='ready'):
        self.directory = Path(tempfile.mkdtemp(prefix='v171-ts-'))
        self.logs = Path(tempfile.mkdtemp(prefix='v171-tslog-'))
        os.chmod(str(self.directory), 0o700)
        os.chmod(str(self.logs), 0o700)
        self.path = str(self.directory / 'tailscale')
        self.state_file = str(self.directory / 'state.json')
        self.log_file = str(self.logs / 'invocations.jsonl')
        self.set(state)
        Path(self.path).write_text(_SCRIPT % {'python': python, 'capture': str(capture), 'state': self.state_file,
                                              'log': self.log_file})
        os.chmod(self.path, 0o700)

    def set(self, state, target=None):
        Path(self.state_file).write_text(json.dumps({'state': state, 'target': target}))

    def target(self):
        return json.loads(Path(self.state_file).read_text()).get('target')

    def invocations(self):
        path = Path(self.log_file)
        return [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []

    def clear(self):
        Path(self.log_file).unlink(missing_ok=True)

    def close(self):
        shutil.rmtree(str(self.directory), ignore_errors=True)
        shutil.rmtree(str(self.logs), ignore_errors=True)


def stand_in(capture, python, state='ready'):
    return StandIn(capture, python, state)


def free_port():
    """A loopback port nothing listens on now, for one suite run's API."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]
