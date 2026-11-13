"""VELDO-0297: the space ledger, its item, pool, hold and reconcile records in the control store.

Run: python3 scripts/selftest.py --suite 132_veldo_0297_space_ledger

Only shared ROOT and expect are consumed. The store is a REAL control store (SQLite) in a temporary folder;
the installation and the project are FIXTURE folders with invented values, read from disk through the
declarations reader (installation.yaml through the one installation reader, .veldo/space.yaml through
read_project). Nothing is created or removed on disk by the ledger: every path a row declares is a name
under the temporary folder. The link rows make their own folders and symbolic links there, since the
ledger resolves a path before it records it. The journal signer is a stub whose signature is a function of the bytes, so
the replay's chain checks bind. The lifecycle table is a fixture, as plain data.

AC1 rows: ac1/declare-to-removed (the whole path, state by state), ac1/confirm-only-from-declared,
ac1/outcome-needs-signal (an outcome removed sent for a present item, without a signal, is refused and the
item is still present), ac1/outcome-only-from-due-or-removing, ac1/moves-table (every command against an
item in every one of the eight states: accepted exactly where 4.1 has the move, refused by the state's name
and nothing written everywhere else), ac1/signal (owner and event decide what becomes due; an unknown
event is refused), ac1/deferred-and-kept, ac1/adopt-report-rebranch, ac1/one-journal-record (each command
is one journal record holding the item, its kind, owner, locator and state), ac1/removing-is-final (a
removing item is not kept and is deferred only as remove_refused; review finding 3).

AC2 rows: ac2/generic-refused (the store's generic entity command is refused entity_owned for an item, a
pool, a hold and a reconcile record, by kind and by id prefix, and for retiring an item),
ac2/every-connection (a second connection nobody attached to refuses the same writes),
ac2/foreign-code (the ledger's command name registered from other code is refused).

AC3 rows: ac3/second-live-item, ac3/trailing-separator (a second declare through the same path written
with a trailing separator, a doubled separator and a dot segment), ac3/outside-roots, ac3/protect-list
(at, beneath and above a protected path; a Docker name pattern on both engine contexts; a compose project;
a project's own addition), ac3/free-after-end (the locator of a removed or gone item can be declared
again), ac3/refusals-counted, ac3/pool-by-device.

AC3 rows from the review (findings 1 and 2): ac3/parent-segment (a locator with a .. segment is refused by
name, also behind a link, where the text collapsed would name another folder), ac3/link-to-protected (a
link to a protected path), ac3/link-beneath-protected (a path beneath such a link), ac3/link-protect-entry
(a protected path that is itself a link protects the folder it leads to), ac3/link-out-of-roots (a link
out of every known root, and a path beneath it), ac3/two-links-one-folder (two links to one folder and the
folder itself are one live item at most).

AC4 rows: ac4/rebuilt-same (the state rebuilt from the exported journal holds the same item, pool, hold
and reconcile records as the live store, and the same state digest), ac4/rebuilt-size (the rebuilt item
has the size that was measured), ac4/rebuilt-pools-holds.

ledger/canon: the engine canon equals this repository copy.
"""


def _v297_space_ledger_suite():
    import importlib.util
    import io
    import shutil
    import tempfile
    from pathlib import Path

    # Literal anchors: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {
        'control_space.py': ROOT / ".veldo" / "control_space.py",
    }
    ROWS = ('ac1/declare-to-removed', 'ac1/confirm-only-from-declared', 'ac1/outcome-needs-signal',
            'ac1/outcome-only-from-due-or-removing', 'ac1/moves-table', 'ac1/signal', 'ac1/deferred-and-kept',
            'ac1/adopt-report-rebranch', 'ac1/one-journal-record', 'ac2/generic-refused', 'ac2/every-connection',
            'ac2/foreign-code', 'ac3/second-live-item', 'ac3/trailing-separator', 'ac3/outside-roots',
            'ac3/protect-list', 'ac3/free-after-end', 'ac3/refusals-counted', 'ac3/pool-by-device',
            'ac1/removing-is-final', 'ac3/parent-segment', 'ac3/link-to-protected',
            'ac3/link-beneath-protected', 'ac3/link-protect-entry', 'ac3/link-out-of-roots',
            'ac3/two-links-one-folder',
            'ac4/rebuilt-same', 'ac4/rebuilt-size', 'ac4/rebuilt-pools-holds', 'ledger/canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    temp = Path(tempfile.mkdtemp(prefix='v297-')).resolve()
    connections = []
    try:
        SP = load('v297_control_space', PRODUCTION['control_space.py'])
        beside = PRODUCTION['control_space.py']
        S = load('v297_control_store', beside.with_name('control_store.py'))
        R = load('v297_control_replay', beside.with_name('control_replay.py'))
        CFG = load('v297_control_space_config', beside.with_name('control_space_config.py'))
        YAML = load('v297_yamlish', beside.with_name('yamlish.py'))

        # ---- the fixture installation and project, read from disk --------------------------------------
        ENGINES = ['default', 'desktop-linux']
        MEGABYTE = 1024 * 1024
        PROTECTED = str(temp / 'state' / 'vms' / '0' / 'data')
        # A protected path that is itself a link: it leads to a folder under the scratch root.
        VAULT_LINK, VAULT = temp / 'state' / 'links' / 'vault', temp / 'scratch' / 'vault-real'
        for made_folder in (Path(PROTECTED), VAULT_LINK.parent, VAULT, temp / 'elsewhere' / 'deep'):
            made_folder.mkdir(parents=True)
        VAULT_LINK.symlink_to(VAULT)
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
                                             'gate': 6000 * MEGABYTE}},
                          'second': {'floor': 500 * MEGABYTE, 'needs': {'build': 0, 'review': 0, 'gate': 0}},
                          'desktop': {'floor': 8000 * MEGABYTE,
                                      'needs': {'build': 0, 'review': 0, 'gate': 3000 * MEGABYTE}}},
                'engines': list(ENGINES),
                'scratch_roots': {'roots': [str(temp / 'scratch')],
                                  'session_pattern': 'sessions/{working_folder}/{session_id}'},
                'build_roots': [str(temp / 'build')],
                'plain_repositories': [{'repository': str(temp / 'projects' / 'plain'),
                                        'worktree_root': str(temp / 'projects' / 'plain-worktrees')}],
                'client_accounts': [str(temp / 'client-a')],
                'protect': {'paths': [PROTECTED, str(VAULT_LINK)], 'volumes': ['atlas_pg_*'], 'containers': ['atlas-*'],
                            'images': ['store/objects'], 'networks': ['atlas_*'],
                            'compose_projects': ['ledgerdb']},
            }}))
        CONFIG = CFG.read(environ={'VELDO_INSTALLATION': str(folder), 'HOME': str(temp / 'home')},
                          stream=io.StringIO())
        REPOSITORY = temp / 'projects' / 'orchard'
        (REPOSITORY / '.veldo').mkdir(parents=True)
        (REPOSITORY / '.veldo' / 'space.yaml').write_text(YAML.dump({'protect': {'volumes': ['orchard_db_*']}}))
        PROJECT = dict(CFG.read_project(str(REPOSITORY), YAML.read, config=CONFIG, stream=io.StringIO()),
                       repository=str(REPOSITORY))
        WORKTREES = Path(PROJECT['worktree_root'])
        STATE = temp / 'state'

        EVENTS = ['run_finished', 'landed', 'ticket_ended']
        LIFECYCLE = {'version': 'fixture-1', 'events': EVENTS, 'ends_on': {
            'worktree': ['landed', 'ticket_ended'], 'branch': ['landed'], 'agent_repository': ['landed'],
            'build_output': EVENTS, 'scratch': EVENTS, 'evidence': ['run_finished'], 'container': EVENTS,
            'volume': EVENTS, 'network': EVENTS, 'image_tag': ['landed']}}

        def device(path):
            return 'dev-second' if path.startswith(str(temp / 'build') + '/') else 'dev-host'

        def sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        def verify(message, signature, signer):
            return (signature == sign(message), 'stub')

        def opened(name):
            conn = S.open_store(str(temp / name / 'control.sqlite3'))
            connections.append(conn)
            return conn

        def ledger(conn):
            return SP.Ledger(S, conn, 'authority', sign, config=CONFIG, projects=[PROJECT], state_root=str(STATE),
                             lifecycle=LIFECYCLE, host='fixture-host', device=device)

        conn = opened('store')
        L = ledger(conn)
        pools = [L.set_pool('host', 'filesystem', device='dev-host'),
                 L.set_pool('second', 'filesystem', device='dev-second'),
                 L.set_pool('desktop', 'engine_image', engine='desktop-linux', backing='host')]

        counter = [0]

        def owner(run=None, ticket='VELDO-9001'):
            counter[0] += 1
            return {'scope': {'type': 'project', 'id': PROJECT['project']}, 'ticket': ticket,
                    'run': {'id': run or 'run-%d' % counter[0], 'station': 'build'}}

        def scratch(name=None):
            counter[0] += 1
            return {'path': str(temp / 'scratch' / (name or 'item-%d' % counter[0]))}

        def state_of(identity):
            return (L.item(identity) or {}).get('state')

        def journal_length():
            return conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        def made(state):
            """A new scratch item brought to `state` by the ledger's own commands: (identity, run id)."""
            who = owner()
            run = who['run']['id']
            identity = L.declare('scratch', scratch(), who, 'seam')['item']
            if state == 'declared':
                return identity, run
            L.confirm(identity)
            if state == 'gone':
                L.gone(identity)
            if state in ('present', 'gone'):
                return identity, run
            L.signal('run_finished', {'run': run})
            if state == 'removing':
                L.outcome(identity, 'removing', {'event': 'run_finished'})
            elif state == 'removed':
                L.outcome(identity, 'removed', {'event': 'run_finished', 'bytes': 10})
            elif state == 'deferred':
                L.outcome(identity, 'deferred', {'rule': 'in_use', 'event': 'run_finished'})
            elif state == 'kept':
                L.outcome(identity, 'kept')
            return identity, run

        # ---- AC1: the whole path --------------------------------------------------------------------
        check('ac1/declare-to-removed', 'the three fixture pools are recorded %s' % [p.get('reason') for p in pools],
              all(p['ok'] for p in pools))
        who = owner(run='run-path')
        declared = L.declare('scratch', scratch('path-item'), who, 'seam')
        item = declared.get('item')
        record = L.item(item) or {}
        check('ac1/declare-to-removed', 'declare creates the item in state declared [%s]' % declared.get('reason'),
              declared['ok'] and declared.get('state') == 'declared' and record.get('state') == 'declared')
        check('ac1/declare-to-removed', 'with its identity under space:item: [%s]' % item,
              str(item).startswith('space:item:') and len(str(item)) > len('space:item:'))
        check('ac1/declare-to-removed', 'with pool filled in from the device [%s]' % record.get('pool'),
              record.get('pool') == 'host')
        check('ac1/declare-to-removed', 'with ends_on copied from the table with its version [%s]' % record.get('ends_on'),
              record.get('ends_on') == {'version': 'fixture-1', 'events': EVENTS})
        check('ac1/declare-to-removed', 'with kind, host, owner, creator and locator as given',
              record.get('kind') == 'scratch' and record.get('host') == 'fixture-host' and record.get('owner') == who
              and record.get('creator') == 'seam' and record.get('locator') == {'path': str(temp / 'scratch' / 'path-item')}
              and record.get('adopted') is False)
        step = L.confirm(item)
        check('ac1/declare-to-removed', 'confirm moves declared to present [%s]' % step.get('reason'),
              step['ok'] and state_of(item) == 'present')
        step = L.measure(item, 4096, 'run_finished')
        check('ac1/declare-to-removed', 'measure writes the size and moves nothing [%s]' % step.get('reason'),
              step['ok'] and state_of(item) == 'present'
              and L.item(item)['size'] == {'bytes': 4096, 'event': 'run_finished'})
        step = L.signal('run_finished', {'run': 'run-path'})
        check('ac1/declare-to-removed', 'signal marks it due and returns it [%s]' % step.get('reason'),
              step['ok'] and step.get('items') == [item] and state_of(item) == 'due')
        step = L.outcome(item, 'removing', {'event': 'run_finished', 'method': 'folder'})
        check('ac1/declare-to-removed', 'outcome removing moves due to removing [%s]' % step.get('reason'),
              step['ok'] and state_of(item) == 'removing')
        facts = {'event': 'run_finished', 'emitter': 'receiver', 'method': 'folder', 'bytes': 4096,
                 'free_before': 100, 'free_after': 4196}
        step = L.outcome(item, 'removed', facts)
        check('ac1/declare-to-removed', 'outcome removed moves removing to removed with the removal facts [%s]'
              % step.get('reason'), step['ok'] and state_of(item) == 'removed' and L.item(item)['removal'] == facts)

        # ---- AC1: confirm only from declared, outcome only from due or removing ----------------------
        for state in SP.STATES:
            identity, run = made(state)
            before, length = L.item(identity), journal_length()
            step = L.confirm(identity)
            if state == 'declared':
                check('ac1/confirm-only-from-declared', 'confirm from declared is accepted', step['ok'])
            else:
                check('ac1/confirm-only-from-declared', 'confirm from %s is refused by the state [%s]'
                      % (state, step.get('reason')), step['ok'] is False
                      and step.get('reason') == 'space_item_state:' + state and L.item(identity) == before
                      and journal_length() == length)

        present, run = made('present')
        length = journal_length()
        step = L.outcome(present, 'removed', {'event': 'run_finished', 'bytes': 1})
        check('ac1/outcome-needs-signal', 'outcome removed for a present item, with no signal, is refused [%s]'
              % (step.get('reason') or 'accepted'), step['ok'] is False
              and step.get('reason') == 'space_item_state:present')
        check('ac1/outcome-needs-signal', 'and the item is still present [%s]' % state_of(present),
              state_of(present) == 'present' and L.item(present)['removal'] is None)
        check('ac1/outcome-needs-signal', 'and nothing was journaled', journal_length() == length)
        L.signal('run_finished', {'run': run})
        step = L.outcome(present, 'removed', {'event': 'run_finished', 'bytes': 1})
        check('ac1/outcome-needs-signal', 'after the signal the same outcome is accepted [%s]' % step.get('reason'),
              step['ok'] and state_of(present) == 'removed')

        for state in SP.STATES:
            for outcome in ('removed', 'deferred', 'kept'):
                identity, run = made(state)
                before = L.item(identity)
                step = L.outcome(identity, outcome, {'rule': 'in_use', 'event': 'run_finished'})
                if state == 'due' or (state == 'removing' and outcome == 'removed'):
                    check('ac1/outcome-only-from-due-or-removing', 'outcome %s from %s is accepted [%s]'
                          % (outcome, state, step.get('reason')), step['ok'] and state_of(identity) == outcome)
                else:
                    check('ac1/outcome-only-from-due-or-removing', 'outcome %s from %s is refused [%s]'
                          % (outcome, state, step.get('reason') or 'accepted'), step['ok'] is False
                          and step.get('reason') == 'space_item_state:' + state and L.item(identity) == before)

        # ---- AC1: a removing item is removed to the end (review finding 3) -----------------------------
        identity, run = made('removing')
        before, length = L.item(identity), journal_length()
        step = L.outcome(identity, 'kept')
        check('ac1/removing-is-final', 'kept for a removing item is refused by the state [%s]'
              % (step.get('reason') or 'accepted'), step['ok'] is False
              and step.get('reason') == 'space_item_state:removing')
        check('ac1/removing-is-final', 'and the item is still removing, nothing written [%s]' % state_of(identity),
              L.item(identity) == before and journal_length() == length)
        for rule in ('in_use', 'unique_work', 'protected', 'not_in_ledger'):
            step = L.outcome(identity, 'deferred', {'rule': rule, 'event': 'run_finished'})
            check('ac1/removing-is-final', 'deferred as %s for a removing item is refused by the state [%s]'
                  % (rule, step.get('reason') or 'accepted'), step['ok'] is False
                  and step.get('reason') == 'space_item_state:removing' and L.item(identity) == before
                  and journal_length() == length)
        step = L.outcome(identity, 'removing', {'event': 'run_finished'})
        check('ac1/removing-is-final', 'removing is not written twice [%s]' % step.get('reason'),
              step['ok'] is False and step.get('reason') == 'space_item_state:removing')
        step = L.outcome(identity, 'deferred', {'rule': 'remove_refused', 'event': 'run_finished'})
        check('ac1/removing-is-final', 'the tool\'s refusal defers a removing item [%s]' % step.get('reason'),
              step['ok'] and state_of(identity) == 'deferred'
              and L.item(identity)['deferral'] == {'rule': 'remove_refused', 'event': 'run_finished', 'attempts': 1})
        identity, run = made('removing')
        step = L.outcome(identity, 'removed', {'event': 'run_finished', 'bytes': 1})
        check('ac1/removing-is-final', 'control: a removing item is removed [%s]' % step.get('reason'),
              step['ok'] and state_of(identity) == 'removed')
        identity, run = made('due')
        step = L.outcome(identity, 'kept')
        check('ac1/removing-is-final', 'control: kept is written from due [%s]' % step.get('reason'),
              step['ok'] and state_of(identity) == 'kept')

        # ---- AC1: every command against every state ---------------------------------------------------
        MOVES = {
            'confirm': (('declared',), 'present', lambda i, run: L.confirm(i)),
            'outcome removing': (('due',), 'removing', lambda i, run: L.outcome(i, 'removing', {'event': 'landed'})),
            'gone': (('present', 'declared', 'due', 'deferred'), 'gone', lambda i, run: L.gone(i)),
            'signal': (('present', 'kept', 'deferred'), 'due', lambda i, run: L.signal('run_finished', {'run': run})),
        }
        for name, (allowed, lands, send) in MOVES.items():
            for state in SP.STATES:
                identity, run = made(state)
                before, length = L.item(identity), journal_length()
                step = send(identity, run)
                if state in allowed:
                    check('ac1/moves-table', '%s from %s gives %s [%s]' % (name, state, lands, step.get('reason')),
                          step['ok'] and state_of(identity) == lands and journal_length() == length + 1)
                elif name == 'signal':
                    check('ac1/moves-table', 'signal leaves a %s item where it is and returns nothing %s'
                          % (state, step.get('items')), step['ok'] and step.get('items') == []
                          and L.item(identity) == before and journal_length() == length)
                else:
                    check('ac1/moves-table', '%s from %s is refused by the state, nothing written [%s]'
                          % (name, state, step.get('reason') or 'accepted'), step['ok'] is False
                          and step.get('reason') == 'space_item_state:' + state and L.item(identity) == before
                          and journal_length() == length)
        check('ac1/moves-table', 'the states are the eight of 4.1',
              set(SP.STATES) == {'declared', 'present', 'due', 'deferred', 'removing', 'removed', 'gone', 'kept'})
        missing = L.confirm('space:item:nobody')
        check('ac1/moves-table', 'a command for an item that does not exist is refused by name [%s]'
              % missing.get('reason'), missing['ok'] is False and missing.get('reason') == 'space_no_item')

        # ---- AC1: signal --------------------------------------------------------------------------
        mine, other = owner(run='run-signal', ticket='VELDO-9002'), owner(run='run-other', ticket='VELDO-9003')
        tree = L.declare('worktree', {'path': str(WORKTREES / 'signal-tree')}, mine, 'seam')['item']
        build = L.declare('build_output', {'path': str(WORKTREES / 'signal-tree' / 'target')}, mine, 'census',
                          parent=tree)['item']
        foreign = L.declare('scratch', scratch(), other, 'seam')['item']
        undeclared = L.declare('scratch', scratch(), mine, 'seam')['item']
        for identity in (tree, build, foreign):
            L.confirm(identity)
        step = L.signal('run_finished', {'run': 'run-signal'})
        check('ac1/signal', 'run finished makes the run\'s build output due and not its worktree %s' % step.get('items'),
              step['ok'] and step.get('items') == [build] and state_of(tree) == 'present')
        check('ac1/signal', 'another run\'s item and an item still declared are untouched',
              state_of(foreign) == 'present' and state_of(undeclared) == 'declared')
        check('ac1/signal', 'the item records the event that made it due', L.item(build).get('due') == {'event': 'run_finished'})
        step = L.signal('ticket_ended', {'scope': {'type': 'project', 'id': PROJECT['project']}, 'ticket': 'VELDO-9002'})
        check('ac1/signal', 'ticket ended, by scope and ticket, makes the worktree due %s' % step.get('items'),
              step['ok'] and step.get('items') == [tree] and state_of(foreign) == 'present')
        length = journal_length()
        step = L.signal('disk_looks_full', {'run': 'run-other'})
        check('ac1/signal', 'an unknown event is refused by name [%s]' % step.get('reason'),
              step['ok'] is False and step.get('reason') == 'space_unknown_event' and state_of(foreign) == 'present'
              and journal_length() == length)
        step = L.signal('run_finished', {})
        check('ac1/signal', 'a signal with no subject is refused [%s]' % step.get('reason'),
              step['ok'] is False and step.get('reason') == 'invalid_input:subject' and state_of(foreign) == 'present')

        # ---- AC1: deferred, kept, gone --------------------------------------------------------------
        identity, run = made('due')
        step = L.outcome(identity, 'deferred', {'rule': 'in_use', 'event': 'run_finished', 'retries_on': 'landed'})
        deferral = L.item(identity)['deferral']
        check('ac1/deferred-and-kept', 'deferred writes the rule, the event, the retry event and one attempt %s' % deferral,
              step['ok'] and deferral == {'rule': 'in_use', 'event': 'run_finished', 'retries_on': 'landed', 'attempts': 1})
        L.signal('landed', {'run': run})
        check('ac1/deferred-and-kept', 'the next event makes the deferred item due again', state_of(identity) == 'due')
        L.outcome(identity, 'deferred', {'rule': 'unique_work', 'event': 'landed'})
        check('ac1/deferred-and-kept', 'a second refusal counts two attempts',
              L.item(identity)['deferral'].get('attempts') == 2 and L.item(identity)['deferral'].get('rule') == 'unique_work')
        identity, run = made('due')
        step = L.outcome(identity, 'deferred', {'event': 'landed'})
        check('ac1/deferred-and-kept', 'a deferral that names no rule is refused [%s]' % step.get('reason'),
              step['ok'] is False and step.get('reason') == 'invalid_input:facts.rule' and state_of(identity) == 'due')
        step = L.outcome(identity, 'kept')
        check('ac1/deferred-and-kept', 'kept is written from due', step['ok'] and state_of(identity) == 'kept')
        L.signal('landed', {'run': run})
        check('ac1/deferred-and-kept', 'a kept item is made due by its next event', state_of(identity) == 'due')
        step = L.outcome(identity, 'burned')
        check('ac1/deferred-and-kept', 'an outcome outside the four is refused [%s]' % step.get('reason'),
              step['ok'] is False and step.get('reason') == 'invalid_input:outcome' and state_of(identity) == 'due')

        # ---- AC1: adopt, report, rebranch -----------------------------------------------------------
        who = {'scope': {'type': 'project', 'id': PROJECT['project']}, 'ticket': 'VELDO-9004'}
        found_at = {'path': str(WORKTREES / 'found-tree')}
        step = L.adopt('worktree', found_at, who, 'branch_pattern', branch='agent/a/VELDO-9004', start='c0ffee')
        adopted = L.item(step.get('item')) or {}
        check('ac1/adopt-report-rebranch', 'adopt creates the item present with adopted true [%s]' % step.get('reason'),
              step['ok'] and adopted.get('state') == 'present' and adopted.get('adopted') is True
              and adopted.get('creator') == 'reconcile' and adopted.get('adoption') == {'rule': 'branch_pattern'})
        again = L.adopt('worktree', found_at, who, 'branch_pattern')
        check('ac1/adopt-report-rebranch', 'adopt has the refusals of declare [%s]' % again.get('reason'),
              again['ok'] is False and str(again.get('reason')).startswith('space_locator_taken:'))
        loose = {'path': str(temp / 'scratch' / 'loose-folder')}
        step = L.report('scratch', loose, {'what': 'folder', 'why': 'no rule gives an owner'})
        reported = L.item(step.get('item')) or {}
        check('ac1/adopt-report-rebranch', 'report creates a report record with no owner [%s]' % step.get('reason'),
              step['ok'] and reported.get('owner') is None and reported.get('report', {}).get('proposed_owner') is None
              and reported.get('ends_on', {}).get('events') == [])
        again = L.report('scratch', loose, {'what': 'folder', 'why': 'still nobody'}, proposed_owner=dict(who))
        refreshed = L.item(step.get('item')) or {}
        check('ac1/adopt-report-rebranch', 'a second report refreshes the same record and still writes no owner',
              again['ok'] and again.get('item') == step.get('item') and refreshed.get('owner') is None
              and refreshed['report']['proposed_owner'] == who and refreshed['report']['found']['why'] == 'still nobody')
        taken = L.adopt('scratch', loose, who, 'owner_adopt')
        check('ac1/adopt-report-rebranch', 'adopting a reported thing gives the same record its owner [%s]'
              % taken.get('reason'), taken['ok'] and taken.get('item') == step.get('item')
              and L.item(taken['item'])['owner'] == who and L.item(taken['item'])['report'] is None)
        over = L.report('worktree', found_at, {'what': 'worktree'})
        check('ac1/adopt-report-rebranch', 'report never replaces an item that has an owner [%s]' % over.get('reason'),
              over['ok'] is False and str(over.get('reason')).startswith('space_locator_taken:'))
        tree_item = [key for key, value in L.items().items() if value['locator'] == found_at][0]
        step = L.rebranch(tree_item, 'agent/a/VELDO-9005', 'beef01')
        branch = L.item(step.get('branch_item')) or {}
        check('ac1/adopt-report-rebranch', 'rebranch writes the branch and the start commit [%s]' % step.get('reason'),
              step['ok'] and L.item(tree_item)['branch'] == 'agent/a/VELDO-9005' and L.item(tree_item)['start'] == 'beef01'
              and state_of(tree_item) == 'present')
        check('ac1/adopt-report-rebranch', 'and records a branch item for the new branch %s' % branch.get('locator'),
              branch.get('kind') == 'branch' and branch.get('locator') == {'repository': str(REPOSITORY), 'ref': 'agent/a/VELDO-9005'}
              and branch.get('start') == 'beef01')
        step = L.rebranch(tree_item, 'agent/a/VELDO-9005', 'beef02')
        check('ac1/adopt-report-rebranch', 'a branch that has an item gets no second one',
              step['ok'] and step.get('branch_item') is None and L.item(tree_item)['start'] == 'beef02')
        identity, run = made('present')
        step = L.rebranch(identity, 'agent/a/x', 'beef03')
        check('ac1/adopt-report-rebranch', 'rebranch of an item that is not a worktree is refused [%s]' % step.get('reason'),
              step['ok'] is False and step.get('reason') == 'space_not_a_worktree')
        L.signal('landed', {'ticket': 'VELDO-9004'})
        step = L.rebranch(tree_item, 'agent/a/y', 'beef04')
        check('ac1/adopt-report-rebranch', 'rebranch of a due worktree is refused by the state [%s]' % step.get('reason'),
              step['ok'] is False and step.get('reason') == 'space_item_state:due')

        # ---- AC1: one journal record per command, with the item ---------------------------------------
        length = journal_length()
        who = owner(run='run-journal')
        identity = L.declare('scratch', scratch('journal-item'), who, 'seam')['item']
        L.confirm(identity)
        records = S.export_journal(conn)[length:]
        check('ac1/one-journal-record', 'declare and confirm are one journal record each [%d]' % len(records),
              len(records) == 2 and all(list(r['transition']) == [identity] for r in records))
        states = [r['transition'][identity]['data'].get('state') for r in records]
        first = records[0]['transition'][identity] if records else {}
        check('ac1/one-journal-record', 'each holds the item\'s kind, owner, locator and state %s' % states,
              states == ['declared', 'present'] and first.get('kind') == 'space_item'
              and first['data'].get('kind') == 'scratch' and first['data'].get('owner') == who
              and first['data'].get('locator') == {'path': str(temp / 'scratch' / 'journal-item')})
        check('ac1/one-journal-record', 'each is signed and names its principal',
              all(r['signature'].startswith('stub:') and r['principal'] == 'authority' for r in records))
        seen = L.observations[-1]
        check('ac1/one-journal-record', 'the ledger\'s own observation names the item, kind, owner, locator and state',
              seen.get('item') == identity and seen.get('kind') == 'scratch' and seen.get('owner') == who
              and seen.get('state') == 'present' and seen.get('outcome') == 'accepted')

        # ---- AC2: only the ledger's module writes these kinds ------------------------------------------
        def generic(connection, operation, entity, kind, data, version=0):
            command = {'command_id': 'generic-%d' % counter[0], 'principal': 'authority', 'operation': operation,
                       'parameters': {'entity_id': entity, 'kind': kind, 'data': data},
                       'expected_versions': {entity: version}, 'artifact_digests': [], 'nonce': 'n-%d' % counter[0]}
            counter[0] += 1
            try:
                S.execute(connection, command, 'authority', sign, 1)
                return 'written'
            except S.StoreRefused as refusal:
                return refusal.code

        def exists(connection, entity):
            return connection.execute('SELECT 1 FROM entities WHERE id=?', (entity,)).fetchone() is not None

        forged = {'kind': 'scratch', 'state': 'present', 'locator': {'path': str(temp / 'scratch' / 'forged')}}
        ATTEMPTS = (
            ('an item', 'space:item:forged', 'space_item', forged),
            ('an item under another id', 'thing:forged', 'space_item', forged),
            ('another kind at an item id', 'space:item:forged-kind', 'note', {'text': 'x'}),
            ('a pool', 'space:pool:fixture-host:forged', 'space_pool', {'type': 'filesystem', 'floor': 0}),
            ('a hold', 'space:hold:forged', 'space_hold', {'state': 'admitted'}),
            ('a reconcile record', 'space:reconcile:forged', 'space_reconcile', {'counts': {}}),
        )
        for label, entity, kind, data in ATTEMPTS:
            code = generic(conn, 'upsert_entity', entity, kind, data)
            check('ac2/generic-refused', 'the generic entity command writing %s is refused entity_owned [%s]'
                  % (label, code), code == 'entity_owned' and not exists(conn, entity))
        real, run = made('present')
        version = conn.execute('SELECT version FROM entities WHERE id=?', (real,)).fetchone()[0]
        before = L.item(real)
        code = generic(conn, 'upsert_entity', real, 'space_item', dict(before, state='removed'), version)
        check('ac2/generic-refused', 'the generic command rewriting a real item\'s state is refused [%s]' % code,
              code == 'entity_owned' and L.item(real) == before)
        code = generic(conn, 'retire_entity', real, 'space_item', {}, version)
        check('ac2/generic-refused', 'the generic retire command on an item is refused [%s]' % code,
              code == 'entity_owned' and L.item(real) == before)
        code = generic(conn, 'upsert_entity', 'note:free', 'note', {'text': 'x'})
        check('ac2/generic-refused', 'control: the generic command still writes a kind nobody owns [%s]' % code,
              code == 'written')
        owners = {(row[0], row[1]): row for row in S.entity_owners(conn)}
        check('ac2/generic-refused', 'the four kinds and their prefixes are declared to the ledger\'s module',
              all(owners.get(('kind', kind), (0, 0, None))[2] == 'space_ledger'
                  for kind in ('space_item', 'space_pool', 'space_hold', 'space_reconcile'))
              and all(('prefix', prefix) in owners for prefix in
                      ('space:item:', 'space:pool:', 'space:hold:', 'space:reconcile:')))

        second = opened('store')
        for label, entity, kind, data in ATTEMPTS[:1] + ATTEMPTS[3:5]:
            code = generic(second, 'upsert_entity', entity, kind, data)
            check('ac2/every-connection', 'a connection nobody attached to refuses %s too [%s]' % (label, code),
                  code == 'entity_owned' and not exists(second, entity))

        third = opened('store')
        third.command_registry['space_confirm'] = {
            'transaction_transition': lambda c, params, before: {
                params['item']: {'kind': 'space_item', 'data': dict(before[params['item']]['data'], state='removed')}},
            'writes': ('entities', 'journal', 'commands', 'nonces')}
        try:
            S.execute(third, {'command_id': 'foreign-1', 'principal': 'authority', 'operation': 'space_confirm',
                              'parameters': {'item': real}, 'expected_versions': {real: version},
                              'artifact_digests': [], 'nonce': 'foreign-n1'}, 'authority', sign, 1)
            code = 'written'
        except S.StoreRefused as refusal:
            code = refusal.code
        check('ac2/foreign-code', 'the ledger\'s command name registered from other code is refused [%s]' % code,
              code == 'foreign_transition' and L.item(real) == before)

        # ---- AC3: the refusals of declare -----------------------------------------------------------
        place = str(temp / 'scratch' / 'one-place')
        first = L.declare('scratch', {'path': place}, owner(), 'seam')
        length = journal_length()
        twice = L.declare('scratch', {'path': place}, owner(), 'seam')
        check('ac3/second-live-item', 'a second declare at the same locator is refused by name [%s]' % twice.get('reason'),
              first['ok'] and twice['ok'] is False and twice.get('reason') == 'space_locator_taken:' + first['item'])
        check('ac3/second-live-item', 'and nothing was written', journal_length() == length
              and len([1 for value in L.items().values() if value['locator'] == {'path': place}]) == 1)
        other_kind = L.declare('build_output', {'path': place}, owner(), 'census')
        check('ac3/second-live-item', 'whatever kind the second one names [%s]' % other_kind.get('reason'),
              other_kind['ok'] is False and str(other_kind.get('reason')).startswith('space_locator_taken:'))
        L.confirm(first['item'])
        check('ac3/second-live-item', 'and while the first is present [%s]' % state_of(first['item']),
              L.declare('scratch', {'path': place}, owner(), 'seam').get('reason') == 'space_locator_taken:' + first['item'])
        name = {'engine': 'default', 'name': 'gate-db-1'}
        box = L.declare('container', name, owner(), 'seam', pool='host')
        again = L.declare('container', dict(name, id='abc123'), owner(), 'seam', pool='host')
        check('ac3/second-live-item', 'a Docker object is one locator by engine and name [%s]' % again.get('reason'),
              box['ok'] and again['ok'] is False and again.get('reason') == 'space_locator_taken:' + box['item'])
        elsewhere = L.declare('container', {'engine': 'desktop-linux', 'name': 'gate-db-1'}, owner(), 'seam')
        check('ac3/second-live-item', 'the same name on the other engine is another thing, in that engine\'s pool [%s]'
              % elsewhere.get('pool'), elsewhere['ok'] and elsewhere.get('pool') == 'desktop')

        base = str(temp / 'scratch' / 'spelled')
        first = L.declare('scratch', {'path': base}, owner(), 'seam')
        for label, spelling in (('a trailing separator', base + '/'),
                                ('a doubled separator', base.replace('/spelled', '//spelled')),
                                ('a dot segment', base.replace('/spelled', '/./spelled'))):
            step = L.declare('scratch', {'path': spelling}, owner(), 'seam')
            check('ac3/trailing-separator', 'a second declare through the path with %s is refused [%s]'
                  % (label, step.get('reason') or 'accepted as ' + str(step.get('item'))), first['ok']
                  and step['ok'] is False and step.get('reason') == 'space_locator_taken:' + first['item'])
        check('ac3/trailing-separator', 'one item holds that path',
              len([1 for value in L.items().values() if value['locator'].get('path', '').rstrip('/') == base]) == 1)
        spelled = L.declare('scratch', {'path': str(temp / 'scratch' / 'slashed') + '/'}, owner(), 'seam')
        check('ac3/trailing-separator', 'a first declare written with a trailing separator records the plain path',
              spelled['ok'] and L.item(spelled['item'])['locator'] == {'path': str(temp / 'scratch' / 'slashed')})

        OUTSIDE = (
            ('a folder outside every root', 'scratch', {'path': str(temp / 'elsewhere' / 'folder')}),
            ('the temporary folder itself', 'scratch', {'path': '/tmp/v297-not-a-root'}),
            ('a root itself', 'scratch', {'path': str(temp / 'build')}),
            ('a folder whose name only begins like a root', 'scratch', {'path': str(temp / 'scratch-other' / 'x')}),
            ('the project repository itself', 'worktree', {'path': str(REPOSITORY / 'sub')}),
            ('a branch of a repository nobody declared', 'branch',
             {'repository': str(temp / 'projects' / 'stranger'), 'ref': 'main'}),
            ('a Docker object on an engine the installation does not name', 'volume',
             {'engine': 'colima', 'name': 'cache'}),
        )
        for label, kind, locator in OUTSIDE:
            length = journal_length()
            step = L.declare(kind, locator, owner(), 'seam', pool='host')
            check('ac3/outside-roots', '%s is refused by name [%s]' % (label, step.get('reason') or 'accepted'),
                  step['ok'] is False and step.get('reason') == 'space_outside_roots' and journal_length() == length)
        INSIDE = (
            ('the project\'s worktree root', 'worktree', {'path': str(WORKTREES / 'inside')}),
            ('the plain repository\'s worktree root', 'worktree', {'path': str(temp / 'projects' / 'plain-worktrees' / 'w')}),
            ('the state root', 'scratch', {'path': str(STATE / 'runs' / 'r1')}),
            ('a scratch root', 'scratch', {'path': str(temp / 'scratch' / 'inside')}),
            ('a build root', 'build_output', {'path': str(temp / 'build' / 'inside')}),
            ('a branch of the bound repository', 'branch', {'repository': str(REPOSITORY), 'ref': 'agent/a/VELDO-9010'}),
            ('a branch of the plain repository', 'branch', {'repository': str(temp / 'projects' / 'plain'), 'ref': 'topic'}),
        )
        for label, kind, locator in INSIDE:
            step = L.declare(kind, locator, owner(), 'seam')
            check('ac3/outside-roots', 'control: a locator under %s is accepted [%s]' % (label, step.get('reason')),
                  step['ok'])

        GUARDED = (
            ('a protected folder itself', 'scratch', {'path': PROTECTED}, 'path:' + PROTECTED),
            ('a folder beneath a protected one', 'scratch', {'path': PROTECTED + '/disk/part'}, 'path:' + PROTECTED),
            ('a folder above a protected one', 'scratch', {'path': str(STATE / 'vms')}, 'path:' + PROTECTED),
            ('a protected volume on the first engine', 'volume', {'engine': 'default', 'name': 'atlas_pg_14'},
             'volume:atlas_pg_*'),
            ('a protected volume on the second engine', 'volume', {'engine': 'desktop-linux', 'name': 'atlas_pg_14'},
             'volume:atlas_pg_*'),
            ('a protected container', 'container', {'engine': 'default', 'name': 'atlas-web'}, 'container:atlas-*'),
            ('a protected network', 'network', {'engine': 'default', 'name': 'atlas_net'}, 'network:atlas_*'),
            ('a protected image name', 'image_tag', {'engine': 'default', 'name': 'store/objects'}, 'image:store/objects'),
            ('an object of a protected compose project', 'container',
             {'engine': 'default', 'name': 'db-1', 'compose_project': 'ledgerdb'}, 'compose_project:ledgerdb'),
            ('a volume the project\'s own file protects', 'volume', {'engine': 'default', 'name': 'orchard_db_main'},
             'volume:orchard_db_*'),
        )
        for label, kind, locator, entry in GUARDED:
            length = journal_length()
            step = L.declare(kind, locator, owner(), 'seam', pool='host')
            check('ac3/protect-list', '%s is refused by the entry\'s name [%s]' % (label, step.get('reason') or 'accepted'),
                  step['ok'] is False and step.get('reason') == 'space_protected:' + entry and journal_length() == length)
        step = L.adopt('volume', {'engine': 'default', 'name': 'atlas_pg_15'}, owner(), 'run_label', pool='host')
        check('ac3/protect-list', 'adopt refuses a protected thing too [%s]' % step.get('reason'),
              step['ok'] is False and step.get('reason') == 'space_protected:volume:atlas_pg_*')
        step = L.report('volume', {'engine': 'default', 'name': 'atlas_pg_16'}, {'what': 'volume'}, pool='host')
        check('ac3/protect-list', 'and a protected thing gets no report record [%s]' % step.get('reason'),
              step['ok'] is False and step.get('reason') == 'space_protected:volume:atlas_pg_*')
        check('ac3/protect-list', 'no item names a protected thing',
              not [1 for value in L.items().values()
                   if str(value['locator'].get('name', '')).startswith(('atlas', 'orchard_db'))
                   or str(value['locator'].get('path', '')).startswith(str(STATE / 'vms'))])
        step = L.declare('volume', {'engine': 'default', 'name': 'gate_pg_1'}, owner(), 'seam', pool='host')
        check('ac3/protect-list', 'control: a volume no entry matches is accepted [%s]' % step.get('reason'), step['ok'])
        step = L.declare('container', {'engine': 'default', 'name': 'runner-1'}, owner(), 'seam')
        check('ac3/protect-list', 'a Docker object on an engine with no image pool needs its pool named [%s]'
              % step.get('reason'), step['ok'] is False and step.get('reason') == 'space_no_pool')

        for ending in ('removed', 'gone'):
            identity, run = made(ending)
            locator = L.item(identity)['locator']
            step = L.declare('scratch', locator, owner(), 'seam')
            check('ac3/free-after-end', 'the locator of a %s item can be declared again [%s]' % (ending, step.get('reason')),
                  step['ok'] and step.get('item') != identity and state_of(identity) == ending)

        metrics = L.metrics()
        refused = metrics['refused_declares']
        check('ac3/refusals-counted', 'refused declares are counted by reason %s' % sorted(refused),
              refused.get('space_locator_taken', 0) >= 6 and refused.get('space_outside_roots') == len(OUTSIDE)
              and refused.get('space_protected') == len(GUARDED) + 1)
        check('ac3/refusals-counted', 'items are counted by kind and state',
              metrics['items'].get('scratch', {}).get('removed', 0) >= 1
              and sum(sum(states.values()) for states in metrics['items'].values()) == len(L.items()))
        unknown = L.declare('cache', scratch(), owner(), 'seam')
        nobody = L.declare('worktree', {'path': str(WORKTREES / 'nobody')}, {'scope': {'type': 'no_project'}}, 'seam')
        session = L.declare('scratch', scratch(), {'scope': {'type': 'no_project'}, 'session': 's-1'}, 'hook')
        check('ac3/refusals-counted', 'an unknown kind, and no project for anything but session scratch, are refused [%s, %s, %s]'
              % (unknown.get('reason'), nobody.get('reason'), session.get('reason')),
              unknown.get('reason') == 'invalid_input:kind' and nobody.get('reason') == 'invalid_input:owner.scope'
              and session['ok'])

        # ---- AC3: a .. segment is refused, never collapsed as text (review finding 1) ------------------
        def at(path):
            return [key for key, value in L.items().items()
                    if value['state'] in SP.LIVE and (value['locator'].get('path') == str(path)
                                                      or value['locator'].get('repository') == str(path))]

        (temp / 'scratch' / 'link').symlink_to(temp / 'elsewhere' / 'deep')
        CLIMBS = (
            ('a path that climbs out of a root', 'scratch', {'path': str(temp / 'scratch') + '/../out/x'}),
            ('a path that climbs and stays in its root', 'scratch', {'path': str(temp / 'scratch') + '/a/../b'}),
            ('a path that climbs back from a link', 'scratch', {'path': str(temp / 'scratch') + '/link/../victim'}),
            ('a path that ends in ..', 'scratch', {'path': str(temp / 'scratch') + '/a/b/..'}),
            ('a branch whose repository climbs', 'branch',
             {'repository': str(temp / 'projects') + '/x/../orchard', 'ref': 'topic-climb'}),
        )
        for label, kind, locator in CLIMBS:
            length = journal_length()
            step = L.declare(kind, locator, owner(), 'seam')
            check('ac3/parent-segment', '%s is refused by name [%s]' % (label, step.get('reason') or 'accepted'),
                  step['ok'] is False and step.get('reason') == 'space_locator_parent' and journal_length() == length)
        check('ac3/parent-segment', 'no item is recorded at the folder the text would collapse to %s'
              % at(temp / 'scratch' / 'victim'), at(temp / 'scratch' / 'victim') == [] and at(temp / 'scratch' / 'b') == [])
        step = L.adopt('scratch', {'path': str(temp / 'scratch') + '/link/../victim'}, owner(), 'run_label')
        again = L.report('scratch', {'path': str(temp / 'scratch') + '/link/../victim'}, {'what': 'folder'})
        check('ac3/parent-segment', 'adopt and report refuse it too [%s, %s]' % (step.get('reason'), again.get('reason')),
              step.get('reason') == 'space_locator_parent' and again.get('reason') == 'space_locator_parent')
        step = L.declare('scratch', {'path': str(temp / 'scratch' / 'dots..in..a..name')}, owner(), 'seam')
        check('ac3/parent-segment', 'control: a name that only contains dots is accepted [%s]' % step.get('reason'),
              step['ok'])

        # ---- AC3: a link does not get a protected or foreign thing a record (review finding 2) --------
        def refused(row, label, kind, path, reason, send='declare'):
            length = journal_length()
            if send == 'declare':
                step = L.declare(kind, {'path': str(path)}, owner(), 'seam')
            elif send == 'adopt':
                step = L.adopt(kind, {'path': str(path)}, owner(), 'run_label')
            else:
                step = L.report(kind, {'path': str(path)}, {'what': 'folder'})
            check(row, '%s is refused by name [%s]' % (label, step.get('reason') or 'accepted as ' + str(step.get('item'))),
                  step['ok'] is False and step.get('reason') == reason and journal_length() == length
                  and at(path) == [])

        alias = temp / 'scratch' / 'alias'
        alias.symlink_to(PROTECTED)
        guarded = 'space_protected:path:' + PROTECTED
        refused('ac3/link-to-protected', 'a link to a protected path, declared as scratch', 'scratch', alias, guarded)
        refused('ac3/link-to-protected', 'the same link adopted', 'scratch', alias, guarded, 'adopt')
        refused('ac3/link-to-protected', 'the same link reported', 'scratch', alias, guarded, 'report')
        (temp / 'scratch' / 'above').symlink_to(STATE / 'vms')
        refused('ac3/link-to-protected', 'a link to a folder above a protected path', 'scratch',
                temp / 'scratch' / 'above', guarded)

        refused('ac3/link-beneath-protected', 'a path beneath a link to a protected path', 'scratch',
                alias / 'sub', guarded)
        refused('ac3/link-beneath-protected', 'a deeper path beneath it, not there yet', 'build_output',
                alias / 'disk' / 'part' / 'x', guarded)
        refused('ac3/link-beneath-protected', 'the same path reported', 'scratch', alias / 'sub', guarded, 'report')

        entry = 'space_protected:path:' + str(VAULT_LINK)
        refused('ac3/link-protect-entry', 'the folder a protected link leads to', 'scratch', VAULT, entry)
        refused('ac3/link-protect-entry', 'a path beneath that folder', 'scratch', VAULT / 'inner', entry)
        refused('ac3/link-protect-entry', 'the protected link itself', 'scratch', VAULT_LINK, entry)

        (temp / 'scratch' / 'out').symlink_to(temp / 'elsewhere')
        refused('ac3/link-out-of-roots', 'a link out of every known root', 'scratch', temp / 'scratch' / 'out',
                'space_outside_roots')
        refused('ac3/link-out-of-roots', 'a path beneath a link out of every known root', 'scratch',
                temp / 'scratch' / 'out' / 'x', 'space_outside_roots')
        refused('ac3/link-out-of-roots', 'the same path adopted', 'scratch', temp / 'scratch' / 'out' / 'x',
                'space_outside_roots', 'adopt')
        (WORKTREES / 'far').parent.mkdir(parents=True, exist_ok=True)
        (WORKTREES / 'far').symlink_to('/')
        refused('ac3/link-out-of-roots', 'a worktree path through a link to the top folder', 'worktree',
                WORKTREES / 'far' / 'usr', 'space_outside_roots')
        (temp / 'projects' / 'stranger').mkdir()
        (temp / 'projects' / 'plain').symlink_to(temp / 'projects' / 'stranger')
        length = journal_length()
        step = L.declare('branch', {'repository': str(temp / 'projects' / 'plain'), 'ref': 'through-link'}, owner(), 'seam')
        check('ac3/link-out-of-roots', 'a branch of a declared repository that is now a link elsewhere is refused [%s]'
              % (step.get('reason') or 'accepted'), step['ok'] is False
              and step.get('reason') in ('space_outside_roots', 'space_locator_link') and journal_length() == length)

        real = temp / 'scratch' / 'real'
        real.mkdir()
        (temp / 'scratch' / 'twin-a').symlink_to(real)
        (temp / 'scratch' / 'twin-b').symlink_to('real')
        (temp / 'scratch' / 'hop').symlink_to(temp / 'scratch')
        refused('ac3/two-links-one-folder', 'the first link to a folder', 'scratch', temp / 'scratch' / 'twin-a',
                'space_locator_link')
        refused('ac3/two-links-one-folder', 'the second link to the same folder', 'scratch', temp / 'scratch' / 'twin-b',
                'space_locator_link')
        first = L.declare('scratch', {'path': str(real)}, owner(), 'seam')
        check('ac3/two-links-one-folder', 'the folder itself, by its own path, is declared [%s]' % first.get('reason'),
              first['ok'] and L.item(first['item'])['locator'] == {'path': str(real)})
        refused('ac3/two-links-one-folder', 'a link to the folder once it has an item', 'scratch',
                temp / 'scratch' / 'twin-a', 'space_locator_link')
        refused('ac3/two-links-one-folder', 'the folder through a link in the middle of the path', 'scratch',
                temp / 'scratch' / 'hop' / 'real', 'space_locator_link')
        refused('ac3/two-links-one-folder', 'a link to the folder, adopted', 'scratch', temp / 'scratch' / 'twin-b',
                'space_locator_link', 'adopt')
        refused('ac3/two-links-one-folder', 'a path beneath a link, not there yet', 'scratch',
                temp / 'scratch' / 'twin-a' / 'new', 'space_locator_link')
        live = [key for key, value in L.items().items() if value['state'] in SP.LIVE
                and 'path' in value['locator'] and SP.resolved_path(value['locator']['path']) == str(real)]
        check('ac3/two-links-one-folder', 'one live item resolves to that folder %s' % live,
              first['ok'] and live == [first['item']])
        every = [value['locator']['path'] for value in L.items().values() if 'path' in value['locator']]
        check('ac3/two-links-one-folder', 'every recorded path of a disk item is the path it resolves to',
              every and all(SP.resolved_path(path) == path for path in every))
        step = L.declare('scratch', {'path': str(real / 'inner' / 'new')}, owner(), 'seam')
        check('ac3/two-links-one-folder', 'control: a path with no link in it, not there yet, is accepted [%s]'
              % step.get('reason'), step['ok'])
        counted = L.metrics()['refused_declares']
        check('ac3/refusals-counted', 'the .. and link refusals are counted by their names %s' % sorted(counted),
              counted.get('space_locator_parent') == len(CLIMBS) + 1 and counted.get('space_locator_link') >= 6)

        on_host = L.item(L.declare('scratch', scratch(), owner(), 'seam')['item'])['pool']
        on_tree = L.item(L.declare('worktree', {'path': str(WORKTREES / 'device-tree')}, owner(), 'seam')['item'])['pool']
        on_build = L.item(L.declare('build_output', {'path': str(temp / 'build' / 'device-tree')}, owner(), 'seam')['item'])['pool']
        check('ac3/pool-by-device', 'two paths on one filesystem are one pool, a path on another is another [%s %s %s]'
              % (on_host, on_tree, on_build), on_host == on_tree == 'host' and on_build == 'second')
        step = L.set_pool('second', 'filesystem', device='dev-host')
        check('ac3/pool-by-device', 'a second pool on a recorded device is refused [%s]' % step.get('reason'),
              step['ok'] is False and step.get('reason') == 'space_pool_device_taken')
        step = L.set_pool('attic', 'filesystem', device='dev-attic')
        check('ac3/pool-by-device', 'a pool the installation does not name is refused [%s]' % step.get('reason'),
              step['ok'] is False and step.get('reason') == 'space_unknown_pool:attic')
        pool = L.pool('desktop') or {}
        check('ac3/pool-by-device', 'an engine image pool has its engine, its backing pool, the floor and returns no space',
              pool.get('type') == 'engine_image' and pool.get('engine') == 'desktop-linux' and pool.get('backing') == 'host'
              and pool.get('floor') == 8000 * MEGABYTE and pool.get('returns_space') is False
              and (L.pool('host') or {}).get('returns_space') is True and (L.pool('host') or {}).get('device') == 'dev-host')

        # ---- holds and reconcile records, written before the rebuild ---------------------------------
        hold = L.place_hold('VELDO-9001:build:1', {'host': 4000 * MEGABYTE}, {'host': 'declared'})
        reason = {'pool': 'host', 'need': 4000 * MEGABYTE, 'free': 21000 * MEGABYTE, 'held': 0, 'floor': 20000 * MEGABYTE}
        waits = L.admit('VELDO-9001:build:1', 'waiting', reason, retry_asked=True)
        admitted = L.admit('VELDO-9001:build:1', 'admitted')
        late = L.admit('VELDO-9001:build:1', 'admitted')
        L.place_hold('gate:run-7', {'host': 6000 * MEGABYTE, 'desktop': 3000 * MEGABYTE},
                     {'host': 'default', 'desktop': 'measured'})
        advised = L.admit('gate:run-7', 'advised', dict(reason, need=6000 * MEGABYTE))
        released = L.release('gate:run-7', used={'host': 12 * MEGABYTE})
        again = L.release('gate:run-7')
        dup = L.place_hold('gate:run-7', {'host': 1}, {'host': 'default'})
        stray = L.place_hold('gate:run-8', {'attic': 1}, {'attic': 'default'})
        reconciled = L.reconcile('service_start', [str(WORKTREES), str(temp / 'scratch')], list(ENGINES),
                                 {'matched': 4, 'adopted': 1, 'reported': 1, 'gone': 0, 'completed': 0})
        holds_ok = (hold['ok'] and waits['ok'] and waits.get('state') == 'waiting' and admitted.get('state') == 'admitted'
                    and late.get('reason') == 'space_hold_state:admitted' and advised.get('state') == 'advised'
                    and released.get('state') == 'released' and again.get('reason') == 'space_hold_state:released'
                    and dup.get('reason') == 'space_hold_exists' and stray.get('reason') == 'invalid_input:needs')
        sized, run = made('present')
        L.measure(sized, 123456789, 'run_finished')

        # ---- AC4: the store rebuilt from its journal --------------------------------------------------
        live = S.materialized_state(conn)
        rebuilt = R.replay(S.export_journal(conn), verify)
        compared = R.compare_with_live(rebuilt, live)

        def of_kind(state, kind):
            return {key: value for key, value in state['entities'].items() if value['kind'] == kind}

        for kind in ('space_item', 'space_pool', 'space_hold', 'space_reconcile'):
            ours, theirs = of_kind(live, kind), of_kind(rebuilt['state'], kind)
            check('ac4/rebuilt-same', 'the rebuilt store holds the same %s records (%d live, %d rebuilt)'
                  % (kind, len(ours), len(theirs)), ours and ours == theirs)
        check('ac4/rebuilt-same', 'and the same state digest %s' % compared.get('differences'),
              compared.get('matches') is True)
        check('ac4/rebuilt-same', 'items in every one of the eight states were rebuilt',
              {value['data']['state'] for value in of_kind(rebuilt['state'], 'space_item').values()} == set(SP.STATES))
        extra = sorted(row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                       if row[0] not in S.DOMAIN_TABLES + (S.OWNERS_TABLE,))
        check('ac4/rebuilt-same', 'the ledger keeps no table of its own beside the store\'s %s' % extra, extra == [])

        size = (rebuilt['state']['entities'].get(sized) or {}).get('data', {}).get('size')
        check('ac4/rebuilt-size', 'the rebuilt store\'s item has the size that was measured [%s]' % size,
              size == {'bytes': 123456789, 'event': 'run_finished'})
        check('ac4/rebuilt-size', 'as the live item has', L.item(sized)['size'] == {'bytes': 123456789, 'event': 'run_finished'})

        check('ac4/rebuilt-pools-holds', 'the hold commands wrote and refused as 4.3 says', holds_ok)
        held = (rebuilt['state']['entities'].get('space:hold:VELDO-9001:build:1') or {}).get('data', {})
        check('ac4/rebuilt-pools-holds', 'the rebuilt admitted hold has its needs, source and retry mark %s' % held,
              held.get('state') == 'admitted' and held.get('needs') == {'host': 4000 * MEGABYTE}
              and held.get('source') == {'host': 'declared'} and held.get('retry_asked') is True and held.get('reason') is None)
        held = (rebuilt['state']['entities'].get('space:hold:gate:run-7') or {}).get('data', {})
        check('ac4/rebuilt-pools-holds', 'the rebuilt released hold has what it used',
              held.get('state') == 'released' and held.get('used') == {'host': 12 * MEGABYTE})
        pool = (rebuilt['state']['entities'].get('space:pool:fixture-host:host') or {}).get('data', {})
        check('ac4/rebuilt-pools-holds', 'the rebuilt pool has its device and floor %s' % pool,
              pool.get('device') == 'dev-host' and pool.get('floor') == 20000 * MEGABYTE)
        record = (rebuilt['state']['entities'].get(reconciled.get('reconcile')) or {}).get('data', {})
        check('ac4/rebuilt-pools-holds', 'the rebuilt reconcile record has what started it and the counts',
              reconciled['ok'] and record.get('started_by') == 'service_start' and record.get('counts', {}).get('matched') == 4
              and record.get('engines') == ENGINES)

        # ---- the canon ----------------------------------------------------------------------------
        canon = ROOT / 'engine' / '.veldo' / 'control_space.py'
        check('ledger/canon', 'the engine canon equals this repository copy',
              canon.is_file() and canon.read_bytes() == (ROOT / '.veldo' / 'control_space.py').read_bytes())
        off = None
        try:
            SP.Ledger(S, opened('off'), 'authority', sign, config=CFG.off(), state_root=str(STATE),
                      lifecycle=LIFECYCLE, host='fixture-host')
        except SP.Refused as refusal:
            off = refusal.code
        check('ledger/canon', 'an installation with no space section has no ledger [%s]' % off,
              off == 'space_not_configured')
    except Exception as error:
        import traceback
        check('ac1/declare-to-removed', 'raised ' + type(error).__name__ + ': ' + str(error)[:300]
              + ' ' + traceback.format_exc().splitlines()[-3][:200], False)
    finally:
        for connection in connections:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - closing a fixture connection never reds a row
                pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0297 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v297_space_ledger_suite()
