"""VELDO-0037: counter aliases, versioned edits and exact published documents.

Only ROOT and expect come from shared.py. Every production module is copied into one temporary
directory, which is also the mutation harness's production seam. Real SQLite store, real Git
repositories and clones, real Ed25519 journal signatures, separate allocation and reader
processes. Every service call goes through _s37_attempt so a driven mutant turns a named row red
by failing its assertion instead of raising out of the suite.
"""
import hashlib as _s37_hashlib
import importlib.util as _s37_ilu
import json as _s37_json
from pathlib import Path as _s37_Path
import shutil as _s37_shutil
import subprocess as _s37_sp
import sys as _s37_sys
import tempfile as _s37_temp
import time as _s37_time


def _s37_load(name, path):
    spec = _s37_ilu.spec_from_file_location(name, path)
    mod = _s37_ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _s37_digest(body):
    return 'sha256:' + _s37_hashlib.sha256(body).hexdigest()


_S37_CHILD_PRELUDE = r'''
import importlib.util, json, subprocess, sys
from pathlib import Path
def load(name):
    s = importlib.util.spec_from_file_location('child_' + name, Path(sys.argv[1]) / (name + '.py'))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
st = load('control_store')
'''

# An independent requester: its own process, its own store connection, its own workspace.
_S37_ALLOCATE = _S37_CHILD_PRELUDE + r'''
al = load('control_alias')
request = json.loads(sys.argv[3])
request['content'] = request['content'].encode('utf-8')
def sign(body):
    return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', sys.argv[4], '-n', 'veldo-alias'], input=body,
                          capture_output=True, timeout=10, check=True).stdout.decode()
conn = st.open_store(sys.argv[2])
service = al.attach(st, conn, 'domain', ['repository', 'other'])
try:
    result = service.allocate(request, signer='allocation-service', sign=sign, authority_generation=1)
    print(json.dumps({'alias': result['alias'], 'reused': bool(result.get('reused')), 'seq': result.get('seq')}))
except st.StoreRefused as error:
    print(json.dumps({'refusal': error.code}))
conn.close()
'''

# An independent reader: read-only store handle plus the published checkout.
_S37_READ = _S37_CHILD_PRELUDE + r'''
doc = load('control_document')
conn = st.open_store(sys.argv[2], mode='r')
out = {}
for alias in json.loads(sys.argv[4]):
    try:
        r = doc.read_published(st, conn, 'repository', alias, sys.argv[3])
        out[alias] = {'version': r['version'], 'digest': r['digest'], 'source': r['source'], 'role': r['role'],
                      'path': r['path'], 'body': r['body'].hex()}
    except doc.SN.Refused as error:
        out[alias] = {'refusal': error.code}
print(json.dumps(out))
conn.close()
'''


def _s37_run():
    started = _s37_time.monotonic()
    observations = {'allocations': {}, 'refusals': {}, 'readers': {}}
    with _s37_temp.TemporaryDirectory(prefix='aliases-37-') as temporary:
        root = _s37_Path(temporary)
        modules = root / 'modules'
        modules.mkdir()
        # Literal anchors are required by the registered mutation driver.
        for name, source in {
            'control_alias.py': ROOT / ".veldo" / "control_alias.py",
            'control_document.py': ROOT / ".veldo" / "control_document.py",
            'control_snapshot.py': ROOT / '.veldo/control_snapshot.py',
            'control_store.py': ROOT / '.veldo/control_store.py',
            'claim.py': ROOT / '.veldo/claim.py',
            'git_process.py': ROOT / '.veldo/git_process.py',
        }.items():
            _s37_shutil.copyfile(source, modules / name)
        st = _s37_load('s37_store', modules / 'control_store.py')
        al = _s37_load('s37_alias', modules / 'control_alias.py')
        doc = _s37_load('s37_document', modules / 'control_document.py')
        claim = _s37_load('s37_claim', modules / 'claim.py')
        git = al._git_process

        def g(repo, *args):
            return git.check_output(['git', '-C', str(repo), *args], identity=('Alias fixture', 'alias@example.test'),
                                    stderr=_s37_sp.PIPE).decode().strip()

        def attempt(call):
            try:
                return call(), None
            except (st.StoreRefused, al.SN.Refused, doc.SN.Refused) as error:
                return None, error

        def code(error):
            return getattr(error, 'code', None)

        origin = root / 'origin'
        origin.mkdir()
        g(origin, 'init', '-q')
        existing = {'specs/VELDO-0001-first.md': b'# first\n', 'specs/VELDO-0003-third.md': b'# third\n',
                    'specs/notes.md': b'not an alias\n', 'plans/PLAN-0002-second.md': b'# plan two\n',
                    '.veldo/decisions/0004-choice.yaml': b'id: four\n'}
        for path, body in existing.items():
            (origin / path).parent.mkdir(parents=True, exist_ok=True)
            (origin / path).write_bytes(body)
        g(origin, 'add', '.')
        g(origin, 'commit', '-qm', 'Accepted inventory')
        accepted_commit = g(origin, 'rev-parse', 'HEAD')
        w1, w2, publication = root / 'w1', root / 'w2', root / 'authority'
        for clone in (w1, w2, publication):
            g(root, 'clone', '-q', str(origin), str(clone))
        key = root / 'journal-key'
        _s37_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                    check=True, capture_output=True, timeout=10)

        def sign(body):
            return _s37_sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', 'veldo-alias'], input=body,
                               capture_output=True, timeout=10, check=True).stdout.decode()

        signing = dict(signer='allocation-service', sign=sign, authority_generation=1)
        db = root / 'control.sqlite3'
        conn = st.open_store(db)
        service = al.attach(st, conn, 'domain', ['repository', 'other'])
        publisher = doc.Publisher(service, publication)
        refusal_log = []

        def call(action):
            result, error = attempt(action)
            if error is not None:
                refusal_log.append(code(error))
            return result, error

        def seq():
            return conn.execute('SELECT COALESCE(MAX(seq),0) FROM journal').fetchone()[0]

        def counter(repository='repository', kind='specification'):
            data = service.current(al.kind_id(repository, kind))[1]
            return data['next'] if data else None

        def request(rid, system, sid, revision, role, slug, body, workspace, repository='repository'):
            return {'request_id': rid, 'principal': 'owner', 'repository_uuid': repository,
                    'workspace': str(workspace), 'source': {'system': system, 'id': sid, 'revision': revision},
                    'role': role, 'slug': slug, 'content': body}

        def publish(alias, version):
            return call(lambda: publisher.publish('repository', alias, version, 'publisher', **signing))

        def child_allocate(item):
            payload = dict(item, content=item['content'].decode('utf-8'))
            proc = _s37_sp.run([_s37_sys.executable, '-B', '-c', _S37_ALLOCATE, str(modules), str(db),
                                _s37_json.dumps(payload), str(key)], capture_output=True, text=True, timeout=30)
            try:
                return _s37_json.loads(proc.stdout)
            except ValueError:
                return {'failed': proc.returncode}

        def child_read(aliases):
            proc = _s37_sp.run([_s37_sys.executable, '-B', '-c', _S37_READ, str(modules), str(db), str(publication),
                                _s37_json.dumps(aliases)], capture_output=True, text=True, timeout=30)
            try:
                return _s37_json.loads(proc.stdout)
            except ValueError:
                return {'failed': proc.returncode}

        # Exactness fixtures: CRLF, non-ASCII, no trailing newline, trailing spaces.
        doc_a = 'API contract\r\n\r\nCaf\u00e9 r\u00e9sum\u00e9 \u00fcber\r\nno final newline'.encode('utf-8')
        doc_a2 = 'API contract, second accepted edit\r\n'.encode('utf-8')
        doc_a4 = b'API contract, fourth version\n'
        doc_evil = b'bytes nobody accepted\n'
        bodies = {name: ('%s body   \n' % name).encode('utf-8') for name in
                  ('b', 'c', 'd', 'e', 'f', 'g', 'h', 'other')}
        plan_doc = b'Plan: journey\n\n1. build\n'
        decision_doc = 'decision: store choice \u00e9\n'.encode('utf-8')

        # --- enabling kinds: first numbers come once from an exact accepted commit (C9) -----
        kinds = {'specification': ('VELDO', 'specs/{alias}-{slug}.md'),
                 'plan': ('PLAN', 'plans/{alias}-{slug}.md'),
                 'decision': ('VELDO-DEC', '.veldo/decisions/{number}-{slug}.yaml')}
        firsts = {}
        for kind, (prefix, template) in kinds.items():
            config = {'prefix': prefix, 'width': 4, 'path_template': template}
            firsts[kind] = al.accepted_maximum(origin, accepted_commit, config) + 1
            call(lambda: service.enable_kind(dict(config, request_id='enable-' + kind, principal='operator',
                                                  repository_uuid='repository', kind=kind, first=firsts[kind]), **signing))
        expect('aliases/accepted-floor', firsts == {'specification': 4, 'plan': 3, 'decision': 5}
               and [counter(kind=k) for k in kinds] == [4, 3, 5])

        # --- invalid unit ids refuse through claim.unit_id_problem before any artifact -------
        before = st.table_snapshot(conn)
        listing = sorted(str(p) for p in publication.rglob('*') if '.git' not in p.parts)
        invalid = []
        for index, prefix in enumerate(('VEL DO', 'VELDO/X', '../VELDO')):
            _, error = call(lambda: service.enable_kind({'request_id': 'enable-broken-%d' % index, 'principal': 'operator',
                'repository_uuid': 'repository', 'kind': 'broken', 'prefix': prefix, 'width': 4,
                'path_template': 'specs/{alias}-{slug}.md', 'first': 1}, **signing))
            problem = claim.unit_id_problem(prefix + '-0001')
            invalid.append(problem is not None and code(error) == 'invalid_unit_id' and error.detail == problem)
        bad_alias = 'VELDO-0004/../x'
        _, error = call(lambda: service.edit({'request_id': 'edit-bad', 'principal': 'owner', 'repository_uuid': 'repository',
            'workspace': str(w1), 'alias': bad_alias, 'role': 'specification', 'expected_version': 1,
            'expected_digest': _s37_digest(doc_a), 'content': doc_evil,
            'source': {'system': 'telegram', 'id': 'bad', 'revision': 'r1'}}, **signing))
        invalid.append(code(error) == 'invalid_unit_id' and error.detail == claim.unit_id_problem(bad_alias))
        _, error = publish(bad_alias, 1)
        invalid.append(code(error) == 'invalid_unit_id')
        expect('aliases/invalid-unit-id', all(invalid) and len(invalid) == 5 and st.table_snapshot(conn) == before
               and sorted(str(p) for p in publication.rglob('*') if '.git' not in p.parts) == listing)
        observations['refusals']['invalid-unit-id'] = invalid

        # --- AC1: independent requests from stale checkouts, each its own process -----------
        request_a = request('req-a', 'telegram', 'msg-100', 'r1', 'specification/api', 'api-contract', doc_a, w1)
        request_b = request('req-b', 'telegram', 'msg-200', 'r1', 'specification', 'ui-shell', bodies['b'], w2)
        request_c = request('req-c', 'api', 'req-7', 'r1', 'specification', 'importer', bodies['c'], w1)
        independent = [child_allocate(item) for item in (request_a, request_b, request_c)]
        observations['allocations']['independent'] = independent
        stale = all(sorted(p.name for p in (w / 'specs').iterdir())
                    == ['VELDO-0001-first.md', 'VELDO-0003-third.md', 'notes.md'] for w in (w1, w2))
        expected_independent = ['VELDO-0004', 'VELDO-0005', 'VELDO-0006']
        expect('aliases/stale-checkouts', [item.get('alias') for item in independent] == expected_independent
               and stale and counter() == 7
               and all(service.current(al.alias_id('repository', a))[0] == 1 for a in expected_independent))

        seq_before = seq()
        again = child_allocate(dict(request_a, request_id='req-a-retry', workspace=str(w2)))
        expect('aliases/same-source-reuse', again == {'alias': 'VELDO-0004', 'reused': True, 'seq': None}
               and counter() == 7 and seq() == seq_before)

        variants = [
            ('system', request('req-d1', 'api', 'msg-100', 'r1', 'specification/api', 'api-by-api', bodies['d'], w1)),
            ('id', request('req-d2', 'telegram', 'msg-101', 'r1', 'specification/api', 'api-by-id', bodies['d'], w1)),
            ('revision', request('req-d3', 'telegram', 'msg-100', 'r2', 'specification/api', 'api-r2', bodies['d'], w1)),
            ('role-label', request('req-d4', 'telegram', 'msg-100', 'r1', 'specification/ui', 'ui-from-100', bodies['d'], w1)),
            ('role-plan', request('req-d5', 'telegram', 'msg-100', 'r1', 'plan', 'journey-plan', plan_doc, w1)),
            ('role-decision', request('req-d6', 'telegram', 'msg-100', 'r1', 'decision', 'store-choice', decision_doc, w1)),
        ]
        distinct = {}
        for label, item in variants:
            result, _ = call(lambda: service.allocate(item, **signing))
            distinct[label] = (result or {}).get('alias')
        observations['allocations']['distinct'] = distinct
        expect('aliases/distinct-source', distinct == {'system': 'VELDO-0007', 'id': 'VELDO-0008',
               'revision': 'VELDO-0009', 'role-label': 'VELDO-0010', 'role-plan': 'PLAN-0003',
               'role-decision': 'VELDO-DEC-0005'} and counter() == 11)

        # A command authored from a counter read that another allocation then moved.
        request_e = request('req-e', 'telegram', 'msg-300', 'r1', 'specification', 'stale-read', bodies['e'], w2)
        request_f = request('req-f', 'telegram', 'msg-301', 'r1', 'specification', 'winner', bodies['f'], w1)
        authored, _ = attempt(lambda: service.author_allocation(request_e))
        won, _ = call(lambda: service.allocate(request_f, **signing))
        before = st.table_snapshot(conn)
        stale_error = None
        if authored and authored[0]:
            _, stale_error = attempt(lambda: st.execute(conn, authored[0], **signing))
        unchanged = st.table_snapshot(conn) == before
        late, _ = call(lambda: service.allocate(request_e, **signing))
        expect('aliases/stale-read-refused', bool(authored and authored[1] and authored[1]['alias'] == 'VELDO-0011')
               and (won or {}).get('alias') == 'VELDO-0011' and code(stale_error) == 'stale_version' and unchanged
               and (late or {}).get('alias') == 'VELDO-0012')

        # No recycling: a published-then-removed file and a re-enable attempt free nothing.
        published_b, _ = publish('VELDO-0005', 1)
        removed = publication / 'specs/VELDO-0005-ui-shell.md'
        was_published = removed.is_file()
        if was_published:
            removed.unlink()
        _, reseed = call(lambda: service.enable_kind({'request_id': 'enable-specification-again', 'principal': 'operator',
            'repository_uuid': 'repository', 'kind': 'specification', 'prefix': 'VELDO', 'width': 4,
            'path_template': 'specs/{alias}-{slug}.md', 'first': 4}, **signing))
        request_g = request('req-g', 'telegram', 'msg-400', 'r1', 'specification', 'after-removal', bodies['g'], w1)
        fresh, _ = call(lambda: service.allocate(request_g, **signing))
        reserved = [row[0] for row in conn.execute("SELECT data FROM entities WHERE kind='alias_reservation'")]
        numbers = sorted(_s37_json.loads(raw)['number'] for raw in reserved
                         if _s37_json.loads(raw)['repository_uuid'] == 'repository'
                         and _s37_json.loads(raw)['kind'] == 'specification')
        expect('aliases/no-recycling', bool(published_b) and was_published and code(reseed) == 'stale_version'
               and (fresh or {}).get('alias') == 'VELDO-0013' and counter() == 14 and numbers == list(range(4, 14)))

        # Counters are per repository; an unenrolled repository refuses by name.
        call(lambda: service.enable_kind({'request_id': 'enable-other', 'principal': 'operator', 'repository_uuid': 'other',
            'kind': 'specification', 'prefix': 'VELDO', 'width': 4, 'path_template': 'specs/{alias}-{slug}.md',
            'first': 1}, **signing))
        other, _ = call(lambda: service.allocate(request('req-o', 'telegram', 'msg-100', 'r1', 'specification/api',
                                                         'api-contract', bodies['other'], w1, repository='other'), **signing))
        _, wrong = call(lambda: service.allocate(request('req-x', 'telegram', 'msg-900', 'r1', 'specification',
                                                         'nowhere', bodies['other'], w1, repository='unknown'), **signing))
        expect('aliases/per-repository', (other or {}).get('alias') == 'VELDO-0001' and counter() == 14
               and counter('other') == 2 and code(wrong) == 'wrong_repository')

        # --- AC3: publish each enabled kind; an independent reader compares the accepted record --
        plan_request, decision_request = variants[4][1], variants[5][1]
        targets = {'VELDO-0004': (request_a, doc_a, 'specs/VELDO-0004-api-contract.md'),
                   'PLAN-0003': (plan_request, plan_doc, 'plans/PLAN-0003-journey-plan.md'),
                   'VELDO-DEC-0005': (decision_request, decision_doc, '.veldo/decisions/0005-store-choice.yaml')}
        publications = {alias: publish(alias, 1)[0] for alias in targets}
        observed = child_read(sorted(targets))
        expected = {alias: {'version': 1, 'digest': _s37_digest(body), 'source': item['source'], 'role': item['role'],
                            'path': path, 'body': body.hex()} for alias, (item, body, path) in targets.items()}
        observations['readers']['v1'] = {alias: {k: v for k, v in (value or {}).items() if k != 'body'}
                                         for alias, value in observed.items()} if isinstance(observed, dict) else observed
        expect('publication/accepted-documents', observed == expected and all(publications.values())
               and all((publication / path).read_bytes() == body for _, body, path in targets.values())
               and not any(('repository', alias, 1) in service.pending() for alias in targets))

        # One journal record carries the counter, reservation, mapping, head, version and obligation.
        record = next((r for r in st.export_journal(conn) if r['command_id'].startswith('alias.allocate:req-a:')), None)
        key_a = _s37_digest(_s37_json.dumps({'repository_uuid': 'repository', 'system': 'telegram', 'id': 'msg-100',
                                              'revision': 'r1', 'role': 'specification/api'}, sort_keys=True,
                                             separators=(',', ':'), ensure_ascii=True).encode())
        ids = {'artifact-kind/repository/specification', 'alias/repository/VELDO-0004',
               'alias-source/repository/' + key_a.split(':', 1)[1], 'document/repository/VELDO-0004',
               'document/repository/VELDO-0004@1', 'publication/repository/VELDO-0004@1'}
        verified = None
        if record:
            signature = root / 'record.sig'
            signature.write_text(record['signature'])
            allowed = root / 'allowed'
            allowed.write_text('allocation-service ' + key.with_suffix('.pub').read_text())
            verified = _s37_sp.run(['ssh-keygen', '-Y', 'verify', '-f', str(allowed), '-I', 'allocation-service',
                                    '-n', 'veldo-alias', '-s', str(signature)], input=st.journal_signed_bytes(record),
                                   capture_output=True, timeout=10).returncode
        transition = (record or {}).get('transition', {})
        together = (set(transition) == ids and verified == 0
                    and transition.get('document/repository/VELDO-0004@1', {}).get('data', {}).get('content', '').encode('utf-8') == doc_a
                    and all(transition[i]['data'].get('alias', 'VELDO-0004') == 'VELDO-0004' for i in ids if i in transition)
                    and transition.get('alias-source/repository/' + key_a.split(':', 1)[1], {}).get('data', {}).get('source')
                    == request_a['source']
                    and transition.get('artifact-kind/repository/specification', {}).get('data', {}).get('next') == 5)
        expect('publication/commit-together', together)

        # Exclusive creation never replaces bytes somebody else put at the declared path.
        occupied, _ = call(lambda: service.allocate(request('req-h', 'telegram', 'msg-500', 'r1', 'specification',
                                                            'occupied', bodies['h'], w1), **signing))
        squatter = publication / 'specs/VELDO-0014-occupied.md'
        squatter.write_bytes(b'somebody else\n')
        _, exclusive = publish('VELDO-0014', 1)
        expect('publication/exclusive-create', (occupied or {}).get('alias') == 'VELDO-0014'
               and code(exclusive) == 'publication_conflict' and squatter.read_bytes() == b'somebody else\n'
               and ('repository', 'VELDO-0014', 1) in service.pending()
               and not list((publication / 'specs').glob('.*.publishing')))

        # --- AC2: edits against a real accepted, published document --------------------------
        def edit(rid, revision, version, expected_digest, body):
            return call(lambda: service.edit({'request_id': rid, 'principal': 'owner', 'repository_uuid': 'repository',
                'workspace': str(w1), 'alias': 'VELDO-0004', 'role': 'specification/api', 'expected_version': version,
                'expected_digest': expected_digest, 'content': body,
                'source': {'system': 'telegram', 'id': 'msg-100', 'revision': revision}}, **signing))

        def version_bytes(alias, version):
            data = service.current(al.version_id('repository', alias, version))[1]
            return data['content'].encode('utf-8') if data else None

        second, _ = edit('edit-1', 'edit-1', 1, _s37_digest(doc_a), doc_a2)
        reader_unpublished = child_read(['VELDO-0004']).get('VELDO-0004', {})
        head = service.current(al.head_id('repository', 'VELDO-0004'))
        expect('documents/edit-current', (second or {}).get('version') == 2 and head[0] == 2
               and (head[1] or {}).get('digest') == _s37_digest(doc_a2) and version_bytes('VELDO-0004', 1) == doc_a
               and ('repository', 'VELDO-0004', 2) in service.pending()
               and reader_unpublished.get('version') == 1 and reader_unpublished.get('body') == doc_a.hex())

        seq_before = seq()
        repeat, _ = edit('edit-1-retry', 'edit-1', 1, _s37_digest(doc_a), doc_a2)
        expect('documents/identical-reuse', (repeat or {}).get('reused') is True and repeat.get('version') == 2
               and seq() == seq_before)

        before = st.table_snapshot(conn)
        _, changed_edit = edit('edit-1-changed', 'edit-1', 1, _s37_digest(doc_a), doc_evil)
        _, changed_allocation = call(lambda: service.allocate(dict(request_a, request_id='req-a-changed', content=doc_evil), **signing))
        expect('documents/changed-content-conflict', code(changed_edit) == 'source_content_conflict'
               and code(changed_allocation) == 'source_content_conflict' and st.table_snapshot(conn) == before)

        # Replacement of the declared version, only after its predecessor is published.
        published_2, _ = publish('VELDO-0004', 2)
        reader_2 = child_read(['VELDO-0004']).get('VELDO-0004', {})
        third, _ = edit('edit-2', 'edit-2', 2, _s37_digest(doc_a2), doc_a)   # v3 carries v1's bytes again
        before = st.table_snapshot(conn)
        stale = {}
        for label, version, expected_digest in [('aba-stale-version', 1, _s37_digest(doc_a)),
                                                ('old-version', 2, _s37_digest(doc_a2)),
                                                ('wrong-digest', 3, _s37_digest(doc_a2)),
                                                ('unknown-digest', 3, 'sha256:' + '0' * 64)]:
            _, error = edit('overwrite-' + label, 'overwrite-' + label, version, expected_digest, doc_evil)
            stale[label] = code(error)
        observations['refusals']['stale-overwrite'] = stale
        head = service.current(al.head_id('repository', 'VELDO-0004'))
        expect('documents/stale-overwrite', (third or {}).get('version') == 3 and stale == {
               'aba-stale-version': 'stale_version', 'old-version': 'stale_version',
               'wrong-digest': 'stale_document', 'unknown-digest': 'stale_document'}
               and st.table_snapshot(conn) == before and head[0] == 3 and (head[1] or {}).get('digest') == _s37_digest(doc_a)
               and [version_bytes('VELDO-0004', v) for v in (1, 2, 3)] == [doc_a, doc_a2, doc_a])

        published_3, _ = publish('VELDO-0004', 3)
        reader_3 = child_read(['VELDO-0004']).get('VELDO-0004', {})
        ordered, _ = call(lambda: service.edit({'request_id': 'edit-d', 'principal': 'owner', 'repository_uuid': 'repository',
            'workspace': str(w1), 'alias': 'VELDO-0010', 'role': 'specification/ui', 'expected_version': 1,
            'expected_digest': _s37_digest(bodies['d']), 'content': b'ui second\n',
            'source': {'system': 'telegram', 'id': 'msg-100', 'revision': 'edit-ui'}}, **signing))
        _, out_of_order = publish('VELDO-0010', 2)
        expect('publication/replace-declared-version', bool(published_2) and bool(published_3)
               and reader_2.get('version') == 2 and reader_2.get('body') == doc_a2.hex()
               and reader_3.get('version') == 3 and reader_3.get('body') == doc_a.hex()
               and (publication / targets['VELDO-0004'][2]).read_bytes() == doc_a
               and (ordered or {}).get('version') == 2 and code(out_of_order) == 'publication_order')

        # An externally edited checkout file is never overwritten by the next version.
        fourth, _ = edit('edit-3', 'edit-3', 3, _s37_digest(doc_a), doc_a4)
        declared = publication / targets['VELDO-0004'][2]
        declared.write_bytes(b'edited in the checkout\n')
        _, guarded = publish('VELDO-0004', 4)
        expect('publication/replace-guard', (fourth or {}).get('version') == 4 and code(guarded) == 'publication_conflict'
               and declared.read_bytes() == b'edited in the checkout\n' and ('repository', 'VELDO-0004', 4) in service.pending())

        # The reader refuses altered or absent bytes under the accepted, recorded digest.
        tampered = child_read(['VELDO-0004']).get('VELDO-0004', {})
        declared.unlink()
        missing = child_read(['VELDO-0004']).get('VELDO-0004', {})
        observations['readers']['tampered'] = tampered
        observations['readers']['missing'] = missing
        expect('publication/tampered-refused', tampered == {'refusal': 'document_mismatch'}
               and missing == {'refusal': 'missing_publication'})

        # Observability: counts, categories, trace joins, pending work and no document bytes.
        records = {r['command_id']: r for r in st.export_journal(conn)}
        refused = [o for o in service.observations if o['outcome'] == 'refused']
        accepted = [o for o in service.observations if o['outcome'] == 'accepted']
        texts = [body.decode('utf-8') for body in (doc_a, doc_a2, doc_a4, doc_evil, plan_doc, decision_doc, *bodies.values())]
        logged = _s37_json.dumps(service.observations, sort_keys=True)
        pending = service.pending()
        expected_pending = sorted([('other', 'VELDO-0001', 1), ('repository', 'VELDO-0004', 4)]
                                  + [('repository', 'VELDO-%04d' % n, 1) for n in (6, 7, 8, 9, 10, 11, 12, 13, 14)]
                                  + [('repository', 'VELDO-0010', 2)])
        expect('aliases/observations', service.counts == {'accepted': len(accepted), 'reused': sum(
               o['outcome'] == 'reused' for o in service.observations), 'refused': len(refused)}
               and [o['refusal'] for o in refused] == refusal_log
               and all(o['category'] in ('invalid_input', 'missing_authority', 'stale_subject', 'unavailable_service',
                                         'missing_evidence') for o in refused)
               and all(o['command_id'] in records and records[o['command_id']]['record_digest'] == o['record_digest']
                       and records[o['command_id']]['seq'] == o['seq'] for o in accepted)
               and not any(text.strip() and text.strip() in logged for text in texts)
               and pending == expected_pending)
        observations['counts'] = dict(service.counts)
        observations['pending'] = pending
        observations['refusal_log'] = refusal_log
        conn.close()

        # --- Review defects: each row owns its store, authority and accepted repositories -------
        defects = observations['defects'] = {}
        serial = [0]

        class _S37Env:
            pass

        def fresh(label, histories=None):
            """histories maps a repository to its accepted commits, each {path: bytes, or None to delete}."""
            env = _S37Env()
            env.base = root / ('defect-' + label)
            env.base.mkdir()
            env.origins, env.revisions = {}, {}
            for repository, commits in (histories or {'repository': [{}]}).items():
                origin = env.base / (repository + '-origin')
                origin.mkdir()
                g(origin, 'init', '-q')
                for index, files in enumerate(commits):
                    for path, body in dict(files, **{'README.md': ('%s %s %d\n' % (label, repository, index)).encode()}).items():
                        if body is None:
                            (origin / path).unlink()
                        else:
                            (origin / path).parent.mkdir(parents=True, exist_ok=True)
                            (origin / path).write_bytes(body)
                    g(origin, 'add', '-A')
                    g(origin, 'commit', '-qm', 'Accepted %s %d' % (repository, index))
                env.origins[repository] = origin
            env.conn = st.open_store(env.base / 'control.sqlite3')
            env.service = al.attach(st, env.conn, 'domain', {r: str(p) for r, p in env.origins.items()})
            for repository, origin in env.origins.items():
                env.revisions[repository] = 'revision/' + repository
                st.execute(env.conn, {'command_id': 'seed-' + repository, 'principal': 'operator',
                                      'operation': 'upsert_entity', 'nonce': 'seed-%s/nonce' % repository,
                                      'parameters': {'entity_id': 'revision/' + repository, 'kind': 'accepted_revision',
                                                     'data': {'domain_uuid': 'domain', 'repository_uuid': repository,
                                                              'commit': g(origin, 'rev-parse', 'HEAD'),
                                                              'documents': {}, 'statuses': {}}},
                                      'expected_versions': {'revision/' + repository: 0}, 'artifact_digests': []},
                           **signing)
            return env

        def checkout_of(env, repository='repository', name=None):
            path = env.base / (name or repository + '-checkout')
            g(env.base, 'clone', '-q', str(env.origins[repository]), str(path))
            return path

        def enable(env, kind, prefix, template, first=1, repository='repository'):
            serial[0] += 1
            item = {'request_id': 'enable-%d' % serial[0], 'principal': 'operator', 'repository_uuid': repository,
                    'kind': kind, 'prefix': prefix, 'width': 4, 'path_template': template,
                    'revision_id': env.revisions[repository]}
            if first is not None:
                item['first'] = first
            return attempt(lambda: env.service.enable_kind(item, **signing))

        def allocate(env, rid, role, slug, body, repository='repository'):
            return attempt(lambda: env.service.allocate(request(rid, 'telegram', rid, 'r1', role, slug, body, env.base,
                                                                repository=repository), **signing))

        def publish_by(publisher, repository, alias, version=1):
            if publisher is None:
                return None, None
            return attempt(lambda: publisher.publish(repository, alias, version, 'publisher', **signing))

        def read_by(env, repository, alias, checkout):
            return attempt(lambda: doc.read_published(st, env.conn, repository, alias, checkout))

        def files_under(directory):
            return sorted(str(p.relative_to(directory)) for p in directory.rglob('*') if '.git' not in p.parts)

        # 1. No symlink anywhere on a declared path: publication refuses a symlinked parent and
        # writes nothing outside the checkout; the reader refuses a symlinked parent or file even
        # when the bytes behind it are the accepted ones.
        env = fresh('symlink')
        checkout = checkout_of(env)
        outside = env.base / 'outside'
        outside.mkdir()
        (checkout / 'specs').symlink_to(outside, target_is_directory=True)
        publisher_1, _ = attempt(lambda: doc.Publisher(env.service, checkout))
        enable(env, 'specification', 'VELDO', 'specs/{alias}-{slug}.md')
        enable(env, 'plan', 'PLAN', 'plans/{alias}-{slug}.md')
        allocate(env, 'escape', 'specification', 'escape', b'escaping bytes\n')
        _, escaped = publish_by(publisher_1, 'repository', 'VELDO-0001')
        allocate(env, 'moved', 'plan', 'moved', b'plan bytes\n')
        published_plan, _ = publish_by(publisher_1, 'repository', 'PLAN-0001')
        honest_read, _ = read_by(env, 'repository', 'PLAN-0001', checkout)
        elsewhere = env.base / 'elsewhere'
        (checkout / 'plans').rename(elsewhere)
        (checkout / 'plans').symlink_to(elsewhere, target_is_directory=True)
        _, parent_link = read_by(env, 'repository', 'PLAN-0001', checkout)
        (checkout / 'plans').unlink()
        elsewhere.rename(checkout / 'plans')
        declared = checkout / 'plans/PLAN-0001-moved.md'
        (env.base / 'copy.md').write_bytes(b'plan bytes\n')
        declared.unlink()
        declared.symlink_to(env.base / 'copy.md')
        _, file_link = read_by(env, 'repository', 'PLAN-0001', checkout)
        defects['symlink'] = {'publish': code(escaped), 'outside': files_under(outside),
                              'reader_parent_link': code(parent_link), 'reader_file_link': code(file_link)}
        expect('publication/no-symlink-escape', publisher_1 is not None and code(escaped) == 'unsafe_path'
               and files_under(outside) == [] and ('repository', 'VELDO-0001', 1) in env.service.pending()
               and bool(published_plan) and (honest_read or {}).get('body') == b'plan bytes\n'
               and code(parent_link) == 'unsafe_path' and code(file_link) == 'unsafe_path')
        env.conn.close()
    observations['elapsed_seconds'] = _s37_time.monotonic() - started
    return observations


_s37_observations = _s37_run()
