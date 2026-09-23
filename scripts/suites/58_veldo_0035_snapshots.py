"""VELDO-0035: real stored snapshots, complete registered inputs, independent readers.

Only ROOT and expect come from shared.py. Temporary sibling copies are also the mutation
harness's production seam. Fixtures provision minimal accepted records for future journey
consumers; no eligibility, PM or landing behavior is implemented here.
"""
import importlib.util as _s35_ilu
import json as _s35_json
from pathlib import Path as _s35_Path
import shutil as _s35_shutil
import subprocess as _s35_sp
import sys as _s35_sys
import tempfile as _s35_temp
import time as _s35_time


def _s35_load(name, path):
    spec = _s35_ilu.spec_from_file_location(name, path)
    mod = _s35_ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _s35_run():
    started = _s35_time.monotonic()
    observations = {'stale': [], 'artifacts': [], 'projections': []}
    with _s35_temp.TemporaryDirectory(prefix='snapshots-35-') as temporary:
        root = _s35_Path(temporary)
        modules = root / 'modules'
        modules.mkdir()
        # Literal anchors are required by the registered mutation driver.
        for name, source in {
            'control_snapshot.py': ROOT / ".veldo" / "control_snapshot.py",
            'control_readset.py': ROOT / ".veldo" / "control_readset.py",
            'control_store.py': ROOT / ".veldo" / "control_store.py",
            'git_process.py': ROOT / '.veldo/git_process.py',
        }.items():
            _s35_shutil.copyfile(source, modules / name)
        sn = _s35_load('s35_snapshot', modules / 'control_snapshot.py')
        rs = _s35_load('s35_readset', modules / 'control_readset.py')
        st = _s35_load('s35_store', modules / 'control_store.py')
        git = sn._git_process
        repo = root / 'repository'
        repo.mkdir()

        def g(*args):
            return git.check_output(['git', '-C', str(repo), *args],
                                    identity=('Snapshot fixture', 'snapshot@example.test'), stderr=_s35_sp.PIPE).decode().strip()

        g('init', '-q')
        documents = {name + '.md': ('accepted ' + name + '\n').encode() for name in
                     ('specification', 'plan', 'release', 'decision', 'floor', 'policy', 'graph',
                      'roster', 'admission', 'receipt')}
        for path, body in documents.items():
            (repo / path).write_bytes(body)
        (repo / 'status.json').write_text('{"status":"unaccepted"}')
        g('add', '.')
        g('commit', '-qm', 'Accepted fixture revision')
        commit = g('rev-parse', 'HEAD')
        key = root / 'journal-key'
        _s35_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                    check=True, capture_output=True, timeout=10)

        def sign(body):
            proc = _s35_sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', 'veldo-snapshot'],
                             input=body, capture_output=True, timeout=10, check=True)
            return proc.stdout.decode()

        signing = dict(signer='snapshot-service', sign=sign, authority_generation=1)
        seed = st.open_store(root / 'seed.sqlite3')
        serial = 0

        def command(operation, parameters, versions):
            nonlocal serial
            serial += 1
            return {'command_id': 'command-' + str(serial), 'principal': 'owner', 'operation': operation,
                    'parameters': parameters, 'expected_versions': versions, 'artifact_digests': [],
                    'nonce': 'nonce-' + str(serial)}

        def put(store, conn, identity, kind, data):
            prior = conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            return store.execute(conn, command('upsert_entity', {'entity_id': identity, 'kind': kind, 'data': data},
                                               {identity: prior[0] if prior else 0}), **signing)

        put(st, seed, 'project', 'project', {'name': 'journey'})
        put(st, seed, 'authority:versions', 'authority_versions', {'membership_version': 1, 'delegation_version': 1})
        put(st, seed, 'owner', 'membership', {'project': 'project', 'roles': ['project_owner']})
        put(st, seed, 'delegation', 'delegation', {'project': 'project', 'principal': 'owner'})
        put(st, seed, 'key', 'verification_key', {'project': 'project', 'principal': 'owner', 'public_key': key.with_suffix('.pub').read_text()})
        put(st, seed, 'unit', 'unit', {'status': 'ready'})
        put(st, seed, 'dependency', 'unit', {'status': 'complete'})
        put(st, seed, 'edge', 'dependency', {'project': 'project', 'target': 'dependency'})
        put(st, seed, 'target', 'unit', {'status': 'ready'})
        put(st, seed, 'revision', 'accepted_revision', {'domain_uuid': 'domain', 'repository_uuid': 'repository',
            'commit': commit, 'documents': {p: sn.digest(b) for p, b in documents.items()},
            'statuses': {'status.json': 'unit'}})
        declaration = {'revision': 'revision',
            'entities': {'project': '$project_id', 'authority': 'authority:versions',
                         'target': '$target_id', 'optional': 'not-yet-present'},
            'collections': {label: {'kind': kind, 'where': {'project': '$project_id'}, 'references': refs}
                            for label, kind, refs in [('dependencies', 'dependency', ['target']),
                                ('blockers', 'blocker', []), ('membership', 'membership', []),
                                ('delegations', 'delegation', []), ('keys', 'verification_key', [])]}}
        operations = {
            'upsert_entity': {'entity_id': 'target', 'kind': 'unit', 'data': {'status': 'built'}},
            'retire_entity': {'entity_id': 'target'},
            'record_receipt': {'receipt_id': 'new-receipt', 'subject': 'target', 'digest': sn.digest(b'receipt')},
            'reserve': {'reservation_id': 'reservation', 'ceiling': 'unit', 'delta': 1},
            'record_effect': {'effect_id': 'effect', 'kind': 'test', 'target': 'target'},
        }
        expect('snapshots/registration-inventory', set(operations) == set(st.COMMAND_REGISTRY))
        scaffold = _s35_load('s35_scaffold', ROOT / '.veldo/init_scaffold.py')
        expect('snapshots/installed-assets', all('.veldo/' + name in scaffold._FILES for name in
               ('control_snapshot.py', 'control_readset.py', 'control_store.py', 'git_process.py')))
        case_number = 0

        def fixture(operation):
            nonlocal case_number
            case_number += 1
            store = _s35_load('s35_store_' + str(case_number), modules / 'control_store.py')
            conn = store.open_store(root / ('case-' + str(case_number) + '.sqlite3'))
            seed.backup(conn)
            reader = rs.attach(store, conn, repo, 'domain', 'repository')
            reader.enable(operation, declaration)
            args = dict(operations[operation], project_id='project', target_id='target')
            result = reader.execute(command('accept_snapshot', {'snapshot_id': 'snapshot', 'operation': operation,
                                    'arguments': args}, {'snapshot': 0}), **signing)
            snapshot = sn.load(store, conn, 'snapshot', 'domain', 'repository')
            versions = {'snapshot': 1}
            if operation in ('upsert_entity', 'retire_entity'):
                versions['target'] = 1
            if operation == 'record_receipt':
                versions['new-receipt'] = 0
            consume = command(operation, dict(args, snapshot_id='snapshot'), versions)
            return store, conn, reader, snapshot, consume, result

        changes = {
            'dependency': ('dependency', 'unit', {'status': 'reopened'}),
            'authority': ('authority:versions', 'authority_versions', {'membership_version': 2, 'delegation_version': 1}),
            'edge': ('edge-2', 'dependency', {'project': 'project', 'target': 'unit'}),
            'blocker': ('block', 'blocker', {'project': 'project'}),
            'absence': ('not-yet-present', 'unit', {'status': 'ready'}),
            'membership': ('owner', 'membership', {'project': 'project', 'roles': []}),
            'delegation': ('delegation', 'delegation', {'project': 'project', 'revoked': True}),
            'key': ('key', 'verification_key', {'project': 'project', 'retired': True}),
            'status': ('unit', 'unit', {'status': 'blocked'}),
        }
        for operation in operations:
            for change, values in changes.items():
                store, conn, reader, snapshot, consume, accepted = fixture(operation)
                # Another actual writer uses the base store on this same accepted database.
                writer = st.open_store(root / ('case-' + str(case_number) + '.sqlite3'))
                put(st, writer, *values)
                writer.close()
                before = store.materialized_state(conn)
                before_seq = conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0]
                refusal = None
                try:
                    reader.execute(consume, **signing)
                except store.StoreRefused as error:
                    refusal = error.code
                okay = (refusal == 'stale_input' and store.materialized_state(conn) == before
                        and conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0] == before_seq)
                observations['stale'].append({'operation': operation, 'change': change, 'refusal': refusal, 'passed': okay})
                conn.close()
            store, conn, reader, snapshot, consume, accepted = fixture(operation)
            result = reader.execute(consume, **signing)
            expect('snapshots/control/' + operation, result['committed'] and reader.counts == {'accepted': 2, 'refused': 0}
                   and reader.pending() == [] and snapshot['watermark'] == accepted['seq']
                   and reader.observations[-1]['accepted_inputs']['entity/authority']['versions'] == {'authority:versions': 1}
                   and set(reader.observations[-1]['accepted_inputs']) == set(snapshot['inputs']))
            conn.close()
        expect('snapshots/stale-input', all(row['passed'] for row in observations['stale']) and len(observations['stale']) == 45)

        store, conn, reader, snapshot, consume, accepted = fixture('upsert_entity')
        before_seq = conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0]
        for label, invalid in [
            ('unregistered', command('reserve', operations['reserve'], {})),
            ('missing-snapshot', command('upsert_entity', operations['upsert_entity'], {'target': 1})),
        ]:
            refusal = None
            try:
                reader.execute(invalid, **signing)
            except store.StoreRefused as error:
                refusal = error.code
            expect('snapshots/refusal/' + label, refusal == {
                   'unregistered': 'unregistered_inputs', 'missing-snapshot': 'missing_snapshot'}[label]
                   and conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0] == before_seq)
        expect('snapshots/refusal-observations', reader.counts == {'accepted': 1, 'refused': 2}
               and reader.pending() == ['snapshot'] and reader.observations[-1]['outcome'] == 'refused'
               and reader.observations[-1]['refusal'] == 'missing_snapshot')
        # An ordinary signed journal entry was really written and its signature verifies.
        record = store.export_journal(conn)[-1]
        signature = root / 'record.sig'
        signature.write_text(record['signature'])
        allowed = root / 'allowed'
        allowed.write_text('snapshot-service ' + key.with_suffix('.pub').read_text())
        verified = _s35_sp.run(['ssh-keygen', '-Y', 'verify', '-f', str(allowed), '-I', 'snapshot-service',
                               '-n', 'veldo-snapshot', '-s', str(signature)], input=store.journal_signed_bytes(record),
                              capture_output=True, timeout=10)
        expect('snapshots/signed-watermark', verified.returncode == 0 and record['seq'] == snapshot['watermark']
               and record['transition']['snapshot']['data'] == snapshot)
        # Every registered document is read by exact accepted object, despite edits AND newer HEAD.
        for path in documents:
            (repo / path).write_text('edited checkout ' + path)
        g('add', '.')
        g('commit', '-qm', 'Unaccepted working revision')
        for path, body in documents.items():
            actual = sn.artifact(repo, snapshot['accepted_commit'], path, snapshot['documents'][path])
            observations['artifacts'].append({'path': path, 'accepted_digest': sn.digest(body),
                                               'observed_digest': sn.digest(actual), 'passed': actual == body})
            blob = g('rev-parse', commit + ':' + path)
            obj = repo / '.git/objects' / blob[:2] / blob[2:]
            saved = obj.read_bytes()
            obj.unlink()
            refused = None
            try:
                sn.artifact(repo, commit, path, snapshot['documents'][path])
            except sn.Refused as error:
                refused = error.code
            obj.parent.mkdir(exist_ok=True)
            obj.write_bytes(saved)
            expect('snapshots/missing-artifact/' + path, refused == 'missing_artifact')
        expect('snapshots/accepted-bytes', all(row['passed'] for row in observations['artifacts']))
        expect('snapshots/coordinates', snapshot['domain_uuid'] == 'domain' and snapshot['repository_uuid'] == 'repository'
               and snapshot['accepted_commit'] == commit and all('version' in item and 'digest' in item
                   for key, item in snapshot['inputs'].items() if key.startswith(('entity/', 'status/', 'reference/'))))
        # Materialize the old accepted status after a newer status has actually committed.
        writer = st.open_store(root / ('case-' + str(case_number) + '.sqlite3'))
        put(st, writer, 'unit', 'unit', {'status': 'changed-after-snapshot'})
        writer.close()
        destination = root / 'published'
        published = sn.materialize(snapshot, repo, destination)
        child = '''import importlib.util, json, sys
from pathlib import Path
def load(name):
 s=importlib.util.spec_from_file_location(name, Path(sys.argv[1])/(name+'.py'))
 m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
st=load('control_store'); sn=load('control_snapshot')
c=st.open_store(sys.argv[2], mode='r')
s=sn.load(st,c,'snapshot','domain','repository')
try:
 r=sn.read_materialized(s,sys.argv[3],sys.argv[4])
 print(json.dumps({'manifest':r['manifest'], 'digests':{p:sn.digest(b) for p,b in r['members'].items()}}))
except sn.Refused as e:
 print(json.dumps({'refusal':e.code}))
c.close()
'''
        def child_read():
            proc = _s35_sp.run([_s35_sys.executable, '-B', '-c', child, str(modules),
                               str(root / ('case-' + str(case_number) + '.sqlite3')), str(repo), str(destination)],
                              capture_output=True, text=True, timeout=20, check=True)
            return _s35_json.loads(proc.stdout)

        observed = child_read()
        # Independent expected digests from accepted store DATA, not materializer helpers.
        expected = dict(snapshot['documents'])
        expected.update({p: sn.digest(sn.canonical(snapshot['inputs']['status/' + p]['value'])) for p in snapshot['statuses']})
        observations['projections'] = [{'path': p, 'expected_digest': d,
            'observed_digest': observed.get('digests', {}).get(p)} for p, d in expected.items()]
        expect('snapshots/materialized-revision', observed.get('digests') == expected
               and observed.get('manifest', {}).get('watermark') == accepted['seq']
               and published['watermark'] == accepted['seq'])
        (destination / 'status.json').write_text('unaccepted replacement')
        expect('snapshots/tampered-projection', child_read().get('refusal') == 'projection_mismatch')
        (destination / 'manifest.json').unlink()
        expect('snapshots/incomplete-projection', child_read().get('refusal') == 'missing_projection')
        conn.close()
        # R1 capsule: the captured reader holds an old WAL view while another writer
        # commits a blocker and attempts the reservation through the SAME store module.
        store, conn, reader, snapshot, consume, accepted = fixture('reserve')
        conn.execute('BEGIN')
        conn.execute('SELECT COUNT(*) FROM entities').fetchone()
        writer = store.open_store(root / ('case-' + str(case_number) + '.sqlite3'))
        put(store, writer, 'stop', 'blocker', {'project': 'project'})
        before = store.materialized_state(writer)
        before_seq = writer.execute('SELECT MAX(seq) FROM journal').fetchone()[0]
        refusal = None
        try:
            store.execute(writer, consume, **signing)
        except store.StoreRefused as error:
            refusal = error.code
        expect('snapshots/connection-bound', refusal in ('unregistered_inputs', 'wrong_connection')
               and store.materialized_state(writer) == before
               and writer.execute('SELECT MAX(seq) FROM journal').fetchone()[0] == before_seq
               and writer.execute('SELECT COUNT(*) FROM reservations').fetchone()[0] == 0)
        conn.execute('ROLLBACK')
        refusal = None
        try:
            reader.execute(consume, **signing)
        except store.StoreRefused as error:
            refusal = error.code
        expect('snapshots/connection-bound-control', refusal == 'stale_input')
        writer.close()
        conn.close()

        store, conn, reader, snapshot, consume, accepted = fixture('reserve')
        # An ordinary BEGIN is not the store's BEGIN IMMEDIATE, even on the right handle.
        conn.execute('BEGIN')
        refusals = []
        guard = getattr(conn, 'command_registry', {}).get('reserve', {}).get('transaction_transition')
        if guard:
            for executing in (conn, writer):
                try:
                    guard(executing, consume['parameters'], {'snapshot': {'version': 1}})
                except store.StoreRefused as error:
                    refusals.append(error.code)
                else:
                    refusals.append(None)
        expect('snapshots/transaction-bound', refusals == ['missing_transaction', 'wrong_connection'])
        conn.execute('ROLLBACK')
        conn.close()

        # R4: one module, two domains, independent declarations, no wrapper stacking.
        store = _s35_load('s35_multi_domain', modules / 'control_store.py')
        registry = dict(store.COMMAND_REGISTRY)
        connections, readers, outcomes = [], [], []
        for index in range(2):
            connection = store.open_store(root / ('domain-' + str(index) + '.sqlite3'))
            seed.backup(connection)
            domain = 'domain-' + str(index)
            put(store, connection, 'revision', 'accepted_revision', dict(
                snapshot['inputs']['revision']['value']['data'], domain_uuid=domain))
            reader = rs.attach(store, connection, repo, domain, 'repository')
            reader.enable('reserve', dict(declaration, entities={'project': 'project'}))
            connections.append(connection)
            readers.append(reader)
        for connection, reader in zip(connections, readers):
            try:
                reader.execute(command('accept_snapshot', dict(snapshot_id='isolated', operation='reserve',
                    arguments={'project_id': 'project'}), {'isolated': 0}), **signing)
                result = store.execute(connection, command('reserve', dict(operations['reserve'],
                    project_id='project', snapshot_id='isolated'), {'isolated': 1}), **signing)
                outcomes.append(result['committed'])
            except (store.StoreRefused, rs.SN.Refused):
                outcomes.append(False)
        duplicate = None
        try:
            readers[0].enable('reserve', declaration)
        except rs.SN.Refused as error:
            duplicate = error.code
        expect('snapshots/scoped-registration', outcomes == [True, True]
               and store.COMMAND_REGISTRY == registry and duplicate == 'invalid_registration')
        for connection in connections:
            connection.close()
        # R2 capsule and prefix variants: acceptance must roll back the whole command.
        prefix_outcomes = []
        inventories = [
            ({'policy.md': sn.digest(documents['policy.md'])}, {'policy.md/status.json': 'unit'}),
            ({'policy.md': sn.digest(documents['policy.md'])}, {'policy.md/deep/status.json': 'unit'}),
            ({}, {'status.json': 'unit', 'status.json/child': 'unit'}),
            ({}, {'manifest.json/child': 'unit'}),
        ]
        for index, (docs, statuses) in enumerate(inventories):
            store = _s35_load('s35_paths_' + str(index), modules / 'control_store.py')
            connection = store.open_store(root / ('paths-' + str(index) + '.sqlite3'))
            seed.backup(connection)
            put(store, connection, 'revision', 'accepted_revision', dict(
                domain_uuid='domain', repository_uuid='repository', commit=commit,
                documents=docs, statuses=statuses))
            reader = rs.attach(store, connection, repo, 'domain', 'repository')
            reader.enable('reserve', dict(revision='revision', entities={}, collections={}))
            before = store.table_snapshot(connection)
            refusal = None
            try:
                reader.execute(command('accept_snapshot', dict(snapshot_id='invalid-paths',
                    operation='reserve', arguments={}), {'invalid-paths': 0}), **signing)
            except store.StoreRefused as error:
                refusal = error.code
            prefix_outcomes.append(refusal == 'invalid_input' and store.table_snapshot(connection) == before)
            connection.close()
        expect('snapshots/path-prefix-inventory', all(prefix_outcomes) and len(prefix_outcomes) == 4)
        # R3 capsule: empty document inventory must still require a real pinned commit.
        commit_outcomes = []
        for index, proposed in enumerate(('HEAD', 'f' * len(commit), g('rev-parse', commit + ':policy.md'), commit)):
            store = _s35_load('s35_commits_' + str(index), modules / 'control_store.py')
            connection = store.open_store(root / ('commits-' + str(index) + '.sqlite3'))
            seed.backup(connection)
            put(store, connection, 'revision', 'accepted_revision', dict(
                domain_uuid='domain', repository_uuid='repository', commit=proposed,
                documents={}, statuses={'status.json': 'unit'}))
            reader = rs.attach(store, connection, repo, 'domain', 'repository')
            reader.enable('reserve', dict(revision='revision', entities={}, collections={}))
            before = store.table_snapshot(connection)
            refusal = None
            try:
                reader.execute(command('accept_snapshot', dict(snapshot_id='status-only',
                    operation='reserve', arguments={}), {'status-only': 0}), **signing)
            except store.StoreRefused as error:
                refusal = error.code
            if proposed == 'HEAD' and refusal is None:
                unpinned = sn.load(store, connection, 'status-only', 'domain', 'repository')
                old_head = g('rev-parse', 'HEAD')
                (repo / 'advance.txt').write_text('advance after status-only acceptance')
                g('add', '.')
                g('commit', '-qm', 'Advance after status-only acceptance')
                unpinned_destination = root / 'unpinned-published'
                sn.materialize(unpinned, repo, unpinned_destination)
                unpinned_result = sn.read_materialized(unpinned, repo, unpinned_destination)
                assert g('rev-parse', 'HEAD') != old_head
                # Preserve the capsule's publication step before the named assertion fails.
                assert unpinned_result['manifest']['accepted_commit'] == 'HEAD'
            if proposed != commit:
                commit_outcomes.append(refusal == 'invalid_input' and store.table_snapshot(connection) == before)
            else:
                accepted_status = sn.load(store, connection, 'status-only', 'domain', 'repository')
                # HEAD already moved above; accepted exact commit and captured status stay fixed.
                destination = root / 'status-only-published'
                sn.materialize(accepted_status, repo, destination)
                observed_status = sn.read_materialized(accepted_status, repo, destination)
                commit_outcomes.append(refusal is None and g('rev-parse', 'HEAD') != commit
                    and observed_status['manifest']['accepted_commit'] == commit
                    and observed_status['members']['status.json'] == sn.canonical(accepted_status['statuses']['status.json']))
            connection.close()
        expect('snapshots/status-only-commit', all(commit_outcomes) and len(commit_outcomes) == 4)
        seed.close()
    observations['elapsed_seconds'] = _s35_time.monotonic() - started
    return observations


_s35_observations = _s35_run()
