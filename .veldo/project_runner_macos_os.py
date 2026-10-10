"""Apple command boundary for VELDO-0124. Tool errors mean unknown, never empty.

launchctl loads one non restarting LaunchAgent in the user/<uid> bootstrap domain.
That domain exists without a console login and on macOS 26 refuses (EIO) any job
not limited to the Background session type; gui/<uid> takes only Aqua jobs.
ps supplies ordinary process group membership. kqueue NOTE_EXIT observes the held
wrapper before release. Deliberate setsid escapes and PID reuse are Release 2.
"""
import os
from pathlib import Path
import plistlib
import select
import signal
import socket
import subprocess
import sys
import time

ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C', 'TZ': 'UTC'}


def command(argv):
    result = subprocess.run(argv, env=ENV, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=5)
    if result.returncode:
        raise OSError('macos_tool_failed:' + Path(argv[0]).name)
    return result.stdout.strip()


def identity(pid):
    start = command(['/bin/ps', '-o', 'lstart=', '-p', str(pid)])
    if not start:
        raise OSError('process_identity_unreadable')
    return dict(platform='darwin', host=socket.gethostname(), pid=pid, start=start,
                boot_id=command(['/usr/sbin/sysctl', '-n', 'kern.boottime']))


def parse_members(text, pgid):
    members = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 3:
            raise OSError('process_table_unreadable')
        pid, group = int(fields[0]), int(fields[1])
        # Zombies have exited but are not yet reaped. They cannot write clone files.
        if group == pgid and not fields[2].startswith('Z'):
            members.append(pid)
    return members


class Native:
    monotonic = staticmethod(time.monotonic)
    wall = staticmethod(time.time)
    sleep = staticmethod(time.sleep)

    def facts(self):
        return dict(platform=sys.platform, host=socket.gethostname(),
                    os_version=command(['/usr/bin/sw_vers', '-productVersion']) if sys.platform == 'darwin' else '',
                    boot_id=command(['/usr/sbin/sysctl', '-n', 'kern.boottime']) if sys.platform == 'darwin' else '',
                    tools=sys.platform == 'darwin' and hasattr(select, 'kqueue') and all(
                        os.access(p, os.X_OK) for p in ('/bin/launchctl', '/usr/bin/sandbox-exec', '/bin/ps')))

    def bootstrap(self, label, argv, directory, grace):
        path = directory / (label + '.plist')
        data = dict(Label=label, ProgramArguments=argv, RunAtLoad=True, KeepAlive=False,
                    LimitLoadToSessionType='Background',
                    AbandonProcessGroup=False, ExitTimeOut=max(1, int(grace + 0.999)),
                    WorkingDirectory=str(directory), EnvironmentVariables=ENV,
                    StandardOutPath=str(directory / 'wrapper.out'), StandardErrorPath=str(directory / 'wrapper.err'))
        path.write_bytes(plistlib.dumps(data))
        command(['/bin/launchctl', 'bootstrap', 'user/%d' % os.getuid(), str(path)])

    def bootout(self, label):
        command(['/bin/launchctl', 'bootout', 'user/%d/%s' % (os.getuid(), label)])

    def members(self, pgid):
        return parse_members(command(['/bin/ps', '-axo', 'pid=,pgid=,stat=']), pgid)

    def watch(self, process):
        if identity(process['pid']) != process:
            raise OSError('process_identity_changed')
        queue = select.kqueue()
        try:
            queue.control([select.kevent(process['pid'], filter=select.KQ_FILTER_PROC,
                                        flags=select.KQ_EV_ADD | select.KQ_EV_ONESHOT,
                                        fflags=select.KQ_NOTE_EXIT)], 0, 0)
        except BaseException:
            queue.close()
            raise
        return queue

    def exited(self, watch, seconds):
        events = watch.control(None, 1, max(0, seconds))
        if any(e.flags & select.KQ_EV_ERROR for e in events):
            raise OSError('exit_notification_failed')
        return any(e.fflags & select.KQ_NOTE_EXIT for e in events)

    def send(self, pgid, number, *, group=True):
        try:
            (os.killpg if group else os.kill)(pgid, number)
        except ProcessLookupError:
            pass

    def check_clone(self, clone, source):
        for kind in ('commit', 'tree'):
            observed = command(['/usr/bin/git', '-C', clone, 'rev-parse', 'HEAD^{%s}' % kind])
            if observed != source[kind]:
                raise ValueError('binding_mismatch:clone_' + kind)
        if command(['/usr/bin/git', '-C', clone, 'status', '--porcelain', '--untracked-files=all']):
            raise ValueError('binding_mismatch:clone_dirty')
