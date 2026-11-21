"""Receiver read errors must reject the handoff so Linux can resend the event."""
import errno
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch


def receiver(modules, config_path, fault, read_number):
    spec = importlib.util.spec_from_file_location('r20_worker', Path(modules) / 'control_worker.py')
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    config = json.loads(Path(config_path).read_text())
    root = Path(config['runs'])
    w.install_resumer = lambda *args: None  # Already installed; no native launchd in this logic row.
    def deliver(config, request):
        entry, = w.OUT.entries(config)
        assert entry['request'] == request and request['action'] == 'release'
        (root / 'delivered.json').write_text(json.dumps(request))
        return dict(record=dict(state='retired'), host_released=True)
    w.receive_locked = deliver
    real_read = Path.read_text
    reads = 0
    def read(path, *args, **kwargs):
        nonlocal reads
        if path.name == w.OUT.key('read-retry'):
            reads += 1
            if fault != 'none' and reads >= read_number and (fault == 'persistent' or reads == read_number):
                raise OSError(errno.EIO, 'injected receiver entry read failure')
        return real_read(path, *args, **kwargs)
    with patch.object(Path, 'read_text', read):
        w.main(config_path)


def cases(T, helper):
    def handoff(base, state, fault, read_number=1):
        w = T.load('control_worker')
        config = dict(runs=str(base / 'runs'))
        config_path = base / 'config.json'
        config_path.write_text(json.dumps(config))
        old = dict(dispatch_id='read-retry', action='run')
        request = dict(old, action='release')
        with w.OUT.locked(config) as root:
            path = w.OUT.move(root, w.OUT.locate(root, old['dispatch_id']), state,
                             w.CL.durable_json, dict(request=old, attempts=3, due=0, reason='held'))
        original = path.read_bytes()
        argv = [sys.executable, str(Path(__file__).resolve()), str(T.MODULES), str(config_path)]
        result = subprocess.run(argv + [fault, str(read_number)], input=json.dumps(request) + '\n',
                                text=True, capture_output=True, timeout=20)
        assert result.returncode != 0, 'receiver acknowledged an unread event: ' + result.stdout
        assert 'worker_delivery_read_failed' in result.stderr and 'OSError' in result.stderr
        assert not result.stdout.strip(), 'failed handoff printed a successful delivery state'
        assert not (root / 'delivered.json').exists(), 'delivery ran after an entry read failure'
        assert path.exists(), 'read error moved the entry'
        if read_number == 1:
            assert path.read_bytes() == original, 'failed event acceptance changed the old entry'
        else:
            assert json.loads(path.read_text())['request'] == request, 'accepted event was lost'
        assert not list((root / '.parked').glob('*.json')), 'read error quarantined valid content'
        assert not list((root / '.active').glob('*.json')), 'failed handoff acquired execution'
        # A fresh receiver process models Linux resending after its nonzero SSH exit.
        resent = subprocess.run(argv + ['none', '1'], input=json.dumps(request) + '\n',
                                text=True, capture_output=True, timeout=20)
        assert resent.returncode == 0, resent.stderr
        assert json.loads(resent.stdout) == dict(state='retired')
        assert json.loads((root / 'delivered.json').read_text()) == request
        assert not path.exists() and not w.OUT.entries(config), 'resend failed to acknowledge delivery'

    rows = {}
    for state in ('.waiting', '.pending'):
        for fault in ('once', 'persistent'):
            rows['AC3/receiver-' + state[1:] + '-release-eio-' + fault + '-resend'] = (
                lambda base, state=state, fault=fault: handoff(base, state, fault))
    rows['AC3/receiver-event-readback-eio-resend'] = lambda base: handoff(base, '.pending', 'once', 2)
    return rows


if __name__ == '__main__':
    receiver(*sys.argv[1:4], int(sys.argv[4]))
