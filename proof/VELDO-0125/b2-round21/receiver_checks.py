"""A corrupt previous entry cannot acknowledge and discard a fresh release event."""
import errno
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch


def receiver(modules, config_path, fault):
    spec = importlib.util.spec_from_file_location('r21_worker', Path(modules) / 'control_worker.py')
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    config = json.loads(Path(config_path).read_text())
    root = Path(config['runs'])
    w.install_resumer = lambda *args: None  # Native launchd is outside these Linux logic rows.
    calls = []
    def deliver(config, request):
        entry, = w.OUT.entries(config)
        assert entry['request'] == request and request['action'] == 'release'
        calls.append(request)
        (root / 'delivered.json').write_text(json.dumps(calls))
        return dict(record=dict(state='retired'), host_released=True)
    w.receive_locked = deliver  # Observe delivery at the trusted endpoint boundary.
    real_replace = w.OUT.replace_entry
    def replace(*args, **kwargs):
        if fault == 'write-eio':
            raise OSError(errno.EIO, 'injected fresh event persistence failure')
        return real_replace(*args, **kwargs)
    with patch.object(w.OUT, 'replace_entry', replace):
        w.main(config_path)
    # An acknowledged event must not remain scheduled for duplicate delivery.
    w.resume_pending(config, drain=True)
    assert len(calls) == 1, 'event lost or delivered more than once'


def cases(T, helper):
    def handoff(base, state, content, fault='none'):
        w = T.load('control_worker')
        config = dict(runs=str(base / 'runs'))
        config_path = base / 'config.json'
        config_path.write_text(json.dumps(config))
        request = dict(dispatch_id='corrupt-release', action='release', contract_digest='original-contract')
        directory = Path(config['runs']) / state
        directory.mkdir(parents=True)
        path = directory / w.OUT.key(request['dispatch_id'])
        path.write_bytes(content)
        root = directory.parent
        argv = [sys.executable, str(Path(__file__).resolve()), str(T.MODULES), str(config_path)]
        def invoke(fault):
            return subprocess.run(argv + [fault], input=json.dumps(request) + '\n',
                                  text=True, capture_output=True, timeout=20)
        result = invoke(fault)
        assert 'worker_delivery_invalid_entry' in result.stderr, result.stderr
        assert (root / '.parked' / path.name).read_bytes() == content
        if fault == 'write-eio':
            assert result.returncode != 0 and 'OSError' in result.stderr, result.stdout
            assert not result.stdout.strip(), 'failed persistence acknowledged the event'
            assert not (root / 'delivered.json').exists()
            result = invoke('none')  # Linux retries a failed transport handoff.
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == dict(state='retired'), 'new release was acknowledged without delivery'
        assert json.loads((root / 'delivered.json').read_text()) == [request]
        assert (root / '.parked' / path.name).read_bytes() == content
        for state in ('.pending', '.active', '.waiting'):
            assert not list((root / state).glob('*.json')), 'delivered event remains queued'

    rows = {}
    for state in ('.waiting', '.pending'):
        for name, content in (('json', b'{broken'), ('shape', b'{"request":null}')):
            rows['AC3/receiver-corrupt-' + state[1:] + '-' + name + '-release-delivered'] = (
                lambda base, state=state, content=content: handoff(base, state, content))
        rows['AC3/receiver-corrupt-' + state[1:] + '-release-write-eio-resend'] = (
            lambda base, state=state: handoff(base, state, b'{broken', 'write-eio'))
    return rows


if __name__ == '__main__':
    receiver(*sys.argv[1:])
