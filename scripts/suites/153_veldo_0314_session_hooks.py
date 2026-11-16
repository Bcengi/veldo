"""VELDO-0314: session hooks, durable notifications, and no synchronous removal.

Real store, ledger, observer signatures, socket, hook processes and kernel process identity.
The event receiver alone is a stand-in for VELDO-0323; the unmodified ledger refusal is tested too.
Only ROOT and expect are shared. All output, keys, databases and planted files are fixture-owned.
"""


def _v314_suite():
    import importlib.machinery
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import select
    import shutil
    import socket
    import subprocess
    import sys
    import tempfile
    import time

    PRODUCTION = {
        'control_space_spool.py': ROOT / ".veldo" / "control_space_spool.py",
        'veldo': ROOT / "bin" / "veldo",
        'space-session.py': ROOT / "packs/claude/scripts" / "space-session.py",
    }
    rows = {}

    def check(row, message, good):
        rows.setdefault(row, []).append((message, bool(good)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    temp = Path(tempfile.mkdtemp(prefix='veldo-0314-')).resolve()
    conn = listener = None
    children = []
    try:
        mods = temp / '.veldo'
        shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(PRODUCTION['control_space_spool.py'], mods / 'control_space_spool.py')
        (temp / 'bin').mkdir()
        shutil.copyfile(PRODUCTION['veldo'], temp / 'bin/veldo')
        hook = temp / 'space-session.py'
        shutil.copyfile(PRODUCTION['space-session.py'], hook)
        spool = load('v314_spool', mods / 'control_space_spool.py')
        SP = spool._sibling('control_space')
        S = spool._sibling('control_store')
        CM = spool._sibling('control_membership')
        K = spool._sibling('control_space_kinds')
        AC = CM.AC
        CM.attach(S)
        state, scratch, installation = (temp / name for name in ('state', 'scratch', 'installation'))
        for path in (state, scratch, installation, installation / 'keys', temp / 'project', temp / 'plain',
                     temp / 'outside', temp / 'trees', temp / 'plain-trees'):
            path.mkdir(mode=0o700)
        keys = {}
        for who in ('owner', SP.OBSERVER):
            key = installation / 'keys' / who
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                           check=True, capture_output=True, timeout=10)
            keys[who] = (key, Path(str(key) + '.pub').read_text().strip())

        def sign_as(who, data):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys[who][0]), '-n',
                                   AC.SIGNATURE_NAMESPACE], input=data, capture_output=True,
                                  check=True, timeout=10).stdout.decode()

        conn = S.open_store(str(temp / 'control.sqlite3'))
        ids = {'domain_uuid': 'd314', 'repository_uuid': 'r314', 'store_uuid': 's314'}
        for index, who in enumerate(('owner', SP.OBSERVER)):
            params = {'principal': who, 'principal_type': 'person' if who == 'owner' else 'service',
                      'roles': ['membership_steward', 'project_owner'] if who == 'owner' else [],
                      'public_key': keys[who][1], 'independence_group': who,
                      'scope': '*' if who == 'owner' else [SP.SCOPE]}
            command = {'command_id': 'setup%d' % index, 'operation': 'enroll_principal', 'target': 'authority',
                       'parameters': params, 'artifact_digests': [], 'expected_versions': {}}
            now = CM.authority_state(S, conn)
            envelope = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal='owner',
                            request_revision=1, nonce='setup%d' % index, expires_at=1600,
                            membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                            command_digest=AC.canonical_command_digest(command))
            cosigned = None if who == 'owner' else sign_as(who, AC.canonical_envelope_bytes(dict(envelope, principal=who)))
            answer = CM.admit(S, conn, envelope, command, sign_as('owner', AC.canonical_envelope_bytes(envelope)),
                              ids, 1000, enrollee_signature=cosigned, journal_signer=('authority', lambda data: 'fixture'))
        config = {'present': True, 'enabled': True, 'engines': [], 'build_roots': [],
                  'scratch_roots': {'roots': [str(scratch)], 'session_pattern': 'sessions/{working_folder}/{session_id}'},
                  'plain_repositories': [{'repository': str(temp / 'plain'), 'worktree_root': str(temp / 'plain-trees')}],
                  'protect': [], 'pools': {'host': {'floor': 0, 'needs': {}}}}
        project = {'project': 'fixture-project', 'repository': str(temp / 'project'),
                   'worktree_root': str(temp / 'trees')}
        ledger = SP.Ledger(S, conn, 'authority', lambda data: 'fixture', config=config,
                           projects=[project], state_root=str(state), lifecycle=K.LIFECYCLE,
                           host=socket.gethostname(), device=lambda path: 'fixture-device')
        ledger.set_pool('host', 'filesystem', device='fixture-device')
        events, seen, operations = [], {}, []
        event_enabled = [True]

        class Authority(spool.Local):
            def accept(self, packet):
                command = packet['command']
                operations.append(command['operation'])
                if command['operation'] == SP.EVENT and not event_enabled[0]:
                    # A Ledger whose event command is not installed: the notification waits.
                    return {'ok': False, 'reason': 'space_no_command:' + SP.EVENT}
                if command['operation'] == SP.EVENT:
                    good = AC.ssh_keygen_verify(S.canonical_bytes(command), packet['signature'],
                            AC.allowed_signers_line(SP.OBSERVER, keys[SP.OBSERVER][1], SP.NAMESPACE),
                            SP.OBSERVER, SP.NAMESPACE)[0]
                    if not good or command['principal'] != SP.OBSERVER:
                        return {'ok': False, 'reason': 'not_authorized'}
                    if command['command_id'] not in seen:
                        events.append(command['parameters'])
                        seen[command['command_id']] = {'ok': True, 'event': 'event%d' % len(events)}
                    return seen[command['command_id']]
                return super().accept(packet)

        authority = Authority(ledger, CM)
        sign = spool.signer(str(installation))
        folder = spool.spool_folder(str(state))
        listener = spool.listen(folder)
        env = dict(os.environ, VELDO_INSTALLATION=str(installation), VELDO_SPACE_CLI=str(temp / 'bin/veldo'),
                   VELDO_SPACE_STATE_ROOT=str(state), PYTHONDONTWRITEBYTECODE='1')
        pid = os.getpid()
        started = int(Path('/proc/%d/stat' % pid).read_bytes().rsplit(b')', 1)[1].split()[19])

        def one(kind, session, where):
            return spool.session_entry(kind, session, str(where), pid, started, socket.gethostname())

        def call_hook(kind, session, where, serve=True, environ=None, payload=None):
            process = subprocess.Popen([sys.executable, str(hook), kind], env=environ or env,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            children.append(process)
            process.stdin.write(json.dumps({'session_id': session, 'cwd': str(where)}
                                           if payload is None else payload).encode())
            process.stdin.close()
            began = time.monotonic()
            while process.poll() is None and time.monotonic() - began < 15:
                if serve and select.select([listener], [], [], 0.02)[0]:
                    spool.serve_one(listener, authority)
                elif not serve:
                    time.sleep(0.02)
            return process.poll(), time.monotonic() - began

        def items(session):
            return [(identity, record) for identity, record in ledger.items().items()
                    if record['owner'].get('session') == session]

        for session, where, scope in (
                ('never-ends', temp / 'project', {'type': 'project', 'id': 'fixture-project'}),
                ('plain', temp / 'plain', {'type': 'plain_repository', 'id': str(temp / 'plain')}),
                ('no-project', temp / 'outside', {'type': 'no_project'})):
            row = 'ac2/no-project' if session == 'no-project' else 'ac1/start-owns-scratch'
            status, elapsed = call_hook('SessionStart', session, where)
            records = items(session)
            event = [event for event in events if event['subject'].get('session') == session]
            check(row, 'start returns and declares before any end: ' + str((status, records)),
                  status == 0 and elapsed < 15 and len(records) == 1)
            check(row, 'one event with client identity and correct ownership',
                  len(records) == 1 and records[0][1]['owner'] == {'scope': scope, 'session': session}
                  and records[0][1]['process'] == {'pid': pid, 'started': started}
                  and len(event) == 1 and event[0]['type'] == 'session_started'
                  and event[0]['subject'] == one('session_started', session, where)['subject'])
            if records:
                check(row, 'declaration precedes creation', not Path(records[0][1]['locator']['path']).exists())
        # Fix round, finding 2: the client's folder is resolved first, and what is still no entry is
        # written under refused/ with why. Real hook processes against the served socket.
        (temp / 'cwd-link').symlink_to(temp / 'outside', target_is_directory=True)
        for session, where in (('through-link', str(temp / 'cwd-link')),
                               ('trailing-slash', str(temp / 'outside') + '/'),
                               ('dot-segment', str(temp / 'project' / '..' / 'outside'))):
            status, elapsed = call_hook('SessionStart', session, where)
            event = [event for event in events if event['subject'].get('session') == session]
            check('fix2/folder-resolved', '%s: one item and one event for the folder it leads to: %s'
                  % (session, (status, items(session), event)),
                  status == 0 and len(items(session)) == 1 and len(event) == 1
                  and event[0]['subject'] == one('session_started', session, temp / 'outside')['subject']
                  and items(session)[0][1]['owner'] == {'scope': {'type': 'no_project'}, 'session': session})
        check('fix2/folder-resolved', 'nothing was refused and nothing waits',
              not spool.refused(folder) and not spool.pending(folder))
        for payload, word in (({'session_id': 'bad/name', 'cwd': str(temp / 'outside')}, 'path component'),
                              ({'session_id': 'no-folder'}, 'cwd'),
                              ({'session_id': 'relative-folder', 'cwd': 'outside'}, 'absolute')):
            before = spool.refused(folder)
            status, elapsed = call_hook('SessionStart', None, None, payload=payload)
            new = [name for name in spool.refused(folder) if name not in before]
            kept = [json.loads((Path(folder) / spool.REFUSED / name).read_text()) for name in new]
            check('fix2/invalid-refused', '%s: the notification is under refused/ with why: %s'
                  % (payload['session_id'], (status, kept)),
                  status == 0 and len(kept) == 1 and kept[0]['notification']['payload'] == payload
                  and kept[0]['notification']['type'] == 'session_started'
                  and kept[0]['notification']['pid'] == pid
                  and kept[0]['refused']['reason'].startswith('space_session_invalid:')
                  and word in kept[0]['refused']['reason'] and not spool.pending(folder)
                  and not items(payload['session_id']))

        # Fix round, finding 3: no state root is the CLI's fallback; a refused spool folder is noted and
        # the entry is spooled under the fallback; with no spool and with no module one line is left.
        def without(*names, **more):
            return dict({name: value for name, value in env.items() if name not in names}, **more)

        def spooled(root):
            where = spool.spool_folder(str(root))
            return [spool.read(where, name)['subject'].get('session') for name in spool.pending(where)]

        def lines(root):
            path = Path(root) / spool.UNSPOOLED
            return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

        status, elapsed = call_hook('SessionStart', 'no-root-xdg', temp / 'outside', serve=False,
                                    environ=without('VELDO_SPACE_STATE_ROOT', XDG_STATE_HOME=str(temp / 'xdg')))
        check('fix3/no-state-root', 'spooled under XDG_STATE_HOME/veldo: ' + str((status, spooled(temp / 'xdg/veldo'))),
              status == 0 and spooled(temp / 'xdg/veldo') == ['no-root-xdg'])
        status, elapsed = call_hook('SessionEnd', 'no-root-home', temp / 'outside', serve=False,
                                    environ=without('VELDO_SPACE_STATE_ROOT', 'XDG_STATE_HOME', HOME=str(temp / 'home')))
        check('fix3/no-state-root', 'spooled under ~/.local/state/veldo: '
              + str((status, spooled(temp / 'home/.local/state/veldo'))),
              status == 0 and spooled(temp / 'home/.local/state/veldo') == ['no-root-home'])
        unsafe = temp / 'unsafe-state'
        (unsafe / spool.SPOOL).mkdir(parents=True, mode=0o700)
        (unsafe / spool.SPOOL).chmod(0o770)
        there = without(VELDO_SPACE_STATE_ROOT=str(unsafe), XDG_STATE_HOME=str(temp / 'xdg-unsafe'))
        status, elapsed = call_hook('SessionStart', 'unsafe-folder', temp / 'outside', serve=False, environ=there)
        noted = unsafe / spool.FOLDER_REFUSED
        check('fix3/unsafe-folder', 'the refused folder is noted beside it and nothing is written into it: '
              + str((status, noted.exists(), os.listdir(unsafe / spool.SPOOL))),
              status == 0 and noted.exists() and 'writable by group or others' in json.loads(noted.read_text())['refused']
              and os.listdir(unsafe / spool.SPOOL) == [])
        check('fix3/unsafe-folder', 'the entry is spooled under the fallback: ' + str(spooled(temp / 'xdg-unsafe/veldo')),
              spooled(temp / 'xdg-unsafe/veldo') == ['unsafe-folder'] and not lines(unsafe))
        # The fallback's spool folder is made here when no entry made it, so the row that follows runs.
        (temp / 'xdg-unsafe/veldo' / spool.SPOOL).mkdir(parents=True, mode=0o700, exist_ok=True)
        (temp / 'xdg-unsafe/veldo' / spool.SPOOL).chmod(0o770)
        status, elapsed = call_hook('SessionEnd', 'no-spool', temp / 'outside', serve=False, environ=there)
        left = lines(unsafe)
        check('fix3/no-spool-last-record', 'both spool folders refused: one line under the state root: '
              + str((status, left)),
              status == 0 and len(left) == 1 and left[0]['type'] == 'session_ended'
              and left[0]['payload'] == {'session_id': 'no-spool', 'cwd': str(temp / 'outside')}
              and left[0]['pid'] == pid
              and 'writable by group or others' in left[0]['reason']
              and (temp / 'xdg-unsafe/veldo' / spool.FOLDER_REFUSED).exists())
        (temp / 'xdg-unsafe/veldo' / spool.SPOOL).chmod(0o700)
        nowhere = temp / 'state-no-module'
        status, elapsed = call_hook('SessionStart', 'no-module', temp / 'outside', serve=False,
                                    environ=without(VELDO_SPACE_STATE_ROOT=str(nowhere),
                                                    VELDO_SPACE_CLI=str(temp / 'nowhere/bin/veldo')))
        left = lines(nowhere)
        check('fix3/no-module-last-record', 'the module cannot be loaded: one line with the input: '
              + str((status, left)),
              status == 0 and len(left) == 1 and left[0]['hook'] == ['SessionStart'] and left[0]['pid'] == pid
              and json.loads(left[0]['input']) == {'session_id': 'no-module', 'cwd': str(temp / 'outside')}
              and left[0]['reason'])
        status, elapsed = call_hook('SessionStart', None, None, serve=False, payload=['no', 'notification'],
                                    environ=without(VELDO_SPACE_STATE_ROOT=str(nowhere)))
        check('fix3/no-module-last-record', 'an input that is no notification is refused with why, not dropped',
              status == 0 and len(spool.refused(spool.spool_folder(str(nowhere)))) == 1)

        for kind in SP.KINDS:
            if kind != 'scratch':
                try:
                    SP.checked_owner({'scope': {'type': 'no_project'}, 'session': 's'}, kind)
                    good = False
                except SP.Refused:
                    good = True
                check('ac2/ledger-owner-rule', kind, good)
        try:
            SP.checked_owner({'scope': {'type': 'no_project'}}, 'scratch')
            good = False
        except SP.Refused:
            good = True
        check('ac2/ledger-owner-rule', 'scratch requires session', good)
        for kind, owner in (('evidence', {'scope': {'type': 'no_project'}, 'session': 's'}),
                            ('scratch', {'scope': {'type': 'no_project'}})):
            refused = ledger.declare(kind, {'path': str(scratch / ('bad-' + kind))}, owner, 'hook')
            check('ac2/ledger-owner-rule', 'real declare refuses ' + kind, not refused['ok'])

        # A fixture child runs the same hook with every remover held. Only this fixture can open it.
        if not items('never-ends'):
            declaration = authority.session(one('session_started', 'never-ends', temp / 'project')['subject'])['declare']
            ledger.declare(**declaration)
        record = items('never-ends')[0][1]
        planted = Path(record['locator']['path'])
        planted.mkdir(parents=True)
        (planted / 'only-copy').write_bytes(b'work that must stay')
        client_work = temp / 'project' / 'only-copy-client'
        client_work.write_bytes(b'client work that must stay')
        # The latch is two files in the suite's own temporary folder (no semaphore: the gate's confined
        # leg grants no /dev/shm). `reached` is written by a remover that was called; `latch` opens it.
        latch, reached = temp / 'latch-open', temp / 'latch-reached'
        removers = spool._sibling('control_space_remove')
        def held(*args, **kwargs):
            reached.write_bytes(b'')
            until = time.monotonic() + 30
            while not latch.exists() and time.monotonic() < until:
                time.sleep(0.02)
        for name in list(vars(removers)):
            if name == 'remove' or name.startswith('_r_') or name in ('tool', 'drop_caches'):
                setattr(removers, name, held)
        def ending():
            # A bypass of the registered removers is held too, in this child alone. The falsifier
            # deletes the client's folder directly; without this latch its planted work is lost.
            shutil.rmtree = held
            os._exit(spool.session_hook('session_ended', {'session_id': 'never-ends', 'cwd': str(temp / 'project')},
                                       str(state), str(installation), pid=pid))
        child = os.fork()
        if child == 0:
            try:
                ending()
            finally:
                os._exit(70)
        began, exited = time.monotonic(), None
        while exited is None and time.monotonic() - began < 15:
            if select.select([listener], [], [], 0.02)[0]:
                spool.serve_one(listener, authority)
            done, status = os.waitpid(child, os.WNOHANG)
            if done:
                exited = os.waitstatus_to_exitcode(status)
        timely = exited is not None
        intact = ((planted / 'only-copy').read_bytes() == b'work that must stay'
                  and client_work.read_bytes() == b'client work that must stay')
        check('ac3/end-returns-with-removers-held', 'bounded return, no remover, file intact',
              timely and exited == 0 and not reached.exists() and intact)
        latch.write_bytes(b'')
        if exited is None:
            os.waitpid(child, 0)
        check('ac3/end-event-once', 'one end, no signal and no item change',
              len([e for e in events if e['type'] == 'session_ended']) == 1
              and SP.SIGNAL not in operations and ledger.item(items('never-ends')[0][0]) == record)
        before = len(events)
        same = one('session_ended', 'never-ends', temp / 'project')
        spool.deliver([same, same], folder, authority, sign)
        check('ac3/end-event-once', 'duplicate notifications write no second event', len(events) == before)

        listener.close()
        listener = None
        os.unlink(spool.socket_path(folder))
        status, elapsed = call_hook('SessionStart', 'offline', temp / 'outside', serve=False)
        pending = [spool.read(folder, name) for name in spool.pending(folder)]
        check('ac4/down-starts-and-spools', 'client success and durable notification',
              status == 0 and elapsed < 15 and any(p['subject'].get('session') == 'offline' for p in pending))
        status, elapsed = call_hook('SessionEnd', 'offline', temp / 'outside', serve=False)
        pending = [spool.read(folder, name) for name in spool.pending(folder)]
        check('ac4/down-starts-and-spools', 'ending also succeeds and stays behind its start',
              status == 0 and elapsed < 15 and [p['type'] for p in pending
              if p['subject'].get('session') == 'offline'] == ['session_started', 'session_ended'])
        spool.start(folder, authority, sign)
        check('ac4/replay', 'offline start records its scratch and event on replay',
              len(items('offline')) == 1 and any(e['subject'].get('session') == 'offline' for e in events))
        class Broken(Authority):
            def session(self, subject):
                raise RuntimeError('fixture authority failed')
        failed = one('session_started', 'failure', temp / 'outside')
        result = spool.submit(failed, str(state), str(installation), Broken(ledger, CM), sign)
        check('ac4/failure-retained', 'exception leaves whole file', result['pending']
              and spool.read(folder, result['spooled'])['subject'] == failed['subject'])
        spool.start(folder, authority, sign)
        event_enabled[0] = False
        waiting = one('session_started', 'unbuilt', temp / 'outside')
        spool.submit(waiting, str(state), str(installation), authority, sign)
        check('ac4/unbuilt-event-waits', 'a Ledger with no event command: item exists and notification waits',
              len(items('unbuilt')) == 1 and len(spool.pending(folder)) == 1
              and spool.read(folder, spool.pending(folder)[0])['tries'] == 1)
        event_enabled[0] = True
        spool.start(folder, authority, sign)
        check('ac4/unbuilt-event-waits', 'event delivered after command becomes available',
              not spool.pending(folder) and len(items('unbuilt')) == 1)
        missing_key = installation / 'keys' / SP.OBSERVER
        moved_key = installation / 'keys' / 'temporarily-away'
        missing_key.rename(moved_key)
        try:
            result = spool.submit(one('session_started', 'no-key', temp / 'outside'),
                                  str(state), str(installation), authority, sign)
            check('ac4/failure-retained', 'missing signing key leaves event durable',
                  result['pending'] and not items('no-key'))
        finally:
            moved_key.rename(missing_key)
        spool.start(folder, authority, sign)
        check('ac4/failure-retained', 'key restored and same entry delivered', len(items('no-key')) == 1)

        # Existing work can never become disposable scratch, even on a delayed replay.
        existing = one('session_started', 'existing', temp / 'outside')
        declaration = authority.session(existing['subject'])['declare']
        work = Path(declaration['locator']['path'])
        work.mkdir(parents=True)
        (work / 'draft').write_text('only copy')
        result = spool.send(existing, authority, sign)
        check('safety/existing-folder-refused', 'unrecorded work kept, no scratch item',
              result['reason'] == 'space_session_exists' and not items('existing')
              and (work / 'draft').read_text() == 'only copy')
        for bad in ('../escape', '/absolute', '..', 'bad/name'):
            try:
                one('session_started', bad, temp / 'outside')
                good = False
            except spool.Malformed:
                good = True
            check('safety/locators', 'session ' + bad, good)
        link = temp / 'linked'
        link.symlink_to(temp / 'outside', target_is_directory=True)
        for bad in (str(link), str(temp / 'outside') + '/../project'):
            try:
                one('session_started', 's', bad)
                good = False
            except spool.Malformed:
                good = True
            check('safety/locators', 'working folder ' + bad, good)
        declaration = authority.session(one('session_started', 'signature', temp / 'outside')['subject'])['declare']
        packet = sign(SP.DECLARE, declaration, 'signature-test', 'signature-test')
        packet['signature'] = 'invalid'
        check('safety/ledger-verifies', 'invalid signature cannot declare',
              not authority.accept(packet)['ok'] and not items('signature'))
        expired = SP.signed(SP.OBSERVER, SP.DECLARE, declaration, str(installation), S.canonical_bytes,
                            time.time() - SP.PACKET_AGE - 10)
        check('safety/ledger-verifies', 'expired packet cannot declare',
              not authority.accept(expired)['ok'] and not items('signature'))

        # A real CLI process with no authority uses the same durable spool, including creator evidence.
        cli_state = temp / 'cli-state'
        cli_env = dict(env, VELDO_SPACE_STATE_ROOT=str(cli_state))
        done = subprocess.run([sys.executable, str(temp / 'bin/veldo'), 'space', 'event', '--type', 'released',
                               '--path', str(planted)], env=cli_env, capture_output=True, timeout=15)
        entries = [spool.read(spool.spool_folder(str(cli_state)), name)
                   for name in spool.pending(spool.spool_folder(str(cli_state)))]
        check('ac4/cli-spools', 'released retained with the Ledger\'s subject, the paths alone',
              done.returncode == 0 and len(entries) == 1 and entries[0]['subject'] == {'paths': [str(planted)]}
              and entries[0]['emitter']['hook'] == 'event')
        done = subprocess.run([sys.executable, str(temp / 'bin/veldo'), 'space', 'event', '--type', 'session_ended',
                               '--session', 'cli-session', '--working-folder', str(temp / 'outside'),
                               '--pid', str(pid), '--started', str(started)],
                              env=cli_env, capture_output=True, timeout=15)
        entries = [spool.read(spool.spool_folder(str(cli_state)), name)
                   for name in spool.pending(spool.spool_folder(str(cli_state)))]
        # The verb takes released alone (design 6.9, the lead's decision at assembly): a session event
        # is the client hook's, which spools it itself, and the verb refuses it by name and spools nothing.
        check('ac4/cli-spools', 'a session event is refused by name and nothing more is spooled: '
              + str((done.returncode, done.stderr.decode())),
              done.returncode == 1 and len(entries) == 1 and entries[0]['type'] == 'released'
              and done.stderr.decode().strip() == 'veldo space event: refused space_event_hook_only:session_ended'
              and not spool.refused(spool.spool_folder(str(cli_state))))

        # Fix round, finding 5: the CLI resolves what it is given. With no ledger: a relative path and a
        # path through a link. A hook's type is refused by name, never recorded in part.
        loose = temp / 'cli-state-loose'
        loose_folder = spool.spool_folder(str(loose))
        done = subprocess.run([sys.executable, str(temp / 'bin/veldo'), 'space', 'event', '--type', 'released',
                               '--path', 'outside/given-up', '--path', str(link / 'linked-given-up'),
                               '--path', str(planted) + '/', '--state-root', str(loose)],
                              env=env, cwd=str(temp), capture_output=True, timeout=15)
        entries = [spool.read(loose_folder, name) for name in spool.pending(loose_folder)]
        check('fix5/cli-resolves', 'released paths are resolved, not refused: '
              + str((done.returncode, done.stderr.decode(), [e['subject'] for e in entries])),
              done.returncode == 0 and len(entries) == 1 and entries[0]['subject'] == {
                  'paths': [str(temp / 'outside/given-up'), str(temp / 'outside/linked-given-up'), str(planted)]})
        done = subprocess.run([sys.executable, str(temp / 'bin/veldo'), 'space', 'event', '--type', 'session_started',
                               '--session', 'cli-linked', '--working-folder', str(link) + '/',
                               '--pid', str(pid), '--started', str(started), '--path', str(planted),
                               '--state-root', str(loose)], env=env, capture_output=True, timeout=15)
        entries = [spool.read(loose_folder, name) for name in spool.pending(loose_folder)]
        check('fix5/cli-session-path-said', 'with no ledger a session event with a path is refused by name, and '
              'neither the session nor the path is spooled or set aside: '
              + str((done.returncode, done.stderr.decode())),
              done.returncode == 1 and len(entries) == 1 and entries[0]['type'] == 'released'
              and done.stderr.decode().strip() == 'veldo space event: refused space_event_hook_only:session_started'
              and not spool.refused(loose_folder))
        done = subprocess.run([sys.executable, str(temp / 'bin/veldo'), 'space', 'event', '--type', 'ref_changed',
                               '--repository', str(temp / 'outside'), '--ref', 'refs/heads/main',
                               '--new', 'a' * 40, '--state-root', str(loose)],
                              env=env, capture_output=True, timeout=15)
        check('fix5/cli-session-path-said', 'with no ledger a ref changed event is refused by name and not spooled: '
              + str((done.returncode, done.stderr.decode())),
              done.returncode == 1
              and [spool.read(loose_folder, name)['type'] for name in spool.pending(loose_folder)] == ['released']
              and done.stderr.decode().strip() == 'veldo space event: refused space_event_hook_only:ref_changed'
              and not spool.refused(loose_folder))
        # Fix round 2: the CLI's own failure leaves a record on disk, by the hook's chain. A line on
        # standard error is no record. Three causes, each with no ledger: a state root that cannot be
        # written, a release that is no entry, and a spool folder that is refused.
        def event(*argv, **environ):
            return subprocess.run([sys.executable, str(temp / 'bin/veldo'), 'space', 'event'] + list(argv),
                                  env=without('VELDO_SPACE_STATE_ROOT', **environ), capture_output=True, timeout=15)

        def released(root):
            where = spool.spool_folder(str(root))
            return [spool.read(where, name)['subject'] for name in spool.pending(where)]

        closed = temp / 'cli-closed-state'
        closed.mkdir(mode=0o700)
        closed.chmod(0o500)
        try:
            done = event('--type', 'released', '--path', str(planted), '--state-root', str(closed),
                         XDG_STATE_HOME=str(temp / 'xdg-cli-closed'))
            check('round2/cli-unwritable-root', 'the entry is spooled under the fallback: '
                  + str((done.returncode, done.stderr.decode(), released(temp / 'xdg-cli-closed/veldo'))),
                  done.returncode == 0 and os.listdir(closed) == []
                  and released(temp / 'xdg-cli-closed/veldo') == [{'paths': [str(planted)]}])
            # The fallback's spool folder is made here when no entry made it, so the check that follows runs.
            (temp / 'xdg-cli-closed/veldo' / spool.SPOOL).mkdir(parents=True, mode=0o700, exist_ok=True)
            (temp / 'xdg-cli-closed/veldo' / spool.SPOOL).chmod(0o777)
            done = event('--type', 'released', '--path', str(planted) + '-second', '--state-root', str(closed),
                         XDG_STATE_HOME=str(temp / 'xdg-cli-closed'))
            left = lines(temp / 'xdg-cli-closed/veldo')
            check('round2/cli-unwritable-root', 'no root takes the entry: one line with what the verb was given: '
                  + str((done.returncode, done.stderr.decode(), left)),
                  done.returncode == 0 and os.listdir(closed) == [] and len(left) == 1
                  and left[0]['type'] == 'released' and str(planted) + '-second' in left[0]['argv']
                  and 'writable by group or others' in left[0]['reason']
                  and (temp / 'xdg-cli-closed/veldo' / spool.FOLDER_REFUSED).exists()
                  and 'could not spool' in done.stderr.decode()
                  and str(temp / 'xdg-cli-closed/veldo' / spool.UNSPOOLED) in done.stderr.decode())
        finally:
            closed.chmod(0o700)
            (temp / 'xdg-cli-closed/veldo' / spool.SPOOL).chmod(0o700)
        evil = temp / 'cli-state-evil'
        done = event('--type', 'released', '--path', '', '--state-root', str(evil))
        kept = spool.refused(spool.spool_folder(str(evil)))
        kept = [json.loads((Path(spool.spool_folder(str(evil))) / spool.REFUSED / name).read_text()) for name in kept]
        check('round2/cli-invalid-refused', 'a release that is no entry is under refused/ with why: '
              + str((done.returncode, done.stderr.decode(), kept)),
              done.returncode == 0 and len(kept) == 1 and kept[0]['notification']['type'] == 'released'
              and '' in kept[0]['notification']['argv']
              and kept[0]['refused']['reason'].startswith('space_event_invalid:')
              and not spool.pending(spool.spool_folder(str(evil))) and 'could not spool' in done.stderr.decode())
        open_state = temp / 'cli-open-state'
        (open_state / spool.SPOOL).mkdir(parents=True, mode=0o700)
        (open_state / spool.SPOOL).chmod(0o777)
        done = event('--type', 'released', '--path', str(planted) + '-unsafe', '--state-root', str(open_state),
                     XDG_STATE_HOME=str(temp / 'xdg-cli-open'))
        noted = open_state / spool.FOLDER_REFUSED
        check('round2/cli-unsafe-folder', 'the refused folder is noted beside it and nothing is written into it: '
              + str((done.returncode, done.stderr.decode(), noted.exists(), os.listdir(open_state / spool.SPOOL))),
              done.returncode == 0 and noted.exists()
              and 'writable by group or others' in json.loads(noted.read_text())['refused']
              and os.listdir(open_state / spool.SPOOL) == [])
        check('round2/cli-unsafe-folder', 'the entry is spooled under the fallback: '
              + str(released(temp / 'xdg-cli-open/veldo')),
              released(temp / 'xdg-cli-open/veldo') == [{'paths': [str(planted) + '-unsafe']}]
              and not lines(open_state))
        (open_state / spool.SPOOL).chmod(0o700)
        # With a ledger (this fixture's, handed to the verb in this process): released goes to the Ledger
        # with the paths its own checks gave, and the Ledger answers by that form. A session event is
        # refused by the verb itself, by name, before anything is sent or spooled: session events reach
        # the Ledger only from the hooks' spool, through the consumer (lead decision at assembly,
        # 2026-11-16, finished in the fix round after the assembly's review).
        loader = importlib.machinery.SourceFileLoader('v314_veldo_cli', str(temp / 'bin/veldo'))
        CLI = importlib.util.module_from_spec(importlib.util.spec_from_loader('v314_veldo_cli', loader))
        was, sys.dont_write_bytecode = sys.dont_write_bytecode, True
        try:
            loader.exec_module(CLI)
        finally:
            sys.dont_write_bytecode = was
        wired = temp / 'cli-state-wired'
        wired_folder = spool.spool_folder(str(wired))
        event_enabled[0] = False

        def verb(argv):
            out, said = io.StringIO(), io.StringIO()
            try:
                status = CLI.space_event(argv + ['--state-root', str(wired)], space={'ledger': ledger},
                                         environ=dict(env), stdout=out, stderr=said)
            except SystemExit as stop:
                status = stop.code
            return status, out.getvalue(), said.getvalue()
        status, out, said = verb(['--type', 'released', '--path', str(scratch) + '//given-up/'])
        entries = [spool.read(wired_folder, name) for name in spool.pending(wired_folder)]
        check('fix5/cli-wired-canonical', 'the Ledger is given its own form of the path and refuses it by that '
              'form (no item there); nothing is spooled: '
              + str((status, out, said, [e['subject'] for e in entries])),
              status == 1 and out == '' and not entries
              and said.strip() == 'veldo space event: refused space_release_no_item:' + str(scratch / 'given-up'))
        status, out, said = verb(['--type', 'session_ended', '--session', 'wired-session', '--path',
                                  str(scratch / 'given-up'), '--pid', str(pid), '--started', str(started),
                                  '--working-folder', str(temp / 'outside')])
        check('fix5/cli-session-path-said', 'with a ledger a session event with a path is refused by name, '
              'nothing is sent and nothing is spooled: ' + str((status, out, said)),
              status == 1 and out == ''
              and said.strip() == 'veldo space event: refused space_event_hook_only:session_ended'
              and not spool.pending(wired_folder) and not spool.refused(wired_folder))
        event_enabled[0] = True

        # Fix round, finding 4: the hook's timer raises TimeoutError. Raised where the entry is read (read
        # is replaced for this one call: the timer cannot be made to fire there on demand), it ends the
        # replay and the entry stays whole; the next replay delivers it.
        timed = spool.spool_folder(str(temp / 'state-deadline'))
        name = spool.put(timed, one('session_started', 'deadline', temp / 'outside'))
        whole = (Path(timed) / name).read_bytes()
        real_read = spool.read

        def late(*args):
            raise TimeoutError('session hook deadline')
        spool.read = late
        try:
            spool.replay(timed, authority, sign)
            raised = False
        except TimeoutError:
            raised = True
        finally:
            spool.read = real_read
        check('fix4/deadline-in-read', 'the replay ends and the entry stays whole in the spool: '
              + str((raised, os.listdir(timed))),
              raised and spool.pending(timed) == [name] and (Path(timed) / name).read_bytes() == whole
              and not (Path(timed) / spool.REFUSED).exists())
        spool.read = late
        try:
            result = spool.submit(one('session_ended', 'deadline', temp / 'outside'), str(temp / 'state-deadline'),
                                  str(installation), authority, sign)
        finally:
            spool.read = real_read
        check('fix4/deadline-in-read', 'a hook whose deadline fires in the replay keeps both entries',
              result['pending'] and len(spool.pending(timed)) == 2 and not (Path(timed) / spool.REFUSED).exists())
        # Finding 6: what a crash in the middle of a write left is set aside by the next replay.
        stale, fresh = Path(timed) / 'x.json.1.aaaaaaaa.partial', Path(timed) / 'y.json.1.bbbbbbbb.partial'
        stale.write_bytes(b'{"cut": ')
        fresh.write_bytes(b'{"being written": ')
        os.chmod(stale, 0o600)
        os.chmod(fresh, 0o600)
        os.utime(stale, (time.time() - 3600, time.time() - 3600))
        spool.replay(timed, authority, sign)
        check('fix4/deadline-in-read', 'the next replay delivers the entry',
              not spool.pending(timed) and len(items('deadline')) == 1
              and len([e for e in events if e['subject'].get('session') == 'deadline']) == 2)
        aside = Path(timed) / spool.REFUSED
        check('fix6/stale-partial-set-aside', 'a stale partial leaves the spool with its bytes and why; a new one stays: '
              + str(sorted(os.listdir(timed))),
              not stale.exists() and fresh.exists()
              and (aside / (stale.name + '.malformed')).read_bytes() == b'{"cut": '
              and json.loads((aside / (stale.name + '.why')).read_text()) == {'refused': 'a write that did not finish'})
        hooks = json.loads((ROOT / 'packs/claude/hooks/hooks.json').read_text())['hooks']
        check('hooks/registered', 'both hooks bounded and use exec to retain client parent identity',
              all(hooks[k][0]['hooks'][0]['timeout'] == 15
                  and hooks[k][0]['hooks'][0]['command'].startswith('exec python3 ')
                  and hooks[k][0]['hooks'][0]['command'].endswith(k) for k in ('SessionStart', 'SessionEnd')))
    except Exception as error:
        import traceback
        check('fixture/completed', traceback.format_exc(), False)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)
        if listener is not None:
            listener.close()
        if conn is not None:
            conn.close()
        shutil.rmtree(temp)
    for row, values in rows.items():
        failed = [message for message, good in values if not good]
        expect('VELDO-0314 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v314_suite()
