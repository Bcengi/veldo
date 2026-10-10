"""Trusted launchd child. Engine output never shares the wrapper's evidence files.

The engine runs in its own process group, so a group SIGKILL of the engine leaves
this wrapper alive to reap it and record the outcome. The wrapper enforces the
elapsed deadline itself: a dead or killed supervisor cannot leave the engine, or
any descendant in the job's coalition, unbounded.
"""
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
from project_runner_macos_os import coalition, coalition_members, identity
from project_runner_macos_profile import Refused, claude_settings


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, sort_keys=True))
    os.replace(temporary, path)


def read(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return None


def main(path):
    directory = Path(path).resolve()
    request = json.loads((directory / 'request.json').read_text())
    parent = identity(os.getpid())
    if os.getpgrp() != os.getpid():
        raise RuntimeError('launchd_process_group_mismatch')
    write(directory / 'ready.json', dict(process=parent, pgid=os.getpgrp()))
    until = time.monotonic() + request['startup_seconds']
    go = read(directory / 'go')
    while go is None:
        if time.monotonic() >= until:
            return 125
        time.sleep(0.02)
        go = read(directory / 'go')
    deadline = time.monotonic() + go['runtime_seconds']
    # Pin checked again at the last trusted boundary before execution.
    with open(request['argv'][0], 'rb') as stream:
        actual = 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != request['binary_digest']:
        return 125
    if request['engine'] == 'claude_code':
        try:
            claude_settings(request['argv'], request['clone'], request['environment'], request['login_profile'])
        except Refused as error:
            write(directory / 'refusal.json', {'refusal': error.code})
            return 125
    child = None

    def stop(number, frame):
        if child is not None and child.poll() is None:
            child.terminate()

    signal.signal(signal.SIGTERM, stop)
    job = coalition(os.getpid())

    def others():
        try:
            return [pid for pid in coalition_members(job) if pid != os.getpid()]
        except OSError:
            return None  # unreadable is never empty

    def signal_all(number, pids):
        for target, group in [(child.pid, True)] + [(pid, False) for pid in pids or ()]:
            try:
                (os.killpg if group else os.kill)(target, number)
            except (ProcessLookupError, PermissionError):
                pass

    with open(directory / 'engine.out', 'wb') as out, open(directory / 'engine.err', 'wb') as err:
        child = subprocess.Popen(['/usr/bin/sandbox-exec', '-p', request['sandbox'], *request['argv']],
                                 cwd=request['clone'], env=request['environment'], stdin=subprocess.DEVNULL,
                                 stdout=out, stderr=err, close_fds=True, process_group=0)
        # Keep this unsandboxed wrapper alive until waitpid observes engine exit and
        # the coalition holds no other process, or the backstop has spent its bounds.
        write(directory / 'worker.json', dict(process=identity(child.pid), pgid=os.getpgid(child.pid)))
        returncode, stage, due = None, None, float('inf')
        while True:
            write(directory / 'heartbeat.json', dict(monotonic=time.monotonic(), dispatch_id=request['dispatch_id']))
            if returncode is None:
                try:
                    returncode = child.wait(timeout=request['heartbeat_seconds'])
                    write(directory / 'engine-exit.json', dict(returncode=returncode))
                except subprocess.TimeoutExpired:
                    pass
            else:
                time.sleep(min(request['heartbeat_seconds'], 0.05))
            remaining = others()
            if returncode is not None and remaining == []:
                break
            now = time.monotonic()
            if stage is None and now >= deadline:
                stage, due = 'terminate', now + request['kill_grace_seconds']
                signal_all(signal.SIGTERM, remaining)
            elif stage == 'terminate' and now >= due:
                stage, due = 'kill', now + request['settle_seconds']
                signal_all(signal.SIGKILL, remaining)
            elif stage == 'kill':
                signal_all(signal.SIGKILL, remaining)
                if now >= due:
                    break
    write(directory / 'result.json', dict(returncode=returncode, process=parent, dispatch_id=request['dispatch_id'],
                                          deadline_stop=stage is not None, remaining=remaining))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
