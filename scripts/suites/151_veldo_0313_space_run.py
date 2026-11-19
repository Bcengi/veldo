"""VELDO-0313: the CLI's space verb and the run wrapper.

Run: python3 scripts/selftest.py --suite 151_veldo_0313_space_run

Only shared ROOT and expect are consumed. The one file this ticket changes is the CLI, bin/veldo, loaded
by path with its ROOT set to this repository, so the modules it loads are this repository's .veldo: the
Ledger, admission, Signal, the kind registry, the probes, the removers, the keeper, the census of
control_launch.py and the Docker adapter's label. The ledger is a real one on a real store under one
temporary folder. Every folder, repository and worktree is real, made with plain git; every command
the wrapper runs is a real process under the wrapper's own supervisor, and a removal really deletes.
The project orchard is put in act mode by the owner's own signed command with a real key; the project
meadow has no mode record and is in report mode.

Every row plants what it is about, drives the CLI's own verb at it, and reads the disk and the ledger
again as the verb returns.

AC1 rows. ac1/declared-started-ended (the run is issued to space-runner by the authority, through the
issuer the wiring carries; its scratch root is an item owned by the run with its station, declared by
the wrapper before the folder is made, with the run's supervisor as its recorded process; the command
is given the temporary folder, the space label, which is the run's identity, and the compose project
name derived from it; when the wrapper returns, every command of the run in the journal is
space-runner's, in the order hold, admit, declare, confirm, then the census, then one signal, then the
outcomes, and the release last). ac1/build-output-has-item-and-goes (the declared falsifier row: the
ignored build folder the command made in its recorded worktree has a build output item of the run,
declared by the census, and is removed at run finished with the scratch root; the untracked notes the
command wrote, an ignored folder only the repository's own exclude file covers, and the tracked file
stay, and the worktree's item is present). ac1/unread-group-sends-nothing (a group nobody could read,
and one the kernel shows a process in: no census, no signal, nothing written, the scratch root present
and on disk with its file, the hold held). ac1/only-the-runs-own-items (an item of the run the owner
marked Keep, with its file, and the scratch root of another run of the same project and ticket: run
finished removes the run's own scratch root and neither of those; the owner's mark and both versions
are as they were; and space-runner is refused, by the Ledger, a signal for another run, a signal that
names items, and worktree abandoned).

The fix round's rows (the review of VELDO-0313). fix1/existing-work-is-never-scratch (finding 1, the
reviewer's case: a worktree's untracked folder holding the only copy of some work, and a hand-made
folder under the project's worktree root, are each refused as scratch, with and without a session, and
as any other kind because they exist; then session ended is signalled for that session as the hook
event's consumer will: no item was made, nothing became due and both files are on disk; a session's
scratch folder that does not exist yet is refused too, so nothing a later writer puts there is ever an
item of this verb). fix2/returns-at-the-commands-exit (finding 2: a command that ends at once and
leaves a process outside its session returns its own status at once; run finished is not sent, the
processes left are named, the scratch root is present with its file and the hold is held; and rule 3
of any judge holds the scratch root by its recorded process, the run's supervisor, read from the
kernel's own table). fix2/end-follows-their-exit (the run's end sleeps until that process exits and
is made then: the process ran to its own last line and saw its file there, nothing was sent before it
ended, and then the scratch root went and the hold was released). In fix round 3 the first of the two
reads rule 3 only after the supervisor's own word that it is asleep on what was left, written from
inside its wait, and the second reads it once more just before the suite lets that process end.
fix2/captured-output-ends-at-return (fix round 3, the re-review's finding 2: a caller that reads the
wrapper's standard output and standard error through a pipe to its end, as a shell's $(...) does,
around a command that leaves a sleep with no end: the wrapper returns at once, the caller's read ends
at once with what the command wrote, the supervisor stays with its descriptors 0, 1 and 2 on
/dev/null, and the run is held until the suite ends that sleep). fix3/handed-outside-the-tree
(finding 3, the reviewer's case: the command hands work to a server that was running before the run;
the server's worker is no descendant of the command and carries the run's space label; the wrapper
returns at once and sends nothing while that worker lives, naming it by the label; the end follows
its exit). fix3/unread-process-holds (fix round 2, fail closed: a process whose environment the kernel
will not show and that started after the run began may be the run's, whatever started it, so the run
stays open, nothing is sent and the hold stays; one that was running before the run began cannot be
the run's and does not hold it; of the process reader's block for such a process only the label
decides, and only one that was read: a whole block with no label read, no block, a block that is not
whole, one with another start time and a refused reader each leave the run open; a label that is this
run's makes the process a holder by its label; and when the label of every unread process was read
and none is this run's, the run is over while they live). fix3/environment-not-whole-holds (the review
of VELDO-0344, finding 1, in the CLI's own scan: a process that carries the run's label and executes
itself again without end is a holder in every one of 150 reads of the kernel's table, by its label or
unread, never missing; a process with an environment of no bytes is unread and holds; one with an
environment and no label is no holder). fix3/same-program-holds (the review of that fix, finding 1: a
process that shares its parent's memory, as posix_spawn makes it, executes a program with the run's
label between the scan's open of its environ entry and the read; the read returns the parent's
environment, which has no label, and the scan does not take it for the process's own: it reads once
more and the process holds the run by its label). fix3/rewritten-environment-cwd-in-scratch and
fix3/rewritten-environment-open-file-in-worktree (the accepted limit put to the proof: a worker a
server started for the command, outside the command's tree and its group, carries the run's label
and then writes over its own environment area, as a program that sets its process title does; it is
no holder and run finished is sent while it lives; with its working directory in the run's scratch
root the scratch root is deferred as in use and stays on disk; with a file open in the build folder
of the run's worktree the build folder is deferred as in use and stays, while the scratch root it
does not hold goes; in both the table rule 4 reads holds the kernel's own entry of the worker and of
no other process, so what is kept is kept for the worker). fix3/rule-3-reads-the-kernel (a group that gains a process after the end has begun: rule 3
asks the kernel again for each item, so the scratch root is deferred as in use and stays, and the hold
is not released). fix3/the-house-group (on a host with the owner's user manager: the command runs in
the house's own transient scope, run finished is not sent while a process it left is in that group,
and the end follows its exit; without a manager the row stands down by name. What of the house's
group does not depend on a run's end is in suite 152_veldo_0313_house_group, which the gate runs
outside its confinement: the scope's name and slice, the membership the kernel lists, a record that
is not the run's scope, and the group read empty once the process has gone).
fix4/docker-objects-are-items (finding 4: at the run's end the container that carries the run's label
and the one that carries its compose project name are declared as space-runner, owned by the run, and
go at run finished through the engine's own stop and remove; another run's container and one with no
label get no item and stay; an engine that cannot be read is named and nothing of it is recorded).
fix5/no-issuer-no-run (finding 5: a wiring with no issuer records no run, writes nothing, and the
command still runs unchanged; the wrapper holds no call of the Ledger's issue). fix6/scratch-not-made
(finding 6: a scratch folder that could not be made leaves its item declared, says so, and sends no
gone as space-runner; the command still runs with its own temporary folder).

Fix round 4 of VELDO-0315 (its second re-review, finding 1: a supervisor that left when its report
reader went, which is what a wrapper does when it returns). supervise/report-loss-keeps-supervising
(the wrapper goes while the command runs: the supervisor is there a second and a half later, the
command runs to its own last line, and the supervisor then ends with the command's status, or stays
on processes the kernel shows and this account cannot read, each named) and
supervise/report-loss-end-is-made (the end of that run, made as the follower makes it: run finished
is sent, the scratch root goes and the hold is released). supervise/stop-after-the-command-ends-nothing
(a command that left a process: after the staying line the wrapper's end of the report is closed and
the supervisor is sent SIGTERM and SIGHUP; a second and a half later the kernel shows it, rule 3
holds the scratch root by it, and nothing was sent) and supervise/stop-after-the-command-end-is-made
(the fixture ends the process the command left, and run finished follows). fix2/end-follows-their-exit
also waits a second and a half after the wrapper's return and finds the supervisor there, and the
end of fix2/captured-output-ends-at-return's run is the row fix2/captured-end-follows.
supervise/staying-is-idle (twelve processes this account cannot read start during the run and end one
by one while the supervisor stays on a process the command left: over thirty seconds the supervisor
uses under one percent of a core and makes no pass over the process table, read as the kernel's count
of its read calls).

Fix round 5 of VELDO-0315 (its third re-review). supervise/wait-reads-again-at-a-read-holders-exit
(finding 1: the wait is given a process of the run that ends after a second and a process nobody
could read that lives on, and a second read that names neither: it returns at the first one's exit,
not at the second's; and the exit of an unread process, while a process of the run lives, costs no
read). supervise/wrapper-gone-the-follower-makes-the-end (finding 2: the wrapper goes while the
command runs and the command leaves nothing; the real space_supervise, in a process of its own, makes
the run's end through its follower, after it has itself ended. The row is about that branch alone, so
it has no ledger: the end it makes is a stand-in that records what it was given, and a process this
account cannot read is no holder there, as with the process reader).
supervise/none-stays-on-nothing (finding 3: when the suite ends, each supervisor it started that the
kernel still shows is classified before it is ended: one that stays while the kernel shows no process
this account cannot read that started after it stays on nothing, and the row is red and names it).

WHAT A FIXTURE LEAVES. Every row ends what its command left before the row ends, by its latch. On a
host shared with other accounts' containers a supervisor also stays on their processes, which this
account cannot read (fail closed), for as long as they keep starting. So the suite ends every
supervisor it started that is still there when the suite ends: they are the suite's own children.
supervise/none-stays-on-nothing reads each of them first, and no row reads them after that.

AC2 rows. ac2/command-status (the wrapper returns the command's own status: 0, 7, 143 for a command a
signal ended, 127 for a command that is not there; each of those runs ends with its hold released).
ac2/act-waits-75 (the declared falsifier row: act mode with too little space: 75, the numbers on
standard error, the command's marker file not there, no scratch root made, no item of the run, and the
hold released, never left admitted). ac2/report-starts (report mode with the same numbers: they are
printed, the command starts and its status is returned, and the hold was advised before it was
released).

AC3 rows. ac3/record-refusals (the declared falsifier row among them: an unknown kind, a folder outside
every known root, a path on the protect list, a path with a .. segment and a link that leads to a
protected folder are each refused by name with exit 1; no item is made and the journal does not move;
scratch, build output and evidence are kinds the verb does not record, and a folder that exists is
refused whatever its kind). ac3/record-accepted (a worktree a script is about to make is declared
before it is made, then made with plain git and confirmed: present, creator record, owned by its
project, written as space-observer; a path inside it is refused). ac3/event-types (the verb takes released alone, design 6.9 and the
lead's decision at assembly; the hooks' three types, session started, session ended and ref changed, are
refused by name, with a ledger and with none, before anything is sent or spooled; any other type, an
owner's action among them, is refused by name; a released event that names a path outside every known
root or on the protect list is refused by name; released is handed to the Ledger as space-observer).

AC4 rows. ac4/no-installation-runs-unchanged (the declared falsifier row: with no central
installation the wrapper says so and the command starts, with its own arguments, environment and
folder and its own status, in this process and as a real CLI process). ac4/each-verb-says-so (record,
event, the hooks' record, event and replay, and sign each say there is no central installation; an
installation whose ledger this process cannot reach, and one whose switch is off, run the command
unchanged and say why).

THE PROCESS TABLE. What holds a run is read from the kernel's own table, in the suite's process and in
the run's supervisor, and a process that started after a run began and whose environment cannot be
read holds that run (fail closed, fix round 2). So the suite is green in a process table of its own,
which the gate's confinement and the mutation workers give it. Run unconfined on a host shared with
other sessions and without the process reader, its rows meet their processes: an end is then not
made, and a row that follows an end is red after the suite's own limit and says what held it. That is
the decision's answer for such a host, not a fault of the row; no row is passed or stood down for it.

STAND-INS. The wiring an installation gives the CLI (the mapping the receiver is given) is made here:
nothing serves the ledger to a CLI process yet (VELDO-0323), so the issuer in it is the suite calling
the authority's own issue, and the run's end for a command that left a process is driven by the suite
calling the function the run's supervisor calls (_space_ended), in this process. The containment group
is the house's own only in fix3/the-house-group: the gate's confinement has no user manager, so every
other row is given a group nobody joined, or one that says what the row is about; what the supervisor
sees and what the process table shows are the kernel's in every row. The Docker engine is a stand-in
that holds what a row plants. The worktree the wrapped command runs in is declared by the suite
(VELDO-0302, 0311). The two checks of a switch to act (VELDO-0332 and 0339)
allow. Free space is a function of the suite. The docker client is a function with no container
anywhere, and the process table the rules of Signal read is a folder shaped as the kernel's with no entry; what
holds a run (its supervisor, its descendants, a labelled process) is always read from the kernel's own
table. The owner's Keep is written as VELDO-0308's
suite writes it.
"""


def _v313_space_run_suite():
    import importlib.machinery
    import importlib.util
    import io
    import json
    import os
    import shutil
    import subprocess
    import sys
    import tempfile
    import time
    import types
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'veldo': ROOT / "bin" / "veldo",
    }
    VELDO = ROOT / '.veldo'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

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

    ROWS = ('ac1/declared-started-ended', 'ac1/build-output-has-item-and-goes',
            'ac1/unread-group-sends-nothing', 'ac1/only-the-runs-own-items',
            'fix2/returns-at-the-commands-exit', 'fix2/end-follows-their-exit',
            'fix2/captured-output-ends-at-return', 'fix2/captured-end-follows',
            'supervise/report-loss-keeps-supervising', 'supervise/report-loss-end-is-made',
            'supervise/stop-after-the-command-ends-nothing', 'supervise/stop-after-the-command-end-is-made',
            'supervise/staying-is-idle', 'supervise/wait-reads-again-at-a-read-holders-exit',
            'supervise/wrapper-gone-the-follower-makes-the-end', 'supervise/none-stays-on-nothing',
            'fix3/handed-outside-the-tree', 'fix3/unread-process-holds', 'fix3/environment-not-whole-holds',
            'fix3/same-program-holds', 'fix3/rewritten-environment-cwd-in-scratch',
            'fix3/rewritten-environment-open-file-in-worktree', 'fix3/rule-3-reads-the-kernel',
            'fix3/the-house-group',
            'fix4/docker-objects-are-items', 'fix5/no-issuer-no-run', 'fix6/scratch-not-made',
            'ac2/command-status', 'ac2/act-waits-75', 'ac2/report-starts',
            'ac3/record-refusals', 'fix1/existing-work-is-never-scratch', 'ac3/record-accepted', 'ac3/event-types',
            'ac4/no-installation-runs-unchanged', 'ac4/each-verb-says-so',
            'paths/canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    ENVIRONMENT = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    ENVIRONMENT.update(GIT_EDITOR='true', GIT_TERMINAL_PROMPT='0', LC_ALL='C')

    def git(where, *argv):
        done = subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                               '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                               '-c', 'advice.detachedHead=false', '-C', str(where)] + list(argv),
                              env=ENVIRONMENT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=120)
        if done.returncode:
            raise RuntimeError('git %s: %s' % (' '.join(argv[:3]), done.stderr.decode()[-300:]))
        return done.stdout.decode().strip()

    def stopped(row, error):
        import traceback
        check(row, 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + ' | '.join(line.strip() for line in traceback.format_exc().splitlines()[-4:])[:400], False)

    def text_of(path):
        try:
            return Path(path).read_text()
        except OSError:
            return None

    temp = Path(os.path.realpath(tempfile.mkdtemp(prefix='veldo-0313-')))
    connections = []
    waiting = []  # the fixture's own processes, ended when the suite ends
    supervisors = []  # every supervisor a row started, {pid, started, run}: none outlives the suite
    opened = []  # descriptors the fixture holds for them
    row = ROWS[0]
    try:
        CLI = load_cli('v313_veldo_cli', PRODUCTION['veldo'])
        CLI.ROOT = ROOT  # the modules the CLI loads are this repository's .veldo
        SP = load('v313_control_space', VELDO / 'control_space.py')
        S = load('v313_control_store', VELDO / 'control_store.py')
        CM = load('v313_control_membership', VELDO / 'control_membership.py')
        CFG = load('v313_control_space_config', VELDO / 'control_space_config.py')
        YAML = load('v313_yamlish', VELDO / 'yamlish.py')
        K = load('v313_control_space_kinds', VELDO / 'control_space_kinds.py')
        P = load('v313_control_space_probe', VELDO / 'control_space_probe.py')
        RM = load('v313_control_space_remove', VELDO / 'control_space_remove.py')
        KP = load('v313_control_space_keep', VELDO / 'control_space_keep.py')
        DK = load('v313_control_space_docker', VELDO / 'control_space_docker.py')
        SIG = load('v313_control_space_signal', VELDO / 'control_space_signal.py')
        AC = CM.AC
        NOW = 1000.0

        keys = temp / 'keys'
        keys.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(keys / 'owner')], check=True,
                       capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
        PUBLIC = (keys / 'owner.pub').read_text().strip()

        def owner_sign(data):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / 'owner'), '-n',
                                   AC.SIGNATURE_NAMESPACE], input=data, capture_output=True, check=True,
                                  timeout=30).stdout.decode()

        MEGABYTE = 1024 * 1024
        FLOOR, NEED = 20000 * MEGABYTE, 4000 * MEGABYTE
        SCRATCH, STATE, BUILD = temp / 'scratch', temp / 'state', temp / 'build'
        for made in (SCRATCH, STATE, BUILD, STATE / 'vms'):
            made.mkdir()
        (STATE / 'vms' / 'disk.raw').write_text('a disk image nobody may touch\n')
        folder = temp / 'installation'
        folder.mkdir()
        (folder / 'installation.yaml').write_text(YAML.dump({
            'schema': 'veldo.installation/v1',
            'owner': {'display_name': 'Fixture Owner', 'role_id': 'owner'},
            'space': {
                'enabled': 'true',
                'time_zone': 'Europe/Lisbon',
                'pools': {'host': {'floor': FLOOR,
                                   'needs': {'build': NEED, 'review': 1000 * MEGABYTE, 'gate': 6000 * MEGABYTE}}},
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

        def commit(where, name, text, message):
            (Path(where) / name).write_text(text)
            git(where, 'add', name)
            git(where, 'commit', '-q', '-m', message)
            return git(where, 'rev-parse', 'HEAD')

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
        A = {'type': 'project', 'id': ORCHARD['project']}
        B = {'type': 'project', 'id': MEADOW['project']}
        for made in (ORCHARD, MEADOW):
            Path(made['worktree_root']).mkdir(parents=True, exist_ok=True)

        def journal_sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        IDS = {'domain_uuid': 'dom-313', 'repository_uuid': 'repo-313', 'store_uuid': 'store-313'}
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

        REGISTRY = K.REGISTRY
        TABLE = REGISTRY['tables'][REGISTRY['version']]
        LIFECYCLE = {'version': REGISTRY['version'], 'events': list(TABLE['events']),
                     'ends_on': {kind: list(events) for kind, events in TABLE['ends_on'].items()}}

        L = SP.Ledger(S, conn, 'authority', journal_sign, config=CONFIG, projects=[ORCHARD, MEADOW],
                      state_root=str(STATE), lifecycle=LIFECYCLE, host='fixture-host',
                      device=lambda path: 'dev-host')
        L.set_pool('host', 'filesystem', device='dev-host')
        L.act_checks = {'clean_report_days': lambda scope: None, 'no_unconfirmed_pending_group': lambda scope: None}
        mode_command = {'principal': 'owner', 'operation': 'space_mode', 'parameters': {'scope': A, 'mode': 'act'},
                        'command_id': 'mode-1', 'nonce': 'mode-nonce-1'}
        switched = L.set_mode({'command': mode_command, 'signature': owner_sign(S.canonical_bytes(mode_command))},
                              CM, NOW)
        if not switched.get('ok') or not L.acts(A) or L.acts(B):
            raise RuntimeError('the fixture could not put orchard in act mode: %s' % (switched.get('reason'),))

        def seq():
            """Where the journal and the Ledger's own observations are now."""
            return conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0], len(L.observations)

        def written(since):
            """(operation, principal) of every command the Ledger accepted after `since`, in order; and
            when the journal moved by another number of records than that, how far it moved."""
            accepted = [(seen.get('operation'), seen.get('principal')) for seen in L.observations[since[1]:]
                        if seen.get('outcome') == 'accepted']
            moved = seq()[0] - since[0]
            return accepted if moved == len(accepted) else accepted + [('journal moved', moved)]

        def version_of(identity):
            return conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()[0]

        def items_of(run):
            return {identity: record for identity, record in sorted(L.items().items())
                    if ((record.get('owner') or {}).get('run') or {}).get('id') == run}

        def item_at(path):
            return [(identity, record) for identity, record in sorted(L.items().items())
                    if (record.get('locator') or {}).get('path') == str(path)]

        # The stand-in engine: it holds the containers a row plants, lists and shows them, and stops
        # and removes one named object. A container's labels are what the files it names hold now.
        ENGINE = {'containers': [], 'unreadable': False, 'calls': []}

        def shown(record):
            labels = dict(record['labels'])
            for name, path in record['labels_from'].items():
                if text_of(path):
                    labels[name] = text_of(path).strip()
            return {'Id': record['Id'], 'Name': '/' + record['name'], 'State': {'Status': record['status']},
                    'Config': {'Labels': labels}, 'Mounts': [], 'NetworkSettings': {'Networks': {}}}

        def container(name, labels=None, labels_from=None):
            record = {'Id': '%064x' % (0xc000 + len(ENGINE['containers']) + 1), 'name': name, 'status': 'running',
                      'labels': dict(labels or {}), 'labels_from': dict(labels_from or {})}
            ENGINE['containers'].append(record)
            return record

        def client(argv, cwd=None):
            if argv[0] != 'docker':
                return P._run(argv, cwd)
            rest = [str(word) for word in argv[3:]]
            ENGINE['calls'].append(tuple(rest))
            if ENGINE['unreadable']:
                return 1, 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock.'
            kind, verb = rest[0], rest[1]
            names = [word for word in rest[2:] if not word.startswith('-')]
            held = ENGINE['containers'] if kind == 'container' else []
            if verb == 'ls':
                return 0, ''.join(record['Id'] + '\n' for record in held)
            found = [next((record for record in held if name in (record['Id'], record['name'])), None)
                     for name in names]
            if not names or None in found:
                return 1, 'Error response from daemon: No such %s' % kind
            if verb == 'inspect':
                return 0, json.dumps([shown(record) for record in found])
            if kind == 'container' and verb == 'stop':
                found[0]['status'] = 'exited'
                return 0, names[0] + '\n'
            if kind == 'container' and verb == 'rm' and found[0]['status'] != 'running':
                held.remove(found[0])
                return 0, names[0] + '\n'
            return 1, 'the stand-in engine does not know %s %s' % (kind, verb)

        PROC = temp / 'proc'
        PROC.mkdir()
        # PLENTY is room for every run of the suite at once. A run whose end could not be made keeps
        # its hold (on a host where processes nobody here can read keep starting, that is every
        # run), and a pool sized for one run then turned every later row into exit 75.
        PLENTY, SHORT = FLOOR + 64 * NEED + 500 * MEGABYTE, FLOOR + NEED - 1

        class Group:
            """A stand-in containment group: no host scope is made for the command, and the read says
            what the row gives it. With nothing given it is a group nobody joined."""

            def __init__(self, read=True, pids=(), after=0):
                self.said, self.pids, self.after, self.reads = read, list(pids), after, 0

            def words(self, run):
                return None

            def read(self, run, group):
                self.reads += 1
                pids = self.pids if self.reads > self.after else []
                return {'read': self.said, 'populated': bool(pids), 'pids': list(pids)}

        def issue(label, scope):
            """The authority's issue of a run to space-runner, as its service will answer a wrapper."""
            return L.issue(SP.RUNNER, label, scope=scope)

        def space(free=PLENTY, **over):
            wired = {'ledger': L, 'probe': P, 'kinds': K, 'remover': RM, 'free': lambda pool: free,
                     'keep': lambda identity, record: KP.keep(L, identity, record),
                     'owner_live': lambda owner: None, 'run': client, 'proc': str(PROC),
                     'borrow_root': str(temp / 'borrowed'), 'issue': issue, 'group': Group()}
            wired.update(over)
            return {name: value for name, value in wired.items() if value is not None}

        def sleeper():
            """A real process that lives until the suite ends it: (process, {pid, started})."""
            child = subprocess.Popen(['cat'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
            waiting.append(child)
            return child, {'pid': child.pid, 'started': CLI._space_process(child.pid)['started']}

        def ended():
            """The process of a supervisor that has already ended, for a row that drives the end itself."""
            child, process = sleeper()
            child.stdin.close()
            child.wait()
            return process

        LINGER = 10.0  # the longest a process a fixture command leaves lives with no word from the suite

        def lingering(code, latch, late, shown=None):
            """The source of a command that ends at once with `code` and leaves a process that left its
            session and its parent. That process holds a file under the command's temporary folder
            and lives until the suite makes `latch` (never by the clock, short of LINGER); at its last
            line it writes to `late` what it sees. `shown`, when given, gets the command's cgroup."""
            return ('import json, os, sys, time\n'
                    'held = os.path.join(os.environ["TMPDIR"], "held.txt")\n'
                    'open(held, "w").write("in use\\n")\n'
                    + ('open(%r, "w").write(open("/proc/self/cgroup").read())\n' % str(shown) if shown else '')
                    + 'if os.fork():\n'
                    '    os._exit(%d)\n'
                    'os.setsid()\n'
                    'if os.fork():\n'
                    '    os._exit(0)\n'
                    'for stream in (0, 1, 2):\n'
                    '    os.close(stream)\n'
                    'handle, until = open(held), time.monotonic() + %r\n'
                    'while not os.path.exists(%r) and time.monotonic() < until:\n'
                    '    time.sleep(0.02)\n'
                    'json.dump({"held": os.path.isfile(held), "text": handle.read(),\n'
                    '           "released": os.path.exists(%r)}, open(%r, "w"))\n'
                    % (code, LINGER, str(latch), str(latch), str(late)))

        def release(latch):
            """Make `latch` a moment from now, from a process of the fixture's own, so that the caller
            is already asleep on the exit it causes."""
            waiting.append(subprocess.Popen(['sh', '-c', 'sleep 0.7; : > "$1"', 'sh', str(latch)],
                                            stdin=subprocess.DEVNULL))

        def alive(holders, how):
            found = [one for one in holders or () if one.get('how') == how]
            return found if found and all(CLI._space_process(one['pid']) is not None for one in found) else []

        def rule_three(identity):
            """Rule 3 as any judge reads it, against the kernel's own process table, from a judge that
            was told the run is over: what it finds, or None."""
            judged = SIG.rules(L, P, identity, L.item(identity), run=client, proc='/proc',
                               owner_live=lambda owner: {'conclusive': True, 'group_empty': True})
            return judged if judged.get('rule') == 'owner_live' else None

        def worktree(project, name, ticket=None):
            """A worktree of the project, made with plain git and recorded as the seams will record it."""
            path = Path(project['worktree_root']) / name
            git(project['repository'], 'worktree', 'add', '-q', '-b', 'agent/' + name, str(path))
            owner = {'scope': {'type': 'project', 'id': project['project']}}
            if ticket:
                owner['ticket'] = ticket
            made = L.declare('worktree', {'path': str(path)}, owner, 'seam', start=git(path, 'rev-parse', 'HEAD'),
                             branch='agent/' + name)
            if not made.get('ok') or not L.confirm(made['item']).get('ok'):
                raise RuntimeError('the fixture could not record the worktree: %s' % (made.get('reason'),))
            return path, made['item']

        BASE = {key: value for key, value in os.environ.items()
                if key not in ('VELDO_SPACE_LABEL', 'COMPOSE_PROJECT_NAME')}
        BASE['TMPDIR'] = str(temp / 'own-tmp')
        (temp / 'own-tmp').mkdir()

        def run(argv, where, wiring=None, **more):
            """The wrapper's own verb, as the CLI's router calls it. Returns (status, what it said on
            standard error, its report)."""
            said, report = io.StringIO(), {}
            status = CLI.space_run(list(argv), space=wiring, environ=more.pop('environ', dict(BASE)),
                                   cwd=str(where), stderr=said, report=report, **more)
            if isinstance((report.get('given') or {}).get('supervisor'), dict):
                supervisors.append(dict(report['given']['supervisor'], run=report['given'].get('run')))
            if isinstance(report.get('end'), dict):
                report['end'] = settled(wiring, report.get('given'), report['end'])
            return status, said.getvalue(), report

        def there(process, seconds):
            """Whether the kernel still shows `process` ({pid, started}) after `seconds`: one wait
            on its pidfd, which ends early only if it exits."""
            import select
            try:
                descriptor = os.pidfd_open(process['pid'])
            except OSError:
                return False
            try:
                now = CLI._space_process(process['pid'])
                if now is None or now['started'] != process['started']:
                    return False
                watch = select.poll()
                watch.register(descriptor, select.POLLIN)
                return not watch.poll(int(seconds * 1000))
            finally:
                os.close(descriptor)

        def unread_by(process, run_identity):
            """The processes the kernel shows that hold `run_identity` unread for the supervisor
            `process`: what a supervisor with nothing of its own left still stays on."""
            return [one['pid'] for one in CLI._space_holders(run_identity, process, [], since=process['started'],
                                                             reader=CLI._space_reader(None))
                    if one.get('how') == 'unread']

        def stays_or_ends(process, run_identity, child=None, status=None, seconds=5.0):
            """(how, said) for a supervisor with nothing of its run left: 'ended' when it ended (with
            `status`, when its exit can be read), 'unread' when it stays and the kernel shows
            processes this account cannot read that started after it (another account's, on a
            shared host), else what it did."""
            if not there(process, seconds):
                if child is None:
                    return 'ended', None
                code = child.wait(timeout=30)
                return ('ended' if code == status else 'exit %s' % code), code
            held = unread_by(process, run_identity)
            return ('unread' if held else 'stays on nothing'), held[:6]

        FOLLOW = 120.0  # the suite's own limit on an end held by what is no part of its fixture

        def follow(wiring, given):
            """The run's end as the supervisor's follower makes it (_space_ended), which sleeps with no
            time limit on the exit of every holder. A process that started after the run and whose
            environment cannot be read holds the run (fail closed), whoever it belongs to. In a
            process table of the suite's own (the gate's confinement) there is none but the
            fixture's. On a host shared with other sessions and without the process reader there
            may be, and the end then waits for it, as it must. The suite does not wait with it: past
            its own limit the row is red and says why. It is never passed and never stood down."""
            import signal

            def late(number, frame):
                raise TimeoutError
            before = signal.signal(signal.SIGALRM, late)
            signal.alarm(int(FOLLOW))
            try:
                return CLI._space_ended(wiring, given)
            except TimeoutError:
                raise RuntimeError(
                    'the run\'s end is still asleep after %ds on processes that hold the run: %s. On a host shared '
                    'with other sessions and without the process reader, a process nobody here can read holds every '
                    'run that began before it (fail closed). Run the suite in a process table of its own.'
                    % (FOLLOW, CLI._space_judged(wiring, given).get('holders'))) from None
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, before)

        def settled(wiring, given, end):
            """The run's end on a host this suite shares with other work: another session's process
            that this account cannot read and that started after the run may be the run's for all
            the wrapper can tell, so the end is not made while it lives. It is no part of the
            fixture. The end then follows its exit (follow). A row that plants such a process itself
            does not come through here."""
            tries = 0
            while end.get('reason') == 'label_unread' and tries < 50:
                end, tries = follow(wiring, given), tries + 1
            return end

        def finish(wiring, given):
            return settled(wiring, given, CLI._space_finish(wiring, given))

        def verb(call, argv, wiring=None, **more):
            out, said = io.StringIO(), io.StringIO()
            try:
                status = call(list(argv), space=wiring, stdout=out, stderr=said, **more)
            except SystemExit as stop:
                status = stop.code
            return status, out.getvalue(), said.getvalue()

        # =====================================================================================
        # AC1: the run is declared, started in its own group, and ended in order
        # =====================================================================================
        try:
            row = 'ac1/declared-started-ended'
            W, W_ITEM = worktree(ORCHARD, 'w-ac1', ticket='VELDO-9001')
            (W / '.git').is_file()
            exclude = Path(git(W, 'rev-parse', '--git-common-dir')) / 'info' / 'exclude'
            exclude.parent.mkdir(parents=True, exist_ok=True)
            exclude.write_text('private/\n')
            seen = temp / 'seen-ac1.json'
            script = (
                'import json, os, sys\n'
                'tmp = os.environ.get("TMPDIR")\n'
                'open(os.path.join(tmp, "scrap.bin"), "w").write("x" * 4096)\n'
                'os.mkdir("build"); open("build/out.o", "w").write("o" * 8192)\n'
                'os.mkdir("private"); open("private/draft.txt", "w").write("only copy\\n")\n'
                'open("notes.txt", "w").write("the builder\'s notes\\n")\n'
                'json.dump({"tmp": tmp, "tmp_is_dir": os.path.isdir(tmp), "label": os.environ.get("VELDO_SPACE_LABEL"),\n'
                '           "compose": os.environ.get("COMPOSE_PROJECT_NAME"), "cwd": os.getcwd(), "argv": sys.argv[1:]},\n'
                '          open(%r, "w"))\n' % str(seen))
            since = seq()
            status, said, report = run(['--station', 'build', '--label', 'ac1', '--', sys.executable, '-c', script,
                                        'one', 'two words'], W, space())
            RUN = report.get('run')
            saw = json.loads(text_of(seen) or '{}')
            mine = items_of(RUN)
            scratch = [(identity, record) for identity, record in mine.items() if record['kind'] == 'scratch']
            check(row, 'the wrapper returns the command\'s status 0 and the run is one the authority issued to '
                       'space-runner, with the scope of the folder it ran in [%s %s %s]'
                  % (status, RUN, said.strip()[:200]),
                  status == 0 and isinstance(RUN, str) and RUN.startswith('ac1:') and L.issued_to(RUN) == SP.RUNNER
                  and (L.issued(RUN) or {}).get('scope') == A and (L.issued(RUN) or {}).get('issued_by') == 'authority')
            check(row, 'the scratch root is an item of the run with its station, declared by the wrapper, under the '
                       'installation\'s scratch root [%s]' % ([record['owner'] for _, record in scratch],),
                  len(scratch) == 1 and scratch[0][1]['owner'] == {'scope': A, 'ticket': 'VELDO-9001',
                                                                 'run': {'id': RUN, 'station': 'build'}}
                  and scratch[0][1]['creator'] == 'wrapper'
                  and scratch[0][1]['locator']['path'].startswith(str(SCRATCH) + '/run-scratch/'))
            supervisor = (report.get('given') or {}).get('supervisor') or {}
            check(row, 'the scratch root records the run\'s supervisor, a process the kernel showed with that start '
                       'time; it has ended by the time run finished is sent [%s %s]'
                  % (scratch[0][1].get('process') if scratch else None, supervisor),
                  bool(scratch) and isinstance(supervisor.get('pid'), int) and isinstance(supervisor.get('started'), int)
                  and scratch[0][1].get('process') == supervisor and CLI._space_process(supervisor['pid']) is None)
            check(row, 'the command was given its temporary folder, which was there, the space label, which is the '
                       'run\'s identity, and the compose project name derived from it; its arguments and folder are '
                       'its own [%s]' % (saw,),
                  bool(scratch) and saw.get('tmp') == scratch[0][1]['locator']['path'] and saw.get('tmp_is_dir') is True
                  and saw.get('label') == RUN and saw.get('compose') == DK.compose_project(RUN)
                  and saw.get('cwd') == str(W) and saw.get('argv') == ['one', 'two words'])
            wrote = written(since)
            names = [name for name, _ in wrote]
            order_ok = False
            if SP.SIGNAL in names and SP.RELEASE in names:
                at_signal, at_release = names.index(SP.SIGNAL), names.index(SP.RELEASE)
                census = [at for at, name in enumerate(names) if name == SP.MEASURE]
                outcomes = [at for at, name in enumerate(names) if name == SP.OUTCOME]
                order_ok = (names[:5] == [SP.ISSUE, SP.HOLD, SP.ADMIT, SP.DECLARE, SP.CONFIRM]
                            and names.count(SP.SIGNAL) == 1 and names.count(SP.RELEASE) == 1
                            and bool(census) and max(census) < at_signal and bool(outcomes)
                            and min(outcomes) > at_signal and max(outcomes) < at_release
                            and at_release == len(names) - 1)
            check(row, 'in the journal: the issue, then the hold, the admission, the scratch root declared and '
                       'confirmed; after the command the census, then one signal, then the outcomes, and the release '
                       'last [%s]' % (names,), order_ok)
            check(row, 'the run was issued by the authority, and every other command of it was written as '
                       'space-runner [%s]' % (sorted(set(wrote)),),
                  bool(wrote) and wrote[0][0] == SP.ISSUE and wrote[0][1] != SP.RUNNER
                  and all(principal == SP.RUNNER for _, principal in wrote[1:]))
            check(row, 'the hold is released and the wrapper sent run finished [%s %s]'
                  % ((L.hold(RUN) or {}).get('state'), (report.get('end') or {}).get('reason')),
                  (L.hold(RUN) or {}).get('state') == 'released' and (report.get('end') or {}).get('sent') is True
                  and report.get('holders') == [] and report.get('answer') == 'admitted')

            row = 'ac1/build-output-has-item-and-goes'
            built = [(identity, record) for identity, record in mine.items() if record['kind'] == 'build_output']
            check(row, 'the build folder the command made has an item of the run, declared by the census inside the '
                       'worktree\'s item [%s]' % ([(record['creator'], record['state']) for _, record in built],),
                  len(built) == 1 and built[0][1]['creator'] == 'census' and built[0][1]['parent'] == W_ITEM
                  and built[0][1]['locator']['path'] == str(W / 'build'))
            check(row, 'at run finished the build folder and the scratch root are removed, each through its remover '
                       '[%s %s]' % ({record['kind']: record['state'] for record in mine.values()},
                                    sorted(os.listdir(W))),
                  bool(built) and built[0][1]['state'] == 'removed' and not (W / 'build').exists()
                  and bool(scratch) and scratch[0][1]['state'] == 'removed'
                  and not os.path.lexists(scratch[0][1]['locator']['path']))
            check(row, 'what is work stays: the untracked notes, the folder only the repository\'s own exclude file '
                       'ignores, which got no item, and the tracked file; the worktree\'s item is present [%s]'
                  % ((L.item(W_ITEM) or {}).get('state'),),
                  text_of(W / 'notes.txt') == 'the builder\'s notes\n'
                  and text_of(W / 'private' / 'draft.txt') == 'only copy\n' and text_of(W / 'tracked.txt') == 'base\n'
                  and item_at(W / 'private') == [] and (L.item(W_ITEM) or {}).get('state') == 'present')
        except Exception as error:
            stopped(row, error)

        try:
            row = 'fix2/returns-at-the-commands-exit'
            W2, _ = worktree(ORCHARD, 'w-child')
            late, latch = temp / 'late.json', temp / 'latch-child'
            # The command ends at once with 3. It leaves a process that left its session and its
            # parent, holds a file under the scratch root, and at its last line says what it sees.
            script = lingering(3, latch, late)
            wiring = space()
            since = seq()
            began = time.monotonic()
            status, said, report = run(['--label', 'child', '--', sys.executable, '-c', script], W2, wiring)
            took = time.monotonic() - began
            given, first = report.get('given') or {}, report.get('end') or {}
            mine = items_of(report.get('run'))
            left = alive(first.get('holders'), 'descendant')
            check(row, 'the wrapper returns the command\'s own status when the command exits: the process the '
                       'command left is alive, and has not been told to end [%s %.1fs %s]' % (status, took, left),
                  status == 3 and bool(left) and not late.exists() and not latch.exists() and took < LINGER)
            check(row, 'run finished is not sent, and the wrapper names the processes that hold the run: its '
                       'supervisor and what the command left [%s %s]' % (first.get('reason'), said.strip()[-160:]),
                  first.get('sent') is False and first.get('reason') == 'group_not_empty' and bool(left)
                  and any(one.get('how') == 'supervisor' and one.get('pid') == (given.get('supervisor') or {}).get('pid')
                          for one in first.get('holders') or ())
                  and 'it follows the exit of process' in said and all(str(one['pid']) in said for one in left))
            check(row, 'nothing of the run was judged: no census, no signal and no release are written, the scratch '
                       'root is present with the file the process holds, and the hold is held [%s %s %s]'
                  % ([name for name, _ in written(since)], [record['state'] for record in mine.values()],
                     (L.hold(report.get('run')) or {}).get('state')),
                  [name for name, _ in written(since)] == [SP.ISSUE, SP.HOLD, SP.ADMIT, SP.DECLARE, SP.CONFIRM]
                  and [record['state'] for record in mine.values()] == ['present']
                  and text_of(Path(report.get('scratch') or temp) / 'held.txt') == 'in use\n'
                  and (L.hold(report.get('run')) or {}).get('state') == 'admitted')
            check(row, 'the supervisor said, from inside its wait and before the wrapper returned, that it is asleep '
                       'on the exit of what the command left [%s]' % (report.get('staying'),),
                  report.get('staying') is True)
            # Read after that word, never before it: the supervisor is then in its sleep, not on its
            # way out.
            held_by = rule_three(given['items'][given['scratch']]) if given.get('scratch') else None
            check(row, 'the scratch root records the run\'s supervisor, and after that word rule 3 of a judge that '
                       'was told the run is over holds the item, by that process as the kernel shows it [%s]'
                  % ((held_by or {}).get('found'),),
                  held_by is not None and held_by.get('deferral') == 'in_use'
                  and ((held_by.get('found') or {}).get('process') or {}).get('pid') == given['supervisor']['pid']
                  and ((held_by.get('found') or {}).get('process') or {}).get('start') == given['supervisor']['started'])

            row = 'fix2/end-follows-their-exit'
            since = seq()
            check(row, 'a second and a half after the wrapper returned and closed its end of the report, the '
                       'kernel still shows the supervisor: losing its reader ended nothing',
                  isinstance(given.get('supervisor'), dict) and there(given['supervisor'], 1.5))
            still = rule_three(given['items'][given['scratch']]) if given.get('scratch') else None
            check(row, 'just before the suite lets that process end, the supervisor is there and rule 3 still holds '
                       'the scratch root by it [%s]' % ((still or {}).get('found'),),
                  still is not None and still.get('deferral') == 'in_use'
                  and ((still.get('found') or {}).get('process') or {}).get('pid') == given['supervisor']['pid']
                  and CLI._space_process(given['supervisor']['pid']) is not None and not late.exists())
            release(latch)
            end = follow(wiring, given)
            saw = json.loads(text_of(late) or '{}')
            mine = items_of(report.get('run'))
            check(row, 'the run\'s end sleeps until the process the command left exits, and is made then: that '
                       'process had written its last line when the end returned [%s %s]' % (end.get('reason'), saw),
                  late.is_file() and end.get('sent') is True)
            check(row, 'that process was never stopped: it ended on the suite\'s word, at its own last line, and its '
                       'file under the scratch root was there to that moment [%s]' % (saw,),
                  saw == {'held': True, 'text': 'in use\n', 'released': True})
            check(row, 'then run finished was sent, the scratch root removed and the hold released, in that order '
                       '[%s %s %s]' % ([name for name, _ in written(since)], [record['state'] for record in mine.values()],
                                       (L.hold(report.get('run')) or {}).get('state')),
                  [record['state'] for record in mine.values()] == ['removed']
                  and not os.path.lexists(report.get('scratch') or str(temp))
                  and [name for name, _ in written(since)][-1:] == [SP.RELEASE]
                  and [name for name, _ in written(since)].count(SP.SIGNAL) == 1
                  and (L.hold(report.get('run')) or {}).get('state') == 'released'
                  and CLI._space_process(given['supervisor']['pid']) is None)
        except Exception as error:
            stopped(row, error)

        try:
            row = 'fix2/captured-output-ends-at-return'
            import select
            W15, _ = worktree(ORCHARD, 'w-captured')
            wiring = space()
            # The caller's pipe on the wrapper's standard output and standard error, as a shell's
            # $(...) makes it: the suite's own descriptors 1 and 2 are that pipe while the wrapper
            # runs, so the supervisor it starts is given them. The command says one word and leaves
            # a sleep with no end, which holds none of the three. That sleep is the fixture's
            # stand-in for a daemon, and only the fixture ends it: a process of the suite's own
            # sends it one stop when the suite makes the latch, or after LINGER with no word from
            # the suite, so that a wrapper that waited for it would be late and not asleep for ever.
            napping, latch = temp / 'captured.pid', temp / 'latch-captured'
            waiting.append(subprocess.Popen(
                [sys.executable, '-c',
                 'import os, signal, sys, time\n'
                 'until = time.monotonic() + 60\n'
                 'while not (os.path.exists(sys.argv[1]) and open(sys.argv[1]).read().strip()) '
                 'and time.monotonic() < until:\n'
                 '    time.sleep(0.02)\n'
                 'pid, until = int(open(sys.argv[1]).read()), time.monotonic() + float(sys.argv[3])\n'
                 'while not os.path.exists(sys.argv[2]) and time.monotonic() < until:\n'
                 '    time.sleep(0.02)\n'
                 'try:\n'
                 '    if b"infinity" in open("/proc/%d/cmdline" % pid, "rb").read():\n'
                 '        os.kill(pid, signal.SIGTERM)\n'
                 'except OSError:\n'
                 '    pass\n', str(napping), str(latch), str(LINGER)], stdin=subprocess.DEVNULL))
            reading, writing = os.pipe()
            kept = os.dup(1), os.dup(2)
            sys.stdout.flush()
            sys.stderr.flush()
            began = time.monotonic()
            try:
                os.dup2(writing, 1)
                os.dup2(writing, 2)
                os.close(writing)
                status, said, report = run(
                    ['--label', 'captured', '--', 'sh', '-c',
                     'sleep infinity </dev/null >/dev/null 2>&1 & echo $! > "$1"; echo the command said this; '
                     'exit 4', 'sh', str(napping)], W15, wiring)
            finally:
                os.dup2(kept[0], 1)
                os.dup2(kept[1], 2)
                os.close(kept[0])
                os.close(kept[1])
            returned = time.monotonic() - began
            # The caller reads to the end of the pipe. With a supervisor that kept it the end comes
            # only with the sleep's, which is never: the row gives it five seconds and is red.
            got, closed, watch = b'', False, select.poll()
            watch.register(reading, select.POLLIN | select.POLLHUP)
            until = time.monotonic() + 5.0
            while not closed and time.monotonic() < until:
                if watch.poll(int(max(0.0, until - time.monotonic()) * 1000)):
                    part = os.read(reading, 65536)
                    got, closed = got + part, part == b''
            read_to_end = time.monotonic() - began
            os.close(reading)
            given, first = report.get('given') or {}, report.get('end') or {}
            left = alive(first.get('holders'), 'descendant')
            check(row, 'the wrapper returns the command\'s status at once and the caller\'s read of its output ends '
                       'at once too, with what the command wrote, while the sleep the command left lives '
                       '[%s %.2fs %.2fs %r %s]' % (status, returned, read_to_end, got, left),
                  status == 4 and closed and got == b'the command said this\n' and len(left) == 1
                  and [one['pid'] for one in left] == [int(text_of(napping) or 0)]
                  and returned < 5.0 and read_to_end < 5.0 and not latch.exists())
            names = []
            for number in (0, 1, 2):
                try:
                    names.append(os.readlink('/proc/%d/fd/%d' % (given['supervisor']['pid'], number)))
                except (OSError, KeyError, TypeError) as error:
                    names.append(type(error).__name__)
            check(row, 'the supervisor stays, asleep on that sleep\'s exit, and its descriptors 0, 1 and 2 are '
                       '/dev/null [%s %s]' % (report.get('staying'), names),
                  report.get('staying') is True and names == ['/dev/null'] * 3)
            check(row, 'the run is held as before: run finished is not sent, the scratch root is present and the '
                       'hold is held [%s %s %s]'
                  % (first.get('reason'), [record['state'] for record in items_of(report.get('run')).values()],
                     (L.hold(report.get('run')) or {}).get('state')),
                  first.get('sent') is False and first.get('reason') == 'group_not_empty'
                  and [record['state'] for record in items_of(report.get('run')).values()] == ['present']
                  and (L.hold(report.get('run')) or {}).get('state') == 'admitted')
            # The suite's word: the fixture's own process ends the sleep, and nothing of the wrapper
            # ever does. The end that follows is a row of its own (fix round 4 of VELDO-0315): what
            # the row above is about is read when the wrapper returns, on any host.
            row = 'fix2/captured-end-follows'
            release(latch)
            end = follow(wiring, given)
            check(row, 'when the suite ends that sleep the run\'s end follows [%s %s]'
                  % (end.get('reason'), (L.hold(report.get('run')) or {}).get('state')),
                  end.get('sent') is True and (L.hold(report.get('run')) or {}).get('state') == 'released')
        except Exception as error:
            stopped(row, error)

        try:
            row = 'supervise/report-loss-keeps-supervising'
            import signal
            W16, _ = worktree(ORCHARD, 'w-report-loss')
            wiring = space()
            done, latch = temp / 'report-loss.done', temp / 'latch-report-loss'
            # The command leaves nothing: it waits for the suite's word, writes its last line and
            # exits 7. The fixture is the wrapper here, so that it can go while the command runs.
            script = ('import os, sys, time\n'
                      'until = time.monotonic() + %r\n'
                      'while not os.path.exists(sys.argv[1]) and time.monotonic() < until:\n'
                      '    time.sleep(0.02)\n'
                      'open(sys.argv[2], "w").write("ran to its own last line\\n")\n'
                      'sys.exit(7)\n' % (6 * LINGER,))
            wrapper = CLI._SpaceSupervisor([sys.executable, '-c', script, str(latch), str(done)], dict(BASE), str(W16))
            given = CLI._space_begin(wiring, 'build', 'report-loss', str(W16), start=wrapper.start)
            process = given.get('supervisor') or {}
            if process:
                supervisors.append(dict(process, run=given.get('run')))
            wrapper.go(given, CLI._space_group(wiring, dict(BASE)))
            started = json.loads(wrapper.lines.readline().decode() or 'null')
            wrapper.lines.close()  # the wrapper is gone: nobody reads the supervisor's report any more
            check(row, 'the command was started, and a second and a half after its report lost its reader the '
                       'supervisor is there and the command runs on [%s]' % (started,),
                  isinstance(started, dict) and 'group' in started and bool(process) and there(process, 1.5)
                  and not done.exists())
            latch.write_text('go\n')
            until = time.monotonic() + 60
            while not done.exists() and time.monotonic() < until:
                time.sleep(0.02)
            how, said = stays_or_ends(process, given['run'], child=wrapper.child, status=7)
            check(row, 'the command ran to its own last line, and the supervisor then ended with the command\'s '
                       'status 7, or stays on processes this account cannot read that started after it [%s %s]'
                  % (how, said),
                  text_of(done) == 'ran to its own last line\n' and how in ('ended', 'unread'))

            row = 'supervise/report-loss-end-is-made'
            since = seq()
            given['status'], given['unread'], given['group'] = 7, False, None
            end = follow(wiring, given)
            mine = items_of(given['run'])
            check(row, 'the end of that run is made as the follower makes it: run finished is sent, the scratch '
                       'root is removed and the hold is released [%s %s %s]'
                  % (end.get('reason'), [record['state'] for record in mine.values()],
                     (L.hold(given['run']) or {}).get('state')),
                  end.get('sent') is True and [record['state'] for record in mine.values()] == ['removed']
                  and [name for name, _ in written(since)].count(SP.SIGNAL) == 1
                  and (L.hold(given['run']) or {}).get('state') == 'released')
        except Exception as error:
            stopped(row, error)
        finally:
            try:
                (temp / 'latch-report-loss').write_text('end\n')  # the command ends, whatever the row found
            except OSError:
                pass

        try:
            row = 'supervise/stop-after-the-command-ends-nothing'
            import signal
            W17, _ = worktree(ORCHARD, 'w-stop-after')
            late, latch = temp / 'late-stop-after.json', temp / 'latch-stop-after'
            wiring = space()
            since = seq()
            status, said, report = run(['--label', 'stop-after', '--', sys.executable, '-c',
                                        lingering(5, latch, late)], W17, wiring)
            given, first = report.get('given') or {}, report.get('end') or {}
            process = given.get('supervisor') or {}
            left = alive(first.get('holders'), 'descendant')
            # The wrapper has returned and closed its end of the report. Now the stops: after the
            # command ended they reach nothing and end nothing.
            for number in (signal.SIGTERM, signal.SIGHUP):
                os.kill(process['pid'], number)
            check(row, 'the command left a process and the supervisor said it stays; SIGTERM and SIGHUP after the '
                       'command ended leave it there a second and a half later, and the process the command left '
                       'was sent nothing [%s %s %s]' % (status, report.get('staying'), left),
                  status == 5 and report.get('staying') is True and bool(left) and there(process, 1.5)
                  and bool(alive(first.get('holders'), 'descendant')) and not late.exists())
            held_by = rule_three(given['items'][given['scratch']]) if given.get('scratch') else None
            check(row, 'rule 3 still holds the scratch root by the supervisor, and nothing of the run was sent '
                       '[%s %s]' % ((held_by or {}).get('found'), [name for name, _ in written(since)]),
                  held_by is not None and held_by.get('deferral') == 'in_use'
                  and ((held_by.get('found') or {}).get('process') or {}).get('pid') == process.get('pid')
                  and [name for name, _ in written(since)] == [SP.ISSUE, SP.HOLD, SP.ADMIT, SP.DECLARE, SP.CONFIRM]
                  and (L.hold(report.get('run')) or {}).get('state') == 'admitted')

            row = 'supervise/stop-after-the-command-end-is-made'
            release(latch)
            end = follow(wiring, given)
            mine = items_of(report.get('run'))
            check(row, 'the fixture ends the process the command left, at its own last line, and run finished '
                       'follows: the scratch root is removed and the hold released [%s %s %s %s]'
                  % (end.get('reason'), text_of(late), [record['state'] for record in mine.values()],
                     (L.hold(report.get('run')) or {}).get('state')),
                  end.get('sent') is True and json.loads(text_of(late) or '{}').get('released') is True
                  and [record['state'] for record in mine.values()] == ['removed']
                  and (L.hold(report.get('run')) or {}).get('state') == 'released')
        except Exception as error:
            stopped(row, error)
        finally:
            # The fixture ends what its command left, whatever the row found.
            try:
                (temp / 'latch-stop-after').write_text('end\n')
            except OSError:
                pass

        idle_churn = []  # (process, the descriptor that ends it), for each the row has not ended yet
        try:
            row = 'supervise/staying-is-idle'
            import signal
            WINDOW, CHURN = 30.0, 12
            latch, napping = temp / 'latch-idle', temp / 'idle.pid'
            reading, writing = os.pipe()
            heard, told = os.pipe()
            # The fixture is the wrapper of a raw supervisor: no ledger is part of this row. The
            # command waits for the suite's word, leaves a sleep and exits.
            idle = subprocess.Popen(
                [sys.executable, '-B', str(PRODUCTION['veldo']), 'space', 'supervise', '--report', str(writing),
                 '--control', str(heard), '--', 'sh', '-c',
                 'while [ ! -e "$1" ]; do sleep 0.05; done; sleep 600 </dev/null >/dev/null 2>&1 & echo $! > "$2"',
                 'sh', str(latch), str(napping)],
                pass_fds=(writing, heard), env=dict(BASE), cwd=str(temp), stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.close(writing)
            os.close(heard)
            idle_process = {'pid': idle.pid, 'started': (CLI._space_process(idle.pid) or {}).get('started')}
            idle_run = 'row:idle-' + os.urandom(4).hex()
            supervisors.append(dict(idle_process, run=idle_run))
            os.write(told, (json.dumps({'run': idle_run, 'environment': {}, 'scope': None, 'given': {}}) + '\n').encode())
            os.close(told)
            lines = os.fdopen(reading, 'rb')
            first_line = json.loads(lines.readline().decode() or 'null')
            # Processes this account cannot read, started after the supervisor: each holds the run
            # (fail closed) and is one more pidfd the supervisor sleeps on. Each lives until the
            # suite closes its pipe.
            for _ in range(CHURN):
                end_read, end_write = os.pipe()
                made = subprocess.Popen(
                    [sys.executable, '-c', 'import ctypes, os, sys\nctypes.CDLL(None).prctl(4, 0, 0, 0, 0)\n'
                                           'os.write(1, b"ready\\n")\nos.read(int(sys.argv[1]), 1)\n', str(end_read)],
                    stdout=subprocess.PIPE, pass_fds=(end_read,), env=dict(BASE), stdin=subprocess.DEVNULL)
                made.stdout.readline()
                os.close(end_read)
                idle_churn.append((made, end_write))
            latch.write_text('go\n')
            status_line, staying = None, None
            for line in lines:
                said_line = json.loads(line.decode())
                if 'status' in said_line:
                    status_line = said_line
                if 'staying' in said_line:
                    staying = said_line['staying']
                    break
            lines.close()
            hows = [one.get('how') for one in (status_line or {}).get('holders') or ()]
            check(row, 'the supervisor stays on the sleep the command left and on the %d processes it cannot read '
                       '[%s %s %s]' % (CHURN, first_line, {how: hows.count(how) for how in set(hows)}, staying),
                  staying is True and 'descendant' in hows and hows.count('unread') >= CHURN)

            def used():
                fields = Path('/proc/%d/stat' % idle.pid).read_text().rsplit(')', 1)[1].split()
                reads = next(int(line.split()[1]) for line in Path('/proc/%d/io' % idle.pid).read_text().splitlines()
                             if line.startswith('syscr:'))
                return (int(fields[11]) + int(fields[12])) / os.sysconf('SC_CLK_TCK'), reads
            before, began = used(), time.monotonic()
            for made, end_write in list(idle_churn):  # one exit every two seconds, each a wake of the supervisor
                time.sleep(2.0)
                idle_churn.remove((made, end_write))
                os.close(end_write)
                made.wait(timeout=30)
            time.sleep(max(0.0, WINDOW - (time.monotonic() - began)))
            after, took = used(), time.monotonic() - began
            check(row, 'over %.0f seconds, while those %d processes ended one by one, the staying supervisor used '
                       'under one percent of a core and made no pass over the process table: its count of read '
                       'calls did not move [cpu %.2fs, read calls %d]'
                  % (took, CHURN, after[0] - before[0], after[1] - before[1]),
                  took >= WINDOW and idle.poll() is None and after[0] - before[0] < took / 100.0
                  and after[1] - before[1] < 20)
            os.kill(int(text_of(napping) or 0), signal.SIGTERM)  # the fixture ends what its command left
            how, said = stays_or_ends(idle_process, idle_run, child=idle, status=0)
            check(row, 'when the fixture ends that sleep the supervisor ends with the command\'s status, or stays on '
                       'processes this account cannot read that started after it [%s %s]' % (how, said),
                  how in ('ended', 'unread'))
        except Exception as error:
            stopped(row, error)
        finally:
            # The fixture ends what it started, whatever the row found: the sleep its command left,
            # and each process of its own that the row did not get to.
            try:
                (temp / 'latch-idle').write_text('end\n')
                if text_of(temp / 'idle.pid'):
                    os.kill(int(text_of(temp / 'idle.pid')), 15)
            except (OSError, ValueError):
                pass
            for made, end_write in idle_churn:
                try:
                    os.close(end_write)
                    made.wait(timeout=30)
                except Exception:  # noqa: BLE001 - the fixture's own stand-in, never a process of a run
                    made.kill()

        nappers = []  # the row's own stand-ins for holders
        try:
            row = 'supervise/wait-reads-again-at-a-read-holders-exit'
            import threading

            def napper(seconds):
                made = subprocess.Popen(['sleep', str(seconds)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
                nappers.append(made)
                return made

            def holder(made, how):
                return {'pid': made.pid, 'how': how, 'started': (CLI._space_process(made.pid) or {}).get('started')}

            def waited(first, later):
                """(seconds, reads) of one _space_wait whose first read names `first` and whose
                later reads name what `later` gives."""
                reads = []

                def read():
                    reads.append(time.monotonic())
                    return {'group': 'empty', 'holders': first if len(reads) == 1 else later()}

                def reap():
                    for made in nappers:
                        made.poll()
                began = time.monotonic()
                CLI._space_wait(read, reap)
                return time.monotonic() - began, len(reads)

            # A process of the run that ends after a second, and one nobody could read at the
            # first read that lives on. The next read does not name it: the reader has read it
            # since, and it is not the run's. The suite ends it after six seconds, so a wait that
            # sleeps on it ends too, late.
            own, other = napper(1), napper(20)
            ender = threading.Timer(6.0, other.kill)
            ender.start()
            try:
                took, reads = waited([holder(own, 'descendant'), holder(other, 'unread')], lambda: [])
                lived = other.poll() is None
            finally:
                ender.cancel()
            check(row, 'the wait returns at the exit of the run\'s own process, after about a second, while the '
                       'process the next read no longer names lives on [%.1fs, %d reads, lives on %s]'
                  % (took, reads, lived), 0.5 <= took < 4.0 and reads == 2 and lived)
            # The exit of an unread process while a process of the run lives: one wake, no read.
            own, other = napper(2), napper(0.3)
            named = [holder(own, 'descendant'), holder(other, 'unread')]
            took, reads = waited(named, lambda: [one for one, made in zip(named, (own, other)) if made.poll() is None])
            check(row, 'the exit of a process nobody could read, while a process of the run lives, costs no read: '
                       'the table is read again once, at the exit of the run\'s own [%.1fs, %d reads]' % (took, reads),
                  took >= 1.5 and reads == 2)
        except Exception as error:
            stopped(row, error)
        finally:
            for made in nappers:
                try:
                    made.kill()  # the row's own stand-in, never a process of a wrapped run
                    made.wait(timeout=30)
                except Exception:  # noqa: BLE001
                    pass

        try:
            row = 'supervise/wrapper-gone-the-follower-makes-the-end'
            marker, stand_in = temp / 'follower-end.json', temp / 'follower_end.py'
            # The real space_supervise of the production file, in a process of its own, with two
            # stand-ins and nothing else changed: a process this account cannot read is no holder
            # (as with the process reader), and the run's end records what it was given in a file
            # instead of asking a ledger.
            stand_in.write_text(
                'import importlib.machinery, importlib.util, json, os, sys\n'
                'path, marker = sys.argv[1], sys.argv[2]\n'
                'loader = importlib.machinery.SourceFileLoader("veldo_cli", path)\n'
                'spec = importlib.util.spec_from_loader("veldo_cli", loader)\n'
                'V = importlib.util.module_from_spec(spec)\n'
                'loader.exec_module(V)\n'
                'real = V._space_environment\n'
                'def environment(pid):\n'
                '    try:\n'
                '        got = real(pid)\n'
                '    except PermissionError:\n'
                '        return []\n'
                '    return [] if got is None else got\n'
                'V._space_environment = environment\n'
                'V._space_usable = lambda *given: ({"stand-in": True}, None)\n'
                'def ended(pid):\n'
                '    try:\n'
                '        return open("/proc/%d/stat" % pid).read().rsplit(")", 1)[1].split()[0] == "Z"\n'
                '    except OSError:\n'
                '        return True\n'
                'def finish(space, given, environ=None):\n'
                '    with open(marker + ".part", "w") as out:\n'
                '        json.dump({"status": given.get("status"), "run": given.get("run"),\n'
                '                   "supervisor": (given.get("supervisor") or {}).get("pid"),\n'
                '                   "supervisor_ended": ended((given.get("supervisor") or {}).get("pid")),\n'
                '                   "by": os.getpid()}, out)\n'
                '    os.rename(marker + ".part", marker)\n'
                'V._space_finish = finish\n'
                'sys.exit(V.space_supervise(sys.argv[3:]))\n')
            reading, writing = os.pipe()
            heard, told = os.pipe()
            gone = subprocess.Popen(
                [sys.executable, '-B', str(stand_in), str(PRODUCTION['veldo']), str(marker), '--report', str(writing),
                 '--control', str(heard), '--', 'sleep', '1'],
                pass_fds=(writing, heard), env=dict(BASE), cwd=str(temp), stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.close(writing)
            os.close(heard)
            gone_run = 'row:gone-' + os.urandom(4).hex()
            supervisors.append({'pid': gone.pid, 'started': (CLI._space_process(gone.pid) or {}).get('started'),
                                'run': gone_run})
            os.write(told, (json.dumps({'run': gone_run, 'environment': {}, 'scope': None,
                                        'given': {'run': gone_run}}) + '\n').encode())
            os.close(told)
            lines = os.fdopen(reading, 'rb')
            started = json.loads(lines.readline().decode() or 'null')
            lines.close()  # the wrapper is gone while the command runs: nobody hears that nothing is left
            code = gone.wait(timeout=60)
            until = time.monotonic() + 15
            while not marker.exists() and time.monotonic() < until:
                time.sleep(0.05)
            made = json.loads(text_of(marker) or 'null')
            check(row, 'the command was started, its report lost its reader while it ran, it left nothing, and the '
                       'supervisor ended with its status [%s %s]' % (started, code),
                  isinstance(started, dict) and 'group' in started and code == 0)
            check(row, 'the run\'s end was then made from the supervisor\'s side, by the process that follows it, '
                       'for that run, with the command\'s status and the supervisor it records, after the '
                       'supervisor had ended [%s]' % (made,),
                  isinstance(made, dict) and made.get('run') == gone_run and made.get('status') == 0
                  and made.get('supervisor') == gone.pid and made.get('by') not in (None, gone.pid)
                  and made.get('supervisor_ended') is True)
        except Exception as error:
            stopped(row, error)

        try:
            row = 'fix3/handed-outside-the-tree'
            W7, _ = worktree(ORCHARD, 'w-handed')
            fifo, acknowledged, late = temp / 'server.fifo', temp / 'server.ack', temp / 'late-worker.json'
            latch = temp / 'latch-worker'
            os.mkfifo(fifo)
            # A server that is running before the run starts, the way a terminal multiplexer's or a
            # user manager's is. It starts one worker for each line it is sent, with the environment
            # the line carries. The worker is the server's child and never the command's.
            worker = ('import json, os, sys, time\n'
                      'until = time.monotonic() + %r\n'
                      'while not os.path.exists(%r) and time.monotonic() < until:\n'
                      '    time.sleep(0.02)\n'
                      'json.dump({"held": os.path.isfile(sys.argv[1]), "released": os.path.exists(%r)},\n'
                      '          open(sys.argv[2], "w"))\n' % (LINGER, str(latch), str(latch)))
            server = subprocess.Popen(
                [sys.executable, '-c',
                 'import os, subprocess, sys\n'
                 'for line in open(sys.argv[1]):\n'
                 '    label, held, late = line.rstrip("\\n").split("\\t")\n'
                 '    made = subprocess.Popen([sys.executable, "-c", sys.argv[3], held, late],\n'
                 '                            env=dict(os.environ, VELDO_SPACE_LABEL=label))\n'
                 '    open(sys.argv[2], "w").write(str(made.pid))\n',
                 str(fifo), str(acknowledged), worker], env=dict(BASE), stdin=subprocess.DEVNULL)
            waiting.append(server)
            opened.append(os.open(str(fifo), os.O_RDWR))  # the server stays for as long as the suite holds this
            # The command writes a file under its scratch root, hands the work to the server with its
            # own label, waits for the server's word that the work has started, and exits 0.
            script = ('import os, sys, time\n'
                      'held = os.path.join(os.environ["TMPDIR"], "handed.txt")\n'
                      'open(held, "w").write("the worker reads this\\n")\n'
                      'open(sys.argv[1], "w").write("\\t".join([os.environ["VELDO_SPACE_LABEL"], held, sys.argv[3]]) + "\\n")\n'
                      'while not os.path.exists(sys.argv[2]):\n'
                      '    time.sleep(0.02)\n')
            wiring = space()
            began = time.monotonic()
            status, said, report = run(['--label', 'handed', '--', sys.executable, '-c', script, str(fifo),
                                        str(acknowledged), str(late)], W7, wiring)
            took = time.monotonic() - began
            given, first = report.get('given') or {}, report.get('end') or {}
            carried = [one for one in first.get('holders') or () if one.get('how') == 'label']
            working = int(text_of(acknowledged) or 0)
            check(row, 'the fixture\'s worker is the server\'s child, started for the command, and no descendant of '
                       'the run\'s supervisor [%s %s]' % (working, carried),
                  working > 0 and (CLI._space_process(working) or {}).get('parent') == server.pid
                  and not any(one.get('how') == 'descendant' for one in first.get('holders') or ()))
            check(row, 'the wrapper returns the command\'s status while that worker lives and does not send run '
                       'finished: a process outside the command\'s tree carries the run\'s label [%s %.1fs %s]'
                  % (status, took, first.get('reason')),
                  status == 0 and took < LINGER and first.get('sent') is False
                  and first.get('reason') == 'label_carried' and [one.get('pid') for one in carried] == [working]
                  and bool(alive(first.get('holders'), 'label')))
            check(row, 'while that worker lives the scratch root is present with its file and the hold is held '
                       '[%s %s]' % ([record['state'] for record in items_of(report.get('run')).values()],
                                    (L.hold(report.get('run')) or {}).get('state')),
                  [record['state'] for record in items_of(report.get('run')).values()] == ['present']
                  and text_of(Path(report.get('scratch') or temp) / 'handed.txt') == 'the worker reads this\n'
                  and (L.hold(report.get('run')) or {}).get('state') == 'admitted' and not late.exists())
            release(latch)
            end = follow(wiring, given)
            check(row, 'the end follows the worker\'s exit: the worker ended on the suite\'s word and saw the file to '
                       'its last line, and then the scratch root went and the hold was released [%s %s]'
                  % (text_of(late), end.get('reason')),
                  json.loads(text_of(late) or '{}') == {'held': True, 'released': True} and end.get('sent') is True
                  and [record['state'] for record in items_of(report.get('run')).values()] == ['removed']
                  and (L.hold(report.get('run')) or {}).get('state') == 'released')
        except Exception as error:
            stopped(row, error)

        try:
            row = 'fix3/unread-process-holds'
            W14, _ = worktree(ORCHARD, 'w-unreadable')

            def hidden(orphan=False):
                """A process of this account that made itself not dumpable: the kernel then shows its
                environment to nobody without privilege. It lives until the descriptor returned with
                its id is closed. An orphan is started by a process that ends at once, so nothing
                the suite could read stands above it."""
                import select
                reading, writing = os.pipe()
                argv = [sys.executable, '-c', 'import ctypes, os, sys\nctypes.CDLL(None).prctl(4, 0, 0, 0, 0)\n'
                                              'os.write(1, b"%d\\n" % os.getpid())\nos.read(int(sys.argv[1]), 1)\n',
                        str(reading)]
                if orphan:
                    argv = [sys.executable, '-c', 'import subprocess, sys\n'
                                                  'subprocess.Popen(sys.argv[1:], pass_fds=(int(sys.argv[-1]),))\n'] + argv
                child = subprocess.Popen(argv, stdout=subprocess.PIPE, pass_fds=(reading,), env=dict(BASE))
                pid = int(child.stdout.readline())
                os.close(reading)
                opened.append(writing)
                if orphan:
                    child.wait()
                else:
                    waiting.append(child)

                def end():
                    opened.remove(writing)
                    os.close(writing)
                    try:
                        descriptor = os.pidfd_open(pid)
                    except OSError:
                        return
                    try:
                        watch = select.poll()
                        watch.register(descriptor, select.POLLIN)
                        watch.poll()
                    finally:
                        os.close(descriptor)
                return pid, end

            class Reader:
                """The probe with a stand-in process reader (VELDO-0344) in the state used. Its table
                holds a whole block, with the start time the kernel shows, for every process of the
                table but the ones in `but`; a process in `torn` gets a block that is not whole, and
                one in `stale` a block with another start time. `state` is the state it says it is in.
                Every block has a label that was read and holds no run, but the ones `labels` names:
                there a list is the values the reader read, and None a label it did not read."""

                def __init__(self, but=(), torn=(), stale=(), state='used', labels=None):
                    self.but, self.torn, self.stale, self.asked = set(but), set(torn), set(stale), 0
                    self.state, self.labels = state, dict(labels or {})

                def __getattr__(self, name):
                    return getattr(P, name)

                def reader_read(self, proc=None):
                    self.asked += 1
                    blocks = {}
                    for name in os.listdir('/proc'):
                        seen = CLI._space_process(int(name)) if name.isdigit() else None
                        if seen is not None and seen['pid'] not in self.but:
                            blocks[seen['pid']] = {'start': seen['started'] + (1 if seen['pid'] in self.stale else 0),
                                                   'whole': seen['pid'] not in self.torn, 'facts': [],
                                                   'label': self.labels.get(seen['pid'], [])}
                    return {'state': self.state, 'said': None, 'blocks': blocks, 'writer': None, 'digest': None}

            def unread_of(end):
                return {one.get('pid') for one in end.get('holders') or () if one.get('how') == 'unread'}
            before_the_run, end_before = hidden(orphan=True)
            try:
                open('/proc/%d/environ' % before_the_run, 'rb').close()
                unreadable = False
            except OSError:
                unreadable = True
            if not unreadable:
                end_before()
                check(row, 'here this account reads the environment of its every process, so no process is unread '
                           'in the way the row needs: it stands down', True)
            else:
                # The fixture's are the only unread processes the row answers for.
                wiring = space(probe=Reader())
                given = CLI._space_begin(wiring, 'build', 'unreadable', str(W14), start=ended)
                given['status'] = 0
                (Path(given['scratch']) / 'kept.bin').write_text('it may still be written\n')
                child_of_the_suite, end_child = hidden()
                after_the_run, end_after = hidden(orphan=True)
                wiring['probe'].but = {before_the_run, child_of_the_suite, after_the_run}
                since = seq()
                end = CLI._space_finish(wiring, given)
                check(row, 'a process that started after the run began and whose environment cannot be read may be '
                           'the run\'s: the run stays open, nothing is sent or written, and each is named. The one '
                           'that was running before the run began cannot be the run\'s and is not [%s %s]'
                      % (end.get('reason'), end.get('holders')),
                      end.get('sent') is False and end.get('reason') == 'label_unread' and written(since) == []
                      and unread_of(end) == {after_the_run, child_of_the_suite}
                      and text_of(Path(given['scratch']) / 'kept.bin') == 'it may still be written\n'
                      and (L.hold(given['run']) or {}).get('state') == 'admitted')
                end_after()
                end = CLI._space_finish(wiring, given)
                check(row, 'the orphan has ended, and the run is still open: the unread process that a process '
                           'without the label started holds it, since nobody read what it carries [%s %s]'
                      % (end.get('reason'), end.get('holders')),
                      end.get('sent') is False and end.get('reason') == 'label_unread' and written(since) == []
                      and unread_of(end) == {child_of_the_suite}
                      and os.path.isdir(given['scratch'])
                      and (L.hold(given['run']) or {}).get('state') == 'admitted')
                # Only the label decides, and only a label that was read (fix round 3, the re-review's
                # finding 1; the reader reads the label since VELDO-0344's change of 2026-11-14). A
                # block whose label was not read rules nothing out, whole or not; and with a label
                # that was read and holds no run, a block that is not this process's whole block
                # rules nothing out either.
                for name, reader in (
                        ('shows a whole block for it, with the kernel\'s start time, and no label read',
                         Reader(labels={child_of_the_suite: None})),
                        ('shows no block for it', Reader(but=[child_of_the_suite])),
                        ('shows a block for it that is not whole', Reader(torn=[child_of_the_suite])),
                        ('shows a block with another start time', Reader(stale=[child_of_the_suite])),
                        ('is refused, whatever its table holds', Reader(state='refused:digest'))):
                    wiring['probe'] = reader
                    end = CLI._space_finish(wiring, given)
                    check(row, 'a reader that %s has not read what it carries: the run stays open, its file is '
                               'there and the hold is held [%s %s]' % (name, end.get('reason'), end.get('holders')),
                          reader.asked >= 1 and end.get('sent') is False and end.get('reason') == 'label_unread'
                          and unread_of(end) == {child_of_the_suite} and written(since) == []
                          and CLI._space_process(child_of_the_suite) is not None
                          and text_of(Path(given['scratch']) / 'kept.bin') == 'it may still be written\n'
                          and (L.hold(given['run']) or {}).get('state') == 'admitted')
                wiring['probe'] = Reader(labels={child_of_the_suite: [b'another:run', given['run'].encode()]})
                end = CLI._space_finish(wiring, given)
                check(row, 'a reader that read this run\'s label in its environment: the process is the run\'s, '
                           'named by the label; the run stays open and nothing is written [%s %s]'
                      % (end.get('reason'), end.get('holders')),
                      end.get('sent') is False and end.get('reason') == 'label_carried' and written(since) == []
                      and [(one.get('pid'), one.get('how')) for one in end.get('holders') or ()]
                      == [(child_of_the_suite, 'label')]
                      and text_of(Path(given['scratch']) / 'kept.bin') == 'it may still be written\n'
                      and (L.hold(given['run']) or {}).get('state') == 'admitted')
                # One more unread process, started now: the reader reads it too, with no label.
                bystander, end_bystander = hidden(orphan=True)
                wiring['probe'] = Reader(labels={child_of_the_suite: [b'another:run']})
                end = CLI._space_finish(wiring, given)
                check(row, 'a reader that read the label of each, another run\'s in one and none in the other: '
                           'neither is this run\'s, so the run is over while both live, and rule 4 judged them by '
                           'their files [%s %s %s]' % (end.get('reason'), end.get('holders'), wiring['probe'].asked),
                      end.get('sent') is True and wiring['probe'].asked >= 1
                      and CLI._space_process(child_of_the_suite) is not None
                      and CLI._space_process(bystander) is not None
                      and CLI._space_process(before_the_run) is not None
                      and not os.path.lexists(given['scratch'])
                      and (L.hold(given['run']) or {}).get('state') == 'released')
                end_child()
                end_bystander()
                end_before()
        except Exception as error:
            stopped(row, error)

        try:
            row = 'fix3/environment-not-whole-holds'
            # A program that executes itself again at once, for ever, with the environment it has.
            # The kernel reads environ from the memory a process had when the entry was opened, so a
            # read that falls across one of its executions returns nothing.
            again = temp / 'again.sh'
            again.write_text('#!/bin/sh\nexec "$0"\n')
            again.chmod(0o755)
            carried_run = 'row:run-' + os.urandom(4).hex()
            spinner = subprocess.Popen([str(again)], stdin=subprocess.DEVNULL,
                                       env={'PATH': '/usr/bin:/bin', CLI.SPACE_LABEL_VARIABLE: carried_run})
            waiting.append(spinner)
            READS, hows = 150, {}
            for _ in range(READS):
                how = [one.get('how') for one in CLI._space_holders(carried_run, None, []) if one.get('pid') == spinner.pid]
                hows[str(how)] = hows.get(str(how), 0) + 1
            alive = spinner.poll() is None
            spinner.kill()
            spinner.wait()
            check(row, 'a process that carries the run\'s label and executes itself again without end is a holder '
                       'of the run in each of %d reads of the kernel\'s table: by its label when its environment '
                       'was read whole, unread when it was not, and never missing [%s alive %s]' % (READS, hows, alive),
                  alive and sum(hows.values()) == READS and set(hows) <= {"['label']", "['unread']"}
                  and hows.get("['label']", 0) >= 1)
            quiet = [sys.executable, '-c', 'import os\nos.write(1, b"ready\\n")\nos.read(0, 1)\n']
            bare = subprocess.Popen(quiet, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env={})
            plain = subprocess.Popen(quiet, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env={'OTHER': 'value'})
            mine = subprocess.Popen(quiet, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    env={'OTHER': 'value', CLI.SPACE_LABEL_VARIABLE: carried_run})
            waiting.extend([bare, plain, mine])
            ready = [one.stdout.readline() for one in (bare, plain, mine)]
            held = {one.get('pid'): one.get('how') for one in CLI._space_holders(carried_run, None, [])}
            for one in (bare, plain, mine):
                one.stdin.close()
                one.wait(timeout=30)
                one.stdout.close()
            check(row, 'an environment of no bytes is what the kernel returns for a process that is executing, so '
                       'a process that has one is unread and holds the run; one with an environment and no label '
                       'is no holder, and one with the label holds by it [%s %s %s %s]'
                  % (ready, held.get(bare.pid), held.get(plain.pid), held.get(mine.pid)),
                  ready == [b'ready\n'] * 3 and held.get(bare.pid) == 'unread' and plain.pid not in held
                  and held.get(mine.pid) == 'label')
        except Exception as error:
            stopped(row, error)

        try:
            row = 'fix3/same-program-holds'
            # A process that shares its parent's memory until it executes (posix_spawn, which is how
            # most programs start another). The kernel reads environ from the memory the process had
            # when the entry was opened, and the parent keeps that memory alive: a read that falls
            # across the execution returns the parent's whole environment, as many bytes as the ends
            # taken before it are apart. Only what the process is, before and after, tells it apart.
            # The child waits in the open of a fifo, one of posix_spawn's own file actions, and the
            # scan's open of its environ entry is what lets it go on.
            shared_run = 'row:run-' + os.urandom(4).hex()
            go = temp / 'share.fifo'
            os.mkfifo(go)
            spawner = subprocess.Popen(
                [sys.executable, '-c',
                 'import os, sys\n'
                 'os.posix_spawn(sys.executable, [sys.executable, "-c", "import os\\nos.read(0, 1)\\n"],\n'
                 '               {sys.argv[2]: sys.argv[3]}, file_actions=[(os.POSIX_SPAWN_OPEN, 9, sys.argv[1], os.O_RDONLY, 0)])\n'
                 'os.read(0, 1)\n', str(go), CLI.SPACE_LABEL_VARIABLE, shared_run],
                stdin=subprocess.PIPE, env={'OTHER': 'value'})
            waiting.append(spawner)
            until, sharing = time.monotonic() + 30, None
            while sharing is None and time.monotonic() < until:
                born = [int(name) for name in os.listdir('/proc') if name.isdigit()
                        and (CLI._space_process(int(name)) or {}).get('parent') == spawner.pid]
                sharing = born[0] if born else None
                time.sleep(0.01)
            entry = '/proc/%d/environ' % sharing
            wanted = (CLI.SPACE_LABEL_VARIABLE + '=' + shared_run).encode()
            early = open(entry, 'rb')  # opened before the execution, as the scan's own will be
            opens = []

            def across(path, *more, **named):
                made = open(path, *more, **named)
                if path == entry and not opens:
                    opens.append(path)
                    with open(go, 'wb') as word:
                        word.write(b'x')
                    limit = time.monotonic() + 30
                    while time.monotonic() < limit:
                        with open(entry, 'rb') as now:
                            if now.read() == wanted + b'\0':
                                opens.append('executed')
                                break
                        time.sleep(0.005)
                return made
            CLI.open = across
            try:
                how = [one.get('how') for one in CLI._space_holders(shared_run, None, []) if one.get('pid') == sharing]
            finally:
                del CLI.open
            through = early.read()
            early.close()
            spawner.stdin.close()
            spawner.wait(timeout=30)
            check(row, 'a process that shares its parent\'s memory and executes a program with the run\'s label '
                       'between the scan\'s open of its environ entry and the read: a descriptor opened before the '
                       'execution returns the parent\'s environment, which has no label, and the scan does not take '
                       'that for the process\'s own: it reads once more and the process holds the run by its label '
                       '[%s %s; before the execution: %r]' % (how, opens, through[:40]),
                  opens == [entry, 'executed'] and through == b'OTHER=value\0' and how == ['label'])
        except Exception as error:
            stopped(row, error)

        # A LABEL IS WHAT THE ENVIRONMENT AREA SAYS NOW (the accepted limit, the lead's claim put to
        # the proof). A worker that a server started for the command, outside the command's tree and
        # outside its group, carries the run's label and then writes over its own environment area,
        # as a program that sets its process title does. Nothing shows it as the run's any more, so
        # run finished is sent while it lives. What the rows ask is whether anything it holds is
        # removed then.
        def titled(name, command):
            """One run whose command hands work to such a worker. Returns (the run's report, what the
            worker said of itself, the latch that ends the worker, the wiring)."""
            where, _ = worktree(ORCHARD, 'w-' + name)
            fifo, said, latch = temp / (name + '.fifo'), temp / (name + '.said'), temp / (name + '.latch')
            os.mkfifo(fifo)
            # The table rule 4 reads in this row: the kernel's own entry of the worker, through a
            # link the server makes, and of no other process. In the whole table of a host, or of the
            # gate's confinement, there are processes this account cannot read in full, and each of
            # them alone defers every item; here what is kept is kept for the worker.
            view = temp / (name + '.proc')
            view.mkdir()
            worker = ('import ctypes, json, os, sys, time\n'
                      'cwd, held, said, latch = sys.argv[1:5]\n'
                      'label = os.environ.get(%r)\n'
                      'fields = open("/proc/self/stat", "rb").read().rsplit(b")", 1)[1].split()\n'
                      'first, last = int(fields[47]), int(fields[48])\n'
                      'ctypes.memset(first, 0, last - first)\n'
                      'ctypes.memmove(first, b"worker: title", 13)\n'
                      'if cwd:\n'
                      '    os.chdir(cwd)\n'
                      'handle = open(held) if held else None\n'
                      'json.dump({"pid": os.getpid(), "label": label, "area": last - first,\n'
                      '           "now": %r in open("/proc/self/environ", "rb").read()}, open(said + ".part", "w"))\n'
                      'os.rename(said + ".part", said)\n'
                      'until = time.monotonic() + %r\n'
                      'while not os.path.exists(latch) and time.monotonic() < until:\n'
                      '    time.sleep(0.02)\n'
                      % (CLI.SPACE_LABEL_VARIABLE, CLI.SPACE_LABEL_VARIABLE.encode(), 3 * LINGER))
            server = subprocess.Popen(
                [sys.executable, '-c',
                 'import os, subprocess, sys\n'
                 'for line in open(sys.argv[1]):\n'
                 '    label, cwd, held = line.rstrip("\\n").split("\\t")\n'
                 '    made = subprocess.Popen([sys.executable, "-c", sys.argv[4], cwd, held, sys.argv[2], sys.argv[3]],\n'
                 '                            env=dict(os.environ, %s=label), stdin=subprocess.DEVNULL)\n'
                 '    os.symlink("/proc/%%d" %% made.pid, os.path.join(sys.argv[5], str(made.pid)))\n'
                 % CLI.SPACE_LABEL_VARIABLE, str(fifo), str(said), str(latch), worker, str(view)],
                env=dict(BASE), stdin=subprocess.DEVNULL)
            waiting.append(server)
            opened.append(os.open(str(fifo), os.O_RDWR))
            wiring = space(proc=str(view))
            status, words, report = run(['--station', 'build', '--label', name, '--', sys.executable, '-c',
                                         command, str(fifo), str(said)], where, wiring)
            report.update(status=status, words=words, where=where, server=server.pid, view=sorted(os.listdir(view)))
            return report, json.loads(text_of(said) or '{}'), latch, wiring

        def outside(report, worker):
            """Whether the worker is alive, the server's child, and nothing the run's end counts."""
            seen = CLI._space_process(worker.get('pid') or 0) or {}
            judged = CLI._space_holders(report.get('run'), (report.get('given') or {}).get('supervisor'), [])
            return (seen.get('parent') == report['server'] and worker.get('label') == report.get('run')
                    and worker.get('now') is False and worker.get('area', 0) > 0
                    and report.get('view') == [str(worker.get('pid'))]
                    and worker['pid'] not in [one.get('pid') for one in judged]
                    and (report.get('end') or {}).get('sent') is True and report.get('status') == 0)

        def gone(worker, latch):
            latch.write_text('')
            until = time.monotonic() + 30
            while CLI._space_process(worker.get('pid') or 0) is not None and time.monotonic() < until:
                time.sleep(0.02)
            return CLI._space_process(worker.get('pid') or 0) is None

        def kept_for(record):
            """Who the item's own deferral names: {pid: the ways it holds the item}, and the processes
            the judge could not read."""
            found = (record.get('deferral') or {}).get('found') or {}
            return ({user['pid']: sorted(set(use['how'] for use in user['uses'])) for user in found.get('processes') or ()},
                    (found.get('unread') or {}).get('processes'))

        def users_of(path):
            facts = P.in_use(str(path), L.engines, run=client)
            return {user['pid']: sorted(set(use['how'] for use in user['uses'])) for user in facts['processes']}

        try:
            row = 'fix3/rewritten-environment-cwd-in-scratch'
            script = ('import os, sys, time\n'
                      'open(os.path.join(os.environ["TMPDIR"], "kept.txt"), "w").write("the worker is here\\n")\n'
                      'open(sys.argv[1], "w").write("\\t".join([os.environ["VELDO_SPACE_LABEL"], os.environ["TMPDIR"], ""]) + "\\n")\n'
                      'while not os.path.exists(sys.argv[2]):\n'
                      '    time.sleep(0.02)\n')
            report, worker, latch, wiring = titled('titled-cwd', script)
            mine = items_of(report.get('run'))
            scratch = [record for record in mine.values() if record['kind'] == 'scratch']
            path = Path(report.get('scratch') or temp / 'none')
            check(row, 'the limit itself: the worker was started with the run\'s label, wrote over its environment '
                       'area and now shows none; it is the server\'s child, no descendant of the run\'s supervisor, in '
                       'no group and no holder, and run finished was sent while it lives [%s %s %s]'
                  % (worker, (report.get('end') or {}).get('reason'), report.get('words', '').strip()[:200]),
                  outside(report, worker))
            check(row, 'its working directory is the run\'s scratch root, and the scratch root is not removed: the '
                       'item is deferred as in use by the rule that reads what processes hold, its deferral names the '
                       'worker alone, by its working directory, as the probe does on the whole table, and the folder and its file are on disk [%s %s %s]'
                  % ([(record['state'], (record.get('deferral') or {}).get('rule'),
                       (record.get('deferral') or {}).get('refused_by')) for record in scratch],
                     users_of(path).get(worker.get('pid')), sorted(os.listdir(path)) if path.is_dir() else None),
                  len(scratch) == 1 and scratch[0]['state'] == 'deferred'
                  and (scratch[0].get('deferral') or {}).get('rule') == 'in_use'
                  and (scratch[0].get('deferral') or {}).get('refused_by') == 'process_use'
                  and kept_for(scratch[0]) == ({worker.get('pid'): ['cwd']}, [])
                  and users_of(path).get(worker.get('pid')) == ['cwd']
                  and text_of(path / 'kept.txt') == 'the worker is here\n')
            check(row, 'once the worker has ended the probe names nobody in the scratch root [%s]' % (users_of(path),),
                  gone(worker, latch) and users_of(path) == {})
        except Exception as error:
            stopped(row, error)

        try:
            row = 'fix3/rewritten-environment-open-file-in-worktree'
            script = ('import os, sys, time\n'
                      'os.mkdir("build"); open("build/out.o", "w").write("o" * 8192)\n'
                      'open(sys.argv[1], "w").write("\\t".join([os.environ["VELDO_SPACE_LABEL"], "", os.path.abspath("build/out.o")]) + "\\n")\n'
                      'while not os.path.exists(sys.argv[2]):\n'
                      '    time.sleep(0.02)\n')
            report, worker, latch, wiring = titled('titled-open', script)
            mine = items_of(report.get('run'))
            built = [record for record in mine.values() if record['kind'] == 'build_output']
            scratch = [record for record in mine.values() if record['kind'] == 'scratch']
            where = report['where']
            check(row, 'the limit itself, as in the row before: no label now, outside the tree and the group, no '
                       'holder, and run finished was sent while the worker lives [%s %s]'
                  % (worker, (report.get('end') or {}).get('reason')), outside(report, worker))
            check(row, 'it holds a file of the run\'s worktree open, in the build folder that is the run\'s item there: '
                       'the build folder is not removed, deferred as in use by the same rule, and the file is on disk '
                       'whole; the probe names the worker by its open file, for the build folder and for the worktree; '
                       'the scratch root, which it does not hold, went, so the same judge removes what nobody holds [%s %s %s %s]'
                  % ([(record['state'], (record.get('deferral') or {}).get('rule'),
                       (record.get('deferral') or {}).get('refused_by')) for record in built],
                     users_of(where / 'build').get(worker.get('pid')), users_of(where).get(worker.get('pid')),
                     [record['state'] for record in scratch]),
                  len(built) == 1 and built[0]['state'] == 'deferred'
                  and (built[0].get('deferral') or {}).get('rule') == 'in_use'
                  and (built[0].get('deferral') or {}).get('refused_by') == 'process_use'
                  and kept_for(built[0]) == ({worker.get('pid'): ['open']}, [])
                  and users_of(where / 'build').get(worker.get('pid')) == ['open']
                  and users_of(where).get(worker.get('pid')) == ['open']
                  and text_of(where / 'build' / 'out.o') == 'o' * 8192
                  and [record['state'] for record in scratch] == ['removed'])
            check(row, 'once the worker has ended the probe names nobody in the worktree [%s]' % (users_of(where),),
                  gone(worker, latch) and users_of(where) == {})
        except Exception as error:
            stopped(row, error)

        try:
            row = 'fix3/rule-3-reads-the-kernel'
            W8, _ = worktree(ORCHARD, 'w-turning')
            member, process = sleeper()
            # A group that is empty when the end begins and has a live process in it from then on.
            wiring = space(group=Group(pids=[member.pid], after=1))
            given = CLI._space_begin(wiring, 'build', 'turning', str(W8), start=ended)
            given['status'] = 0
            (Path(given['scratch']) / 'written-late.bin').write_text('a process of the run writes this\n')
            end = finish(wiring, given)
            mine = L.item(given['items'][given['scratch']])
            check(row, 'the end began on an empty group, and rule 3 asked the kernel again when it judged the item: '
                       'the scratch root is deferred as in use and is on disk with its file [%s %s %s]'
                  % (end.get('sent'), mine.get('state'), (mine.get('deferral') or {}).get('refused_by')),
                  end.get('sent') is True and wiring['group'].reads >= 2 and mine.get('state') == 'deferred'
                  and (mine.get('deferral') or {}).get('rule') == 'in_use'
                  and (mine.get('deferral') or {}).get('refused_by') == 'owner_live'
                  and text_of(Path(given['scratch']) / 'written-late.bin') == 'a process of the run writes this\n')
            check(row, 'the hold is not released for a run the kernel still shows [%s %s]'
                  % (end.get('hold'), (L.hold(given['run']) or {}).get('state')),
                  end.get('hold') == 'held:group_not_empty' and (L.hold(given['run']) or {}).get('state') == 'admitted')
            L.release(given['run'])
        except Exception as error:
            stopped(row, error)

        try:
            row = 'fix3/the-house-group'
            house = CLI._SpaceScope(dict(os.environ))
            words = house.words('probe:' + temp.name)
            able = bool(words) and subprocess.run(
                [word.replace('veldo-dispatch-', 'veldo-probe-') for word in words] + ['true'],
                stdin=subprocess.DEVNULL, capture_output=True, timeout=60).returncode == 0
            if not able:
                check(row, 'this host gives the suite no user manager to make a scope with: the row stands down, and '
                           'the wrapper\'s answer for such a host is in ac1/unread-group-sends-nothing', True)
            else:
                W9, _ = worktree(ORCHARD, 'w-house')
                seen, late, latch = temp / 'seen-house.txt', temp / 'late-house.json', temp / 'latch-house'
                wiring = space(group=None)  # no group is wired: the wrapper makes the house's own
                status, said, report = run(
                    ['--label', 'house', '--', sys.executable, '-c', lingering(5, latch, late, shown=seen)],
                    W9, wiring, environ=dict(BASE, XDG_RUNTIME_DIR=house.environment['XDG_RUNTIME_DIR']))
                given, first = report.get('given') or {}, report.get('end') or {}
                read = house.read(report.get('run'), report.get('group'))
                check(row, 'the command ran in the house\'s own group and left a process in it: run finished is not '
                           'sent while the kernel lists that process there [%s %s %s]'
                      % (status, read, first.get('reason')),
                      status == 5 and read.get('read') is True and read.get('populated') is True
                      and first.get('sent') is False and first.get('reason') == 'group_not_empty'
                      and not late.exists())
                release(latch)
                end = follow(wiring, given)
                after = house.read(report.get('run'), report.get('group'))
                check(row, 'the end follows its exit: the group is read empty, run finished is sent and the scratch '
                           'root goes [%s %s %s]' % (after, end.get('reason'), end.get('holders')),
                      after == {'read': True, 'populated': False, 'pids': []} and end.get('sent') is True
                      and json.loads(text_of(late) or '{}').get('released') is True
                      and [record['state'] for record in items_of(report.get('run')).values()] == ['removed'])
        except Exception as error:
            stopped(row, error)

        try:
            row = 'fix4/docker-objects-are-items'
            W10, _ = worktree(ORCHARD, 'w-docker')
            label_file, compose_file = temp / 'docker-label.txt', temp / 'docker-compose.txt'
            # What the command made on the engine: one container with the run's label, one that compose
            # stamped with the run's project name. And two that are not the run's.
            labelled = container('built-by-the-run', labels_from={'veldo.space.run': label_file})
            composed = container('composed-by-the-run', labels_from={'com.docker.compose.project': compose_file})
            foreign = container('another-runs', labels={'veldo.space.run': 'another:run-nobody-knows'})
            plain = container('made-by-hand')
            since = seq()
            del ENGINE['calls'][:]
            status, said, report = run(['--label', 'docker', '--', 'sh', '-c',
                                        'printf %%s "$VELDO_SPACE_LABEL" > %s; printf %%s "$COMPOSE_PROJECT_NAME" > %s'
                                        % (label_file, compose_file)], W10, space())
            RUN = report.get('run')
            end = report.get('end') or {}
            mine = [record for record in items_of(RUN).values() if record['kind'] == 'container']
            check(row, 'the container with the run\'s label and the one with its compose project name are items of '
                       'the run, declared by the census with the identity the engine showed [%s %s]'
                  % (sorted(record['locator']['name'] for record in mine), (end.get('docker') or {}).get('engines')),
                  status == 0 and sorted(record['locator']['name'] for record in mine)
                  == ['built-by-the-run', 'composed-by-the-run']
                  and all(record['creator'] == 'census' and record['owner'] == report['given']['owner'] for record in mine)
                  and sorted(record['locator'].get('id') for record in mine) == sorted([labelled['Id'], composed['Id']])
                  and (end.get('docker') or {}).get('engines') == {'default': 'read'})
            wrote = written(since)
            check(row, 'each was declared and confirmed as space-runner, before the one signal [%s]'
                  % ([name for name, _ in wrote],),
                  [name for name, _ in wrote].count(SP.DECLARE) == 3 and SP.SIGNAL in [name for name, _ in wrote]
                  and all(principal == SP.RUNNER for _, principal in wrote[1:])
                  and [name for name, _ in wrote].index(SP.SIGNAL)
                  > max(at for at, (name, _) in enumerate(wrote) if name == SP.DECLARE))
            check(row, 'at run finished both go through the engine\'s own stop and remove, with no force option; '
                       'another run\'s container and the one with no label have no item and are still on the engine '
                       '[%s %s]' % ([record['state'] for record in mine], [one['name'] for one in ENGINE['containers']]),
                  [record['state'] for record in mine] == ['removed', 'removed']
                  and [one['name'] for one in ENGINE['containers']] == ['another-runs', 'made-by-hand']
                  and ('container', 'stop', labelled['Id']) in ENGINE['calls']
                  and ('container', 'rm', composed['Id']) in ENGINE['calls']
                  and not any(word in ('--force', '-f', 'kill', 'prune') for call in ENGINE['calls'] for word in call)
                  and not [record for record in L.items().values() if record.get('kind') == 'container'
                           and (record.get('locator') or {}).get('name') in ('another-runs', 'made-by-hand')])
            # An engine nobody can read: it is named, and nothing of it is recorded.
            late = container('made-while-unread', labels_from={'veldo.space.run': label_file})
            ENGINE['unreadable'] = True
            try:
                status, said, report = run(['--label', 'docker', '--', 'sh', '-c',
                                            'printf %%s "$VELDO_SPACE_LABEL" > %s' % label_file], W10, space())
            finally:
                ENGINE['unreadable'] = False
            said_of = ((report.get('end') or {}).get('docker') or {}).get('engines') or {}
            check(row, 'an engine that cannot be read is named, its labelled container gets no item and stays [%s]'
                  % (said_of,),
                  status == 0 and 'Cannot connect' in str(said_of.get('default'))
                  and not [record for record in items_of(report.get('run')).values() if record['kind'] == 'container']
                  and late in ENGINE['containers'])
            ENGINE['containers'].remove(late)
            L.release(report.get('run'))
        except Exception as error:
            stopped(row, error)

        try:
            row = 'fix5/no-issuer-no-run'
            W11, _ = worktree(ORCHARD, 'w-issuer')
            marker = temp / 'ran-with-no-issuer.json'
            since = seq()
            status, said, report = run(
                ['--', sys.executable, '-c',
                 'import json, os, sys\n'
                 'json.dump({"tmp": os.environ.get("TMPDIR"), "label": os.environ.get("VELDO_SPACE_LABEL")}, '
                 'open(%r, "w"))\nsys.exit(9)\n' % str(marker)], W11, space(issue=None))
            check(row, 'a wiring with no issuer: the wrapper says the run is not recorded, and the command runs '
                       'unchanged with its own status [%s %s %s]' % (status, said.strip(), text_of(marker)),
                  status == 9 and 'the run is not recorded (no authority issues a run to this process)' in said
                  and report.get('wrapped') is False
                  and json.loads(text_of(marker) or '{}') == {'tmp': BASE['TMPDIR'], 'label': None})
            check(row, 'no run was issued and nothing was written: the wrapper never issues its own run [%s]'
                  % (written(since),), written(since) == [])
            refused = space(issue=lambda label, scope: L.issue(SP.OBSERVER, label, scope=scope))
            status, said, report = run(['--', 'sh', '-c', 'exit 4'], W11, refused)
            check(row, 'a run the issuer did not issue to space-runner is not the wrapper\'s: it is not recorded '
                       'and the command runs unchanged [%s %s]' % (status, said.strip()[:120]),
                  status == 4 and report.get('wrapped') is False and 'the run is not recorded' in said)
        except Exception as error:
            stopped(row, error)

        try:
            row = 'fix6/scratch-not-made'
            W12, _ = worktree(ORCHARD, 'w-unmade')
            marker = temp / 'ran-with-no-scratch.json'

            def cannot(path):
                raise PermissionError(13, 'the fixture lets nobody make this folder')
            make, CLI._space_make = CLI._space_make, cannot
            before = len(L.observations)
            try:
                status, said, report = run(
                    ['--label', 'unmade', '--', sys.executable, '-c',
                     'import json, os\njson.dump({"tmp": os.environ.get("TMPDIR")}, open(%r, "w"))\n' % str(marker)],
                    W12, space())
            finally:
                CLI._space_make = make
            mine = items_of(report.get('run'))
            check(row, 'a scratch folder that could not be made: the wrapper says its item stays declared, the '
                       'command runs with its own temporary folder, and the item is declared with nothing at its '
                       'path [%s %s]' % (status, [note for note in report.get('notes') or ()]),
                  status == 0 and json.loads(text_of(marker) or '{}') == {'tmp': BASE['TMPDIR']}
                  and any('stays declared, for reconcile' in note for note in report.get('notes') or ())
                  and [record['state'] for record in mine.values()] == ['declared']
                  and not os.path.lexists(list(mine.values())[0]['locator']['path']))
            check(row, 'no gone was sent as space-runner, accepted or refused [%s]'
                  % (sorted({seen.get('operation') for seen in L.observations[before:]}),),
                  not any('gone' in str(seen.get('operation')) for seen in L.observations[before:]))
        except Exception as error:
            stopped(row, error)

        try:
            row = 'ac1/unread-group-sends-nothing'
            W3, _ = worktree(ORCHARD, 'w-unread')
            member, _ = sleeper()
            for answer, group, reason in (('nobody could read', Group(read=False), 'group_unread'),
                                          ('has a process in it', Group(pids=[member.pid]), 'group_not_empty')):
                wiring = space(group=group)
                given = CLI._space_begin(wiring, 'build', 'unread', str(W3), start=ended)
                given['status'] = 0
                (Path(given['scratch']) / 'half-written.bin').write_text('still being written\n')
                (W3 / 'build').mkdir(exist_ok=True)
                (W3 / 'build' / 'out.o').write_text('o')
                since = seq()
                end = CLI._space_finish(wiring, given)
                mine = items_of(given['run'])
                check(row, 'a group that %s: run finished is not sent and the reason is %s; no census, '
                           'no signal and no release are written [%s %s]' % (answer, reason, end, written(since)),
                      end['sent'] is False and end['reason'] == reason and end['census'] is None
                      and end['docker'] is None and end['signal'] is None and written(since) == [])
                check(row, 'the scratch root is present and on disk with its file, the build folder has no item and '
                           'is there, and the hold is held [%s %s]'
                      % ([record['state'] for record in mine.values()], (L.hold(given['run']) or {}).get('state')),
                      [record['state'] for record in mine.values()] == ['present']
                      and text_of(Path(given['scratch']) / 'half-written.bin') == 'still being written\n'
                      and (W3 / 'build' / 'out.o').is_file() and item_at(W3 / 'build') == []
                      and (L.hold(given['run']) or {}).get('state') == 'admitted')
                # the fixture ends the run it left open, so that the rows after this one start even
                Path(given['scratch'], 'half-written.bin').write_text('still being written\n')
                L.release(given['run'])
        except Exception as error:
            stopped(row, error)

        try:
            row = 'ac1/only-the-runs-own-items'
            W4, _ = worktree(ORCHARD, 'w-own', ticket='VELDO-9004')
            wiring = space()
            given = CLI._space_begin(wiring, 'build', 'own', str(W4), start=ended)
            given['status'] = 0
            RUN = given['run']
            # An item of this run the owner marked Keep, and the scratch root of another run of the
            # same project and ticket.
            kept_path = SCRATCH / 'kept-by-the-owner'
            kept_path.mkdir()
            (kept_path / 'results.txt').write_text('the owner said keep\n')
            kept = L.declare('scratch', {'path': str(kept_path)}, given['owner'], 'seam')['item']
            L.confirm(kept)
            due = L.signal('run_finished', {'items': [{'item': kept, 'version': version_of(kept)}]})
            # The owner's Keep is the signed space_disposition command and nothing else (VELDO-0318). The
            # Ledger raises no request for a scratch folder, so the settled request is planted
            # (support/space_owner_keep.py, keep_planted); the signature, the membership check and the
            # one transition are the Ledger's own.
            claimed = L.outcome(kept, 'kept', {'owner_keep': {'at': NOW, 'answer': 'keep'}}, principal='owner')
            check(row, 'an outcome that claims the owner mark is refused [%s]' % (claimed.get('reason'),),
                  not claimed.get('ok') and claimed.get('reason') == 'not_authorized'
                  and not (L.item(kept) or {}).get('owner_keep'))
            KEEP = load('v313_owner_keep', ROOT / 'scripts' / 'suites' / 'support' / 'space_owner_keep.py')
            marked = KEEP.keep_planted(L, S, CM, conn, SP.ITEM_KIND, kept, owner_sign, NOW)
            other_run = L.issue(SP.RUNNER, 'other', scope=A)['run']
            other_path = SCRATCH / 'other-run'
            other_path.mkdir()
            (other_path / 'theirs.txt').write_text('another run is writing this\n')
            other = L.declare('scratch', {'path': str(other_path)},
                              {'scope': A, 'ticket': 'VELDO-9004', 'run': {'id': other_run, 'station': 'build'}},
                              'seam')['item']
            L.confirm(other)
            versions = (version_of(kept), version_of(other))
            end = finish(wiring, given)
            mine = L.item(given['items'][given['scratch']])
            check(row, 'the fixture marked the item Keep as the owner [%s %s]' % (due.get('reason'), marked.get('reason')),
                  due.get('ok') is True and marked.get('ok') is True)
            check(row, 'run finished removes the run\'s own scratch root [%s %s]' % (mine.get('state'), end.get('reason')),
                  end['sent'] is True and mine.get('state') == 'removed' and not os.path.lexists(given['scratch']))
            check(row, 'the item of the run the owner marked Keep is kept with the owner\'s mark at the version it '
                       'had, and its folder and file are there [%s]' % ((L.item(kept) or {}).get('state'),),
                  (L.item(kept) or {}).get('state') == 'kept'
                  and ((L.item(kept) or {}).get('owner_keep') or {}).get('by') == 'owner'
                  and version_of(kept) == versions[0]
                  and text_of(kept_path / 'results.txt') == 'the owner said keep\n')
            check(row, 'the scratch root of another run of the same project and ticket is present at the version it '
                       'had, with its file [%s]' % ((L.item(other) or {}).get('state'),),
                  (L.item(other) or {}).get('state') == 'present' and version_of(other) == versions[1]
                  and text_of(other_path / 'theirs.txt') == 'another run is writing this\n')
            runner = CLI._SpaceAs(L, SP, SP.RUNNER)
            since = seq()
            nobody = runner.signal('run_finished', {'run': 'a-dispatch:nobody-issued'})
            named = runner.signal('run_finished', {'items': [{'item': other, 'version': version_of(other)}]})
            abandon = runner.signal('worktree_abandoned', {'run': RUN})
            keep_it = runner.outcome(other, 'kept', {'owner_keep': {'at': NOW, 'answer': 'keep'}})
            check(row, 'the Ledger refuses space-runner a signal for a run nobody issued to it, a signal that names '
                       'items, worktree abandoned and the owner\'s Keep, each by name, with nothing written [%s]'
                  % ([answer.get('reason') for answer in (nobody, named, abandon, keep_it)],),
                  [answer.get('reason') for answer in (nobody, named, abandon, keep_it)]
                  == ['space_not_permitted:space_signal', 'space_not_permitted:space_signal',
                      'space_not_permitted:space_abandon', 'space_not_permitted:space_disposition']
                  and written(since) == [])
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC2: the command's own status; 75 in act mode with too little space; report mode starts
        # =====================================================================================
        try:
            row = 'ac2/command-status'
            W5, _ = worktree(ORCHARD, 'w-status')
            for argv, wanted in ((['sh', '-c', 'exit 0'], 0), (['sh', '-c', 'exit 7'], 7),
                                 (['sh', '-c', 'kill -TERM $$'], 143),
                                 ([str(temp / 'no-such-program')], 127)):
                # what the supervisor says of a command that is not there goes to this process's own
                # standard error, as the command's would: it is sent nowhere for this one call
                quiet, kept_stderr = os.open(os.devnull, os.O_WRONLY), os.dup(2)
                os.dup2(quiet, 2)
                try:
                    status, said, report = run(['--'] + argv, W5, space())
                finally:
                    os.dup2(kept_stderr, 2)
                    os.close(quiet)
                    os.close(kept_stderr)
                check(row, 'the wrapper returns the command\'s own status %d for %s, and the run\'s hold is released '
                           'and its scratch root removed [%s %s %s]'
                      % (wanted, argv[-1][-20:], status, (L.hold(report.get('run')) or {}).get('state'),
                         said.strip()[:160]),
                      status == wanted and (L.hold(report.get('run')) or {}).get('state') == 'released'
                      and [record['state'] for record in items_of(report.get('run')).values()] == ['removed'])
        except Exception as error:
            stopped(row, error)

        try:
            row = 'ac2/act-waits-75'
            W6, _ = worktree(ORCHARD, 'w-wait')
            marker = temp / 'started-in-act.txt'
            before = set(os.listdir(SCRATCH / 'run-scratch'))
            status, said, report = run(['--label', 'wait', '--', 'sh', '-c', 'echo started > %s' % marker], W6,
                                       space(free=SHORT))
            RUN = report.get('run')
            check(row, 'act mode with too little space: the wrapper returns 75 [%s]' % (status,), status == 75)
            check(row, 'the numbers are on standard error: the pool, the need, the free bytes, what other runs hold '
                       'and the floor [%s]' % (said.strip(),),
                  'NOT STARTED' in said and 'pool host' in said and 'need %d' % NEED in said
                  and 'free %d' % SHORT in said and 'held by other runs 0' in said and 'floor %d' % FLOOR in said)
            check(row, 'the command was not started: its marker file is not there', not marker.exists())
            check(row, 'no scratch root was made and the run has no item; its hold is released, never left admitted '
                       '[%s %s]' % (items_of(RUN), (L.hold(RUN) or {}).get('state')),
                  items_of(RUN) == {} and set(os.listdir(SCRATCH / 'run-scratch')) == before
                  and (L.hold(RUN) or {}).get('state') == 'released' and report.get('started') is False)

            row = 'ac2/report-starts'
            WM, _ = worktree(MEADOW, 'w-report')
            marker = temp / 'started-in-report.txt'
            since = seq()
            status, said, report = run(['--label', 'advised', '--', 'sh', '-c', 'echo started > %s; exit 4' % marker],
                                       WM, space(free=SHORT))
            RUN = report.get('run')
            check(row, 'report mode with the same numbers: they are printed, and the command starts and its status '
                       'is returned [%s %s]' % (status, said.strip()),
                  status == 4 and text_of(marker) == 'started\n' and 'would wait' in said and 'need %d' % NEED in said
                  and 'free %d' % SHORT in said and 'floor %d' % FLOOR in said and 'NOT STARTED' not in said)
            check(row, 'the hold was recorded advised, with the numbers, and released at the run\'s end [%s %s]'
                  % (report.get('answer'), (L.hold(RUN) or {}).get('state')),
                  report.get('answer') == 'advised'
                  and report.get('reason') == {'pool': 'host', 'need': NEED, 'free': SHORT, 'held': 0, 'floor': FLOOR}
                  and (L.hold(RUN) or {}).get('state') == 'released')
            check(row, 'in report mode run finished marks the run\'s scratch root due and removes nothing [%s]'
                  % ([record['state'] for record in items_of(RUN).values()],),
                  [record['state'] for record in items_of(RUN).values()] == ['due']
                  and os.path.isdir(report.get('scratch') or ''))
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC3: record and event refuse by name
        # =====================================================================================
        try:
            row = 'ac3/record-refusals'
            outside = temp / 'elsewhere' / 'made-by-a-script'
            outside.mkdir(parents=True)
            link = Path(ORCHARD['worktree_root']) / 'link-to-vms'
            link.symlink_to(STATE / 'vms')
            since = seq()
            status, out, said = verb(CLI.space_record, ['--kind', 'worktree', '--path', str(outside)], space())
            check(row, 'a folder outside every known root is refused by name, exit 1, and gets no item [%s %s]'
                  % (status, said.strip()),
                  status == 1 and said.strip() == 'veldo space record: refused space_outside_roots'
                  and item_at(outside) == [] and out == '')
            for argv, wanted in ((['--kind', 'bucket', '--path', str(outside)], 'space_unknown_kind:bucket'),
                                 (['--kind', 'worktree', '--path', str(STATE / 'vms' / 'disk.raw')],
                                  'space_protected:path:' + str(STATE / 'vms')),
                                 (['--kind', 'agent_repository', '--path', str(STATE / 'vms')],
                                  'space_protected:path:' + str(STATE / 'vms')),
                                 (['--kind', 'worktree', '--path', str(link / 'disk.raw')],
                                  'space_protected:path:' + str(STATE / 'vms')),
                                 (['--kind', 'worktree', '--path', ORCHARD['worktree_root'] + '/a/../../../elsewhere'],
                                  'space_locator_parent'),
                                 (['--kind', 'scratch', '--path', str(SCRATCH / 'a-script-scratch')],
                                  'space_record_kind:scratch'),
                                 (['--kind', 'build_output', '--path', str(BUILD / 'a-script-build')],
                                  'space_record_kind:build_output'),
                                 (['--kind', 'evidence', '--path', str(SCRATCH / 'a-script-evidence')],
                                  'space_record_kind:evidence'),
                                 (['--kind', 'worktree', '--path', ORCHARD['worktree_root'] + '/new', '--session', 's-9'],
                                  'space_record_session'),
                                 (['--kind', 'agent_repository', '--path', str(W)], 'space_record_exists'),
                                 (['--confirm', 'space:item:nobody-declared-this'], 'space_record_not_declared'),
                                 (['--confirm', W_ITEM], 'space_record_not_declared')):
                status, out, said = verb(CLI.space_record, argv, space())
                check(row, '%s is refused as %s, exit 1, with no item [%s %s]'
                      % (' '.join(argv[:2] + [argv[-1][-24:]]), wanted, status, said.strip()),
                      status == 1 and said.strip() == 'veldo space record: refused ' + wanted and out == '')
            check(row, 'none of the refusals wrote to the journal, and the protected file is as it was [%s]'
                  % (written(since),),
                  written(since) == [] and text_of(STATE / 'vms' / 'disk.raw') == 'a disk image nobody may touch\n')

            row = 'fix1/existing-work-is-never-scratch'
            W13, W13_ITEM = worktree(ORCHARD, 'w-notes', ticket='VELDO-9013')
            (W13 / 'notes').mkdir()
            (W13 / 'notes' / 'only-copy.txt').write_text('the only copy of some work\n')
            handmade = Path(ORCHARD['worktree_root']) / 'made-by-hand'
            handmade.mkdir()
            (handmade / 'draft.txt').write_text('a folder a person made\n')
            unmade = SCRATCH / 'sessions' / 'orchard' / 'sess-y'
            since = seq()
            for argv, wanted in ((['--kind', 'scratch', '--path', str(W13 / 'notes'), '--session', 'sess-x'],
                                  'space_record_kind:scratch'),
                                 (['--kind', 'scratch', '--path', str(handmade), '--session', 'sess-x'],
                                  'space_record_kind:scratch'),
                                 (['--kind', 'scratch', '--path', str(handmade)], 'space_record_kind:scratch'),
                                 (['--kind', 'scratch', '--path', str(unmade), '--session', 'sess-y'],
                                  'space_record_kind:scratch'),
                                 (['--kind', 'worktree', '--path', str(handmade)], 'space_record_exists'),
                                 (['--kind', 'agent_repository', '--path', str(handmade)], 'space_record_exists'),
                                 (['--kind', 'worktree', '--path', str(W13 / 'notes')], 'space_record_exists'),
                                 (['--kind', 'worktree', '--path', str(W13 / 'notes' / 'only-copy.txt')],
                                  'space_record_exists')):
                status, out, said = verb(CLI.space_record, argv, space())
                check(row, '%s %s is refused as %s, exit 1 [%s %s]'
                      % (' '.join(argv[:2]), argv[3][-22:] + (' with a session' if '--session' in argv else ''),
                         wanted, status, said.strip()),
                      status == 1 and said.strip() == 'veldo space record: refused ' + wanted and out == '')
            check(row, 'no refusal made an item or wrote to the journal [%s]' % (written(since),),
                  written(since) == [] and item_at(W13 / 'notes') == [] and item_at(handmade) == []
                  and item_at(unmade) == [])
            # What a later writer puts where the refused session folder would have been is nobody's item.
            unmade.mkdir(parents=True)
            (unmade / 'later.txt').write_text('written after the refusal\n')
            # The session ends, as the consumer of the hook's event will signal it (VELDO-0323).
            sent = [SIG.signal(L, 'session_ended', {'session': name}, probe=P, kinds=K, remover=RM, emitter='fixture',
                               free=lambda pool: PLENTY, keep=lambda identity, record: KP.keep(L, identity, record),
                               run=client, proc=str(PROC), borrow_root=str(temp / 'borrowed'))
                    for name in ('sess-x', 'sess-y')]
            check(row, 'session ended for those sessions makes nothing due and removes nothing [%s]'
                  % ([(answer.get('ok'), answer.get('items')) for answer in sent],),
                  all(answer.get('ok') is True and answer.get('items') == [] for answer in sent))
            check(row, 'the worktree\'s untracked file, the hand-made folder\'s file and the later file are on disk, '
                       'byte for byte, and the worktree\'s item is present [%s]' % ((L.item(W13_ITEM) or {}).get('state'),),
                  text_of(W13 / 'notes' / 'only-copy.txt') == 'the only copy of some work\n'
                  and text_of(handmade / 'draft.txt') == 'a folder a person made\n'
                  and text_of(unmade / 'later.txt') == 'written after the refusal\n'
                  and (L.item(W13_ITEM) or {}).get('state') == 'present')

            row = 'ac3/record-accepted'
            made = Path(ORCHARD['worktree_root']) / 'by-a-script'
            since = seq()
            status, out, said = verb(CLI.space_record, ['--kind', 'worktree', '--path', str(made) + '/'], space())
            found = item_at(made)
            check(row, 'a worktree a script is about to make is declared before it is there: exit 0, one item, '
                       'declared, creator record, owned by its project, and the verb prints the item [%s %s %s]'
                  % (status, out.strip(), said.strip()),
                  status == 0 and len(found) == 1 and found[0][1]['state'] == 'declared'
                  and found[0][1]['creator'] == 'record' and found[0][1]['owner'] == {'scope': A}
                  and json.loads(out or '{}') == {'item': found[0][0], 'state': 'declared'} and not made.exists())
            status, out, said = verb(CLI.space_record, ['--confirm', found[0][0]], space())
            check(row, 'it is not confirmed while nothing is at its path [%s %s]' % (status, said.strip()),
                  status == 1 and said.strip() == 'veldo space record: refused space_record_absent')
            git(ORCHARD['repository'], 'worktree', 'add', '-q', '--detach', str(made))
            status, out, said = verb(CLI.space_record, ['--confirm', found[0][0]], space())
            check(row, 'made with plain git and confirmed, it is present [%s %s %s]' % (status, out.strip(), said.strip()),
                  status == 0 and json.loads(out or '{}') == {'item': found[0][0], 'state': 'present'}
                  and item_at(made)[0][1]['state'] == 'present')
            check(row, 'both commands were written as space-observer [%s]' % (written(since),),
                  written(since) == [(SP.DECLARE, SP.OBSERVER), (SP.CONFIRM, SP.OBSERVER)])
            status, out, said = verb(CLI.space_record, ['--kind', 'worktree', '--path', str(made)], space())
            check(row, 'recorded a second time it is refused, because it exists [%s]' % (said.strip(),),
                  status == 1 and said.strip() == 'veldo space record: refused space_record_exists')
            status, out, said = verb(CLI.space_record, ['--kind', 'agent_repository', '--path', str(made / 'nested')],
                                     space())
            check(row, 'a path inside a recorded worktree is refused by the item it is inside [%s]' % (said.strip(),),
                  status == 1 and said.strip() == 'veldo space record: refused space_record_inside:' + found[0][0])

            row = 'ac3/event-types'
            check(row, 'the verb takes released and no other type; the hooks\' three are named apart [%s %s]'
                  % (CLI.SPACE_EVENT_TYPES, CLI.SPACE_HOOK_EVENT_TYPES),
                  tuple(CLI.SPACE_EVENT_TYPES) == ('released',)
                  and tuple(CLI.SPACE_HOOK_EVENT_TYPES) == ('ref_changed', 'session_started', 'session_ended'))
            since = seq()
            for name in ('landed', 'worktree_abandoned', 'run_finished', 'ticket_ended', ''):
                status, out, said = verb(CLI.space_event, ['--type', name, '--path', str(made)], space())
                check(row, 'the event type %r is refused by name, exit 1 [%s %s]' % (name, status, said.strip()),
                      status == 1 and said.strip() == 'veldo space event: refused space_unknown_event:' + name)
            for argv, wanted in ((['--type', 'released', '--path', str(made), '--path', str(outside)],
                                  'space_outside_roots'),
                                 (['--type', 'released', '--path', str(STATE / 'vms' / 'disk.raw')],
                                  'space_protected:path:' + str(STATE / 'vms'))):
                status, out, said = verb(CLI.space_event, argv, space())
                check(row, 'the event %s is refused as %s, exit 1 [%s %s]'
                      % (' '.join(argv[:2]), wanted, status, said.strip()),
                      status == 1 and said.strip() == 'veldo space event: refused ' + wanted and out == '')
            # The hooks' types: refused by name before any send (with a ledger) and before any spool
            # (with none). The Ledger sees no command and the state root holds no entry.
            hook_state = temp / 'event-types-state'
            for argv in (['--type', 'session_started', '--session', 's-1'],
                         ['--type', 'session_ended', '--session', 's-1', '--path', str(SCRATCH / 'sessions' / 's-1')],
                         ['--type', 'session_ended', '--session', 's-1', '--path', str(link)],
                         ['--type', 'ref_changed', '--repository', ORCHARD['repository'], '--ref', 'refs/heads/main',
                          '--new', git(ORCHARD['repository'], 'rev-parse', 'HEAD')],
                         ['--type', 'ref_changed', '--repository', str(temp / 'elsewhere'), '--ref',
                          'refs/heads/main', '--new', 'a' * 40]):
                wanted = 'veldo space event: refused space_event_hook_only:' + argv[1]
                seen = len(L.observations)
                status, out, said = verb(CLI.space_event, argv + ['--state-root', str(hook_state)], space())
                check(row, 'with a ledger the hook type %s is refused by name and nothing is sent [%s %s]'
                      % (argv[1], status, said.strip()),
                      status == 1 and out == '' and said.strip() == wanted and len(L.observations) == seen
                      and not hook_state.exists())
                out, said = io.StringIO(), io.StringIO()
                status = CLI.space_event(argv + ['--state-root', str(hook_state)],
                                         environ=dict(BASE, VELDO_INSTALLATION=str(temp / 'no-installation'),
                                                      XDG_STATE_HOME=str(temp / 'event-types-xdg')),
                                         stdout=out, stderr=said)
                check(row, 'with no ledger the hook type %s is refused by name and nothing is spooled [%s %s]'
                      % (argv[1], status, said.getvalue().strip()),
                      status == 1 and out.getvalue() == '' and said.getvalue().strip() == wanted
                      and not hook_state.exists() and not (temp / 'event-types-xdg').exists())
            check(row, 'no event wrote to the journal and the recorded worktree is present and on disk [%s]'
                  % (written(since),),
                  written(since) == [] and item_at(made)[0][1]['state'] == 'present' and (made / 'tracked.txt').is_file())
            status, out, said = verb(CLI.space_event, ['--type', 'released', '--path', str(made)], space())
            observed = json.loads(out) if out else {}
            event_record = L.event_record(observed.get('event')) or {}
            check(row, 'released records the exact item as space-observer and returns without removal',
                  status == 0 and observed.get('recorded') is True and event_record.get('state') == 'received'
                  and event_record.get('subject', {}).get('items') == [item_at(made)[0][0]]
                  and item_at(made)[0][1]['state'] == 'present' and (made / 'tracked.txt').is_file()
                  and L.observations[-1].get('principal') == SP.OBSERVER)
        except Exception as error:
            stopped(row, error)

        # =====================================================================================
        # AC4: no central installation
        # =====================================================================================
        try:
            row = 'ac4/no-installation-runs-unchanged'
            NOWHERE = dict(BASE, VELDO_INSTALLATION=str(temp / 'no-installation'), MARK='kept as it was')
            seen = temp / 'seen-ac4.json'
            script = ('import json, os, sys\n'
                      'json.dump({"tmp": os.environ.get("TMPDIR"), "label": os.environ.get("VELDO_SPACE_LABEL"),\n'
                      '           "compose": os.environ.get("COMPOSE_PROJECT_NAME"), "mark": os.environ.get("MARK"),\n'
                      '           "cwd": os.getcwd(), "argv": sys.argv[1:]}, open(%r, "w"))\n'
                      'sys.exit(7)\n' % str(seen))
            said, report = io.StringIO(), {}
            since = seq()
            status = CLI.space_run(['--', sys.executable, '-c', script, 'a b', 'c'], environ=dict(NOWHERE),
                                   cwd=str(temp / 'elsewhere'), stderr=said, report=report)
            saw = json.loads(text_of(seen) or '{}')
            check(row, 'with no central installation the wrapper says so [%s]' % (said.getvalue().strip(),),
                  'no central installation' in said.getvalue() and report.get('wrapped') is False)
            check(row, 'the command starts, with its own arguments, environment and folder, and the wrapper returns '
                       'its status [%s %s]' % (status, saw),
                  status == 7 and saw == {'tmp': BASE['TMPDIR'], 'label': None, 'compose': None,
                                          'mark': 'kept as it was', 'cwd': str(temp / 'elsewhere'),
                                          'argv': ['a b', 'c']}
                  and written(since) == [])
            seen.unlink()
            done = subprocess.run([sys.executable, str(PRODUCTION['veldo']), 'space', 'run', '--', sys.executable, '-c',
                                   script, 'a b', 'c'], env=dict(NOWHERE, PYTHONDONTWRITEBYTECODE='1'),
                                  cwd=str(temp / 'elsewhere'), stdin=subprocess.DEVNULL, capture_output=True,
                                  timeout=120)
            saw = json.loads(text_of(seen) or '{}')
            check(row, 'as a real CLI process: it says so, the command starts unchanged and the CLI exits with its '
                       'status [%s %s %s]' % (done.returncode, done.stderr.decode().strip()[-200:], saw),
                  done.returncode == 7 and b'no central installation' in done.stderr
                  and saw.get('argv') == ['a b', 'c'] and saw.get('label') is None
                  and saw.get('tmp') == BASE['TMPDIR'] and saw.get('mark') == 'kept as it was')

            row = 'ac4/each-verb-says-so'
            for call, argv in ((CLI.space_record, ['--kind', 'worktree', '--path', str(temp / 'elsewhere')]),
                               (CLI.space_event, ['--type', 'released', '--path', str(temp / 'elsewhere')])):
                status, out, said = verb(call, argv, environ=dict(NOWHERE))
                check(row, '%s says there is no central installation, writes nothing and exits 0 [%s %s]'
                      % (call.__name__, status, said.strip()),
                      status == 0 and 'no central installation' in said and out == '')
            hook_state = temp / 'hook-state'
            hook_state.mkdir()
            for argv in (['space', 'record', '--state-root', str(hook_state), '--worktree', str(temp / 'elsewhere'),
                          '--git-dir', str(temp / 'elsewhere'), '--common-dir', str(temp / 'elsewhere'),
                          '0' * 40, '1' * 40, '1'],
                         ['space', 'event', '--state-root', str(hook_state), '--common-dir', str(temp / 'elsewhere')],
                         ['space', 'replay', '--state-root', str(hook_state)],
                         ['space', 'sign', '--as', 'space-runner']):
                done = subprocess.run([sys.executable, str(ROOT / 'bin' / 'veldo')] + argv,
                                      env=dict(NOWHERE, PYTHONDONTWRITEBYTECODE='1'), cwd=str(temp / 'elsewhere'),
                                      input=b'', capture_output=True, timeout=120)
                check(row, 'veldo %s says there is no central installation [%s %s]'
                      % (' '.join(argv[:2]), done.returncode, done.stderr.decode().strip()[-160:]),
                      (b'no central installation' in done.stderr or b'space_no_installation' in done.stderr)
                      and (done.returncode == 0 or argv[1] in ('replay', 'sign')))
            marker = temp / 'ran-unreachable.txt'
            said = io.StringIO()
            status = CLI.space_run(['--', 'sh', '-c', 'echo ran > %s; exit 2' % marker],
                                   environ=dict(BASE, VELDO_INSTALLATION=str(folder)), cwd=str(temp), stderr=said)
            check(row, 'an installation whose ledger this process cannot reach: the wrapper says so and runs the '
                       'command unchanged [%s %s]' % (status, said.getvalue().strip()),
                  status == 2 and text_of(marker) == 'ran\n' and 'not reachable' in said.getvalue())
            marker = temp / 'ran-off.txt'
            off = {'ledger': types.SimpleNamespace(config={'enabled': False})}
            status, said, report = run(['--', 'sh', '-c', 'echo ran > %s; exit 6' % marker], temp, off)
            check(row, 'an installation whose switch is off: no admission is asked, the wrapper says so and runs the '
                       'command unchanged [%s %s]' % (status, said.strip()),
                  status == 6 and text_of(marker) == 'ran\n' and 'is off' in said and report.get('wrapped') is False)
        except Exception as error:
            stopped(row, error)

        try:
            row = 'paths/canon'
            check(row, 'the engine canon engine/bin/veldo equals this repository copy',
                  (ROOT / 'engine' / 'bin' / 'veldo').read_bytes() == (ROOT / 'bin' / 'veldo').read_bytes())
            source = Path(PRODUCTION['veldo']).read_text()  # the copy the rows above ran
            block = source[source.index('# VELDO-0313: the run wrapper'):source.index('def route(argv):')]
            check(row, 'the wrapper and the verbs hold no delete of their own: no recursive delete, no unlink, no '
                       'rmdir and no git or engine remove',
                  not any(word in block for word in ('rmtree', 'unlink', 'rmdir', 'os.remove', "'rm'", '"rm"',
                                                     'worktree remove', '"remove"', 'prune')))
            import re
            check(row, 'they stop nothing: no kill of a process or a group, and the one signal sent is the stop the '
                       'wrapper was sent, passed on to the command',
                  block.count('os.kill(') == 1 and block.count('send_signal(') == 1
                  and not any(word in block for word in ('SIGKILL', 'cgroup.kill', '.terminate(', '.kill()',
                                                         'killpg', 'systemctl')))
            check(row, 'they wait on no timer: no sleep, and every poll is one with no time limit',
                  'sleep(' not in block and 'timeout=' not in block and not re.search(r'\.poll\([^)]', block)
                  and block.count('poller.poll()') == 1)
            check(row, 'they hold no call of the Ledger\'s issue and no gone, and the label they look for in a '
                       'process\'s environment is the one the Docker adapter gives a run',
                  '.issue(' not in block and '.gone(' not in block and CLI.SPACE_LABEL_VARIABLE == DK.LABEL_VARIABLE)
        except Exception as error:
            stopped(row, error)

    except Exception as error:
        stopped(row, error)
    finally:
        for descriptor in opened:
            try:
                os.close(descriptor)
            except OSError:
                pass
        for child in waiting:
            try:
                if child.stdin is not None:
                    child.stdin.close()
                child.wait(timeout=30)
            except Exception:  # noqa: BLE001 - a fixture process that will not end never reds a row
                try:
                    child.kill()  # the fixture's own stand-in, never a process of a wrapped run
                except Exception:  # noqa: BLE001
                    pass
        # No supervisor outlives the suite. Each row has ended what its command left. One that is
        # still there stays on processes that are no part of the fixture (another account's, which
        # this account cannot read), and it is the suite's own child: it is ended and collected.
        import signal
        try:
            row = 'supervise/none-stays-on-nothing'
            # Read before any of them is ended: one the kernel still shows, with no process this
            # account cannot read that started after it, stays on nothing. It is given five
            # seconds to end first, as stays_or_ends gives.
            stayed = []
            for process in supervisors:
                one = {'pid': process['pid'], 'started': process.get('started')}
                if not there(one, 0.0):
                    continue
                held = unread_by(one, process.get('run'))
                if not held and there(one, 5.0):
                    held = unread_by(one, process.get('run'))
                    stayed.append((process['pid'], process.get('run'), 'unread' if held else 'stays on nothing'))
                elif held:
                    stayed.append((process['pid'], process.get('run'), 'unread'))
            check(row, 'of the %d supervisors the suite started, each one the kernel still shows at the suite\'s '
                       'end stays on processes this account cannot read that started after it %s'
                  % (len(supervisors), stayed), all(how == 'unread' for _, _, how in stayed))
        except Exception as error:
            stopped(row, error)
        for process in supervisors:
            try:
                now = CLI._space_process(process['pid'])
                if now is not None and now['started'] == process.get('started'):
                    os.kill(process['pid'], signal.SIGKILL)
                os.waitpid(process['pid'], 0)
            except Exception:  # noqa: BLE001 - one that ended and was collected already
                pass
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0313 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v313_space_run_suite()
