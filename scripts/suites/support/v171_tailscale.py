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
VELDO-0234: `set(state, target, https_port, neighbors)` also takes the HTTPS port the mapping is on (443, 8443
or 10000; the captured `served` state's 443 keys renamed to it) and `neighbors`, a Serve status fragment (Web,
TCP, AllowFunnel) of mappings another app holds, merged into every `serve status --json` the stand-in prints;
`serve --bg --https=<port> <target>` is refused (exit 1) when a neighbor already holds that port.
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
serve_status = json.loads(json.dumps(outputs['serve-status']))
neighbors = state.get('neighbors') or {}
held = state.get('https_port') or 443


def ours(port):
    served = json.loads(json.dumps(states['served']['serve-status']).replace('@TARGET@', state['target']))
    return {'TCP': {str(port) if k == '443' else k: v for k, v in served.get('TCP', {}).items()},
            'Web': {(k[:-len(':443')] + ':%%d' %% port) if k.endswith(':443') else k: v
                    for k, v in served.get('Web', {}).items()}}


for part in (neighbors, ours(held) if state.get('target') is not None else {}):
    for section, entries in part.items():
        serve_status.setdefault(section, {}).update(entries)


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
elif (argv[:1] in (['serve'], ['funnel']) and '--bg' in argv and len(argv) == 4
      and argv[2] in ('--https=443', '--https=8443', '--https=10000')):
    port = int(argv[2].split('=', 1)[1])
    taken = (str(port) in (neighbors.get('TCP') or {})
             or any(k.endswith(':%%d' %% port) for k in (neighbors.get('Web') or {})))
    if (state['state'] != 'ready' or taken or state.get('target') not in (None, argv[3])
            or (state.get('target') is not None and held != port)):
        sys.exit(1)
    state['target'], state['https_port'] = argv[3], port
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

    def set(self, state, target=None, https_port=443, neighbors=None):
        Path(self.state_file).write_text(json.dumps({'state': state, 'target': target, 'https_port': https_port,
                                                     'neighbors': neighbors or {}}))

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


_HELD = []  # every port free_port() gave out, still bound (VELDO-0358, C11)


def free_port():
    """A loopback port for one suite run's API, held until this process ends (VELDO-0358, C11: the port
    holder of support/ports.py). It used to be read and released at once (bind to 0, read, close), which
    left it free for the whole start of the server, and on a loaded host another bind to port 0 took it.
    The reservation stays bound, not listening, with SO_REUSEADDR, so the kernel hands the port to no
    other bind to 0 and the server's own bind to it succeeds. release_ports() gives them back."""
    hold = _ports().reserve()
    _HELD.append(hold)
    return hold.port


def release_ports():
    """Give back every port free_port() holds: for a caller whose servers are all up or all gone."""
    while _HELD:
        _HELD.pop().release()


def _ports():
    """support/ports.py, the instance the suites' namespace already loaded when there is one."""
    import importlib.util
    import sys
    if 'ports' in sys.modules:
        return sys.modules['ports']
    path = Path(__file__).resolve().parent / 'ports.py'
    spec = importlib.util.spec_from_file_location('ports', str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules['ports'] = module
    spec.loader.exec_module(module)
    return module
