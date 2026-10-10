#!/usr/bin/env python3
"""Owner-run real SSH/Mac probe, from the Linux checkout. Never called by a suite.

Argument: this Linux account's SSH alias as reachable FROM dmitrys-mac-mini.
Creates disposable state, exports only tracked code, supervises one ordinary
Linux authority at a time and retains evidence under the caller's private temp.
No deployed service, provider login, live capture, branch or worktree is changed.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
import native_authority as A

MAC = 'dmitrys-mac-mini'
PINNED = '/opt/homebrew/bin/python3.12'


def main(linux_alias, fixed_socket, transport_key):
    if not linux_alias or linux_alias.startswith('-'):
        raise ValueError('a configured Linux SSH alias is required')
    root = Path(tempfile.mkdtemp(prefix='v125-native-'))
    export = 'veldo-0125-check-' + uuid.uuid4().hex[:12]
    remote = '"$HOME"/' + export
    ssh = ['ssh', '-T', '-o', 'BatchMode=yes', MAC]
    def mac(command, data=None, timeout=90):
        result = subprocess.run(ssh + [command], input=data, capture_output=True, timeout=timeout)
        if result.returncode:
            (root / 'remote-error.log').write_bytes(result.stdout + result.stderr)
            raise RuntimeError('native remote command failed; see ' + str(root / 'remote-error.log'))
        return result.stdout
    archive = root / 'code.tar'
    with archive.open('wb') as out:
        subprocess.run(['git', 'archive', 'HEAD', '.veldo', 'proof/VELDO-0124', 'proof/VELDO-0125'],
                       cwd=A.T.ROOT, stdout=out, stderr=subprocess.PIPE, check=True, timeout=30)
    mac('mkdir ' + remote + ' && tar -xf - -C ' + remote, archive.read_bytes())
    reports = []
    for engine in ('claude_code', 'codex'):
        prefix = 'cd ' + remote + ' && ' + PINNED + ' proof/VELDO-0125/native_checks.py '
        (root / (engine + '-prepare.log')).write_bytes(mac(prefix + 'prepare ' + engine))
        candidate = root / (engine + '-candidate.json')
        candidate.write_bytes(mac('cat ' + remote + '/runs-0125/' + engine + '/candidate.json'))
        directory = root / engine
        A.setup(str(candidate), str(directory), linux_alias, fixed_socket, transport_key)
        (root / (engine + '-client-transfer.log')).write_bytes(mac(
            'cat > ' + remote + '/client-' + engine + '.json', (directory / 'client.json').read_bytes()))
        log = (directory / 'service.log').open('wb')
        child = subprocess.Popen([sys.executable, str(A.T.MODULES / 'control_worker_service.py'),
                                   str(directory / 'config.json')], stdout=log, stderr=log)
        try:
            until = time.monotonic() + 15
            while not Path(fixed_socket).exists() and time.monotonic() < until:
                if child.poll() is not None:
                    raise RuntimeError('authority failed; see ' + str(directory / 'service.log'))
                time.sleep(.02)
            if not Path(fixed_socket).exists():
                raise RuntimeError('authority socket unavailable')
            (root / (engine + '-run.log')).write_bytes(mac(prefix + 'run ' + engine + ' client-' + engine + '.json'))
            result = root / (engine + '-result.json')
            result.write_bytes(mac('cat ' + remote + '/runs-0125/' + engine + '/result.json'))
            reports.append(A.compare(str(directory), str(result)))
            child.terminate()
            child.wait(timeout=15)
            stopped = mac(prefix + 'unavailable ' + engine + ' client-' + engine + '.json')
            (root / (engine + '-unavailable.json')).write_bytes(stopped)
            reports.append(json.loads(stopped))
        finally:
            child.terminate()
            child.wait(timeout=15)
            log.close()
    summary = dict(status='observed', rows=reports, evidence=str(root), mac_export=export,
                   scope='synthetic engines only; no qualification or activation')
    (root / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main(*sys.argv[1:])
