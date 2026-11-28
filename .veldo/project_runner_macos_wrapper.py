"""Trusted launchd child. Engine output never shares the wrapper's evidence files.

VELDO-0147 AC3: the wrapper reads the engine's two output pipes itself and appends each chunk, as it
reads it, to engine.out or engine.err and, tagged with its stream, to one ordered file
(project_runner_macos_stream). The totals of what the engine printed go into result.json.

The engine runs in its own process group, so a group SIGKILL of the engine leaves
this wrapper alive to reap it and record the outcome. The wrapper enforces the
elapsed deadline itself: a dead or killed supervisor cannot leave the engine, or
any descendant in the job's coalition, unbounded.
"""
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time
import threading

# Script use and library use deliberately share the installed sibling modules.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_runner_macos_os import coalition, coalition_members, identity, wait_file, wait_members
from project_runner_macos_profile import Refused, claude_settings
import project_runner_macos_stream as stream_frames


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, sort_keys=True))
    os.replace(temporary, path)


def read(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return None


def pump(pipes, framed, tally, wake):
    """Copy every chunk of the engine's pipes to its own file and, tagged, to the ordered file, until both
    pipes end or `wake` is written; then take what is already in the pipes and stop. Returns whether every
    chunk read was written: a failed write keeps reading, so the engine never blocks on a full pipe."""
    whole = True
    open_pipes = {source.fileno(): (name, sink) for name, source, sink in pipes}
    last = False
    while open_pipes:
        ready, _, _ = select.select(list(open_pipes) + ([] if last else [wake]), [], [], 0 if last else None)
        if not last and wake in ready:
            last = True
            continue
        if last and not ready:
            break
        for descriptor in ready:
            name, sink = open_pipes[descriptor]
            data = os.read(descriptor, stream_frames.CHUNK)
            if not data:
                del open_pipes[descriptor]
                continue
            tally.feed(name, data)
            try:
                sink.write(data)
                framed.write(stream_frames.chunk(name, data))
            except OSError:
                whole = False
    return whole


def main(path):
    directory = Path(path).resolve()
    request = json.loads((directory / 'request.json').read_text())
    parent = identity(os.getpid())
    if os.getpgrp() != os.getpid():
        raise RuntimeError('launchd_process_group_mismatch')
    write(directory / 'ready.json', dict(process=parent, pgid=os.getpgrp()))
    if not wait_file(directory / 'go', request['startup_seconds']):
        return 125
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

    tally, kept, reader, wake = stream_frames.Tally(), [], None, None
    with open(directory / 'engine.out', 'wb', buffering=0) as out, \
            open(directory / 'engine.err', 'wb', buffering=0) as err, \
            open(directory / stream_frames.FILE, 'wb', buffering=0) as framed:
        child = subprocess.Popen(['/usr/bin/sandbox-exec', '-p', request['sandbox'], *request['argv']],
                                 cwd=request['clone'], env=request['environment'], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, process_group=0)
        pipes = [(name, getattr(child, name, None), sink) for name, sink in (('stdout', out), ('stderr', err))]
        if all(source is not None for _, source, _ in pipes):
            wake = os.pipe()
            reader = threading.Thread(target=lambda: kept.append(pump(pipes, framed, tally, wake[0])), daemon=True)
            reader.start()
        # Keep this unsandboxed wrapper alive until waitpid observes engine exit and
        # the coalition holds no other process, or the backstop has spent its bounds.
        write(directory / 'worker.json', dict(process=identity(child.pid), pgid=os.getpgid(child.pid)))
        finished = threading.Event()
        def reap():
            child.wait()  # Blocking waitpid, with no subprocess timeout polling.
            finished.set()
        threading.Thread(target=reap, daemon=True).start()
        returncode, stage, due = None, None, deadline
        deadline_stop = False
        while True:
            if returncode is None:
                timeout = max(0, due - time.monotonic())
                finished.wait(timeout)
                if finished.is_set():
                    returncode = child.returncode
                    write(directory / 'engine-exit.json', dict(returncode=returncode))
            remaining = others()
            if returncode is not None and remaining == []:
                break
            now = time.monotonic()
            if stage is None and (returncode is not None or now >= deadline):
                deadline_stop = now >= deadline
                stage, due = 'terminate', now + request['kill_grace_seconds']
                signal_all(signal.SIGTERM, remaining)
            elif stage == 'terminate' and now >= due:
                stage, due = 'kill', now + request['settle_seconds']
                signal_all(signal.SIGKILL, remaining)
                killed = set(remaining or ())
            elif stage == 'kill' and now >= due:
                break
            elif stage == 'kill':
                # Each wake of the kill stage SIGKILLs a member first seen since the stage began (one a SIGTERM
                # handler forked between the scan and the group kill), so the wrapper does not settle on it.
                fresh = [pid for pid in remaining or () if pid not in killed]
                for pid in fresh:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
                killed.update(fresh)
            if returncode is not None:
                if remaining is None:
                    raise OSError('coalition_unreadable')
                wait_members(remaining, due - time.monotonic())
        if reader is not None:
            # The engine and its coalition are gone or were given their bounds: take what is in the pipes.
            os.write(wake[1], b'x')
            reader.join()
    result = dict(returncode=returncode, process=parent, dispatch_id=request['dispatch_id'],
                  deadline_stop=deadline_stop, remaining=remaining)
    if kept:
        # What the engine printed, by stream. None when a chunk could not be written: the Mac then signs
        # that it has no totals, and the main node refuses the result (missing_evidence:streams).
        result['streams'] = tally.totals() if kept == [True] else None
    write(directory / 'result.json', result)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
