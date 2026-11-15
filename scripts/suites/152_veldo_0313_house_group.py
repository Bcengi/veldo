"""VELDO-0313, fix round 3: the house's containment group of a wrapped run, read from the kernel.

Run: python3 scripts/selftest.py --suite 152_veldo_0313_house_group

Only shared ROOT and expect are consumed. The one file under test is the CLI, bin/veldo, loaded by
path with its ROOT set to this repository. The suite needs the owner's systemd user manager, which
the gate's confinement does not have, so the gate runs it outside the confinement (the authority's
scripts/gate_unconfined.json names it whole). On a host with no manager every row stands down by
name.

These are the checks of suite 151's row fix3/the-house-group that do not depend on a run's end (the
re-review of VELDO-0313). They need no ledger, so the suite makes none: it drives the run's own
supervisor (the wrapper's _SpaceSupervisor, the real process that starts the command), and reads the
group with the reads the wrapper uses (_SpaceScope.read and _space_judged). No hold is placed and
nothing waits for a run's end, so no other session's process on a shared host decides a row.

Rows. house/scope-named-for-the-run (the command runs in a transient scope of the owner's user
manager, named for the run by control_containment's own rule, in the slice of wrapped runs, and the
supervisor reports that group and the command's own status). house/member-holds-the-run (a process
the command left is listed by the kernel in that group; the wrapper's read of the run says the group
is populated and names every member as a holder; the supervisor said it is asleep on their exit; the
process has not been told to end). house/another-scope-is-unread (a group record that is not the
run's own scope, and no record at all, are a group nobody read). house/group-read-empty-after-exit
(when the suite lets that process end, it ends at its own last line, and the group is then read
empty).

The supervisor is a process of the fixture's own start. On a host shared with other sessions it may
stay asleep after its group is empty, on a process it cannot read (fail closed, as decided): the
suite ends it when the rows are done. Nothing of the wrapper ever ends a process.
"""


def _v313_house_group_suite():
    import importlib.machinery
    import importlib.util
    import json
    import os
    import select
    import shutil
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'veldo': ROOT / "bin" / "veldo",
    }

    def load_cli(name, path):
        loader = importlib.machinery.SourceFileLoader(name, str(path))
        spec = importlib.util.spec_from_loader(name, loader)
        module = importlib.util.module_from_spec(spec)
        before = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = before
        return module

    ROWS = ('house/scope-named-for-the-run', 'house/member-holds-the-run', 'house/another-scope-is-unread',
            'house/group-read-empty-after-exit')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def text_of(path):
        try:
            return Path(path).read_text()
        except OSError:
            return None

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0313-house-')))
    started = []  # the fixture's own processes, ended when the suite ends
    row = ROWS[0]
    try:
        CLI = load_cli('v313_house_veldo_cli', PRODUCTION['veldo'])
        CLI.ROOT = ROOT  # the modules the CLI loads are this repository's .veldo
        house = CLI._SpaceScope(dict(os.environ))
        words = house.words('probe:' + temp.name)
        able = bool(words) and subprocess.run(
            [word.replace('veldo-dispatch-', 'veldo-probe-') for word in words] + ['true'],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=60).returncode == 0
        if not able:
            for row in ROWS:
                check(row, 'this host gives the suite no user manager to make a scope with: the row stands down',
                      True)
        else:
            LINGER = 10.0  # the longest the process the command leaves lives with no word from the suite
            RUN = 'house:' + temp.name
            scratch, seen, late, latch = temp / 'scratch', temp / 'seen.txt', temp / 'late.json', temp / 'latch'
            scratch.mkdir()
            # The command ends at once with 5. It leaves a process that left its session and its
            # parent and closed its own input and output, and that lives until the suite makes the
            # latch; at its last line it says what it sees.
            script = ('import json, os, sys, time\n'
                      'open(%r, "w").write(open("/proc/self/cgroup").read())\n'
                      'if os.fork():\n'
                      '    os._exit(5)\n'
                      'os.setsid()\n'
                      'if os.fork():\n'
                      '    os._exit(0)\n'
                      'for stream in (0, 1, 2):\n'
                      '    os.close(stream)\n'
                      'until = time.monotonic() + %r\n'
                      'while not os.path.exists(%r) and time.monotonic() < until:\n'
                      '    time.sleep(0.02)\n'
                      'json.dump({"released": os.path.exists(%r), "label": os.environ.get("VELDO_SPACE_LABEL")},\n'
                      '          open(%r, "w"))\n' % (str(seen), LINGER, str(latch), str(latch), str(late)))
            environ = {key: value for key, value in os.environ.items()
                       if key not in ('VELDO_SPACE_LABEL', 'COMPOSE_PROJECT_NAME')}
            environ['XDG_RUNTIME_DIR'] = house.environment['XDG_RUNTIME_DIR']
            supervisor = CLI._SpaceSupervisor([sys.executable, '-c', script], environ, str(temp))
            process = supervisor.start()
            started.append(supervisor.child)
            given = {'run': RUN, 'environment': {CLI.SPACE_LABEL_VARIABLE: RUN, 'TMPDIR': str(scratch)},
                     'supervisor': process, 'group': None}
            supervisor.go(given, house)
            status, holders, group = supervisor.result()
            given.update(status=status, group=group)
            shown = (text_of(seen) or '').strip()
            unit = house.house.unit_name(RUN)

            row = 'house/scope-named-for-the-run'
            check(row, 'the command ran in a scope of the owner\'s user manager named for the run by the house\'s own '
                       'rule, in the slice of wrapped runs, and the supervisor reports that group and the command\'s '
                       'own status [%s %s %s]' % (status, shown, group),
                  status == 5 and shown.endswith('/' + CLI.SPACE_SLICE + '/' + unit)
                  and (group or {}).get('cgroup') == shown[3:] and (group or {}).get('unit') == unit)

            row = 'house/member-holds-the-run'
            read = house.read(RUN, group)
            judged = CLI._space_judged({}, given, environ)
            named = {one.get('pid') for one in judged.get('holders') or ()}
            check(row, 'the process the command left is a member of that group as the kernel lists it [%s]' % (read,),
                  read.get('read') is True and read.get('populated') is True and bool(read.get('pids'))
                  and all(CLI._space_process(pid) is not None for pid in read['pids']))
            check(row, 'the wrapper\'s read of the run says the group is populated and names every member as a '
                       'holder, as the supervisor did when the command exited [%s %s %s]'
                  % (judged.get('group'), sorted(named, key=str), holders),
                  judged.get('group') == 'populated' and bool(read.get('pids')) and set(read['pids']) <= named
                  and set(read['pids']) <= {one.get('pid') for one in holders or ()})
            check(row, 'the supervisor said it is asleep on their exit, and the process has not been told to end '
                       '[%s]' % (supervisor.staying,),
                  supervisor.staying is True and not late.exists() and not latch.exists()
                  and CLI._space_process(process['pid']) is not None)

            row = 'house/another-scope-is-unread'
            check(row, 'a group record that is not the run\'s own scope is a group nobody read, and so is no record '
                       '[%s %s]' % (house.read('another:run', group), house.read(RUN, None)),
                  house.read('another:run', group) == {'read': False, 'populated': None, 'pids': []}
                  and house.read(RUN, None)['read'] is False
                  and CLI._space_judged({}, dict(given, group=None), environ) == {'group': 'unread', 'holders': []})

            row = 'house/group-read-empty-after-exit'
            members = list(read.get('pids') or ())
            watched = []
            for pid in members:
                try:
                    watched.append(os.pidfd_open(pid))
                except OSError:
                    pass
            latch.write_text('')
            try:
                for descriptor in watched:
                    watch = select.poll()
                    watch.register(descriptor, select.POLLIN)
                    watch.poll(int(LINGER * 3000))
            finally:
                for descriptor in watched:
                    os.close(descriptor)
            after = house.read(RUN, group)
            said = json.loads(text_of(late) or '{}')
            check(row, 'the process ended on the suite\'s word, at its own last line, carrying the run\'s label [%s]'
                  % (said,), said == {'released': True, 'label': RUN} and len(watched) == len(members) > 0)
            check(row, 'and the group is then read empty [%s]' % (after,),
                  after == {'read': True, 'populated': False, 'pids': []})
    except Exception as error:
        import traceback
        check(row, 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + ' | '.join(line.strip() for line in traceback.format_exc().splitlines()[-4:])[:400], False)
    finally:
        for child in started:
            try:
                child.wait(timeout=5)
            except Exception:  # noqa: BLE001 - held by a process of another session: the fixture's own, ended here
                try:
                    child.kill()
                    child.wait(timeout=30)
                except Exception:  # noqa: BLE001
                    pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0313 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v313_house_group_suite()
