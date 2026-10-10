"""Trusted launchd child. Engine output never shares the wrapper's evidence files."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

# Script use and library use deliberately share the installed sibling modules.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_runner_macos_os import identity
from project_runner_macos_profile import claude_settings


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, sort_keys=True))
    os.replace(temporary, path)


def main(path):
    directory = Path(path).resolve()
    request = json.loads((directory / 'request.json').read_text())
    parent = identity(os.getpid())
    if os.getpgrp() != os.getpid():
        raise RuntimeError('launchd_process_group_mismatch')
    write(directory / 'ready.json', dict(process=parent, pgid=os.getpgrp()))
    until = time.monotonic() + request['startup_seconds']
    while not (directory / 'go').exists():
        if time.monotonic() >= until:
            return 125
        time.sleep(0.02)
    # Pin checked again at the last trusted boundary before execution.
    with open(request['argv'][0], 'rb') as stream:
        actual = 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != request['binary_digest']:
        return 125
    if request['engine'] == 'claude_code':
        claude_settings(request['argv'], request['clone'], request['environment'], request['login_profile'])
    child = None

    def stop(number, frame):
        if child is not None and child.poll() is None:
            child.terminate()

    signal.signal(signal.SIGTERM, stop)
    with open(directory / 'engine.out', 'wb') as out, open(directory / 'engine.err', 'wb') as err:
        child = subprocess.Popen(['/usr/bin/sandbox-exec', '-p', request['sandbox'], *request['argv']],
                                 cwd=request['clone'], env=request['environment'], stdin=subprocess.DEVNULL,
                                 stdout=out, stderr=err, close_fds=True)
        # Keep this unsandboxed wrapper alive until waitpid observes engine exit.
        # A very short lived child remains a zombie until polled, so ps can identify it.
        write(directory / 'worker.json', dict(process=identity(child.pid), pgid=os.getpgrp()))
        while True:
            write(directory / 'heartbeat.json', dict(monotonic=time.monotonic(), dispatch_id=request['dispatch_id']))
            try:
                result = child.wait(timeout=request['heartbeat_seconds'])
                break
            except subprocess.TimeoutExpired:
                pass
    write(directory / 'result.json', dict(returncode=result, process=parent,
                                          dispatch_id=request['dispatch_id']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
