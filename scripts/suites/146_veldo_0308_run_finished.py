"""VELDO-0308: run finished, from the receiver.

Run: python3 scripts/selftest.py --suite 146_veldo_0308_run_finished

Only shared ROOT and expect are consumed. The three modules this ticket changes are loaded by path:
control_launch.py, control_retirement.py and control_clone.py (the clone provisioner, since the fourth
fix round). Signal, the Ledger, admission, the
store, the membership module, the declarations reader, the kind registry, the probes, the removers and
the keeper are loaded from this repository's .veldo. The ledger is a real one on a real store under one
temporary folder. Every folder, repository, worktree, clone and pin is real, made with plain git, and a
removal really deletes it. The project orchard is put in act mode by the owner's own signed command with
a real key; the project meadow has no mode record and is in report mode.

Every row plants what it is about, drives the module's own path at it, and reads the disk and the ledger
again as the call returns.

AC1 rows, the receiver's space end (Receiver._space_end, _finish and report_end):
ac1/not-before-the-record (while the dispatch record says running, or unknown, nothing is sent and
nothing is written; once it says exited and the group is empty run finished is sent once and the run
directory and the scratch folder are gone as the end returns), ac1/surviving-child (the declared
falsifier row: the worker's end is on the record and a real child process lives on with a file under the
scratch root open and its working directory elsewhere; run finished is not sent, the scratch item is
present with no deferral, nothing is written and the hold stays; once the child has ended the same end
removes both folders and releases the hold), ac1/removal-before-the-report (the receiver's own _finish:
at the exit record nothing of the run has been judged; the end is reported only after the removal is
complete and the hold released, and it carries what the space end did; a run whose group could not be
emptied is recorded unknown and sent nothing), ac1/refused-never-started (a dispatch refused before any
worker started is conclusive with no group).

AC2 rows: ac2/census-signal-release (the ledger's own commands in the order they were committed: every
measure of the census, then the one signal, then every removal outcome, then the release, last; all in
the ledger as the end returns; the worker's untracked notes stay), ac2/waiting-unit (the declared
falsifier row: a unit of the act-mode project waits; it needs the bytes the run's folders took and the
run's hold; after the receiver's end, and with the receiver gone, admission admits it),
ac2/hold-named-by-the-contract (the hold the contract's space field names is the one released; a hold
released already and a run with no hold write nothing).

AC3 rows, the retirement service wired as the runner wires it: ac3/unchanged-sweeps-retry-nothing (the
declared falsifier row: a retirement pending on its accounting, a run directory deferred as in_use;
three sweeps send no event, write nothing and make no attempt), ac3/retried-when-carried-out (when the
accounting completes the sweep carries the retirement out and in that call the dispatch's deferred
items are retried once: the run directory, free now, is removed through the rules and the folder
remover; later sweeps retry nothing), ac3/only-a-pending-retirement (a retirement carried out at its
first attempt retries nothing; one with no deferred item sends nothing; the runner wires its own retry
as the seam), ac3/not-under-a-consumer (the retry is not sent while a consumer of the run's clone has
not ended), ac3/not-for-a-run-not-ended (the retry answers rule 3 only for a run whose record shows an
end and of which the kernel shows nothing: otherwise the item is refused by the owner rule and whole).

AC4 rows, one for each declared falsifier and the cases beside them: ac4/deferred-releases-the-slot
(report mode: the clone is left due and whole with its pin, the teardown is recorded as deferred with
the ledger's item, and the slot is not held after the sweep), ac4/retired-releases-the-slot,
ac4/clone-in-use-keeps-the-slot (a consumer that has not ended: the obligation stays open, the slot
held, the ledger asked nothing; once it ends the sweep tears down), ac4/one-run-finished-per-clone (a
clone deferred as in_use and handed over while the slot is kept by a refusal that names no obligation:
three sweeps attempt the retirement and none the teardown; run finished was sent once for the clone),
ac4/handed-over-for-every-user (a worker and a consumer of one clone: one teardown, both slots
released), ac4/pins-follow-the-removal (the slot is released while the work tree is deferred and its
pin held; a removal made from outside the teardown removes the work tree; the next sweep releases the
pin, once), ac4/pins-held-while-deferred (through the hand-over and two sweeps the pin is held, and
after the cache was collected the work tree's commit is readable; a work tree that is not at its path
while its item is not removed releases nothing; through all of it the remover was asked for no
release, and asked itself for the deferred work tree's own item it refuses as not_in_ledger),
ac4/not-handed-over-keeps-the-slot (a clone no item
records, and an installation with no ledger: the obligation stays open and the slot held).

Rows of the fix round (the review of this ticket, findings 1 and 3 to 5). f1/sweep-never-resends (the
reviewer's probe row with the expectation reversed: a clone a process holds and the run directory of
the same run, both deferred and the clone handed over; the run is a leftover of a whole Runner, and
three Runner.sweep calls send no event, drop the leftover as handed over and write nothing, the clone's
items still deferred), f1/start-sweep-applies-the-rule (the start sweep of a restarted runner: a run
directory the ledger holds is no leftover and is sent nothing, and the observation says it was found
at start; one no event has reached is sent its one event and removed), f1/sent-once-and-alone (a
leftover whose item no event reaches has nothing the event could name: no command is sent over three
sweeps, and looked at once it is no leftover any more; one a process sits in is deferred by the
sweep's one event, handed over and never sent another), f3/unread-group-sends-nothing (a group nobody could read is not known to be empty: nothing is
sent, nothing is written, the hold stays, the reason is group_unread; the sweep, which reads the
kernel itself, then removes the folders), f4/pins-followed-after-a-restart (a clone handed over, the
retirement service made anew: it remembers nothing and still releases the pin after the work tree's
removal, at a sweep and at its own start, and not before), f4/clone-being-made-keeps-its-pin (a pin
on disk for a clone whose work tree is not made yet: no item and nothing at the path releases
nothing, and neither do items that are only declared), f5/refused-before-spawn and f5/spawn-failed
(Receiver.launch itself: the refusal is recorded first, with the folders on disk and the hold held;
the space end runs next; the refusal is reported last, with the folders gone and the hold released).

Rows of the second fix round (the re-review's N1 and N2). n1/own-items-ended (the re-review's probe row
with the expectation reversed: a run with a run directory, a scratch folder and an agent repository of
the same owner outside its folders and outside every clone is sent run finished once, by its receiver
and, for a leftover, by the sweep, and all three items are removed, the repository after its commit was
kept; with the run's clone handed to the ledger and left due, which no event takes, the run's own items
are ended the same way and the clone's three items keep their state and their version),
n2/observations-bounded (a leftover a sweep looked at once and could not move: no command and two
observations over six sweeps, and it is dropped from memory; a leftover held back by a consumer of its
clone: one observation over six sweeps, and once the consumer has ended the next sweep sends the one
event while the clone is still live and present).

Rows of the third fix round (the item-naming signal: run finished names the run's own items at their
versions). n1/handed-over-clone-untouched (the old N1 probe, closed: a clone a retirement handed over,
deferred, and beside it the run's directory and an agent repository of the same owner. The runner,
space-runner, is refused the signal that names those items. The receiver, as its own principal, sends
run finished once, naming exactly the run directory and the agent repository at the versions read:
both are removed, the repository after its commit was kept, and the clone's three items keep their
state and their version, the clone whole and its pin held. The sweep does the same for a leftover of
such a run. Five runner sweeps after the holders have gone send nothing and write nothing. No event
the receiver or the sweep sent in this suite named an item of a clone),
n1/changed-between-judge-and-send (an item of the run is measured after the receiver read it and
before the ledger's command: the ledger refuses the whole send by that item, the receiver reports not
sent with the ledger's reason, the three items stay present and on disk and nothing but the measure
is written; the sweep then sends the one event with the versions read then, and all three go).

Rows of the fourth fix round (the lead's decision on N1's open point: the clone's teardown names exactly
the clone's own items at their versions, and a live clone holds nothing back).
n1/live-clone-holds-nothing-back (a clone of the same owner no teardown has run for, its items present:
the receiver sends run finished once, naming exactly the run directory and the agent repository at the
versions read, and both are removed; the clone's three items stay present at the version they had, the
clone whole and pinned. The sweep does the same for a leftover. Each clone is then removed by its own
teardown, one event each), n1/teardown-names-its-clone-only (the teardown first, while the run directory
and an agent repository of the same owner are live: it names exactly the clone's root, work tree and
scratch folder at the versions read; the clone goes, and the two items outside it keep their state and
version and are on disk; no teardown of this suite named an item outside its own clone; the receiver's
send then ends the two), n1/teardown-changed-between-judge-and-send (an item of the clone is measured
after the teardown read it and before the ledger's command: the ledger refuses the whole send by that
item, the teardown is refused remove_refused with the ledger's reason, the three items stay present, no
pin is released and nothing but the measure is written; the next teardown names the versions read then
and the clone goes). f1/sweep-never-resends now has the run directory deferred by the receiver's own
event, f1/sent-once-and-alone no longer has a not_alone part, and the last check of
n2/observations-bounded is as told above.

Rows of the fifth fix round (the review of the item naming, finding 1: an item the owner marked Keep is
judged with the others and never named). keep/run-kept-item-not-named (a run with its run directory, its
scratch folder and an agent repository of the same owner, which the owner marked Keep: the receiver sends
run finished once, naming exactly the run directory and the scratch folder at the versions read; the
ledger accepts it and both are removed; the repository is on disk at its commit, its item kept with the
owner's mark at the version it had. The sweep does the same for a leftover of such a run),
keep/teardown-kept-item-not-named (a clone whose scratch folder the owner marked Keep: the teardown sends
run finished once, naming exactly the clone's root and its work tree at the versions read, and the ledger
accepts it; the work tree is removed after its commit was kept and its pin released; the folder the owner
kept is on disk with its file, its item kept with the owner's mark at the version it had, and the clone's
root, which holds it, is deferred and on disk: the teardown hands the clone over as deferred by a rule).

paths/no-delete-and-canon: no drive of this suite made the launch module or the clone provisioner
delete by itself, and the engine canon equals this repository's copies.

STAND-INS. The Signal the launch module and the clone provisioner call is counted: every event is
recorded as it is sent, with the items it named and the ledger's answer, and a row may have one thing
happen inside it, after the sender's read and before the ledger's command. The creators declare nothing yet (VELDO-0302): the suite declares each run directory,
scratch folder, worktree and clone item itself. Nothing writes a hold yet (VELDO-0316): the suite
places and admits each hold through the ledger's own commands. The owner's Confirm (VELDO-0320) is not
built: in ac4/pins-follow-the-removal it stands as what it will make, a removal of the deferred items
through Signal from outside the teardown and the retirement. The row VELDO-0347 adds to the kind
registry (an agent repository at run finished: remove) is added to a copy. The two checks of a switch
to act (VELDO-0332 and 0339). The docker client, a function. The process table, a folder shaped as the
kernel's; in ac1/surviving-child its entry is that of a real child process the row starts, which really
holds the file. The dispatch records, a mapping. The reservation service, as far as a retirement reads
it: a worker slot, the calls reserved under a dispatch, and a retire transition that takes its
observation from the lifecycle it is given. The receiver, the runner and the clone provisioner are made
without their stores (object.__new__ and the attributes the driven paths read). The clone is laid out
on disk as the provisioner's own _create lays it out, with its own _cache, _pin and _write. In the two
f5 rows the stations of Receiver.launch before the spawn (the recheck, the qualification, the login,
the binding, the memory handoff) answer that nothing is wrong, and the spawn raises as a missing
program does; the dispatch records of f1/start-sweep-applies-the-rule are a table of two rows.
"""


def _v308_run_finished_suite():
    import copy
    import importlib.util
    import io
    import json
    import os
    import shutil
    import subprocess
    import sys
    import tempfile
    import types
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_retirement.py': ROOT / ".veldo" / "control_retirement.py",
        'control_clone.py': ROOT / ".veldo" / "control_clone.py",
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
    }
    VELDO = ROOT / '.veldo'
    CHANGED = ('control_launch.py', 'control_retirement.py', 'control_clone.py')  # what VELDO-0308 changed
    # VELDO-0304: a pin is released only by control_space_remove.remove_ref, which the clone module finds
    # beside itself and which decides by the ledger's item. The driver gives a mutated module inside a
    # whole copy of .veldo; the modules under test are loaded from that folder (HOME), so the remover a
    # release reaches is the copy under test. Unmutated, HOME is .veldo itself.
    HOME = next((Path(path).parent for path in PRODUCTION.values() if Path(path).parent != VELDO), VELDO)
    PRODUCTION = {name: HOME / name for name in PRODUCTION}

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    ROWS = ('ac1/not-before-the-record', 'ac1/surviving-child', 'ac1/removal-before-the-report',
            'ac1/refused-never-started',
            'ac2/census-signal-release', 'ac2/waiting-unit', 'ac2/hold-named-by-the-contract',
            'ac3/unchanged-sweeps-retry-nothing', 'ac3/retried-when-carried-out', 'ac3/only-a-pending-retirement',
            'ac3/not-under-a-consumer', 'ac3/not-for-a-run-not-ended',
            'ac4/deferred-releases-the-slot', 'ac4/retired-releases-the-slot', 'ac4/clone-in-use-keeps-the-slot',
            'ac4/one-run-finished-per-clone', 'ac4/handed-over-for-every-user', 'ac4/pins-follow-the-removal',
            'ac4/pins-held-while-deferred', 'ac4/not-handed-over-keeps-the-slot',
            'f1/sweep-never-resends', 'f1/start-sweep-applies-the-rule', 'f1/sent-once-and-alone',
            'f3/unread-group-sends-nothing',
            'f4/pins-followed-after-a-restart', 'f4/clone-being-made-keeps-its-pin',
            'f5/refused-before-spawn', 'f5/spawn-failed',
            'n1/own-items-ended', 'n1/handed-over-clone-untouched', 'n1/changed-between-judge-and-send',
            'n1/live-clone-holds-nothing-back', 'n1/teardown-names-its-clone-only',
            'n1/teardown-changed-between-judge-and-send',
            'keep/run-kept-item-not-named', 'keep/teardown-kept-item-not-named',
            'n2/observations-bounded',
            'paths/no-delete-and-canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    ENVIRONMENT = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    ENVIRONMENT.update(GIT_EDITOR='true', GIT_TERMINAL_PROMPT='0', LC_ALL='C')

    def git(where, *argv, ok=True):
        done = subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                               '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                               '-c', 'advice.detachedHead=false', '-C', str(where)] + list(argv),
                              env=ENVIRONMENT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=120)
        if ok and done.returncode:
            raise RuntimeError('git %s: %s' % (' '.join(argv[:3]), done.stderr.decode()[-300:]))
        return done.returncode if not ok else done.stdout.decode().strip()

    def commit(where, name, text, message):
        (Path(where) / name).write_text(text)
        git(where, 'add', name)
        git(where, 'commit', '-q', '-m', message)
        return git(where, 'rev-parse', 'HEAD')

    def stopped(row, error):
        """A section that raised: its current row is red with what was raised, and the next section runs."""
        import traceback
        check(row, 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + ' | '.join(line.strip() for line in traceback.format_exc().splitlines()[-4:])[:400], False)

    def text_of(path):
        try:
            return Path(path).read_text()
        except OSError:
            return None

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0308-')))
    connections = []
    row = ROWS[0]
    try:
        LA = load('v308_control_launch', PRODUCTION['control_launch.py'])
        RT = load('v308_control_retirement', PRODUCTION['control_retirement.py'])
        CL = load('v308_control_clone', PRODUCTION['control_clone.py'])
        ADM = load('v308_control_space_admission', VELDO / 'control_space_admission.py')
        SIG = load('v308_control_space_signal', VELDO / 'control_space_signal.py')
        SP = load('v308_control_space', VELDO / 'control_space.py')
        S = load('v308_control_store', VELDO / 'control_store.py')
        CM = load('v308_control_membership', VELDO / 'control_membership.py')
        CFG = load('v308_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v308_yamlish', VELDO / 'yamlish.py')
        K = load('v308_control_space_kinds', VELDO / 'control_space_kinds.py')
        P = load('v308_control_space_probe', VELDO / 'control_space_probe.py')
        RM = load('v308_control_space_remove', VELDO / 'control_space_remove.py')
        KP = load('v308_control_space_keep', VELDO / 'control_space_keep.py')
        AC = CM.AC
        NOW = 1000.0

        # Every recursive delete the launch module and the clone provisioner make by themselves,
        # recorded as it is made: with a ledger there is none.
        DELETES = []

        def watched(name, module):
            real = module.shutil

            class Watched:
                def __getattr__(self, attribute):
                    return getattr(real, attribute)

                @staticmethod
                def rmtree(path, *args, **kwargs):
                    DELETES.append((name, str(path)))
                    return real.rmtree(path, *args, **kwargs)

            module.shutil = Watched()

        for name, module in (('control_clone.py', CL), ('control_launch.py', LA)):
            watched(name, module)

        # the owner's real key
        keys = temp / 'keys'
        keys.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(keys / 'owner')], check=True,
                       capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
        PUBLIC = (keys / 'owner.pub').read_text().strip()

        def owner_sign(data):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / 'owner'), '-n',
                                   AC.SIGNATURE_NAMESPACE], input=data, capture_output=True, check=True,
                                  timeout=30).stdout.decode()

        # the fixture installation and two projects, read from disk
        MEGABYTE = 1024 * 1024
        SCRATCH, STATE, BUILD = temp / 'scratch', temp / 'state', temp / 'build'
        for made in (SCRATCH, STATE, BUILD):
            made.mkdir()
        folder = temp / 'installation'
        folder.mkdir()
        (folder / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1',
            'owner': {'display_name': 'Fixture Owner', 'role_id': 'owner'},
            'space': {
                'enabled': 'true',
                'time_zone': 'Europe/Lisbon',
                'pools': {'host': {'floor': 20000 * MEGABYTE,
                                   'needs': {'build': 4000 * MEGABYTE, 'review': 1000 * MEGABYTE,
                                             'gate': 6000 * MEGABYTE}}},
                'engines': ['default'],
                'scratch_roots': {'roots': [str(SCRATCH)],
                                  'session_pattern': 'sessions/{working_folder}/{session_id}'},
                'build_roots': [str(BUILD)],
                'plain_repositories': [],
                'client_accounts': [str(temp / 'client-a')],
                'protect': {'paths': [str(STATE / 'vms')], 'volumes': [], 'containers': [],
                            'images': [], 'networks': [], 'compose_projects': []},
            }}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(temp / 'home')},
                          stream=io.StringIO())

        def project(name):
            path = temp / 'projects' / name
            path.mkdir(parents=True)
            git(path, 'init', '-q', '-b', 'main')
            (path / '.gitignore').write_text('build/\n')
            git(path, 'add', '.gitignore')
            commit(path, 'tracked.txt', 'base\n', 'base')
            (path / '.veldo').mkdir()
            return dict(CFG.read_project(str(path), YAML.read, config=CONFIG, stream=io.StringIO()),
                        repository=str(path))

        ORCHARD, MEADOW = project('orchard'), project('meadow')
        REPOSITORY = Path(ORCHARD['repository'])
        WORKTREES = Path(ORCHARD['worktree_root'])
        WORKTREES.mkdir(parents=True, exist_ok=True)
        A = {'type': 'project', 'id': ORCHARD['project']}
        B = {'type': 'project', 'id': MEADOW['project']}

        def journal_sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        # the store, the owner's bootstrap, the ledger
        IDS = {'domain_uuid': 'dom-308', 'repository_uuid': 'repo-308', 'store_uuid': 'store-308'}
        store_path = temp / 'authority' / 'control.sqlite3'
        store_path.parent.mkdir(mode=0o700)
        conn = S.open_store(str(store_path))
        connections.append(conn)
        CM.attach(S)
        command = {'command_id': 'setup-enroll-owner', 'operation': 'enroll_principal', 'target': 'authority',
                   'parameters': {'principal': 'owner', 'principal_type': 'person',
                                  'roles': ['membership_steward', 'project_owner'], 'public_key': PUBLIC,
                                  'independence_group': 'owner', 'scope': '*'},
                   'artifact_digests': [], 'expected_versions': {}}
        state = CM.authority_state(S, conn)
        envelope = dict(IDS, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal='owner',
                        request_revision=1, nonce='nonce-' + command['command_id'], expires_at=NOW + 600,
                        membership_version=state['membership_version'],
                        delegation_version=state['delegation_version'],
                        command_digest=AC.canonical_command_digest(command))
        CM.admit(S, conn, envelope, command, owner_sign(AC.canonical_envelope_bytes(envelope)), IDS, NOW,
                 enrollee_signature=None, journal_signer=('authority', journal_sign))

        # The row VELDO-0347 adds to the table (design section 5): an agent repository whose form is a
        # worker clone or a candidate workspace is removed at run finished. A stand-in, on a copy.
        REGISTRY = copy.deepcopy(K.REGISTRY)
        TABLE = REGISTRY['tables'][REGISTRY['version']]
        TABLE['rows']['agent_repository']['run_finished'] = {'action': 'remove', 'after': ['worktree']}
        TABLE['ends_on']['agent_repository'] = ['run_finished'] + list(TABLE['ends_on']['agent_repository'])
        LIFECYCLE = {'version': REGISTRY['version'], 'events': list(TABLE['events']),
                     'ends_on': {kind: list(events) for kind, events in TABLE['ends_on'].items()}}
        KINDS = types.SimpleNamespace(
            due=lambda event, items, queued=None, look=None: K.due(event, items, queued=queued, registry=REGISTRY,
                                                                   look=look))

        L = SP.Ledger(S, conn, 'authority', journal_sign, config=CONFIG, projects=[ORCHARD, MEADOW],
                      state_root=str(STATE), lifecycle=LIFECYCLE, host='fixture-host',
                      device=lambda path: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        # The two checks of a switch to act stand in for VELDO-0332 and 0339, and allow.
        L.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
        mode_command = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': A, 'mode': 'act'},
                        'command_id': 'mode-1', 'nonce': 'mode-nonce-1'}
        switched = L.set_mode({'command': mode_command, 'signature': owner_sign(S.canonical_bytes(mode_command))},
                              CM, NOW)
        if not switched.get('ok') or not L.acts(A) or L.acts(B):
            raise RuntimeError('the fixture could not put orchard in act mode: %s' % (switched.get('reason'),))

        def journal_length():
            return conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        def state_of(identity):
            return (L.item(identity) or {}).get('state')

        def deferral_of(identity):
            return ((L.item(identity) or {}).get('deferral') or {}).get('rule')

        def removal_of(identity):
            return (L.item(identity) or {}).get('removal') or {}

        def client(argv, cwd=None):
            """The client runner: docker from the fixture (no container anywhere), git by the probes' own."""
            if argv[0] != 'docker':
                return P._run(argv, cwd)
            if argv[3] == 'container' and argv[4] == 'ls':
                return 0, ''
            return 1, 'Error response from daemon: No such %s' % argv[3]

        PROC = temp / 'proc'
        PROC.mkdir()

        def process_entry(pid, cwd, opened=None):
            """One entry of the fixture process table: a process of this user whose working directory
            is `cwd` and that holds `opened` open, when given."""
            base = PROC / str(pid)
            (base / 'fd').mkdir(parents=True)
            (base / 'comm').write_text('holder\n')
            (base / 'maps').write_text('')
            (base / 'cwd').symlink_to(cwd)
            if opened is not None:
                (base / 'fd' / '3').symlink_to(opened)
            return base

        def free(pool):
            return shutil.disk_usage(str(temp)).free

        def keep(identity, record):
            return KP.keep(L, identity, record)

        ENDED = {'conclusive': True, 'group_empty': True}
        handed = []

        class Spy:
            """The removers, with every answer recorded: (item, what the remover said)."""
            left = staticmethod(RM.left)

            @staticmethod
            def remove(ledger, probe, identity, record, **given):
                said = RM.remove(ledger, probe, identity, record, **given)
                handed.append((identity, said))
                return said

        def space(**over):
            """What an installation with a ledger wires into each module. owner_live answers None by
            default: nobody answers for a run, so rule 3 passes only where the module's own kernel
            test answered it."""
            wired = {'ledger': L, 'probe': P, 'kinds': KINDS, 'remover': Spy, 'free': free, 'keep': keep,
                     'owner_live': lambda owner: None, 'run': client, 'proc': str(PROC),
                     'borrow_root': str(temp / 'borrowed')}
            wired.update(over)
            return wired

        def declared(kind, locator, owner, confirm=True, **more):
            made = L.declare(kind, locator, owner, 'seam', **more)
            if not made['ok']:
                raise RuntimeError('declare %s: %s %s' % (kind, made.get('reason'), made.get('detail')))
            if confirm:
                L.confirm(made['item'])
            return made['item']

        def kept_refs(identity):
            return ((L.item(identity) or {}).get('kept') or {}).get('refs') or {}

        def kept_at(identity, repository, commit):
            """Whether the item's keep record holds a kept ref ending in /head at `commit`, and the main
            repository `repository` really has that ref at that commit now."""
            for ref, at in kept_refs(identity).items():
                if ref.endswith('/head') and at == commit:
                    return git(repository, 'rev-parse', '--verify', '--quiet', ref + '^{commit}', ok=False) == 0 \
                        and git(repository, 'rev-parse', ref) == commit
            return False

        def readable(work, commit_id):
            return git(work, 'cat-file', '-e', commit_id + '^{commit}', ok=False) == 0

        def hold_state(identity):
            return (L.hold(identity) or {}).get('state')

        def operations(since):
            """The operation of every command the ledger committed after its first `since` observations,
            in the order of their journal records."""
            return [event.get('operation') for event in L.observations[since:] if event.get('outcome') == 'accepted']

        # Every event sent through Signal by the launch module and by the clone provisioner, as it is
        # sent: (emitter, event, the run of the subject). For a signal that names items the run is the
        # one run that owns every item named, and NAMED holds what it named: (emitter, the run, the items).
        SENT = []
        NAMED = []
        # What a row has happen inside the stand-in, once, as the event for a run is sent: after the
        # sender read the items and their versions, and before the ledger's command.
        INSIDE = {}

        def run_of(subject):
            if 'items' not in subject:
                return subject.get('run')
            runs = {(((L.item(one['item']) or {}).get('owner') or {}).get('run') or {}).get('id')
                    for one in subject['items']}
            return runs.pop() if len(runs) == 1 else sorted(runs, key=str)

        def counted(ledger, event, subject, **given):
            run = run_of(subject)
            SENT.append((given.get('emitter'), event, run))
            if 'items' in subject:
                NAMED.append((given.get('emitter'), run, [dict(one) for one in subject['items']]))
            inside = INSIDE.pop(run, None) if isinstance(run, str) else None
            if inside is not None:
                inside()
            answer = SIG.signal(ledger, event, subject, **given)
            ANSWERS.append((run, answer.get('ok'), answer.get('reason')))
            return answer

        ANSWERS = []

        LA._SPACE['signal'] = counted
        CL._SPACE['signal'] = counted

        def sent_for(dispatch_id, emitter=None):
            return [entry for entry in SENT if entry[2] == dispatch_id and (emitter is None or entry[0] == emitter)]

        RECORDS = {}

        class Dispatches:
            domain = 'dom-308'
            store = S

            def __init__(self, connection):
                self.conn = connection

            @staticmethod
            def record(dispatch_id):
                return RECORDS.get(dispatch_id)

        DISPATCHES = Dispatches(conn)
        RUNS = STATE / 'runs'
        RUNS.mkdir()

        def folder_bytes(path):
            return sum(os.lstat(os.path.join(base, name)).st_size for base, _, names in os.walk(str(path)) for name in names)

        def run_folders(name, scope=A, hold=True, need=4000 * MEGABYTE, size=3000):
            """A run as its creators will declare it (VELDO-0302): its run directory and its temporary
            folder under the scratch root, both scratch items the run owns, and its hold, admitted."""
            dispatch_id = 'dispatch/' + name
            owner = {'scope': scope, 'ticket': 'VELDO-94' + name[-2:], 'run': {'id': dispatch_id, 'station': 'build'}}
            place = Path(LA.run_directory(str(RUNS), dispatch_id))
            (place / LA.RUN_CONFIG).mkdir(parents=True)
            (place / LA.RUN_CONFIG / 'settings.json').write_text('{"generated": true}\n')
            scratch = Path(LA.run_directory(os.path.join(str(SCRATCH), LA.SPACE_RUN_SCRATCH), dispatch_id))
            scratch.mkdir(parents=True)
            (scratch / 'tmp.bin').write_bytes(b't' * size)
            items = {'run': declared('scratch', {'path': str(place)}, owner),
                     'scratch': declared('scratch', {'path': str(scratch)}, owner)}
            if hold:
                placed = L.place_hold(dispatch_id, {'host': need}, {'host': 'default'}, scope=scope)
                answered = L.admit(dispatch_id, 'admitted') if placed.get('ok') else placed
                if not answered.get('ok'):
                    raise RuntimeError('the fixture could not place the hold: %s' % (answered.get('reason'),))
            RECORDS[dispatch_id] = {'state': 'running', 'process': None}
            return dispatch_id, owner, place, scratch, items

        def receiver(dispatch_id, run, scratch=None, owner=None, worktree=None, supervision=None, clones=None):
            """The receiver, made without its stores: the attributes its space end reads and no other."""
            made = object.__new__(LA.Receiver)
            made.space, made.run_removal, made.run, made.supervision, made.role_skills = (
                space(), None, str(run) if run else None, supervision, [])
            made.config, made.dispatches, made.run_dispatch = ({'clones': clones} if clones else {}), DISPATCHES, dispatch_id
            made.space_run = {'worktree': str(worktree) if worktree else None, 'scratch': str(scratch) if scratch else None,
                              'owner': owner, 'build': None}
            made.run_census, made.run_end, made.run_sent = None, None, False
            return made

        class Reservations:
            """The reservation service (VELDO-0036) as far as a retirement reads it: the worker slot of a
            dispatch, the model calls reserved under it, and the retire transition, which takes its
            observation from the lifecycle it is given and refuses a live worker, a populated group and
            missing accounting. `stale` names dispatches whose retire is refused stale_version, a
            refusal that names no obligation."""
            domain, repository, store = 'dom-308', 'repo-308', S

            def __init__(self):
                import sqlite3
                self.conn = sqlite3.connect(':memory:')
                self.conn.execute('CREATE TABLE entities (id TEXT PRIMARY KEY, version INTEGER, data TEXT)')
                self.calls, self.stale, self.retired, self.observe = {}, set(), [], None

            def slot(self, dispatch_id):
                self.conn.execute('INSERT INTO entities VALUES (?, ?, ?)', (
                    RT.RES.entity('worker', [self.domain, dispatch_id]), 1,
                    json.dumps({'retired': False, 'context': {'unit': 'VELDO-9400'}})))

            def held(self, dispatch_id):
                row = self.conn.execute('SELECT data FROM entities WHERE id=?', (
                    RT.RES.entity('worker', [self.domain, dispatch_id]),)).fetchone()
                return row is not None and not json.loads(row[0])['retired']

            def _records(self):
                return {'call/%s/%d' % (dispatch_id, number): {
                    'type': 'invocation', 'context': {'domain': self.domain}, 'dispatch': dispatch_id,
                    'invocation': 'call/%s/%d' % (dispatch_id, number), 'state': state, 'unknown': []}
                    for dispatch_id, states in self.calls.items() for number, state in enumerate(states)}

            def retire(self, request, dispatch_id, lifecycle, now=None):
                if dispatch_id in self.stale:
                    raise S.StoreRefused('stale_version', dispatch_id)
                seen = lifecycle(None)
                for name, code in (('termination', 'worker_alive'), ('group', 'cleanup_incomplete'),
                                   ('accounting', 'missing_accounting')):
                    if seen['obligations'][name]['open']:
                        raise S.StoreRefused(code, dispatch_id)
                entity = RT.RES.entity('worker', [self.domain, dispatch_id])
                self.conn.execute('UPDATE entities SET version=2, data=? WHERE id=?', (
                    json.dumps({'retired': True, 'context': {'unit': 'VELDO-9400'}}), entity))
                self.retired.append(dispatch_id)

        def runner(clones=None):
            """The runner, made without its stores, with the retirement service wired as Runner.__init__
            wires it: the seam for a dispatch's deferred items is the runner's own retry_deferred."""
            made = object.__new__(LA.Runner)
            made.space, made.runs, made.profile, made.leftovers, made.observations = space(), str(RUNS), None, {}, []
            made.clones, made.dispatches, made.launches, made.orphans = clones, DISPATCHES, {}, {}
            made.clock = lambda: NOW
            made.reservations = Reservations()
            made.retirements = RT.Retirements(made.reservations, DISPATCHES, clones=clones, clock=made.clock,
                                              observations=made.observations, deferred=made.retry_deferred)
            return made

        def retries(made):
            return [event for event in made.observations if event.get('operation') == 'retry_deferred']

        def retire_events(made, dispatch_id):
            return [event for event in made.observations
                    if event.get('operation') == 'retire' and event.get('dispatch_id') == dispatch_id]

        CLONES, CACHES = STATE / 'clones', temp / 'caches'
        CLONES.mkdir()
        CACHES.mkdir()

        def provisioner(wired, caches=CACHES):
            """The clone provisioner over the fixture roots, made without its store checks: the teardown
            reads these attributes and no other."""
            made = object.__new__(CL.Clones)
            made.C = CL._organ('control_containment')
            made.dispatches, made.store, made.conn = DISPATCHES, S, conn
            made.domain, made.clock = 'dom-308', lambda: NOW
            made.clones, made.caches = CLONES, caches
            made.protected, made.engines, made.store_directory = [], [], []
            made.observations, made.counts = [], {'accepted': 0, 'refused': 0}
            made.space = wired
            return made

        def clone(C, name, project=ORCHARD, scope=A, declare=True, state='exited'):
            """A worker clone laid out as the provisioner's _create lays it out, its pin held in the
            cache, and its three items declared as design 6.10 gives them: the root and the scratch
            folder as scratch, the work tree as an agent repository, both inside the root."""
            clone_id, dispatch_id = 'clone-' + name, 'dispatch/' + name
            repository = Path(project['repository'])
            root = CLONES / clone_id
            root.mkdir(mode=0o700)
            work = root / 'work'
            head = git(repository, 'rev-parse', 'main')
            pin = C._pin(C._cache('dom-308', project['project']), project['project'], str(repository), head, clone_id)
            git(root, 'init', '-q', '--template=', str(work))
            info = work / '.git' / 'objects' / 'info'
            info.mkdir(parents=True, exist_ok=True)
            (info / 'alternates').write_text('%s\n' % (Path(pin['cache']) / 'objects'))
            git(work, 'checkout', '-q', '--detach', head)
            scratch = CL._scratch(root, dispatch_id)
            scratch.mkdir(parents=True)
            (scratch / 'tmp.bin').write_bytes(b't' * 4000)
            C._write({'schema': CL.SCHEMA, 'clone_id': clone_id, 'root': str(root), 'work': str(work),
                      'domain': 'dom-308', 'repository': project['project'], 'unit': 'VELDO-92' + name[-2:],
                      'commit': head, 'tree': git(repository, 'rev-parse', head + '^{tree}'), 'identity': 'identity-1',
                      'attachments': [], 'pins': [pin], 'protected': {'write': [], 'read': []}, 'ancestors': [],
                      'created_at': NOW,
                      'users': [{'dispatch_id': dispatch_id, 'role': 'worker', 'scratch': str(scratch),
                                 'group': None}]})
            RECORDS[dispatch_id] = {'state': state, 'process': None}
            items = {}
            if declare:
                owner = {'scope': scope, 'ticket': 'VELDO-92' + name[-2:], 'run': {'id': dispatch_id, 'station': 'build'}}
                items['root'] = declared('scratch', {'path': str(root)}, owner)
                items['work'] = declared('agent_repository', {'path': str(work)}, owner, parent=items['root'])
                items['scratch'] = declared('scratch', {'path': str(root / 'scratch')}, owner, parent=items['root'])
            return clone_id, dispatch_id, root, work, head, items

        def consumer(C, clone_id, root, name, state='running'):
            """A consumer dispatch attached to the clone, as Clones.attach records one."""
            consumer_id = 'dispatch/' + name
            manifest = C._manifest(clone_id)
            place = CL._scratch(root, consumer_id)
            place.mkdir(parents=True, exist_ok=True)
            manifest['users'].append({'dispatch_id': consumer_id, 'role': 'consumer', 'scratch': str(place), 'group': None})
            C._write(manifest)
            RECORDS[consumer_id] = {'state': state, 'process': None}
            return consumer_id

        def states(items):
            return [state_of(items[name]) for name in ('root', 'work', 'scratch')]

        # =====================================================================================
        # AC1: run finished only after the dispatch is conclusive and its group is empty
        # =====================================================================================
        try:
            row = 'ac1/not-before-the-record'
            dispatch_id, owner, place, scratch, items = run_folders('early-01')
            R = receiver(dispatch_id, place, scratch, owner, supervision={'empty': True})
            length = journal_length()
            end = R._space_end(dispatch_id)
            check(row, 'while the dispatch record says running nothing is sent, and the end says why [%s %s]'
                  % (end.get('sent'), end.get('reason')),
                  end.get('sent') is False and end.get('reason') == 'not_conclusive:running' and sent_for(dispatch_id) == [])
            check(row, 'nothing was written: the run directory and the scratch folder are on disk, their items present, '
                       'the hold still admitted [%s %s]' % (journal_length() - length, hold_state(dispatch_id)),
                  journal_length() == length and place.is_dir() and (scratch / 'tmp.bin').is_file()
                  and [state_of(items[name]) for name in ('run', 'scratch')] == ['present'] * 2
                  and hold_state(dispatch_id) == 'admitted')
            RECORDS[dispatch_id] = {'state': 'unknown', 'process': None}
            end = R._space_end(dispatch_id)
            check(row, 'an unknown outcome is not a recorded end either: nothing is sent [%s]' % (end.get('reason'),),
                  end.get('sent') is False and end.get('reason') == 'not_conclusive:unknown'
                  and journal_length() == length and place.is_dir() and hold_state(dispatch_id) == 'admitted')
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            end = R._space_end(dispatch_id)
            check(row, 'once the record says exited and the group is empty, run finished is sent, once [%s]'
                  % (sent_for(dispatch_id),),
                  end.get('sent') is True and sent_for(dispatch_id) == [('receiver', 'run_finished', dispatch_id)])
            check(row, 'the removal is complete as the end returns: neither folder is on disk and both items are removed '
                       '[%s]' % (end.get('items'),),
                  not os.path.lexists(place) and not os.path.lexists(scratch)
                  and [state_of(items[name]) for name in ('run', 'scratch')] == ['removed'] * 2
                  and sorted(entry['state'] for entry in end['items'].values()) == ['removed', 'removed'])
            removal = removal_of(items['scratch'])
            check(row, 'the removal record names run finished, the receiver and the folder remover [%s]'
                  % {key: removal.get(key) for key in ('event', 'emitter', 'method')},
                  removal.get('event') == 'run_finished' and removal.get('emitter') == 'receiver'
                  and removal.get('method') == 'rename_probe_delete')

            row = 'ac1/surviving-child'
            dispatch_id, owner, place, scratch, items = run_folders('child-02')
            CHILD = 'what the child of the worker is still writing\n'
            (scratch / 'child.log').write_text(CHILD)
            # The worker's own process has exited and its end is on the record. A child it started lives
            # on, with a file under the scratch root open and its working directory elsewhere.
            child = subprocess.Popen([sys.executable, '-I', '-c',
                                      'import sys, time\nheld = open(sys.argv[1], "a")\nprint("open", flush=True)\n'
                                      'time.sleep(120)\n', str(scratch / 'child.log')],
                                     cwd='/', stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                child.stdout.readline()
                holds = [os.readlink('/proc/%d/fd/%s' % (child.pid, name)) for name in os.listdir('/proc/%d/fd' % child.pid)]
                holder = process_entry(child.pid, '/', opened=str(scratch / 'child.log'))
                RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
                R = receiver(dispatch_id, place, scratch, owner, supervision={'empty': False, 'cause': None})
                length = journal_length()
                end = R._space_end(dispatch_id)
                check(row, 'the child lives and holds the file under the scratch root open, from another working '
                           'directory [%s]' % (child.poll(),),
                      child.poll() is None and str(scratch / 'child.log') in holds
                      and os.readlink('/proc/%d/cwd' % child.pid) == '/')
                check(row, 'while the group still has the child, run finished is not sent [%s %s]'
                      % (end.get('sent'), end.get('reason')),
                      end.get('sent') is False and end.get('reason') == 'group_not_empty' and sent_for(dispatch_id) == [])
                check(row, 'the scratch is not judged while the child lives: its item is present, with no deferral, and '
                           'nothing was written [%s %s %s]'
                      % (state_of(items['scratch']), deferral_of(items['scratch']), journal_length() - length),
                      state_of(items['scratch']) == 'present' and deferral_of(items['scratch']) is None
                      and state_of(items['run']) == 'present' and journal_length() == length)
                check(row, 'the file the child writes and the run directory are on disk, and the hold is still held [%s]'
                      % (hold_state(dispatch_id),),
                      text_of(scratch / 'child.log') == CHILD and place.is_dir() and hold_state(dispatch_id) == 'admitted')
            finally:
                child.kill()
                child.wait(timeout=30)
                child.stdout.close()
            shutil.rmtree(holder)
            R.supervision = {'empty': True, 'cause': None}
            end = R._space_end(dispatch_id)
            check(row, 'once the child has ended and the group is empty the same end removes the scratch and the run '
                       'directory and releases the hold [%s %s]' % (end.get('sent'), hold_state(dispatch_id)),
                  end.get('sent') is True and not os.path.lexists(scratch) and not os.path.lexists(place)
                  and [state_of(items[name]) for name in ('run', 'scratch')] == ['removed'] * 2
                  and hold_state(dispatch_id) == 'released')

            row = 'ac1/removal-before-the-report'
            dispatch_id, owner, place, scratch, items = run_folders('finish-03')
            LOG = []

            class Recording(Dispatches):
                """The dispatch records, with what was on disk and in the ledger at each terminal write."""

                def exit(self, dispatch, digest, process, termination, now=None, artifact=None, execution_record=None):
                    LOG.append(('exit', os.path.isdir(self.place), state_of(self.items['run']),
                                state_of(self.items['scratch']), hold_state(dispatch), len(sent_for(dispatch))))
                    RECORDS[dispatch] = {'state': 'exited', 'process': None}

                def unknown(self, dispatch, digest, reason, now=None, expected_state=None, execution_record=None):
                    LOG.append(('unknown', reason))
                    RECORDS[dispatch] = {'state': 'unknown', 'process': None}

            def finishing(dispatch_id, place, scratch, owner, items, supervision):
                made = receiver(dispatch_id, place, scratch, owner, supervision=supervision)
                made.dispatches = Recording(conn)
                made.dispatches.place, made.dispatches.items = place, items
                made.metering, made.recorder, made.committed, made._exit_group = None, None, None, None
                (STATE / 'receiver').mkdir(exist_ok=True)
                made.config = {'state_root': str(STATE / 'receiver')}
                made.workspace_before, made.conversation_directory = None, None
                made.emit = lambda event: LOG.append((
                    'emit', event.get('event'), os.path.lexists(place), os.path.lexists(scratch),
                    hold_state(dispatch_id), event.get('space')))
                return made

            R = finishing(dispatch_id, place, scratch, owner, items, {'empty': True, 'cause': None})
            contract = {'dispatch_id': dispatch_id, 'repository': 'repo-308', 'reservation': {'project': ORCHARD['project']}}
            R._finish({'deadline_stop': False}, contract, 'digest', None, False)
            check(row, 'when the worker has ended and the exit is being recorded nothing of the run has been judged: both '
                       'folders there, both items present, the hold held, no event sent [%s]' % (LOG[:1],),
                  LOG[:1] == [('exit', True, 'present', 'present', 'admitted', 0)])
            reported = LOG[-1] if LOG else ()
            check(row, 'the end is reported, and so the receiver exits, only after the removal is complete and the hold '
                       'released [%s]' % (reported[:5],),
                  len(LOG) == 2 and reported[:5] == ('emit', 'exited', False, False, 'released'))
            check(row, 'the reported end carries what the space end did [%s]' % (reported[5:],),
                  isinstance(reported[5], dict) and reported[5].get('sent') is True and reported[5].get('hold') == 'released'
                  and sorted(entry['state'] for entry in reported[5]['items'].values()) == ['removed', 'removed'])
            dispatch_id, owner, place, scratch, items = run_folders('finish-04')
            del LOG[:]
            R = finishing(dispatch_id, place, scratch, owner, items, {'empty': False, 'cause': None})
            contract = dict(contract, dispatch_id=dispatch_id)
            length = journal_length()
            R._finish({'deadline_stop': False}, contract, 'digest', None, False)
            reported = LOG[-1] if LOG else ()
            check(row, 'a run whose group could not be emptied is recorded unknown and sent nothing: the folders, the '
                       'items and the hold stay [%s]' % (LOG,),
                  LOG[:1] == [('unknown', 'containment_not_empty')] and reported[:5] == ('emit', 'unknown', True, True, 'admitted')
                  and reported[5].get('sent') is False and reported[5].get('reason') == 'not_conclusive:unknown'
                  and journal_length() == length and [state_of(items[name]) for name in ('run', 'scratch')] == ['present'] * 2)
            source = Path(PRODUCTION['control_launch.py']).read_text()
            finish = source[source.index('    def _finish(self, termination'):source.index('    def _conclude_exit(self)')]
            order = [finish.find(mark) for mark in ('self.dispatches.exit(', 'self._conclude_exit()',
                                                    "report_end(self, contract, {'event': 'exited'")]
            report = source[source.index('def report_end(receiver'):source.index('def _failure_log(')]
            inner = [report.find(mark) for mark in ('run_end_scan(', 'receiver._space_end(', 'receiver.emit(event)')]
            check(row, 'in the source the exit is recorded before the end is reported, and the report runs the scan, then '
                       'the space end, then the emit [%s %s]' % (order, inner),
                  -1 not in order and order == sorted(order) and -1 not in inner and inner == sorted(inner))

            row = 'ac1/refused-never-started'
            dispatch_id, owner, place, scratch, items = run_folders('refused-05')
            RECORDS[dispatch_id] = {'state': 'refused', 'process': None}
            R = receiver(dispatch_id, place, scratch, owner, supervision=None)
            end = R._space_end(dispatch_id)
            check(row, 'a dispatch refused before any worker started is conclusive with no group: its folders go and its '
                       'hold is released [%s %s]' % (end.get('sent'), hold_state(dispatch_id)),
                  end.get('sent') is True and not os.path.lexists(place) and not os.path.lexists(scratch)
                  and hold_state(dispatch_id) == 'released')
            dispatch_id = 'dispatch/refused-06'
            RECORDS[dispatch_id] = {'state': 'refused', 'process': None}
            L.admit(dispatch_id, 'admitted') if L.place_hold(dispatch_id, {'host': MEGABYTE}, {'host': 'default'},
                                                           scope=A).get('ok') else None
            R = receiver(dispatch_id, None, supervision=None)
            length = len(L.observations)
            end = R._space_end(dispatch_id)
            check(row, 'one refused before it was given any folder is sent nothing and its hold is released, the one write '
                       '[%s %s %s]' % (end.get('sent'), end.get('reason'), operations(length)),
                  end.get('sent') is False and end.get('reason') == 'nothing_recorded'
                  and hold_state(dispatch_id) == 'released' and operations(length) == ['space_release'])
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC2: the census, then Signal, then the release of the hold
        # =====================================================================================
        try:
            row = 'ac2/census-signal-release'
            dispatch_id, owner, place, scratch, items = run_folders('order-11')
            path = WORKTREES / 'order-11'
            tree = declared('worktree', {'path': str(path)}, {'scope': A, 'ticket': owner['ticket']}, confirm=False,
                            start=git(REPOSITORY, 'rev-parse', 'main'))
            git(REPOSITORY, 'worktree', 'add', '-q', '--detach', str(path), 'main')
            L.confirm(tree)
            (path / 'build').mkdir()
            (path / 'build' / 'app.o').write_bytes(b'o' * 5000)
            NOTES = 'what the worker learned and never committed\n'
            (path / 'notes.txt').write_text(NOTES)
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            R = receiver(dispatch_id, place, scratch, owner, worktree=path, supervision={'empty': True})
            length, records = len(L.observations), journal_length()
            end = R._space_end(dispatch_id)
            written = operations(length)
            census = end.get('census') or {}
            output = (census.get('items') or {}).get(str(path / 'build'))
            where = {name: [index for index, operation in enumerate(written) if operation == name]
                     for name in ('space_measure', 'space_signal', 'space_outcome', 'space_release')}
            check(row, 'the census ran: the build folder the worker left is an item of the run, measured [%s %s]'
                  % (census.get('refusal'), census.get('sizes')),
                  census.get('refusal') is None and output is not None and census.get('sizes', {}).get(output, 0) >= 5000
                  and census.get('sizes', {}).get(items['scratch'], 0) >= 3000)
            check(row, 'the three are written in order: every measure of the census before the signal, every removal '
                       'outcome after it, and the release of the hold last [%s]' % (written,),
                  where['space_measure'] and len(where['space_signal']) == 1 and where['space_outcome']
                  and journal_length() - records == len(written)
                  and where['space_release'] == [len(written) - 1]
                  and max(where['space_measure']) < where['space_signal'][0] < min(where['space_outcome'])
                  and max(where['space_outcome']) < where['space_release'][0])
            check(row, 'all three are in the ledger as the end returns: the sizes, the removals and the released hold '
                       '[%s %s]' % (end.get('items'), end.get('hold')),
                  (L.item(output) or {}).get('state') == 'removed' and state_of(items['run']) == 'removed'
                  and state_of(items['scratch']) == 'removed' and hold_state(dispatch_id) == 'released'
                  and (end.get('hold') or {}).get('released') is True
                  and not any(os.path.lexists(found) for found in (place, scratch, path / 'build')))
            check(row, 'the notes the worker left untracked are byte for byte in the worktree, which stays present',
                  text_of(path / 'notes.txt') == NOTES and state_of(tree) == 'present'
                  and text_of(path / 'tracked.txt') == 'base\n')

            row = 'ac2/waiting-unit'
            NEED, WAITING_NEED, PLANTED = 4000 * MEGABYTE, 1000 * MEGABYTE, 3 * MEGABYTE
            dispatch_id, owner, place, scratch, items = run_folders('holds-12', need=NEED, size=PLANTED)
            FLOOR = L.pool('host')['floor']
            others = ADM.held(L, 'host', but=dispatch_id)
            # The fixture pool: free is a figure of the row's own, less what the run's folders take on
            # disk, so a removal frees exactly the bytes that were there.
            BASE = WAITING_NEED + FLOOR + others + MEGABYTE

            def free_now(pool):
                return BASE - folder_bytes(scratch) - folder_bytes(place)

            taken = folder_bytes(scratch) + folder_bytes(place)
            waiting = 'unit/waiting-12'
            L.place_hold(waiting, {'host': WAITING_NEED}, {'host': 'default'}, scope=A)
            first = ADM.admit(L, waiting, free_now)
            check(row, 'a unit of a project in act mode waits for space, with the numbers [%s %s]'
                  % (first.get('answer'), first.get('reason')),
                  first.get('answer') == 'waiting' and hold_state(waiting) == 'waiting'
                  and (first.get('reason') or {}).get('held') == others + NEED)
            check(row, 'it needs both: the freed bytes alone, or the released hold alone, would leave it short [%s]' % (taken,),
                  taken >= PLANTED and BASE - (others + NEED) < WAITING_NEED + FLOOR
                  and (BASE - taken) - others < WAITING_NEED + FLOOR and BASE - others >= WAITING_NEED + FLOOR)
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            R = receiver(dispatch_id, place, scratch, owner, supervision={'empty': True})
            end = R._space_end(dispatch_id)
            del R  # the receiver has gone
            second = ADM.admit(L, waiting, free_now)
            check(row, 'the run\'s end freed the bytes and released the hold [%s %s]' % (free_now(None) - BASE, hold_state(dispatch_id)),
                  free_now(None) == BASE and hold_state(dispatch_id) == 'released' and (end.get('hold') or {}).get('released') is True)
            check(row, 'after the receiver has gone the waiting unit is admitted [%s %s]'
                  % (second.get('answer'), second.get('reason')),
                  second.get('answer') == 'admitted' and hold_state(waiting) == 'admitted')
            L.release(waiting)

            row = 'ac2/hold-named-by-the-contract'
            dispatch_id, owner, place, scratch, items = run_folders('named-13', hold=False)
            named = 'hold/named-13'
            L.place_hold(named, {'host': MEGABYTE}, {'host': 'default'}, scope=A)
            L.admit(named, 'admitted')
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            R = receiver(dispatch_id, place, scratch, owner, supervision={'empty': True})
            end = R._space_end(dispatch_id, {'dispatch_id': dispatch_id, 'space': {'hold': named, 'needs': {'host': MEGABYTE}}})
            check(row, 'the hold the contract\'s space field names is the one released [%s]' % (end.get('hold'),),
                  hold_state(named) == 'released' and (end.get('hold') or {}).get('hold') == named)
            length = journal_length()
            again = LA.space_release(space(), named)
            none = LA.space_release(space(), 'hold/never-placed')
            check(row, 'a hold released already is left as it is, and a run that was given none has none: nothing is '
                       'written [%s %s]' % (again, none),
                  again.get('released') is False and again.get('state') == 'released'
                  and none.get('refusal') == 'no_hold' and journal_length() == length)
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC3: a pending retirement that is carried out retries the dispatch's deferred items
        # =====================================================================================
        try:
            row = 'ac3/unchanged-sweeps-retry-nothing'
            dispatch_id, owner, place, scratch, items = run_folders('retry-21', hold=False)
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            holder = process_entry(5821, '/', opened=str(place / LA.RUN_CONFIG / 'settings.json'))
            LA.space_signal(space(), 'run_finished', [str(place), str(scratch)], 'receiver', ended=True)
            N = runner()
            N.reservations.slot(dispatch_id)
            N.reservations.calls[dispatch_id] = ['reserved']
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            pending = N.retirements.pending().get(dispatch_id) or {}
            check(row, 'the run directory a process holds a file in was deferred at the run\'s end, and the retirement is '
                       'pending on its accounting [%s %s %s]' % (deferral_of(items['run']), first, pending),
                  state_of(items['run']) == 'deferred' and deferral_of(items['run']) == 'in_use' and first is False
                  and pending.get('open') == ['accounting'] and N.reservations.held(dispatch_id))
            sent, length, attempts = len(SENT), journal_length(), pending.get('attempts')
            swept = [N.sweep() for _ in range(3)]
            check(row, 'three sweeps that find the obligation unchanged retry nothing: no event is sent, nothing is '
                       'written, no attempt is made [%d %d %s]'
                  % (len(SENT) - sent, journal_length() - length, len(retries(N))),
                  swept == [[], [], []] and len(SENT) == sent and journal_length() == length and retries(N) == []
                  and (N.retirements.pending().get(dispatch_id) or {}).get('attempts') == attempts
                  and N.retirements.counts['retried'] == 0)
            check(row, 'the deferred run directory is as it was, whole', state_of(items['run']) == 'deferred'
                  and text_of(place / LA.RUN_CONFIG / 'settings.json') == '{"generated": true}\n')

            row = 'ac3/retried-when-carried-out'
            shutil.rmtree(holder)
            N.reservations.calls[dispatch_id] = ['settled']
            released = N.sweep()
            retried = retries(N)
            check(row, 'when the accounting completes the sweep carries the retirement out [%s]' % (released,),
                  released == [dispatch_id] and not N.reservations.held(dispatch_id) and N.retirements.pending() == {})
            check(row, 'and in that call the dispatch\'s deferred items are retried, once [%s %s]'
                  % (SENT[sent:], [event.get('answer') for event in retried]),
                  SENT[sent:] == [('runner.retirement', 'run_finished', dispatch_id)] and len(retried) == 1
                  and retried[0].get('outcome') == 'retried' and retried[0]['answer'].get('retried') == [items['run']]
                  and retried[0]['answer'].get('signals') == 1)
            removal = removal_of(items['run'])
            check(row, 'the run directory, free now, is removed by that retry, through the rules and the folder remover '
                       '[%s]' % {key: removal.get(key) for key in ('event', 'emitter', 'method')},
                  not os.path.lexists(place) and state_of(items['run']) == 'removed'
                  and removal.get('event') == 'run_finished' and removal.get('emitter') == 'runner.retirement'
                  and removal.get('method') == 'rename_probe_delete')
            sent, length = len(SENT), journal_length()
            swept = [N.sweep() for _ in range(3)]
            check(row, 'later sweeps retry nothing more', swept == [[], [], []] and len(SENT) == sent
                  and journal_length() == length and len(retries(N)) == 1)

            row = 'ac3/only-a-pending-retirement'
            dispatch_id, owner, place, scratch, items = run_folders('retry-22', hold=False)
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            holder = process_entry(5822, '/', opened=str(place / LA.RUN_CONFIG / 'settings.json'))
            LA.space_signal(space(), 'run_finished', [str(place), str(scratch)], 'receiver', ended=True)
            N = runner()
            N.reservations.slot(dispatch_id)
            sent, length = len(SENT), journal_length()
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            check(row, 'a retirement carried out at its first attempt was never pending: nothing is retried, and the '
                       'deferred item waits for its next event [%s %s]' % (first, len(retries(N))),
                  first is True and retries(N) == [] and len(SENT) == sent and journal_length() == length
                  and state_of(items['run']) == 'deferred')
            shutil.rmtree(holder)
            dispatch_id, owner, place, scratch, items = run_folders('retry-23', hold=False)
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            LA.space_signal(space(), 'run_finished', [str(place), str(scratch)], 'receiver', ended=True)
            N = runner()
            N.reservations.slot(dispatch_id)
            N.reservations.calls[dispatch_id] = ['reserved']
            N._retire(dispatch_id, 'completed', 'worker_reaped')
            N.reservations.calls[dispatch_id] = ['settled']
            sent, length = len(SENT), journal_length()
            released = N.sweep()
            check(row, 'a pending retirement of a run with no deferred item is carried out and sends nothing [%s %s]'
                  % (released, [event.get('answer') for event in retries(N)]),
                  released == [dispatch_id] and len(retries(N)) == 1 and retries(N)[0]['answer'].get('signals') == 0
                  and len(SENT) == sent and journal_length() == length)
            check(row, 'the runner wires its own retry as the retirement service\'s seam',
                  'deferred=self.retry_deferred' in source and N.retirements.deferred == N.retry_deferred)
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC4: the clone obligation closes on hand-over to the ledger; the pins follow the work tree
        # =====================================================================================
        try:
            C = provisioner(space())

            row = 'ac4/deferred-releases-the-slot'
            clone_id, dispatch_id, root, work, head, items = clone(C, 'report-31', project=MEADOW, scope=B)
            N = runner(C)
            N.reservations.slot(dispatch_id)
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            swept = N.sweep()
            event = (retire_events(N, dispatch_id) or [{}])[-1]
            check(row, 'in a project in report mode the clone is left due: whole on disk, its items due, its pin held [%s]'
                  % (states(items),),
                  (work / 'tracked.txt').is_file() and (root / CL.MANIFEST).is_file() and states(items) == ['due'] * 3
                  and len(C._pins_held(clone_id)) == 1)
            check(row, 'the teardown was handed to the ledger, so the worker slot is released: not held after the sweep '
                       '[%s %s %s]' % (first, swept, N.retirements.pending()),
                  first is True and not N.reservations.held(dispatch_id) and N.retirements.pending() == {})
            check(row, 'the retirement records the teardown as deferred, with the refusal and the ledger\'s item [%s %s]'
                  % (event.get('clone'), N.retirements.handed.get(clone_id)),
                  event.get('outcome') == 'retired' and (event.get('clone') or {}).get('teardown') == 'deferred'
                  and (event.get('clone') or {}).get('refusal') == 'space_deferred:due'
                  and (N.retirements.handed.get(clone_id) or {}).get('item') == items['root'])
            check(row, 'run finished was sent once for the clone, by the teardown [%s]' % (sent_for(dispatch_id),),
                  sent_for(dispatch_id) == [('clone.teardown', 'run_finished', dispatch_id)])

            row = 'ac4/retired-releases-the-slot'
            clone_id, dispatch_id, root, work, head, items = clone(C, 'clean-32')
            N = runner(C)
            N.reservations.slot(dispatch_id)
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            check(row, 'a teardown that answers retired closes the obligation and releases the slot; the clone is gone, '
                       'its commit kept, its pins released by the teardown [%s %s]' % (first, states(items)),
                  first is True and not N.reservations.held(dispatch_id) and not os.path.lexists(root)
                  and states(items) == ['removed'] * 3 and kept_at(items['work'], REPOSITORY, head)
                  and C._pins_held(clone_id) == []
                  and (N.retirements.handed.get(clone_id) or {}).get('teardown') == 'retired')

            row = 'ac4/clone-in-use-keeps-the-slot'
            clone_id, dispatch_id, root, work, head, items = clone(C, 'inuse-33')
            consumer_id = consumer(C, clone_id, root, 'consumer-33')
            N = runner(C)
            N.reservations.slot(dispatch_id)
            length = journal_length()
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            pending = N.retirements.pending().get(dispatch_id) or {}
            check(row, 'a teardown refused clone_in_use keeps the obligation open and the slot held, unchanged [%s %s]'
                  % (first, pending),
                  first is False and N.reservations.held(dispatch_id) and pending.get('open') == ['clone']
                  and pending.get('refusal') == 'cleanup_incomplete:clone'
                  and (retire_events(N, dispatch_id)[-1].get('clone') or {}).get('refusal') == 'clone_in_use'
                  and clone_id not in N.retirements.handed)
            swept = [N.sweep() for _ in range(2)]
            check(row, 'the ledger was asked nothing and the clone is whole under its consumer [%s]' % (states(items),),
                  swept == [[], []] and journal_length() == length and states(items) == ['present'] * 3
                  and (work / 'tracked.txt').is_file() and len(C._pins_held(clone_id)) == 1
                  and sent_for(dispatch_id) == [])
            RECORDS[consumer_id] = {'state': 'exited', 'process': None}
            released = N.sweep()
            check(row, 'once the consumer has ended the sweep tears the clone down and releases the slot [%s %s]'
                  % (released, states(items)),
                  released == [dispatch_id] and not os.path.lexists(root) and states(items) == ['removed'] * 3
                  and not N.reservations.held(dispatch_id))

            row = 'ac4/one-run-finished-per-clone'
            clone_id, dispatch_id, root, work, head, items = clone(C, 'once-34')
            holder = process_entry(5834, '/', opened=str(work / 'tracked.txt'))
            N = runner(C)
            N.reservations.slot(dispatch_id)
            N.reservations.stale.add(dispatch_id)
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            check(row, 'the clone a process holds a file in is deferred as in_use and handed to the ledger, while the '
                       'slot is kept by a refusal that names no obligation [%s %s %s]'
                  % (first, states(items), N.retirements.pending().get(dispatch_id)),
                  first is False and state_of(items['work']) == 'deferred' and deferral_of(items['work']) == 'in_use'
                  and (N.retirements.handed.get(clone_id) or {}).get('teardown') == 'deferred'
                  and (N.retirements.pending().get(dispatch_id) or {}).get('refusal') == 'stale_version')
            attempts = N.retirements.pending()[dispatch_id]['attempts']
            swept = [N.sweep() for _ in range(3)]
            check(row, 'three sweeps attempt the retirement again and none attempts the teardown again: run finished was '
                       'sent once for the clone [%s %s]'
                  % (sent_for(dispatch_id), N.retirements.pending()[dispatch_id]['attempts'] - attempts),
                  swept == [[], [], []] and N.retirements.pending()[dispatch_id]['attempts'] == attempts + 3
                  and sent_for(dispatch_id) == [('clone.teardown', 'run_finished', dispatch_id)])
            check(row, 'the clone is whole, its pin held', (work / 'tracked.txt').is_file()
                  and len(C._pins_held(clone_id)) == 1)
            N.reservations.stale.discard(dispatch_id)
            released = N.sweep()
            check(row, 'when the retirement is carried out the teardown is still not called again; the one retry of the '
                       'dispatch\'s deferred items is the retirement\'s own [%s %s]' % (released, sent_for(dispatch_id)),
                  released == [dispatch_id]
                  and sent_for(dispatch_id) == [('clone.teardown', 'run_finished', dispatch_id),
                                                ('runner.retirement', 'run_finished', dispatch_id)]
                  and (work / 'tracked.txt').is_file() and state_of(items['work']) == 'deferred')
            sent = len(SENT)
            swept = [N.sweep() for _ in range(3)]
            check(row, 'and no later sweep sends anything for it', swept == [[], [], []] and len(SENT) == sent)
            shutil.rmtree(holder)

            row = 'ac4/handed-over-for-every-user'
            clone_id, dispatch_id, root, work, head, items = clone(C, 'both-35', project=MEADOW, scope=B)
            consumer_id = consumer(C, clone_id, root, 'consumer-35')
            N = runner(C)
            N.reservations.slot(dispatch_id)
            N.reservations.slot(consumer_id)
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            RECORDS[consumer_id] = {'state': 'exited', 'process': None}
            second = N._retire(consumer_id, 'completed', 'worker_reaped')
            check(row, 'the worker\'s retirement waits while the consumer lives; the consumer\'s end hands the clone over '
                       'and releases both slots in that call [%s %s %s]' % (first, second, N.reservations.retired),
                  first is False and second is True and sorted(N.reservations.retired) == sorted([dispatch_id, consumer_id])
                  and N.retirements.pending() == {})
            check(row, 'the teardown ran once for the clone, whichever dispatch asked [%s]'
                  % ([entry for entry in SENT if entry[0] == 'clone.teardown' and entry[2] == dispatch_id],),
                  len(sent_for(dispatch_id, 'clone.teardown')) == 1 and states(items) == ['due'] * 3
                  and (work / 'tracked.txt').is_file())

            row = 'ac4/pins-follow-the-removal'
            clone_id, dispatch_id, root, work, head, items = clone(C, 'confirm-36')
            holder = process_entry(5836, '/', opened=str(work / 'tracked.txt'))
            N = runner(C)
            N.reservations.slot(dispatch_id)
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            N.sweep()
            check(row, 'the slot is released while the work tree is deferred, and its pin is held [%s %s]'
                  % (first, state_of(items['work'])),
                  first is True and not N.reservations.held(dispatch_id) and state_of(items['work']) == 'deferred'
                  and len(C._pins_held(clone_id)) == 1)
            # The owner's Confirm (VELDO-0320 is not built) stands here as what it will make: a removal
            # of the deferred items through Signal, from outside the teardown and the retirement.
            shutil.rmtree(holder)
            LA.space_signal(space(owner_live=lambda found: dict(ENDED)), 'run_finished', [str(root), str(work)],
                            'owner.confirm')
            check(row, 'the owner\'s Confirm removes the work tree after the slot was released: gone from disk, its commit '
                       'kept, and the pin still in the cache, for nothing has looked yet [%s]' % (states(items),),
                  not os.path.lexists(work) and state_of(items['work']) == 'removed'
                  and removal_of(items['work']).get('emitter') == 'owner.confirm'
                  and kept_at(items['work'], REPOSITORY, head) and len(C._pins_held(clone_id)) == 1)
            N.sweep()
            followed = [event for event in N.observations if event.get('operation') == 'release_pins']
            check(row, 'the next sweep finds the work tree\'s item removed and releases the pin [%s %s]'
                  % (C._pins_held(clone_id), followed),
                  C._pins_held(clone_id) == [] and len(followed) == 1 and followed[0].get('outcome') == 'released'
                  and len(followed[0].get('released') or ()) == 1)
            N.sweep()
            check(row, 'and it is released once', len([event for event in N.observations
                                                      if event.get('operation') == 'release_pins']) == 1)

            row = 'ac4/pins-held-while-deferred'
            ALONE = temp / 'caches-alone'
            ALONE.mkdir()
            C2 = provisioner(space(), caches=ALONE)
            clone_id, dispatch_id, root, work, head, items = clone(C2, 'gc-37')
            holder = process_entry(5837, '/', opened=str(work / 'tracked.txt'))
            N = runner(C2)
            N.reservations.slot(dispatch_id)
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            swept = [N.sweep() for _ in range(2)]
            for cache in sorted(ALONE.glob('*.git')):
                git(cache, 'gc', '-q', '--prune=now')
            check(row, 'the slot is released and the work tree is deferred, on disk [%s %s]' % (first, state_of(items['work'])),
                  first is True and not N.reservations.held(dispatch_id) and state_of(items['work']) == 'deferred'
                  and (work / 'tracked.txt').is_file())
            check(row, 'its pin is held through the hand-over and the sweeps [%s]' % (C2._pins_held(clone_id),),
                  len(C2._pins_held(clone_id)) == 1 and not [event for event in N.observations
                                                             if event.get('operation') == 'release_pins'])
            check(row, 'after the cache was collected the work tree\'s commit is still readable through it',
                  readable(work, head) and git(work, 'rev-parse', 'HEAD') == head
                  and git(work, 'show', 'HEAD:tracked.txt') == 'base')
            # A work tree left under its marked name is not at its path and is not removed: no release.
            marked = work.with_name('work.veldo-removing.fixture')
            os.rename(work, marked)
            N.sweep()
            check(row, 'a work tree that is not at its path while its item is not removed releases nothing',
                  len(C2._pins_held(clone_id)) == 1)
            os.rename(marked, work)
            # VELDO-0304: the release itself is the remover's now, and it refuses any item that is not
            # removed. So a release asked too early no longer takes the pin; it is still a defect of the
            # retirement, seen as what the remover was asked: nothing, from the hand-over to here.
            check(row, 'and through the hand-over, the sweeps and the marked name the remover was asked for no release '
                       '[%s]' % (sorted(getattr(C2, 'ref_outcomes', {})),), not getattr(C2, 'ref_outcomes', {}))
            # And the remover itself, asked for the work tree's own item while it is deferred: refused as
            # not the ledger's to release, the pin where it was.
            asked = [C2._release(Path(pin['cache']), pin['ref'], identity=items['work']) for pin in C2._pins_held(clone_id)]
            check(row, 'asked for the deferred work tree\'s own item the remover releases nothing: not_in_ledger [%s]'
                  % ([(answer.get('ok'), answer.get('deferral'), answer.get('said')) for answer in asked],),
                  [(answer.get('ok'), answer.get('deferral')) for answer in asked] == [(False, 'not_in_ledger')]
                  and len(C2._pins_held(clone_id)) == 1 and state_of(items['work']) == 'deferred')
            shutil.rmtree(holder)

            row = 'ac4/not-handed-over-keeps-the-slot'
            clone_id, dispatch_id, root, work, head, items = clone(C, 'unrecorded-38', declare=False)
            N = runner(C)
            N.reservations.slot(dispatch_id)
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            event = (retire_events(N, dispatch_id) or [{}])[-1]
            check(row, 'a clone no item records is not the ledger\'s: the obligation stays open and the slot held [%s %s]'
                  % (first, event.get('clone')),
                  first is False and N.reservations.held(dispatch_id)
                  and (event.get('clone') or {}).get('teardown') == 'refused'
                  and (event.get('clone') or {}).get('refusal') == 'space_deferred:not_in_ledger'
                  and clone_id not in N.retirements.handed and (work / 'tracked.txt').is_file()
                  and len(C._pins_held(clone_id)) == 1)
            PLAIN = provisioner(None)
            clone_id, dispatch_id, root, work, head, items = clone(PLAIN, 'noledger-39', declare=False)
            DRAFT = 'a draft the worker never committed\n'
            (work / 'draft.md').write_text(DRAFT)
            N = runner(PLAIN)
            N.reservations.slot(dispatch_id)
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            event = (retire_events(N, dispatch_id) or [{}])[-1]
            check(row, 'with no ledger wired a refused teardown is handed to nobody: the slot stays held and the clone '
                       'stays whole with its draft and its pin [%s %s]' % (first, event.get('clone')),
                  first is False and N.reservations.held(dispatch_id)
                  and (event.get('clone') or {}).get('teardown') == 'refused'
                  and str((event.get('clone') or {}).get('refusal')).startswith('space_deferred:')
                  and N.retirements.handed == {} and text_of(work / 'draft.md') == DRAFT
                  and len(PLAIN._pins_held(clone_id)) == 1)

            row = 'ac3/not-under-a-consumer'
            clone_id, dispatch_id, root, work, head, items = clone(C, 'shared-41')
            consumer_id = consumer(C, clone_id, root, 'consumer-41')
            held_run = Path(LA.run_directory(str(RUNS), dispatch_id))
            (held_run / LA.RUN_CONFIG).mkdir(parents=True)
            run_item = declared('scratch', {'path': str(held_run)}, {
                'scope': A, 'ticket': 'VELDO-9241', 'run': {'id': dispatch_id, 'station': 'build'}})
            holder = process_entry(5841, str(held_run / LA.RUN_CONFIG), opened=str(work / 'tracked.txt'))
            SIG.signal(L, 'run_finished', {'scope': A, 'ticket': 'VELDO-9241', 'run': dispatch_id}, emitter='fixture',
                       **{key: value for key, value in space(owner_live=lambda found: dict(ENDED)).items() if key != 'ledger'})
            shutil.rmtree(holder)
            N = runner(C)
            sent, length = len(SENT), journal_length()
            answer = N.retry_deferred(dispatch_id)
            check(row, 'the retry is not sent while a consumer of the run\'s clone has not ended: the clone would end '
                       'under it [%s %s]' % (state_of(run_item), answer),
                  state_of(run_item) == 'deferred' and state_of(items['work']) == 'deferred'
                  and answer.get('refusal') == 'clone_in_use'
                  and answer.get('users') == [consumer_id] and len(SENT) == sent and journal_length() == length
                  and (work / 'tracked.txt').is_file())
            RECORDS[consumer_id] = {'state': 'exited', 'process': None}

            row = 'ac3/not-for-a-run-not-ended'
            dispatch_id, owner, place, scratch, items = run_folders('retry-42', hold=False)
            holder = process_entry(5842, '/', opened=str(place / LA.RUN_CONFIG / 'settings.json'))
            LA.space_signal(space(), 'run_finished', [str(place), str(scratch)], 'receiver', ended=True)
            shutil.rmtree(holder)
            RECORDS[dispatch_id] = {'state': 'unknown', 'process': None}
            N = runner()
            answer = N.retry_deferred(dispatch_id)
            found = (L.item(items['run']) or {}).get('deferral') or {}
            check(row, 'a retry asked for a run whose record shows no end answers rule 3 for nobody: the item is judged, '
                       'refused by the owner rule and whole [%s %s]' % (answer.get('states'), found.get('refused_by')),
                  state_of(items['run']) == 'deferred' and found.get('refused_by') == 'owner_live'
                  and text_of(place / LA.RUN_CONFIG / 'settings.json') == '{"generated": true}\n')
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            answer = N.retry_deferred(dispatch_id)
            check(row, 'once the record shows the end and the kernel shows nothing of the run, the retry removes it [%s]'
                  % (answer.get('states'),), state_of(items['run']) == 'removed' and not os.path.lexists(place))
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # The fix round: the review's findings 1, 3, 4 and 5
        # =====================================================================================
        try:
            import errno
            import sqlite3

            def run_place(dispatch_id, ticket, scope=A, confirm=True):
                """The run directory of a run that has a clone, or of one given nothing else: a scratch
                item the run owns."""
                place = Path(LA.run_directory(str(RUNS), dispatch_id))
                (place / LA.RUN_CONFIG).mkdir(parents=True)
                (place / LA.RUN_CONFIG / 'settings.json').write_text('{"generated": true}\n')
                return place, declared('scratch', {'path': str(place)}, {
                    'scope': scope, 'ticket': ticket, 'run': {'id': dispatch_id, 'station': 'build'}}, confirm=confirm)

            def handed_over(made, dispatch_id):
                return [event for event in made.observations if event.get('operation') == 'remove_run'
                        and event.get('dispatch_id') == dispatch_id and event.get('outcome') == 'handed_over']

            def pin_events(made, clone_id):
                return [event for event in made.observations
                        if event.get('operation') == 'release_pins' and event.get('clone_id') == clone_id]

            C5 = provisioner(space())

            row = 'f1/sweep-never-resends'
            clone_id, dispatch_id, root, work, head, items = clone(C5, 'resend-51')
            holders = [process_entry(5851, '/', opened=str(work / 'tracked.txt'))]
            place, run_item = run_place(dispatch_id, 'VELDO-9251')
            holders.append(process_entry(5852, str(place / LA.RUN_CONFIG)))
            N = runner(C5)
            N.reservations.slot(dispatch_id)
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            before = states(items)
            reached = state_of(run_item)
            end = receiver(dispatch_id, place, None, None, supervision={'empty': True}, clones=C5)._space_end(dispatch_id)
            check(row, 'the clone a process holds is handed to the ledger and the slot released, by the teardown\'s '
                       'event, which does not reach the run directory; the run directory of the same run, which a '
                       'process sits in, is deferred by the receiver\'s own event [%s %s %s %s %s]'
                  % (first, before, reached, state_of(run_item), sent_for(dispatch_id)),
                  first is True and (N.retirements.handed.get(clone_id) or {}).get('teardown') == 'deferred'
                  and state_of(items['work']) == 'deferred' and reached == 'present' and end.get('sent') is True
                  and state_of(run_item) == 'deferred' and states(items) == before
                  and sent_for(dispatch_id) == [('clone.teardown', 'run_finished', dispatch_id),
                                                ('receiver', 'run_finished', dispatch_id)])
            # The run is a leftover, as the start sweep makes it after any restart, in a whole Runner.
            N.leftovers[dispatch_id] = {'group': None, 'process': None}
            mark, length = len(sent_for(dispatch_id)), journal_length()
            swept = [N.sweep() for _ in range(3)]
            check(row, 'three Runner.sweep calls send no event for the run [%s]' % (sent_for(dispatch_id)[mark:],),
                  swept == [[], [], []] and sent_for(dispatch_id)[mark:] == [])
            check(row, 'the leftover is dropped as handed over, once, and nothing was written [%s %s]'
                  % (handed_over(N, dispatch_id), journal_length() - length),
                  dispatch_id not in N.leftovers and len(handed_over(N, dispatch_id)) == 1
                  and handed_over(N, dispatch_id)[0].get('space') == {'item': run_item, 'state': 'deferred'}
                  and journal_length() == length)
            check(row, 'the clone\'s items are still deferred as they were, the clone whole and its pin held, the run '
                       'directory whole [%s]' % (states(items),),
                  states(items) == before and state_of(items['work']) == 'deferred' and state_of(run_item) == 'deferred'
                  and (work / 'tracked.txt').is_file() and len(C5._pins_held(clone_id)) == 1
                  and text_of(place / LA.RUN_CONFIG / 'settings.json') == '{"generated": true}\n')

            row = 'f1/start-sweep-applies-the-rule'

            class Stored(Dispatches):
                """The dispatch records as the start sweep reads them: a table of records of this domain
                and repository."""
                repository = 'repo-308'

                def __init__(self, records):
                    self.conn = sqlite3.connect(':memory:')
                    self.conn.execute('CREATE TABLE entities (kind TEXT, data TEXT)')
                    for identity, state in records:
                        self.conn.execute('INSERT INTO entities VALUES (?, ?)', (LA.D.RECORD_KIND, json.dumps({
                            'dispatch_id': identity, 'state': state, 'process': None,
                            'contract': {'domain': 'dom-308', 'repository': 'repo-308'}})))

            fresh_id, fresh_owner, fresh_place, fresh_scratch, fresh_items = run_folders('fresh-52', hold=False)
            RECORDS[fresh_id] = {'state': 'unknown', 'process': None}
            N = runner(C5)  # a runner made anew: it remembers no leftover and no hand-over
            N.dispatches = Stored([(dispatch_id, 'exited'), (fresh_id, 'unknown')])
            mark, sent = len(sent_for(dispatch_id)), len(SENT)
            removed = N.sweep_runs()
            found = handed_over(N, dispatch_id)
            check(row, 'at start a run directory the ledger holds is no leftover: it is sent nothing, and the '
                       'observation says it was found at start [%s %s]' % (found, sent_for(dispatch_id)[mark:]),
                  dispatch_id not in N.leftovers and len(found) == 1 and found[0].get('at') == 'start'
                  and sent_for(dispatch_id)[mark:] == [] and state_of(run_item) == 'deferred' and place.is_dir())
            check(row, 'a run directory no event has reached is a leftover, is sent its one event and is removed [%s %s]'
                  % (removed, SENT[sent:]),
                  removed == [fresh_id] and SENT[sent:] == [('runner.sweep', 'run_finished', fresh_id)]
                  and not os.path.lexists(fresh_place) and state_of(fresh_items['run']) == 'removed')
            sent = len(SENT)
            swept = [N.sweep() for _ in range(3)]
            check(row, 'and three sweeps after the start send nothing [%s]' % (SENT[sent:],),
                  swept == [[], [], []] and len(SENT) == sent)
            for holder in holders:
                shutil.rmtree(holder)

            row = 'f1/sent-once-and-alone'
            dispatch_id = 'dispatch/once-53'
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            place, run_item = run_place(dispatch_id, 'VELDO-9453', confirm=False)
            N = runner()
            N.leftovers[dispatch_id] = {'group': None, 'process': None}
            length = journal_length()
            swept = [N.sweep() for _ in range(3)]
            check(row, 'a leftover whose item no event reaches (it was never confirmed) has nothing the event could '
                       'name: over three sweeps no command is sent to the ledger and nothing is written, and it stays '
                       'on disk; looked at once, it is no leftover of a sweep any more [%s %s]'
                  % (sent_for(dispatch_id), N.observations[-1:]),
                  sent_for(dispatch_id) == [] and journal_length() == length
                  and dispatch_id not in N.leftovers
                  and N.observations[-1].get('refusal') == 'run_finished_sent' and place.is_dir()
                  and state_of(run_item) == 'declared')
            dispatch_id, owner, place, scratch, items = run_folders('once-54', hold=False)
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            holder = process_entry(5854, str(place / LA.RUN_CONFIG))
            N = runner()
            N.leftovers[dispatch_id] = {'group': None, 'process': None}
            swept = [N.sweep() for _ in range(3)]
            check(row, 'a leftover a process sits in is deferred by the sweep\'s one event, handed over and never sent '
                       'another [%s %s]' % (sent_for(dispatch_id), deferral_of(items['run'])),
                  sent_for(dispatch_id) == [('runner.sweep', 'run_finished', dispatch_id)]
                  and state_of(items['run']) == 'deferred' and deferral_of(items['run']) == 'in_use'
                  and dispatch_id not in N.leftovers and len(handed_over(N, dispatch_id)) == 1
                  and handed_over(N, dispatch_id)[0].get('at') == 'sweep' and place.is_dir())
            shutil.rmtree(holder)

            row = 'f3/unread-group-sends-nothing'
            dispatch_id, owner, place, scratch, items = run_folders('unread-56')
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None, 'dispatch_id': dispatch_id,
                                    'termination': {'returncode': 0, 'signal': None, 'deadline_stop': False}}
            R = receiver(dispatch_id, place, scratch, owner, supervision={'empty': None, 'cause': 'unreadable'})
            length = journal_length()
            end = R._space_end(dispatch_id)
            check(row, 'a group nobody could read is not known to be empty: run finished is not sent, and the end says '
                       'group_unread [%s %s]' % (end.get('sent'), end.get('reason')),
                  end.get('sent') is False and end.get('reason') == 'group_unread' and sent_for(dispatch_id) == [])
            check(row, 'nothing was judged or written: both folders on disk, both items present with no deferral, the '
                       'hold still held [%s %s]' % (journal_length() - length, hold_state(dispatch_id)),
                  journal_length() == length and place.is_dir() and (scratch / 'tmp.bin').is_file()
                  and [state_of(items[name]) for name in ('run', 'scratch')] == ['present'] * 2
                  and deferral_of(items['run']) is None and hold_state(dispatch_id) == 'admitted')
            # The sweep's kernel test takes over: the runner reads the end, keeps the run as a leftover, and
            # its sweep, which asks the kernel itself, sends the one event.
            N = runner()
            N.reservations.slot(dispatch_id)
            record = N.wait(types.SimpleNamespace(dispatch_id=dispatch_id, group=None,
                                                  wait=lambda timeout=None: RECORDS[dispatch_id]))
            check(row, 'the runner\'s sweep, which reads the kernel itself, then sends the one event and the folders go '
                       '[%s %s]' % (sent_for(dispatch_id), (record or {}).get('state')),
                  sent_for(dispatch_id) == [('runner.sweep', 'run_finished', dispatch_id)]
                  and not os.path.lexists(place) and not os.path.lexists(scratch)
                  and [state_of(items[name]) for name in ('run', 'scratch')] == ['removed'] * 2 and N.leftovers == {})

            row = 'f4/pins-followed-after-a-restart'
            clone_id, dispatch_id, root, work, head, items = clone(C5, 'restart-57')
            holder = process_entry(5857, '/', opened=str(work / 'tracked.txt'))
            N = runner(C5)
            N.reservations.slot(dispatch_id)
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            check(row, 'the clone is handed over with its work tree deferred and its pin held [%s %s]'
                  % (first, state_of(items['work'])),
                  first is True and clone_id in N.retirements.handed and state_of(items['work']) == 'deferred'
                  and len(C5._pins_held(clone_id)) == 1)
            # The restart: the retirement service is made anew and remembers no hand-over.
            N = runner(C5)
            N.sweep()
            check(row, 'the service made anew remembers nothing of it, and while the work tree is deferred its start '
                       'and its sweep release nothing [%s]' % (N.retirements.handed,),
                  N.retirements.handed == {} and N.retirements.entries == {} and len(C5._pins_held(clone_id)) == 1
                  and pin_events(N, clone_id) == [] and readable(work, head))
            shutil.rmtree(holder)
            LA.space_signal(space(owner_live=lambda found: dict(ENDED)), 'run_finished', [str(root), str(work)],
                            'owner.confirm')
            check(row, 'the work tree is then removed from outside, its commit kept, and the pin is still in the cache '
                       '[%s]' % (states(items),),
                  not os.path.lexists(work) and state_of(items['work']) == 'removed'
                  and kept_at(items['work'], REPOSITORY, head) and len(C5._pins_held(clone_id)) == 1)
            N.sweep()
            check(row, 'the next sweep of the restarted service releases the pin, from the refs on disk [%s]'
                  % (pin_events(N, clone_id),),
                  C5._pins_held(clone_id) == [] and len(pin_events(N, clone_id)) == 1
                  and pin_events(N, clone_id)[0].get('outcome') == 'released'
                  and len(pin_events(N, clone_id)[0].get('released') or ()) == 1 and N.retirements.handed == {})
            clone_id, dispatch_id, root, work, head, items = clone(C5, 'start-58')
            holder = process_entry(5858, '/', opened=str(work / 'tracked.txt'))
            N = runner(C5)
            N.reservations.slot(dispatch_id)
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            shutil.rmtree(holder)
            LA.space_signal(space(owner_live=lambda found: dict(ENDED)), 'run_finished', [str(root), str(work)],
                            'owner.confirm')
            held = len(C5._pins_held(clone_id))
            N = runner(C5)  # the restart, after the removal: the start itself looks
            check(row, 'a service started after the removal releases the pin at its start, before any sweep [%s %s]'
                  % (held, pin_events(N, clone_id)),
                  first is True and held == 1 and state_of(items['work']) == 'removed' and C5._pins_held(clone_id) == []
                  and len(pin_events(N, clone_id)) == 1)

            row = 'f4/clone-being-made-keeps-its-pin'
            # A clone as _create has it between its pins and the git init of its work tree: the root is
            # there, the pin is in the cache, the work tree is not made, and no item records it.
            clone_id = 'clone-making-59'
            root = CLONES / clone_id
            root.mkdir(mode=0o700)
            work = root / 'work'
            head = git(REPOSITORY, 'rev-parse', 'main')
            pin = C5._pin(C5._cache('dom-308', ORCHARD['project']), ORCHARD['project'], str(REPOSITORY), head, clone_id)
            N = runner(C5)
            swept = [N.sweep() for _ in range(2)]
            check(row, 'no item and nothing at the path releases nothing: the pin of a clone being made is held through '
                       'the start and two sweeps [%s %s]' % (C5._pins_held(clone_id), pin_events(N, clone_id)),
                  not os.path.lexists(work) and len(C5._pins_held(clone_id)) == 1 and pin_events(N, clone_id) == []
                  and git(pin['cache'], 'rev-parse', pin['ref']) == head)
            making = {'scope': A, 'ticket': 'VELDO-9259', 'run': {'id': 'dispatch/making-59', 'station': 'build'}}
            made_root = declared('scratch', {'path': str(root)}, making, confirm=False)
            made_work = declared('agent_repository', {'path': str(work)}, making, confirm=False, parent=made_root)
            N = runner(C5)
            swept = [N.sweep() for _ in range(2)]
            check(row, 'nor do its items once they are declared and the work tree is still not made [%s %s]'
                  % (state_of(made_work), C5._pins_held(clone_id)),
                  state_of(made_work) == 'declared' and not os.path.lexists(work)
                  and len(C5._pins_held(clone_id)) == 1 and pin_events(N, clone_id) == [])

            # Receiver.launch itself, on its refusal paths: refuse, then the space end, then the report.
            LOG = []

            class Refusing(Dispatches):
                """The dispatch records, with what was on disk and in the ledger at each write."""

                def refuse(self, dispatch, digest, refusal, now=None, expected_state=None):
                    LOG.append(('refuse', refusal, expected_state, os.path.isdir(self.place),
                                state_of(self.items['run']), state_of(self.items['scratch']), hold_state(dispatch),
                                len(sent_for(dispatch))))
                    RECORDS[dispatch] = dict(RECORDS[dispatch], state='refused')

                def accept(self, dispatch, digest, me, now=None):
                    LOG.append(('accept',))
                    RECORDS[dispatch] = dict(RECORDS[dispatch], state='accepted')

                @staticmethod
                def receipt(dispatch, what):
                    return {'digest': 'acceptance-digest'}

            def launching(name, adapters):
                dispatch_id, owner, place, scratch, items = run_folders(name)
                made = receiver(dispatch_id, place, scratch, owner, supervision=None)
                made.dispatches = Refusing(conn)
                made.dispatches.place, made.dispatches.items = place, items
                made.config = {'adapters': adapters, 'store': str(store_path), 'principal': 'receiver',
                               'repository': 'repo-308'}
                made.runner, made.confined_checked, made.metering, made.host = (
                    {'runner': 'default', 'why': None}, {}, None, 'fixture-host')
                made.emit = lambda event: LOG.append((
                    'emit', event.get('event'), event.get('refusal'), os.path.lexists(place), os.path.lexists(scratch),
                    hold_state(dispatch_id), len(sent_for(dispatch_id))))
                contract = {'dispatch_id': dispatch_id, 'repository': 'repo-308', 'capability': {'adapter': 'engine'},
                            'reservation': {'project': ORCHARD['project']}, 'input': {'context': {}}}
                RECORDS[dispatch_id] = {'state': 'prepared', 'process': None, 'contract_digest': LA.D.digest(contract)}
                del LOG[:]
                return made, contract, dispatch_id, place, scratch, items

            row = 'f5/refused-before-spawn'
            R, contract, dispatch_id, place, scratch, items = launching('refused-60', {})
            R.launch(contract)
            check(row, 'a launch whose adapter is not registered is refused before any spawn, and the refusal is '
                       'recorded first: the folders on disk, their items present, the hold held, no event sent [%s]'
                  % (LOG[:1],),
                  LOG[:1] == [('refuse', 'unregistered_adapter:engine', 'prepared', True, 'present', 'present',
                               'admitted', 0)])
            check(row, 'the refusal is reported last, after the space end: the folders gone, the hold released, run '
                       'finished sent once [%s]' % (LOG[1:],),
                  LOG[1:] == [('emit', 'refused', 'unregistered_adapter:engine', False, False, 'released', 1)]
                  and [state_of(items[name]) for name in ('run', 'scratch')] == ['removed'] * 2
                  and (R.run_end or {}).get('sent') is True)

            row = 'f5/spawn-failed'
            R, contract, dispatch_id, place, scratch, items = launching('spawn-61', {'engine': {'argv': ['/nonexistent/engine']}})
            R._recheck = lambda offered: None
            R._qualify = lambda adapter: None
            R._login = lambda offered, adapter: None
            R._bind = lambda adapter, dispatch: None

            def failing(offered, acceptance, adapter):
                LOG.append(('spawn', os.path.isdir(place), hold_state(dispatch_id)))
                raise OSError(errno.ENOENT, 'No such file or directory')
            R._invoke = failing
            real_organ = LA._organ
            LA._organ = lambda name: (types.SimpleNamespace(handoff=lambda reader, host: None, Refused=RuntimeError)
                                      if name == 'control_memory' else real_organ(name))
            try:
                R.launch(contract)
            finally:
                LA._organ = real_organ
            check(row, 'the launch is accepted, the spawn fails, and the refusal is recorded with nothing of the run '
                       'judged: the folders on disk, their items present, the hold held, no event sent [%s]' % (LOG[:4],),
                  LOG[:4] == [('accept',), ('emit', 'accepted', None, True, True, 'admitted', 0),
                              ('spawn', True, 'admitted'),
                              ('refuse', 'spawn_failed:ENOENT', 'accepted', True, 'present', 'present', 'admitted', 0)])
            check(row, 'the refusal is reported last, after the space end: the folders gone, the hold released, run '
                       'finished sent once [%s]' % (LOG[4:],),
                  LOG[4:] == [('emit', 'refused', 'spawn_failed:ENOENT', False, False, 'released', 1)]
                  and [state_of(items[name]) for name in ('run', 'scratch')] == ['removed'] * 2
                  and (R.run_end or {}).get('sent') is True)
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # The second fix round: the re-review's N1 and N2
        # =====================================================================================
        try:
            SANDBOXES = STATE / 'sandboxes'
            SANDBOXES.mkdir()

            def sandbox(name, owner):
                """An agent repository the run owns outside its folders and outside every clone, as the
                sandbox prepare of VELDO-0302 will declare one: a real repository with the project's commits."""
                where = SANDBOXES / name
                git(temp, 'clone', '-q', str(REPOSITORY), str(where))
                return where, git(where, 'rev-parse', 'HEAD'), declared('agent_repository', {'path': str(where)}, owner)

            def refusals(made, dispatch_id):
                return [event.get('refusal') for event in made.observations if event.get('operation') == 'remove_run'
                        and event.get('dispatch_id') == dispatch_id and event.get('outcome') == 'refused']

            def versions(items):
                return [conn.execute('SELECT version FROM entities WHERE id=?', (items[name],)).fetchone()[0]
                        for name in ('root', 'work', 'scratch')]

            row = 'n1/own-items-ended'
            # The re-review's probe row with the expectation reversed: a run with its run directory and its
            # scratch folder, and an agent repository of the same owner outside its folders. No clone.
            dispatch_id, owner, place, scratch, items = run_folders('apart-71', hold=False)
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            where, head, repository_item = sandbox('apart-71', owner)
            R = receiver(dispatch_id, place, scratch, owner, supervision={'empty': True}, clones=C5)
            end = R._space_end(dispatch_id)
            check(row, 'a run whose owner has an agent repository elsewhere is sent run finished by its receiver, '
                       'once [%s %s %s]' % (end.get('sent'), end.get('reason'), sent_for(dispatch_id)),
                  end.get('sent') is True and sent_for(dispatch_id) == [('receiver', 'run_finished', dispatch_id)])
            check(row, 'every item of the run is ended by that event: the run directory, the scratch folder and the '
                       'agent repository are removed, the repository after its commit was kept [%s]'
                  % ([state_of(items['run']), state_of(items['scratch']), state_of(repository_item)],),
                  [state_of(items['run']), state_of(items['scratch']), state_of(repository_item)] == ['removed'] * 3
                  and not os.path.lexists(place) and not os.path.lexists(scratch) and not os.path.lexists(where)
                  and kept_at(repository_item, REPOSITORY, head)
                  and removal_of(repository_item).get('emitter') == 'receiver')
            dispatch_id, owner, place, scratch, items = run_folders('apart-72', hold=False)
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            where, head, repository_item = sandbox('apart-72', owner)
            N = runner(C5)
            N.leftovers[dispatch_id] = {'group': None, 'process': None}
            removed = [N.clear_runs() for _ in range(3)]
            check(row, 'the sweep does the same for a leftover of such a run: one event, and the three items removed '
                       '[%s %s %s]' % (removed, sent_for(dispatch_id), refusals(N, dispatch_id)),
                  removed == [[dispatch_id], [], []] and sent_for(dispatch_id) == [('runner.sweep', 'run_finished', dispatch_id)]
                  and [state_of(items['run']), state_of(items['scratch']), state_of(repository_item)] == ['removed'] * 3
                  and not os.path.lexists(where) and kept_at(repository_item, REPOSITORY, head)
                  and refusals(N, dispatch_id) == [] and N.leftovers == {})
            # A clone of the same owner that a teardown's event made due and whose carrying has not ended:
            # the ledger's signal does not take a due item, so the run's event cannot reach it.
            clone_id, dispatch_id, root, work, clone_head, clone_items = clone(C5, 'apart-73')
            owner = {'scope': A, 'ticket': 'VELDO-9273', 'run': {'id': dispatch_id, 'station': 'build'}}
            made_due = L.signal('run_finished', {'scope': A, 'ticket': 'VELDO-9273', 'run': dispatch_id})
            place, run_item = run_place(dispatch_id, 'VELDO-9273')
            where, head, repository_item = sandbox('apart-73', owner)
            before, length = versions(clone_items), journal_length()
            R = receiver(dispatch_id, place, None, None, supervision={'empty': True}, clones=C5)
            end = R._space_end(dispatch_id)
            check(row, 'with the run\'s clone handed to the ledger and left due, the receiver still sends run finished '
                       'for the run, and every item of the run that is no clone\'s is ended by it [%s %s %s]'
                  % (end.get('sent'), sorted(made_due.get('items') or ()) == sorted(clone_items.values()),
                     [state_of(run_item), state_of(repository_item)]),
                  sorted(made_due.get('items') or ()) == sorted(clone_items.values())
                  and end.get('sent') is True and sent_for(dispatch_id) == [('receiver', 'run_finished', dispatch_id)]
                  and [state_of(run_item), state_of(repository_item)] == ['removed'] * 2
                  and not os.path.lexists(place) and not os.path.lexists(where)
                  and kept_at(repository_item, REPOSITORY, head))
            check(row, 'the handed-over clone is untouched: its three items due at the version they had, the clone '
                       'whole and its pin held [%s %s]' % (states(clone_items), versions(clone_items) == before),
                  states(clone_items) == ['due'] * 3 and versions(clone_items) == before
                  and (work / 'tracked.txt').is_file() and readable(work, clone_head)
                  and len(C5._pins_held(clone_id)) == 1 and journal_length() > length)

            def named_by(dispatch_id, emitter):
                """What the events sent for the run by `emitter` named: one list of {item, version} for each."""
                return [named for sender, run, named in NAMED if run == dispatch_id and sender == emitter]

            def version_of(identity):
                return conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()[0]

            def exactly(named, *identities):
                """Whether one event named exactly these items, each at the version it has in `at`."""
                return (len(named) == 1 and sorted(one['item'] for one in named[0]) == sorted(identities)
                        and all(type(one['version']) is int and one['version'] > 0 for one in named[0]))

            row = 'n1/handed-over-clone-untouched'
            # The old N1 probe, closed: a clone a retirement handed to the ledger, deferred, and the run's own
            # items beside it. The event names the run's own items at their versions and never the clone's.
            clone_id, dispatch_id, root, work, clone_head, clone_items = clone(C5, 'apart-74')
            holder = process_entry(5874, '/', opened=str(work / 'tracked.txt'))
            N = runner(C5)
            N.reservations.slot(dispatch_id)
            first = N._retire(dispatch_id, 'completed', 'worker_reaped')
            owner = {'scope': A, 'ticket': 'VELDO-9274', 'run': {'id': dispatch_id, 'station': 'build'}}
            place, run_item = run_place(dispatch_id, 'VELDO-9274')
            where, head, repository_item = sandbox('apart-74', owner)
            before, was, length, mark = versions(clone_items), states(clone_items), journal_length(), len(sent_for(dispatch_id))
            read = {identity: version_of(identity) for identity in (run_item, repository_item)}
            check(row, 'the clone is handed over with its work tree deferred [%s %s]' % (first, was),
                  first is True and (N.retirements.handed.get(clone_id) or {}).get('teardown') == 'deferred'
                  and state_of(clone_items['work']) == 'deferred')
            # The runner (space-runner) stays refused for a signal that names items, these among them.
            subject = {'scope': A, 'ticket': 'VELDO-9274', 'run': dispatch_id}
            names = LA.space_named(L, 'run_finished', [str(place)], [subject], LA.clones_root(C5))
            by_runner = L.signal('run_finished', names, principal='space-runner')
            check(row, 'the runner is refused the signal that names these items, and nothing is written [%s]'
                  % (by_runner.get('reason'),),
                  by_runner.get('ok') is False and by_runner.get('reason') == 'space_not_permitted:space_signal'
                  and journal_length() == length and [state_of(run_item), state_of(repository_item)] == ['present'] * 2)
            R = receiver(dispatch_id, place, None, None, supervision={'empty': True}, clones=C5)
            R.space = space(principal='launch-receiver')
            end = R._space_end(dispatch_id)
            named = named_by(dispatch_id, 'receiver')
            check(row, 'the deferred clone does not hold the run\'s event back: the receiver sends run finished once, '
                       'as its own principal, and it names exactly the run directory and the agent repository, each '
                       'at the version read before the send [%s %s %s]' % (end.get('sent'), end.get('reason'), named),
                  end.get('sent') is True and sent_for(dispatch_id)[mark:] == [('receiver', 'run_finished', dispatch_id)]
                  and exactly(named, run_item, repository_item)
                  and {one['item']: one['version'] for one in named[0]} == read
                  and [event.get('principal') for event in L.observations
                       if event.get('operation') == 'space_signal' and event.get('outcome') == 'accepted'][-1:]
                  == ['launch-receiver'])
            check(row, 'every item of the run that is no clone\'s is ended by it: the run directory and the agent '
                       'repository are removed, the repository after its commit was kept [%s]'
                  % ([state_of(run_item), state_of(repository_item)],),
                  [state_of(run_item), state_of(repository_item)] == ['removed'] * 2
                  and not os.path.lexists(place) and not os.path.lexists(where)
                  and kept_at(repository_item, REPOSITORY, head)
                  and removal_of(repository_item).get('emitter') == 'receiver')
            check(row, 'the handed-over clone is not named and is untouched: its three items in the state and at the '
                       'version they had, the clone whole, its commit readable and its pin held [%s %s]'
                  % (states(clone_items), versions(clone_items) == before),
                  bool(named) and not ({one['item'] for one in named[0]} & set(clone_items.values()))
                  and states(clone_items) == was and versions(clone_items) == before
                  and state_of(clone_items['work']) == 'deferred'
                  and (work / 'tracked.txt').is_file() and readable(work, clone_head)
                  and len(C5._pins_held(clone_id)) == 1 and journal_length() > length)
            # The sweep does the same for a leftover of such a run.
            clone_id2, dispatch_id2, root2, work2, clone_head2, clone_items2 = clone(C5, 'apart-77')
            holder2 = process_entry(5877, '/', opened=str(work2 / 'tracked.txt'))
            N = runner(C5)
            N.reservations.slot(dispatch_id2)
            first = N._retire(dispatch_id2, 'completed', 'worker_reaped')
            owner2 = {'scope': A, 'ticket': 'VELDO-9277', 'run': {'id': dispatch_id2, 'station': 'build'}}
            place2, run_item2 = run_place(dispatch_id2, 'VELDO-9277')
            where2, head2, repository_item2 = sandbox('apart-77', owner2)
            before2, was2, mark2 = versions(clone_items2), states(clone_items2), len(sent_for(dispatch_id2))
            N.leftovers[dispatch_id2] = {'group': None, 'process': None}
            removed = [N.clear_runs() for _ in range(3)]
            named = named_by(dispatch_id2, 'runner.sweep')
            check(row, 'the sweep does the same for a leftover of such a run: one event over three sweeps, naming the '
                       'run directory and the agent repository and nothing of the clone; both are removed, and the '
                       'clone is as it was at the version it had [%s %s %s %s]'
                  % (first, removed, sent_for(dispatch_id2)[mark2:], states(clone_items2)),
                  first is True and state_of(clone_items2['work']) == 'deferred'
                  and removed == [[dispatch_id2], [], []]
                  and sent_for(dispatch_id2)[mark2:] == [('runner.sweep', 'run_finished', dispatch_id2)]
                  and exactly(named, run_item2, repository_item2)
                  and [state_of(run_item2), state_of(repository_item2)] == ['removed'] * 2
                  and not os.path.lexists(place2) and not os.path.lexists(where2)
                  and kept_at(repository_item2, REPOSITORY, head2)
                  and states(clone_items2) == was2 and versions(clone_items2) == before2
                  and (work2 / 'tracked.txt').is_file() and len(C5._pins_held(clone_id2)) == 1
                  and refusals(N, dispatch_id2) == [] and N.leftovers == {})
            # Once the holders have gone the runner's own sweeps send nothing more for these runs: nothing of
            # theirs is left to send for, and the clone is the ledger's, which retries it itself.
            shutil.rmtree(holder)
            shutil.rmtree(holder2)
            length, total = journal_length(), len(SENT)
            swept = [N.sweep() for _ in range(5)]
            check(row, 'after the holders have gone, five runner sweeps send nothing, make no retry and write nothing; '
                       'both clones stay the ledger\'s, deferred at the version they had, whole and pinned [%s %s %s]'
                  % (swept, len(SENT) - total, retries(N)),
                  swept == [[]] * 5 and len(SENT) == total and retries(N) == [] and journal_length() == length
                  and not N.retirements.pending()
                  and states(clone_items) == was and versions(clone_items) == before
                  and states(clone_items2) == was2 and versions(clone_items2) == before2
                  and readable(work, clone_head) and readable(work2, clone_head2)
                  and len(C5._pins_held(clone_id)) == 1 and len(C5._pins_held(clone_id2)) == 1)
            check(row, 'no event of this suite sent from the receiver or the sweep named an item of a clone',
                  bool(NAMED) and not any(
                      (L.item(one['item']) or {}).get('locator', {}).get('path', '').startswith(str(CLONES) + '/')
                      for sender, run, named in NAMED if sender in ('receiver', 'runner.sweep') for one in named))

            row = 'n1/changed-between-judge-and-send'
            # An item of the run changes after the receiver read it and before the ledger's command: the send
            # is refused whole, nothing of the run is ended, and nothing else is sent in its place.
            dispatch_id, owner, place, scratch, items = run_folders('apart-78', hold=False)
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            where, head, repository_item = sandbox('apart-78', owner)
            mine = [items['run'], items['scratch'], repository_item]
            read = {identity: version_of(identity) for identity in mine}
            length, answered = journal_length(), len(ANSWERS)
            INSIDE[dispatch_id] = lambda: L.measure(items['scratch'], 4321, 'run_finished')
            R = receiver(dispatch_id, place, scratch, owner, supervision={'empty': True}, clones=C5)
            end = R._space_end(dispatch_id)
            named = named_by(dispatch_id, 'receiver')
            check(row, 'the receiver named the run\'s three items at the versions it read, and one of them changed '
                       'before the ledger\'s command (its size was measured) [%s %s]' % (named, read),
                  exactly(named, *mine) and {one['item']: one['version'] for one in named[0]} == read
                  and version_of(items['scratch']) == read[items['scratch']] + 1 and dispatch_id not in INSIDE)
            check(row, 'the ledger refuses the whole send by the item that changed, and the receiver says so: not '
                       'sent, remove_refused with the ledger\'s reason [%s %s %s]'
                  % (ANSWERS[answered:], end.get('sent'), (end.get('removal') or {}).get('raised')),
                  ANSWERS[answered:] == [(dispatch_id, False, 'space_item_version:' + items['scratch'])]
                  and end.get('sent') is False and end.get('reason') == 'remove_refused'
                  and 'space_item_version:' + items['scratch'] in str((end.get('removal') or {}).get('raised')))
            check(row, 'nothing of the run is ended and nothing but the measure was written: the three items '
                       'present, the two that did not change at the version read, every folder on disk and the '
                       'repository at its commit [%s %s]'
                  % ([state_of(identity) for identity in mine], journal_length() - length),
                  [state_of(identity) for identity in mine] == ['present'] * 3 and journal_length() == length + 1
                  and version_of(items['run']) == read[items['run']]
                  and version_of(repository_item) == read[repository_item]
                  and place.is_dir() and (scratch / 'tmp.bin').is_file() and git(where, 'rev-parse', 'HEAD') == head
                  and sent_for(dispatch_id) == [('receiver', 'run_finished', dispatch_id)])
            # Nothing is stuck by it: no event reached the run directory, so it is a leftover the sweep may
            # send its one event for, with the versions read then.
            N = runner(C5)
            N.leftovers[dispatch_id] = {'group': None, 'process': None}
            removed = [N.clear_runs() for _ in range(2)]
            named = named_by(dispatch_id, 'runner.sweep')
            check(row, 'the sweep then sends the one event for the run, naming the three items at the versions they '
                       'have now, and all three are removed, the repository after its commit was kept [%s %s]'
                  % (removed, [state_of(identity) for identity in mine]),
                  removed == [[dispatch_id], []] and exactly(named, *mine)
                  and {one['item']: one['version'] for one in named[0]}[items['scratch']] == read[items['scratch']] + 1
                  and [state_of(identity) for identity in mine] == ['removed'] * 3
                  and not os.path.lexists(place) and not os.path.lexists(scratch) and not os.path.lexists(where)
                  and kept_at(repository_item, REPOSITORY, head))

            row = 'n1/live-clone-holds-nothing-back'
            # The lead's decision on N1's open point: a clone of the same owner that is still live (no teardown
            # has run: its items present) does not hold the run's send back, and is not reached by it.
            clone_id, dispatch_id, root, work, clone_head, clone_items = clone(C5, 'live-81')
            owner = {'scope': A, 'ticket': 'VELDO-9281', 'run': {'id': dispatch_id, 'station': 'build'}}
            place, run_item = run_place(dispatch_id, 'VELDO-9281')
            where, head, repository_item = sandbox('live-81', owner)
            before, read = versions(clone_items), {identity: version_of(identity) for identity in (run_item, repository_item)}
            R = receiver(dispatch_id, place, None, None, supervision={'empty': True}, clones=C5)
            end = R._space_end(dispatch_id)
            named = named_by(dispatch_id, 'receiver')
            check(row, 'with a live clone of the same owner the receiver sends run finished, once, naming exactly the '
                       'run directory and the agent repository at the versions read [%s %s %s]'
                  % (end.get('sent'), end.get('reason'), named),
                  end.get('sent') is True and sent_for(dispatch_id) == [('receiver', 'run_finished', dispatch_id)]
                  and exactly(named, run_item, repository_item)
                  and {one['item']: one['version'] for one in named[0]} == read)
            check(row, 'the run\'s own items are ended: the run directory and the agent repository are removed, the '
                       'repository after its commit was kept [%s]' % ([state_of(run_item), state_of(repository_item)],),
                  [state_of(run_item), state_of(repository_item)] == ['removed'] * 2
                  and not os.path.lexists(place) and not os.path.lexists(where)
                  and kept_at(repository_item, REPOSITORY, head))
            check(row, 'the live clone is not named and not reached: its three items present at the version they had, '
                       'the clone whole, its commit readable, its pin held [%s]' % (states(clone_items),),
                  states(clone_items) == ['present'] * 3 and versions(clone_items) == before
                  and (work / 'tracked.txt').is_file() and (root / CL.MANIFEST).is_file()
                  and readable(work, clone_head) and len(C5._pins_held(clone_id)) == 1)
            # The sweep does the same for a leftover of such a run.
            clone_id2, dispatch_id2, root2, work2, clone_head2, clone_items2 = clone(C5, 'live-82')
            place2, run_item2 = run_place(dispatch_id2, 'VELDO-9282')
            before2 = versions(clone_items2)
            N = runner(C5)
            N.reservations.slot(dispatch_id2)
            N.leftovers[dispatch_id2] = {'group': None, 'process': None}
            removed = [N.clear_runs() for _ in range(3)]
            check(row, 'the sweep does the same for a leftover whose clone is live: one event over three sweeps, the '
                       'run directory removed, no refusal recorded, the clone present at the version it had [%s %s %s]'
                  % (removed, sent_for(dispatch_id2), refusals(N, dispatch_id2)),
                  removed == [[dispatch_id2], [], []]
                  and sent_for(dispatch_id2) == [('runner.sweep', 'run_finished', dispatch_id2)]
                  and exactly(named_by(dispatch_id2, 'runner.sweep'), run_item2)
                  and state_of(run_item2) == 'removed' and not os.path.lexists(place2)
                  and refusals(N, dispatch_id2) == [] and N.leftovers == {}
                  and states(clone_items2) == ['present'] * 3 and versions(clone_items2) == before2
                  and (work2 / 'tracked.txt').is_file() and len(C5._pins_held(clone_id2)) == 1)
            # Each clone is then ended by its own teardown, which was not waited for.
            first = [N._retire(dispatch_id, 'completed', 'worker_reaped'), N._retire(dispatch_id2, 'completed', 'worker_reaped')]
            check(row, 'each clone is then removed by its own teardown, one event each [%s %s %s]'
                  % (first, states(clone_items), states(clone_items2)),
                  first == [True, True] and states(clone_items) == ['removed'] * 3 and states(clone_items2) == ['removed'] * 3
                  and len(sent_for(dispatch_id, 'clone.teardown')) == 1 and len(sent_for(dispatch_id2, 'clone.teardown')) == 1
                  and not os.path.lexists(root) and not os.path.lexists(root2)
                  and C5._pins_held(clone_id) == [] and C5._pins_held(clone_id2) == [])

            row = 'n1/teardown-names-its-clone-only'
            # The teardown first, while the run's own items are live: it names the clone's three items at the
            # versions read and nothing else of that owner.
            clone_id, dispatch_id, root, work, clone_head, clone_items = clone(C5, 'only-83')
            owner = {'scope': A, 'ticket': 'VELDO-9283', 'run': {'id': dispatch_id, 'station': 'build'}}
            place, run_item = run_place(dispatch_id, 'VELDO-9283')
            where, head, repository_item = sandbox('only-83', owner)
            outside = [run_item, repository_item]
            read = {identity: version_of(identity) for identity in clone_items.values()}
            was, length = {identity: version_of(identity) for identity in outside}, journal_length()
            C5.retire(C5.handle(clone_id))
            named = named_by(dispatch_id, 'clone.teardown')
            check(row, 'the teardown sends run finished once, and it names exactly the clone\'s root, work tree and '
                       'scratch folder, each at the version read before the send [%s]' % (named,),
                  sent_for(dispatch_id) == [('clone.teardown', 'run_finished', dispatch_id)]
                  and exactly(named, *clone_items.values())
                  and {one['item']: one['version'] for one in named[0]} == read)
            check(row, 'the clone is removed by it and its pin released [%s]' % (states(clone_items),),
                  states(clone_items) == ['removed'] * 3 and not os.path.lexists(root)
                  and C5._pins_held(clone_id) == [] and journal_length() > length
                  and C5.observations[-1].get('outcome') == 'retired')
            check(row, 'nothing outside the clone is named or reached: the run directory and the agent repository of '
                       'the same owner are present at the version they had, on disk, the repository at its commit [%s]'
                  % ([state_of(identity) for identity in outside],),
                  bool(named) and not ({one['item'] for one in named[0]} & set(outside))
                  and [state_of(identity) for identity in outside] == ['present'] * 2
                  and {identity: version_of(identity) for identity in outside} == was
                  and text_of(place / LA.RUN_CONFIG / 'settings.json') == '{"generated": true}\n'
                  and git(where, 'rev-parse', 'HEAD') == head and removal_of(run_item) == {})
            check(row, 'no teardown of this suite named an item that is not at or beneath its own clone\'s root',
                  any(sender == 'clone.teardown' for sender, run, named in NAMED) and all(
                      len({(L.item(one['item']) or {}).get('locator', {}).get('path', '')[len(str(CLONES)) + 1:].split('/')[0]
                           for one in named}) == 1
                      and all((L.item(one['item']) or {}).get('locator', {}).get('path', '').startswith(str(CLONES) + '/')
                              for one in named)
                      for sender, run, named in NAMED if sender in ('clone.teardown', 'clone.provision')))
            # The run's own send then ends what is the run's.
            end = receiver(dispatch_id, place, None, None, supervision={'empty': True}, clones=C5)._space_end(dispatch_id)
            check(row, 'the receiver\'s own send then ends the run directory and the agent repository [%s %s]'
                  % (end.get('sent'), [state_of(identity) for identity in outside]),
                  end.get('sent') is True and [state_of(identity) for identity in outside] == ['removed'] * 2
                  and exactly(named_by(dispatch_id, 'receiver'), *outside) and kept_at(repository_item, REPOSITORY, head))

            row = 'n1/teardown-changed-between-judge-and-send'
            # An item of the clone changes after the teardown read it and before the ledger's command: the
            # send is refused whole, nothing of the clone is ended, and nothing else is sent in its place.
            clone_id, dispatch_id, root, work, clone_head, clone_items = clone(C5, 'stale-84')
            place, run_item = run_place(dispatch_id, 'VELDO-9284')
            mine = [clone_items[name] for name in ('root', 'work', 'scratch')]
            read = {identity: version_of(identity) for identity in mine}
            ran, length, answered = version_of(run_item), journal_length(), len(ANSWERS)
            INSIDE[dispatch_id] = lambda: L.measure(clone_items['scratch'], 4321, 'run_finished')
            refused = None
            try:
                C5.retire(C5.handle(clone_id))
            except CL.Refused as refusal:
                refused = refusal.code
            named = named_by(dispatch_id, 'clone.teardown')
            event = C5.observations[-1]
            check(row, 'the teardown named the clone\'s three items at the versions it read, and one of them changed '
                       'before the ledger\'s command (its size was measured) [%s %s]' % (named, read),
                  exactly(named, *mine) and {one['item']: one['version'] for one in named[0]} == read
                  and version_of(clone_items['scratch']) == read[clone_items['scratch']] + 1 and dispatch_id not in INSIDE)
            check(row, 'the ledger refuses the whole send by the item that changed, and the teardown is refused with '
                       'the ledger\'s reason: remove_refused, no pin released [%s %s %s]'
                  % (ANSWERS[answered:], refused, (event.get('space') or {}).get('raised')),
                  ANSWERS[answered:] == [(dispatch_id, False, 'space_item_version:' + clone_items['scratch'])]
                  and refused == 'space_deferred:remove_refused' and event.get('outcome') == 'refused'
                  and 'space_item_version:' + clone_items['scratch'] in str((event.get('space') or {}).get('raised'))
                  and event.get('released') == [] and len(C5._pins_held(clone_id)) == 1)
            check(row, 'nothing of the clone is ended and nothing but the measure was written: the three items '
                       'present, the two that did not change at the version read, the clone whole and its commit '
                       'readable; one event was sent, and the run directory of the same owner is as it was [%s %s]'
                  % (states(clone_items), journal_length() - length),
                  states(clone_items) == ['present'] * 3 and journal_length() == length + 1
                  and version_of(clone_items['root']) == read[clone_items['root']]
                  and version_of(clone_items['work']) == read[clone_items['work']]
                  and (work / 'tracked.txt').is_file() and (root / CL.MANIFEST).is_file() and readable(work, clone_head)
                  and sent_for(dispatch_id) == [('clone.teardown', 'run_finished', dispatch_id)]
                  and state_of(run_item) == 'present' and version_of(run_item) == ran and place.is_dir())
            # Nothing is stuck by it: the next teardown reads the versions again.
            C5.retire(C5.handle(clone_id))
            named = named_by(dispatch_id, 'clone.teardown')
            check(row, 'the next teardown names the three items at the versions they have then and the clone is '
                       'removed, its pin released; the run directory is still the run\'s [%s %s]'
                  % (states(clone_items), state_of(run_item)),
                  len(named) == 2 and exactly(named[1:], *mine)
                  and {one['item']: one['version'] for one in named[1]}[clone_items['scratch']]
                  == read[clone_items['scratch']] + 1
                  and states(clone_items) == ['removed'] * 3 and not os.path.lexists(root)
                  and C5._pins_held(clone_id) == [] and state_of(run_item) == 'present' and place.is_dir())

            def owner_kept(identity):
                """The owner marked the item Keep: it is made due by a signal that names it and written kept
                with the owner's mark, as the owner (the owner's settled answer, in one command, is
                VELDO-0318's). Returns its version afterwards."""
                due = L.signal('run_finished', {'items': [{'item': identity, 'version': version_of(identity)}]})
                marked = L.outcome(identity, 'kept', {'owner_keep': {'at': NOW, 'answer': 'keep'}}, principal='owner')
                if not (due.get('ok') and marked.get('ok')):
                    raise RuntimeError('the fixture could not mark Keep: %s %s' % (due.get('reason'), marked.get('reason')))
                return version_of(identity)

            def still_kept(identity, at):
                """The item is as the owner's Keep left it: kept, the mark on it, ending on run finished as
                before, and no command wrote it since."""
                record = L.item(identity) or {}
                return (record.get('state') == 'kept' and (record.get('owner_keep') or {}).get('by') == 'owner'
                        and 'run_finished' in ((record.get('ends_on') or {}).get('events') or ())
                        and version_of(identity) == at and removal_of(identity).get('method') is None)

            row = 'keep/run-kept-item-not-named'
            # The review's finding 1: an item of the run that the owner marked Keep. The event would reach
            # it by its state and its owner; it is left out, and the send of the others goes through.
            dispatch_id, owner, place, scratch, items = run_folders('keep-85', hold=False)
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            where, head, repository_item = sandbox('keep-85', owner)
            kept_version = owner_kept(repository_item)
            read = {identity: version_of(identity) for identity in (items['run'], items['scratch'])}
            answered = len(ANSWERS)
            R = receiver(dispatch_id, place, scratch, owner, supervision={'empty': True}, clones=C5)
            end = R._space_end(dispatch_id)
            named = named_by(dispatch_id, 'receiver')
            check(row, 'an agent repository of the run is kept with the owner\'s mark: a state the event reaches, '
                       'ending on run finished, of the run\'s own owner [%s]' % (state_of(repository_item),),
                  still_kept(repository_item, kept_version)
                  and LA._space_owner(L.item(repository_item)) == LA._space_owner(L.item(items['run'])))
            check(row, 'the receiver sends run finished once, naming exactly the run directory and the scratch folder '
                       'at the versions read: the item the owner kept is left out [%s %s %s]'
                  % (end.get('sent'), end.get('reason'), named),
                  sent_for(dispatch_id) == [('receiver', 'run_finished', dispatch_id)]
                  and exactly(named, items['run'], items['scratch'])
                  and {one['item']: one['version'] for one in named[0]} == read)
            check(row, 'the ledger accepts the send and the others are ended: the run directory and the scratch '
                       'folder are removed [%s %s]' % (ANSWERS[answered:], [state_of(items['run']), state_of(items['scratch'])]),
                  [(run, ok) for run, ok, reason in ANSWERS[answered:]] == [(dispatch_id, True)]
                  and end.get('sent') is True
                  and [state_of(items['run']), state_of(items['scratch'])] == ['removed'] * 2
                  and not os.path.lexists(place) and not os.path.lexists(scratch))
            check(row, 'the item the owner kept is as it was: kept, the owner\'s mark on it, at the version it had, '
                       'and the repository on disk at its commit [%s %s]'
                  % (state_of(repository_item), version_of(repository_item) == kept_version),
                  still_kept(repository_item, kept_version) and git(where, 'rev-parse', 'HEAD') == head
                  and (where / 'tracked.txt').is_file())
            # The sweep does the same for a leftover of such a run.
            dispatch_id, owner, place, scratch, items = run_folders('keep-86', hold=False)
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            where, head, repository_item = sandbox('keep-86', owner)
            kept_version = owner_kept(repository_item)
            answered = len(ANSWERS)
            N = runner(C5)
            N.leftovers[dispatch_id] = {'group': None, 'process': None}
            removed = [N.clear_runs() for _ in range(3)]
            named = named_by(dispatch_id, 'runner.sweep')
            check(row, 'the sweep does the same for a leftover of such a run: one event over three sweeps, accepted, '
                       'naming the run directory and the scratch folder; both are removed, and the repository the '
                       'owner kept is as it was, on disk at its commit [%s %s %s %s]'
                  % (removed, ANSWERS[answered:], refusals(N, dispatch_id), state_of(repository_item)),
                  removed == [[dispatch_id], [], []]
                  and sent_for(dispatch_id) == [('runner.sweep', 'run_finished', dispatch_id)]
                  and [(run, ok) for run, ok, reason in ANSWERS[answered:]] == [(dispatch_id, True)]
                  and exactly(named, items['run'], items['scratch'])
                  and [state_of(items['run']), state_of(items['scratch'])] == ['removed'] * 2
                  and not os.path.lexists(place) and not os.path.lexists(scratch)
                  and refusals(N, dispatch_id) == [] and N.leftovers == {}
                  and still_kept(repository_item, kept_version) and git(where, 'rev-parse', 'HEAD') == head)

            row = 'keep/teardown-kept-item-not-named'
            # The same for the clone's teardown: an item beneath the clone's root that the owner marked Keep.
            clone_id, dispatch_id, root, work, clone_head, clone_items = clone(C5, 'keep-87')
            kept_version = owner_kept(clone_items['scratch'])
            read = {identity: version_of(identity) for identity in (clone_items['root'], clone_items['work'])}
            answered, refused = len(ANSWERS), None
            try:
                C5.retire(C5.handle(clone_id))
            except CL.Refused as refusal:
                refused = refusal.code
            named = named_by(dispatch_id, 'clone.teardown')
            event = C5.observations[-1]
            check(row, 'the teardown sends run finished once, naming exactly the clone\'s root and its work tree at '
                       'the versions read: the scratch folder the owner kept is left out [%s]' % (named,),
                  sent_for(dispatch_id) == [('clone.teardown', 'run_finished', dispatch_id)]
                  and exactly(named, clone_items['root'], clone_items['work'])
                  and {one['item']: one['version'] for one in named[0]} == read)
            check(row, 'the ledger accepts the send: nothing raised, and the teardown hands the clone over as '
                       'deferred by a rule, not as a send the ledger refused [%s %s %s]'
                  % (ANSWERS[answered:], refused, (event.get('space') or {}).get('raised')),
                  [(run, ok) for run, ok, reason in ANSWERS[answered:]] == [(dispatch_id, True)]
                  and str(refused).startswith('space_deferred:') and refused != 'space_deferred:remove_refused'
                  and not (event.get('space') or {}).get('raised'))
            check(row, 'the work tree is ended by it: removed, after its commit was kept, and its pin released after '
                       'that removal [%s %s]' % (states(clone_items), event.get('released')),
                  state_of(clone_items['work']) == 'removed' and not os.path.lexists(work)
                  and kept_at(clone_items['work'], REPOSITORY, clone_head)
                  and len(event.get('released') or ()) == 1 and C5._pins_held(clone_id) == [])
            check(row, 'the folder the owner kept is as it was: kept, the owner\'s mark on it, at the version it had, '
                       'on disk with its file; the clone\'s root, which holds it, is deferred and on disk [%s %s]'
                  % (states(clone_items), version_of(clone_items['scratch']) == kept_version),
                  still_kept(clone_items['scratch'], kept_version)
                  and (CL._scratch(root, dispatch_id) / 'tmp.bin').is_file()
                  and state_of(clone_items['root']) == 'deferred' and root.is_dir())

            row = 'n2/observations-bounded'
            dispatch_id = 'dispatch/bound-75'
            RECORDS[dispatch_id] = {'state': 'exited', 'process': None}
            place, run_item = run_place(dispatch_id, 'VELDO-9475', confirm=False)
            N = runner()
            N.leftovers[dispatch_id] = {'group': None, 'process': None}
            removed = [N.clear_runs() for _ in range(6)]
            check(row, 'a leftover that a sweep looked at once and could not move (its item is one no event reaches, '
                       'so nothing was named) is recorded once and dropped from memory: no command and two '
                       'observations over six sweeps [%s %s]' % (sent_for(dispatch_id), refusals(N, dispatch_id)),
                  removed == [[]] * 6 and sent_for(dispatch_id) == []
                  and refusals(N, dispatch_id) == ['space_deferred:declared', 'run_finished_sent']
                  and dispatch_id not in N.leftovers and place.is_dir() and state_of(run_item) == 'declared')
            clone_id, dispatch_id, root, work, clone_head, clone_items = clone(C5, 'bound-76')
            consumer_id = consumer(C5, clone_id, root, 'consumer-76')
            place, run_item = run_place(dispatch_id, 'VELDO-9276')
            N = runner(C5)
            N.leftovers[dispatch_id] = {'group': None, 'process': None}
            length = journal_length()
            removed = [N.clear_runs() for _ in range(6)]
            check(row, 'a leftover held back by a consumer of its clone adds one observation over six sweeps, and stays '
                       'a leftover [%s]' % (refusals(N, dispatch_id),),
                  removed == [[]] * 6 and refusals(N, dispatch_id) == ['clone_in_use'] and dispatch_id in N.leftovers
                  and sent_for(dispatch_id) == [] and journal_length() == length)
            RECORDS[consumer_id] = {'state': 'exited', 'process': None}
            removed = [N.clear_runs() for _ in range(6)]
            check(row, 'once the consumer has ended the live clone holds nothing back: the first of six more sweeps '
                       'sends the one event, the run directory goes and the leftover with it, no further refusal is '
                       'recorded, and the clone\'s items are present as they were [%s %s %s]'
                  % (removed, refusals(N, dispatch_id), sent_for(dispatch_id)),
                  removed == [[dispatch_id]] + [[]] * 5 and refusals(N, dispatch_id) == ['clone_in_use']
                  and dispatch_id not in N.leftovers and not os.path.lexists(place) and state_of(run_item) == 'removed'
                  and sent_for(dispatch_id) == [('runner.sweep', 'run_finished', dispatch_id)]
                  and states(clone_items) == ['present'] * 3 and (work / 'tracked.txt').is_file())
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # No module deletes by itself, and the copies are the canon
        # =====================================================================================
        try:
            row = 'paths/no-delete-and-canon'
            check(row, 'no drive of this suite made the launch module or the clone provisioner delete by itself [%s]'
                  % (DELETES[:3],), DELETES == [])
            for name in CHANGED:
                check(row, 'the engine canon engine/.veldo/%s equals this repository copy' % name,
                      (ROOT / 'engine' / '.veldo' / name).is_file()
                      and (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())
        except Exception as error:
            stopped(row, error)

    except Exception as error:
        stopped(row, error)
    finally:
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0308 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v308_run_finished_suite()
