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
service = al.attach(st, conn, 'domain', json.loads(sys.argv[5]))
try:
    result = service.allocate(request, signer='allocation-service', sign=sign, authority_generation=1)
    print(json.dumps({'alias': result['alias'], 'reused': bool(result.get('reused')), 'seq': result.get('seq')}))
except st.StoreRefused as error:
    print(json.dumps({'refusal': error.code}))
conn.close()
'''

# An independent reader: read-only store handle plus the published checkout, which must carry an
# enrollment binding the reader verifies with the enrollment service's public key.
_S37_READ = _S37_CHILD_PRELUDE + r'''
import tempfile
doc = load('control_document')
def verify(message, signature):
    with tempfile.NamedTemporaryFile('w', suffix='.sig') as handle:
        handle.write(signature)
        handle.flush()
        return subprocess.run(['ssh-keygen', '-Y', 'verify', '-f', sys.argv[5], '-I', 'enrollment-service',
                               '-n', 'veldo-enrollment', '-s', handle.name], input=message, capture_output=True,
                              timeout=10).returncode == 0
conn = st.open_store(sys.argv[2], mode='r')
out = {}
for alias in json.loads(sys.argv[4]):
    try:
        r = doc.read_published(st, conn, 'repository', alias, sys.argv[3], verify=verify, host_identity='alias-host',
                               domain_uuid='domain')
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
            'control_enrollment.py': ROOT / '.veldo/control_enrollment.py',
            'control_readset.py': ROOT / ".veldo" / "control_readset.py",
            'control_store.py': ROOT / ".veldo" / "control_store.py",
            'claim.py': ROOT / '.veldo/claim.py',
            'git_process.py': ROOT / '.veldo/git_process.py',
        }.items():
            _s37_shutil.copyfile(source, modules / name)
        st = _s37_load('s37_store', modules / 'control_store.py')
        al = _s37_load('s37_alias', modules / 'control_alias.py')
        doc = _s37_load('s37_document', modules / 'control_document.py')
        claim = _s37_load('s37_claim', modules / 'claim.py')
        rs = _s37_load('s37_readset', modules / 'control_readset.py')
        enrollment = _s37_load('s37_enrollment', modules / 'control_enrollment.py')
        git = al._git_process

        def g(repo, *args):
            return git.check_output(['git', '-C', str(repo), *args], identity=('Alias fixture', 'alias@example.test'),
                                    stderr=_s37_sp.PIPE).decode().strip()

        def attempt(call):
            try:
                return call(), None
            except (st.StoreRefused, al.SN.Refused, doc.SN.Refused, rs.SN.Refused) as error:
                return None, error

        def code(error):
            return getattr(error, 'code', None)

        origin = root / 'origin'
        origin.mkdir()
        g(origin, 'init', '-q')
        existing = {'specs/VELDO-0001-first.md': b'# first\n', 'specs/VELDO-0003-third.md': b'# third\n',
                    'specs/notes.md': b'not an alias\n', 'plans/PLAN-0002-second.md': b'# plan two\n',
                    'decisions/0004-choice.yaml': b'id: four\n'}
        for path, body in existing.items():
            (origin / path).parent.mkdir(parents=True, exist_ok=True)
            (origin / path).write_bytes(body)
        g(origin, 'add', '.')
        g(origin, 'commit', '-qm', 'Accepted inventory')
        accepted_commit = g(origin, 'rev-parse', 'HEAD')
        other_origin = root / 'other-origin'
        other_origin.mkdir()
        g(other_origin, 'init', '-q')
        (other_origin / 'README.md').write_bytes(b'the other repository\n')
        g(other_origin, 'add', '.')
        g(other_origin, 'commit', '-qm', 'Other accepted inventory')
        accepted_repositories = {'repository': str(origin), 'other': str(other_origin)}
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
        # VELDO-0029 enrollment: a checkout is the repository its signed binding names.
        allowed_enrollers = root / 'allowed-enrollers'
        allowed_enrollers.write_text('enrollment-service ' + key.with_suffix('.pub').read_text())

        def enrollment_sign(body):
            return _s37_sp.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', 'veldo-enrollment'], input=body,
                               capture_output=True, timeout=10, check=True).stdout.decode()

        def verify(message, signature):
            signature_file = root / 'binding.sig'
            signature_file.write_text(signature)
            return _s37_sp.run(['ssh-keygen', '-Y', 'verify', '-f', str(allowed_enrollers), '-I', 'enrollment-service',
                                '-n', 'veldo-enrollment', '-s', str(signature_file)], input=message,
                               capture_output=True, timeout=10).returncode == 0

        def enroll(checkout, repository, store):
            return enrollment.enroll(checkout, 'domain', 'store-' + _s37_Path(store).parent.name, str(store), 'alias-host', 1,
                                     enrollment_sign, 'operator', '2026-09-23T00:00:00Z', repository_uuid=repository)

        bindings = dict(verify=verify, host_identity='alias-host')
        db = root / 'control.sqlite3'
        conn = st.open_store(db)
        service = al.attach(st, conn, 'domain', accepted_repositories)
        # The accepted revisions (VELDO-0035's authority) that enabling reads its first numbers from,
        # written by their own accepting command: no generic command writes one.
        accepting = rs.attach_revisions(st, conn, 'domain', accepted_repositories)
        for repository, accepted in (('repository', origin), ('other', other_origin)):
            accepting.accept('revision/' + repository, repository, g(accepted, 'rev-parse', 'HEAD'), 'operator', **signing)
        enroll(publication, 'repository', db)
        publisher = doc.Publisher(service, publication, **bindings)
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
                                _s37_json.dumps(payload), str(key), _s37_json.dumps(accepted_repositories)],
                               capture_output=True, text=True, timeout=30)
            try:
                return _s37_json.loads(proc.stdout)
            except ValueError:
                return {'failed': proc.returncode}

        def child_read(aliases):
            proc = _s37_sp.run([_s37_sys.executable, '-B', '-c', _S37_READ, str(modules), str(db), str(publication),
                                _s37_json.dumps(aliases), str(allowed_enrollers)], capture_output=True, text=True, timeout=30)
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
                 'decision': ('VELDO-DEC', 'decisions/{number}-{slug}.yaml')}
        firsts = {}
        for kind, (prefix, template) in kinds.items():
            config = {'prefix': prefix, 'width': 4, 'path_template': template}
            firsts[kind] = al.accepted_maximum(origin, accepted_commit, config) + 1
            call(lambda: service.enable_kind(dict(config, request_id='enable-' + kind, principal='operator',
                                                  repository_uuid='repository', kind=kind, first=firsts[kind],
                                                  revision_id='revision/repository'), **signing))
        expect('aliases/accepted-floor', firsts == {'specification': 4, 'plan': 3, 'decision': 5}
               and [counter(kind=k) for k in kinds] == [4, 3, 5])

        # --- invalid unit ids refuse through claim.unit_id_problem before any artifact -------
        before = st.table_snapshot(conn)
        listing = sorted(str(p) for p in publication.rglob('*') if '.git' not in p.parts)
        invalid = []
        for index, prefix in enumerate(('VEL DO', 'VELDO/X', '../VELDO')):
            _, error = call(lambda: service.enable_kind({'request_id': 'enable-broken-%d' % index, 'principal': 'operator',
                'repository_uuid': 'repository', 'kind': 'broken', 'prefix': prefix, 'width': 4,
                'path_template': 'specs/{alias}-{slug}.md', 'first': 1, 'revision_id': 'revision/repository'}, **signing))
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
            'path_template': 'specs/{alias}-{slug}.md', 'first': 4, 'revision_id': 'revision/repository'}, **signing))
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
            'first': 1, 'revision_id': 'revision/other'}, **signing))
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
                   'VELDO-DEC-0005': (decision_request, decision_doc, 'decisions/0005-store-choice.yaml')}
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

        def fresh(label, histories=None, before_attach=None, origins=None):
            """histories maps a repository to its accepted commits, each {path: bytes, or None to delete},
            or origins maps it to an accepted repository already built; before_attach(env) runs on the
            new store before the allocation authority attaches."""
            env = _S37Env()
            env.base = root / ('defect-' + label)
            env.base.mkdir()
            env.origins, env.revisions = dict(origins or {}), {}
            for repository, commits in ({} if origins else (histories or {'repository': [{}]})).items():
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
            env.db = env.base / 'control.sqlite3'
            env.conn = st.open_store(env.db)
            env.accepting = rs.attach_revisions(st, env.conn, 'domain', {r: str(p) for r, p in env.origins.items()})
            for repository, origin in env.origins.items():
                env.revisions[repository] = 'revision/' + repository
                env.accepting.accept('revision/' + repository, repository, g(origin, 'rev-parse', 'HEAD'), 'operator',
                                     **signing)
            if before_attach is not None:
                before_attach(env)
            env.service = al.attach(st, env.conn, 'domain', {r: str(p) for r, p in env.origins.items()})
            return env

        def checkout_of(env, repository='repository', name=None, enrolled=True):
            path = env.base / (name or repository + '-checkout')
            g(env.base, 'clone', '-q', str(env.origins[repository]), str(path))
            if enrolled:
                enroll(path, repository, env.db)
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
            return attempt(lambda: doc.read_published(st, env.conn, repository, alias, checkout, domain_uuid='domain',
                                                      **bindings))

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
        publisher_1, _ = attempt(lambda: doc.Publisher(env.service, checkout, **bindings))
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

        # 2. Two kinds of one repository can never declare one path, or a path that is a
        # directory of the other's: the overlapping kind is refused when it is enabled.
        env = fresh('overlap')
        overlap = {}
        for label, kind, prefix, template in [('first', 'specification', 'VELDO', 'docs/{number}-{slug}.md'),
                                              ('same-path', 'plan', 'PLAN', 'docs/{number}-{slug}.md'),
                                              ('directory-of', 'decision', 'DEC', 'docs/{number}-{slug}.md/index.yaml'),
                                              ('slug-meets-number', 'note', 'NOTE', 'docs/{slug}-{number}.md'),
                                              ('disjoint', 'memo', 'MEMO', 'memos/{alias}.md')]:
            _, error = enable(env, kind, prefix, template)
            overlap[label] = code(error)
        kinds_stored = sorted(json_row['kind'] for json_row in
                              (_s37_json.loads(raw) for (raw,) in env.conn.execute(
                                  "SELECT data FROM entities WHERE kind='artifact_kind'")))
        allocated_plan, _ = allocate(env, 'plan-one', 'plan', 'first', b'plan bytes\n')
        defects['overlap'] = dict(overlap, kinds=kinds_stored)
        expect('aliases/one-path-per-kind', overlap == {'first': None, 'same-path': 'invalid_registration',
               'directory-of': 'invalid_registration', 'slug-meets-number': 'invalid_registration', 'disjoint': None}
               and kinds_stored == ['memo', 'specification'] and allocated_plan is None)
        env.conn.close()

        # 3. The enabling transition derives the first number from the accepted revision's commit,
        # tree and history, so a historical number (even one whose file was later deleted) is
        # never issued again, whatever first number the caller asks for.
        env = fresh('history', {'repository': [
            {'specs/VELDO-0001-first.md': b'# first\n', 'specs/VELDO-0002-gone.md': b'# gone\n'},
            {'specs/VELDO-0002-gone.md': None}]})
        floor = {}
        serial[0] += 1
        _, error = attempt(lambda: env.service.enable_kind({'request_id': 'enable-%d' % serial[0], 'principal': 'operator',
            'repository_uuid': 'repository', 'kind': 'specification', 'prefix': 'VELDO', 'width': 4,
            'path_template': 'specs/{alias}-{slug}.md', 'revision_id': 'revision/never-accepted', 'first': 1}, **signing))
        floor['unaccepted-revision'] = code(error)
        for label, first in (('first-1', 1), ('first-2-deleted', 2), ('derived', None)):
            _, error = enable(env, 'specification', 'VELDO', 'specs/{alias}-{slug}.md', first=first)
            floor[label] = code(error)
        allocated, _ = allocate(env, 'after-history', 'specification', 'after', b'new document\n')
        floor['allocated'] = (allocated or {}).get('alias')
        defects['history'] = floor
        expect('aliases/historical-floor', floor == {'unaccepted-revision': 'missing_authority',
               'first-1': 'below_accepted_history', 'first-2-deleted': 'below_accepted_history', 'derived': None,
               'allocated': 'VELDO-0003'})
        env.conn.close()

        # 5. On the allocation connection the store's generic commands cannot write any alias or
        # document entity, by id or by kind; they still write everything else.
        env = fresh('generic')
        enable(env, 'specification', 'VELDO', 'specs/{alias}-{slug}.md')
        for index in (1, 2):
            allocate(env, 'generic-%d' % index, 'specification', 'generic-%d' % index, b'generic %d\n' % index)
        counter_id = al.kind_id('repository', 'specification')
        version_of = lambda identity: env.service.current(identity)[0]
        _, kind_before = env.service.current(counter_id)
        snapshot = st.table_snapshot(env.conn)
        generic = {}
        for label, operation, parameters, identity in [
                ('rewind-counter', 'upsert_entity', {'entity_id': counter_id, 'kind': 'artifact_kind',
                                                     'data': dict(kind_before or {}, next=1)}, counter_id),
                ('retire-reservation', 'retire_entity', {'entity_id': al.alias_id('repository', 'VELDO-0001')},
                 al.alias_id('repository', 'VELDO-0001')),
                ('receipt-over-version', 'record_receipt', {'receipt_id': al.version_id('repository', 'VELDO-0002', 1),
                                                            'subject': 'x', 'digest': 'sha256:' + '0' * 64},
                 al.version_id('repository', 'VELDO-0002', 1)),
                ('owned-kind-elsewhere', 'upsert_entity', {'entity_id': 'elsewhere/1', 'kind': 'document_version',
                                                           'data': {'content': 'forged'}}, 'elsewhere/1')]:
            _, error = attempt(lambda: st.execute(env.conn, {'command_id': 'generic-' + label, 'principal': 'anyone',
                'operation': operation, 'parameters': parameters, 'nonce': 'generic-%s/nonce' % label,
                'expected_versions': {identity: version_of(identity)}, 'artifact_digests': []}, **signing))
            generic[label] = code(error)
        unchanged = st.table_snapshot(env.conn) == snapshot
        _, unrelated = attempt(lambda: st.execute(env.conn, {'command_id': 'generic-unrelated', 'principal': 'anyone',
            'operation': 'upsert_entity', 'parameters': {'entity_id': 'note/1', 'kind': 'note', 'data': {'text': 'ok'}},
            'nonce': 'generic-unrelated/nonce', 'expected_versions': {'note/1': 0}, 'artifact_digests': []}, **signing))
        generic['unrelated'] = code(unrelated)
        next_alias, _ = allocate(env, 'generic-3', 'specification', 'generic-3', b'generic 3\n')
        generic['next'] = (next_alias or {}).get('alias')
        defects['generic'] = generic
        expect('aliases/generic-writes-refused', unchanged and generic == {
               'rewind-counter': 'entity_owned', 'retire-reservation': 'entity_owned',
               'receipt-over-version': 'entity_owned', 'owned-kind-elsewhere': 'entity_owned',
               'unrelated': None, 'next': 'VELDO-0003'})
        env.conn.close()

        # 6. A publisher and a reader are bound to the repository their checkout is enrolled as
        # (row 13): another repository's accepted document is refused by name even when its path
        # and bytes are identical, and a directory that is no checkout binds nothing.
        env = fresh('cross', {'repository': [{}], 'other': [{}]})
        mine, theirs = checkout_of(env, 'repository'), checkout_of(env, 'other')
        stray = env.base / 'not-a-checkout'
        stray.mkdir()
        publisher_mine, _ = attempt(lambda: doc.Publisher(env.service, mine, **bindings))
        publisher_theirs, _ = attempt(lambda: doc.Publisher(env.service, theirs, **bindings))
        _, stray_error = attempt(lambda: doc.Publisher(env.service, stray, **bindings))
        for repository in ('repository', 'other'):
            enable(env, 'specification', 'VELDO', 'specs/{alias}-{slug}.md', repository=repository)
            allocate(env, 'cross-' + repository, 'specification', 'shared', b'identical bytes\n', repository=repository)
        _, crossed = publish_by(publisher_mine, 'other', 'VELDO-0001')
        after_cross = files_under(mine)
        own, _ = publish_by(publisher_mine, 'repository', 'VELDO-0001')
        their_own, _ = publish_by(publisher_theirs, 'other', 'VELDO-0001')
        honest_read, _ = read_by(env, 'repository', 'VELDO-0001', mine)
        _, other_from_mine = read_by(env, 'other', 'VELDO-0001', mine)
        _, mine_from_theirs = read_by(env, 'repository', 'VELDO-0001', theirs)
        defects['cross-repository'] = {'stray_publisher': code(stray_error), 'publish_other_here': code(crossed),
                                       'files_after': after_cross, 'read_other_here': code(other_from_mine),
                                       'read_here_from_other': code(mine_from_theirs)}
        expect('publication/bound-to-repository', publisher_mine is not None and publisher_theirs is not None
               and code(stray_error) == 'wrong_repository' and code(crossed) == 'wrong_repository'
               and after_cross == ['README.md'] and bool(own) and bool(their_own)
               and (honest_read or {}).get('body') == b'identical bytes\n'
               and code(other_from_mine) == 'wrong_repository' and code(mine_from_theirs) == 'wrong_repository')
        env.conn.close()

        # 4. A publication is recorded only on the bound publisher's own reading of the exact
        # accepted bytes at the declared path inside the recording transaction; the digest a
        # caller supplies (readable by anyone from the store) is never enough.
        env = fresh('record')
        checkout = checkout_of(env)
        enable(env, 'specification', 'VELDO', 'specs/{alias}-{slug}.md')
        allocate(env, 'record-1', 'specification', 'record', b'accepted bytes\n')
        declared = checkout / 'specs/VELDO-0001-record.md'
        accepted_digest = _s37_digest(b'accepted bytes\n')

        def record_on_word():
            return attempt(lambda: env.service.record_publication('repository', 'VELDO-0001', 1, accepted_digest,
                                                                  'someone', **signing))[1]

        recording = {'no-publisher': code(record_on_word())}
        publisher_4, _ = attempt(lambda: doc.Publisher(env.service, checkout, **bindings))
        recording['no-file'] = code(record_on_word())
        declared.parent.mkdir()
        declared.write_bytes(b'other bytes\n')
        recording['other-bytes'] = code(record_on_word())
        still_pending = ('repository', 'VELDO-0001', 1) in env.service.pending()
        declared.unlink()
        published, _ = publish_by(publisher_4, 'repository', 'VELDO-0001')
        honest_read, _ = read_by(env, 'repository', 'VELDO-0001', checkout)
        recording['published-then'] = bool(published)
        defects['record-without-bytes'] = recording
        expect('publication/recorded-only-by-publisher', recording == {
               'no-publisher': 'missing_authority', 'no-file': 'missing_publication', 'other-bytes': 'publication_mismatch',
               'published-then': True} and still_pending and (honest_read or {}).get('body') == b'accepted bytes\n')
        env.conn.close()

        # 7. Names that differ only by case are one file on a case-insensitive filesystem (the
        # macOS default on a Release 1 worker host): prefixes and templates are compared
        # case-insensitively, a historical number counts whatever its case, and a template is ASCII
        # so that no Unicode normalization can merge two names either.
        env = fresh('case', {'repository': [{'specs/veldo-0002-lower.md': b'lower case history\n'}]})
        folded = {}
        for label, kind, prefix, template, first in [
                ('specification', 'specification', 'VELDO', 'specs/{alias}-{slug}.md', None),
                ('prefix-case', 'plan', 'veldo', 'plans/{alias}-{slug}.md', 1),
                ('upper-directory', 'note', 'NOTE', 'Docs/{number}.md', 1),
                ('lower-directory', 'memo', 'MEMO', 'docs/{number}.md', 1),
                ('non-ascii', 'decision', 'DEC', 'décisions/{number}.md', 1)]:
            _, error = enable(env, kind, prefix, template, first=first)
            folded[label] = code(error)
        _, counter_now = env.service.current(al.kind_id('repository', 'specification'))
        folded['counter'] = (counter_now or {}).get('next')
        defects['case'] = folded
        expect('aliases/case-insensitive-names', folded == {'specification': None, 'prefix-case': 'invalid_registration',
               'upper-directory': None, 'lower-directory': 'invalid_registration', 'non-ascii': 'invalid_input',
               'counter': 3})
        env.conn.close()

        # 8. No template may reach .git/ or .veldo/ (the repository's own Git data, the claim
        # ledger and the other control files), in any case, nested, or through a placeholder.
        env = fresh('reserved')
        reserved = {}
        for label, kind, prefix, template in [
                ('git', 'gitkind', 'GITA', '.git/{alias}.md'),
                ('veldo-ledger', 'ledgerkind', 'VLDA', '.veldo/claims/{alias}.json'),
                ('nested-upper-git', 'nestedkind', 'NEST', 'packs/x/.GIT/{number}.md'),
                ('slug-makes-git', 'slugkind', 'SLUG', 'docs/.{slug}/{alias}.md'),
                ('mixed-case-veldo', 'mixedkind', 'MIXV', '.Veldo/{alias}.md'),
                ('github-allowed', 'githubkind', 'GHUB', '.github/{alias}.md')]:
            _, error = enable(env, kind, prefix, template)
            reserved[label] = code(error)
        defects['reserved'] = reserved
        expect('aliases/reserved-directories', reserved == {'git': 'reserved_path', 'veldo-ledger': 'reserved_path',
               'nested-upper-git': 'reserved_path', 'slug-makes-git': 'reserved_path',
               'mixed-case-veldo': 'reserved_path', 'github-allowed': None})
        env.conn.close()

        # --- Second review (2026-09-23): five more defects, each its own row -----------------
        # 9. A historical number is held by EVERY accepted file whose name carries it, whatever
        # the case of its directory (one directory on the Mac) and whatever its slug, or none.
        carriers = {}
        for label, template, files in [
                ('case-directory', 'specs/{alias}-{slug}.md', ['specs/VELDO-0001-a.md', 'Specs/VELDO-0005-b.md']),
                ('irregular-slug', 'specs/{alias}-{slug}.md', ['specs/VELDO-0001-a.md', 'specs/VELDO-0007-foo_bar.md']),
                ('missing-slug', 'specs/{alias}-{slug}.md', ['specs/VELDO-0001-a.md', 'specs/VELDO-0008.md']),
                ('number-template', 'decisions/{number}-{slug}.yaml', ['decisions/0002-a.yaml', 'Decisions/0009_B.YAML']),
                ('not-carriers', 'specs/{alias}-{slug}.md', ['specs/VELDO-0001-a.md', 'specs/XVELDO-0090-x.md',
                                                             'other/VELDO-0080-x.md', 'specs/notes-0070.md'])]:
            history = root / ('carriers-' + label)
            history.mkdir()
            g(history, 'init', '-q')
            for path in files:
                (history / path).parent.mkdir(parents=True, exist_ok=True)
                (history / path).write_bytes(path.encode() + b'\n')
            g(history, 'add', '-A')
            g(history, 'commit', '-qm', 'Accepted ' + label)
            found, error = attempt(lambda: al.accepted_maximum(history, g(history, 'rev-parse', 'HEAD'),
                                                               {'prefix': 'VELDO', 'width': 4, 'path_template': template}))
            carriers[label] = code(error) if error else found
        defects['carriers'] = carriers
        expect('aliases/floor-counts-every-carrier', carriers == {'case-directory': 5, 'irregular-slug': 7,
               'missing-slug': 8, 'number-template': 9, 'not-carriers': 1})

        # 10. Ownership is the store's, on EVERY connection: a second connection from another copy
        # of the store module with nothing registered, and one opened before the allocation
        # authority attached, cannot write what the allocation commands own either.
        other_store = _s37_load('s37_store_other', modules / 'control_store.py')
        early = {}
        env = fresh('connections', before_attach=lambda env: early.update(conn=other_store.open_store(env.db)))
        enable(env, 'specification', 'VELDO', 'specs/{alias}-{slug}.md')
        for index in (1, 2):
            allocate(env, 'connection-%d' % index, 'specification', 'connection-%d' % index, b'connection %d\n' % index)
        second = other_store.open_store(env.db)
        counter_id = al.kind_id('repository', 'specification')
        first_version = al.version_id('repository', 'VELDO-0001', 1)
        _, kind_before = env.service.current(counter_id)
        _, version_before = env.service.current(first_version)
        connections = {}
        for label, connection, operation, parameters, identity in [
                ('rewind-counter', second, 'upsert_entity', {'entity_id': counter_id, 'kind': 'artifact_kind',
                                                             'data': dict(kind_before or {}, next=1)}, counter_id),
                ('rewrite-version', second, 'upsert_entity', {'entity_id': first_version, 'kind': 'document_version',
                                                              'data': dict(version_before or {}, content='REWRITTEN\n')},
                 first_version),
                ('relabel-version', second, 'upsert_entity', {'entity_id': first_version, 'kind': 'note',
                                                              'data': {'text': 'no longer a version'}}, first_version),
                ('retire-reservation', second, 'retire_entity', {'entity_id': al.alias_id('repository', 'VELDO-0002')},
                 al.alias_id('repository', 'VELDO-0002')),
                ('opened-before-attach', early['conn'], 'upsert_entity', {'entity_id': counter_id, 'kind': 'artifact_kind',
                                                                          'data': dict(kind_before or {}, next=1)}, counter_id),
                ('unrelated', second, 'upsert_entity', {'entity_id': 'note/2', 'kind': 'note', 'data': {'text': 'ok'}},
                 'note/2')]:
            row = connection.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            try:
                other_store.execute(connection, {'command_id': 'connection-' + label, 'principal': 'anyone',
                    'operation': operation, 'parameters': parameters, 'nonce': 'connection-%s/nonce' % label,
                    'expected_versions': {identity: row[0] if row else 0}, 'artifact_digests': []}, **signing)
                connections[label] = None
            except other_store.StoreRefused as error:
                connections[label] = error.code
        second.close()
        early['conn'].close()
        connections['counter'] = (env.service.current(counter_id)[1] or {}).get('next')
        connections['version-content'] = (env.service.current(first_version)[1] or {}).get('content')
        next_alias, _ = allocate(env, 'connection-3', 'specification', 'connection-3', b'connection 3\n')
        connections['next'] = (next_alias or {}).get('alias')
        defects['connections'] = connections
        expect('aliases/owned-on-every-connection', connections == {
               'rewind-counter': 'entity_owned', 'rewrite-version': 'entity_owned', 'relabel-version': 'entity_owned',
               'retire-reservation': 'entity_owned', 'opened-before-attach': 'entity_owned', 'unrelated': None,
               'counter': 3, 'version-content': 'connection 1\n', 'next': 'VELDO-0003'})
        env.conn.close()

        # 11. Registration order decides nothing. A read set enabled for the store's generic
        # upsert_entity after the allocation authority attached, or before it, cannot move the
        # counter through an accepted snapshot, while an unowned entity still moves; and nobody
        # but accept_snapshot writes a snapshot (VELDO-0035's own kind), which a generic write
        # from a connection with nothing registered could otherwise forge.
        order = {}
        for label in ('readset-after-attach', 'readset-before-attach'):
            readers = {}

            def readset(env):
                readers['reader'], readers['attach'] = attempt(
                    lambda: rs.attach(st, env.conn, env.origins['repository'], 'domain', 'repository'))
                _, readers['enable'] = attempt(lambda: readers['reader'].enable('upsert_entity', {
                    'revision': 'revision/repository', 'entities': {'target': '$entity_id'}, 'collections': {}}))

            env = fresh('order-' + label, before_attach=readset if label == 'readset-before-attach' else None)
            if label == 'readset-after-attach':
                readset(env)
            enable(env, 'specification', 'VELDO', 'specs/{alias}-{slug}.md')
            for index in (1, 2, 3):
                allocate(env, 'order-%d' % index, 'specification', 'order-%d' % index, b'order %d\n' % index)
            counter_id = al.kind_id('repository', 'specification')
            counter_version, kind_now = env.service.current(counter_id)
            outcomes = {'registered': (code(readers.get('attach')), code(readers.get('enable')))}
            for name, identity, entity_kind, data, version in [
                    ('counter', counter_id, 'artifact_kind', dict(kind_now or {}, next=1), counter_version),
                    ('unowned', 'note/order', 'note', {'text': 'moves'}, 0)]:
                arguments = {'entity_id': identity, 'kind': entity_kind, 'data': data}
                snapshot_id = 'snapshot-' + name

                def command(operation, parameters, versions, suffix):
                    return {'command_id': 'order-%s-%s' % (name, suffix), 'principal': 'anyone', 'operation': operation,
                            'parameters': parameters, 'expected_versions': versions, 'artifact_digests': [],
                            'nonce': 'order-%s-%s/nonce' % (name, suffix)}

                _, accepted = attempt(lambda: readers['reader'].execute(command('accept_snapshot', {
                    'snapshot_id': snapshot_id, 'operation': 'upsert_entity', 'arguments': arguments},
                    {snapshot_id: 0}, 'accept'), **signing))
                _, consumed = attempt(lambda: readers['reader'].execute(command('upsert_entity', dict(
                    arguments, snapshot_id=snapshot_id), {snapshot_id: 1, identity: version}, 'consume'), **signing))
                outcomes[name] = (code(accepted), code(consumed))
            plain = st.open_store(env.db)
            _, forged = attempt(lambda: st.execute(plain, {'command_id': 'order-forge', 'principal': 'anyone',
                'operation': 'upsert_entity', 'parameters': {'entity_id': 'snapshot-forged', 'kind': 'control_snapshot',
                'data': {'schema': rs.SN.SCHEMA, 'snapshot_id': 'snapshot-forged', 'operation': 'upsert_entity',
                         'domain_uuid': 'domain', 'repository_uuid': 'repository'}},
                'nonce': 'order-forge/nonce', 'expected_versions': {'snapshot-forged': 0}, 'artifact_digests': []}, **signing))
            plain.close()
            outcomes['forged-snapshot'] = code(forged)
            outcomes['counter-after'] = (env.service.current(counter_id)[1] or {}).get('next')
            order[label] = outcomes
            env.conn.close()
        defects['registration-order'] = order
        expect('aliases/owned-whatever-registration-order', order == {label: {
               'registered': (None, None), 'counter': (None, 'entity_owned'), 'unowned': (None, None),
               'forged-snapshot': 'entity_owned', 'counter-after': 4}
               for label in ('readset-after-attach', 'readset-before-attach')})

        # 12. The first number is above EVERY accepted revision of the repository, not only the
        # one an enabling request names; accepted revisions are written only by accept_revision,
        # never by a generic command on any connection, and an accepted revision never moves back.
        env = fresh('revisions', {'repository': [{}, {'specs/VELDO-0001-held.md': b'# held\n'}]})
        first_commit = g(env.origins['repository'], 'rev-list', '--max-parents=0', 'HEAD')
        revisions = {}
        for label, identity in (('generic-new', 'revision/repository/generic'), ('generic-rewrite', 'revision/repository')):
            row = env.conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            _, error = attempt(lambda: st.execute(env.conn, {'command_id': 'revisions-' + label, 'principal': 'anyone',
                'operation': 'upsert_entity', 'nonce': 'revisions-%s/nonce' % label, 'artifact_digests': [],
                'parameters': {'entity_id': identity, 'kind': 'accepted_revision', 'data': {
                    'domain_uuid': 'domain', 'repository_uuid': 'repository', 'commit': first_commit,
                    'documents': {}, 'statuses': {}}},
                'expected_versions': {identity: row[0] if row else 0}}, **signing))
            revisions[label] = code(error)
        _, regression = attempt(lambda: env.accepting.accept('revision/repository', 'repository', first_commit, 'operator',
                                                             **signing))
        revisions['regression'] = code(regression)
        _, older = attempt(lambda: env.accepting.accept('revision/repository/older', 'repository', first_commit,
                                                        'operator', **signing))
        revisions['older-revision'] = code(older)
        env.revisions['repository'] = 'revision/repository/older'
        for label, first in (('first-1', 1), ('derived', None)):
            _, error = enable(env, 'specification', 'VELDO', 'specs/{alias}-{slug}.md', first=first)
            revisions[label] = code(error)
        allocated, _ = allocate(env, 'after-revisions', 'specification', 'after', b'after revisions\n')
        revisions['allocated'] = (allocated or {}).get('alias')
        defects['revisions'] = revisions
        expect('aliases/floor-from-every-accepted-revision', revisions == {
               'generic-new': 'entity_owned', 'generic-rewrite': 'entity_owned', 'regression': 'revision_regression',
               'older-revision': None, 'first-1': 'below_accepted_history', 'derived': None, 'allocated': 'VELDO-0002'})
        env.conn.close()

        # 13. A checkout is the repository its VELDO-0029 enrollment binding says, never what its
        # root commits suggest. B is A plus a merged unrelated history, so a clone of B checked out
        # before the merge carries exactly A's root commits; it binds as nothing unenrolled, as
        # nothing when its binding no longer matches it or is edited, and as B when enrolled so.
        shared = root / 'shared-root'
        shared.mkdir()
        a_origin, unrelated = shared / 'A-origin', shared / 'X-origin'
        for path, name in ((a_origin, 'README.md'), (unrelated, 'x.txt')):
            path.mkdir()
            g(path, 'init', '-q')
            (path / name).write_bytes(name.encode() + b' starts a history\n')
            g(path, 'add', '-A')
            g(path, 'commit', '-qm', 'Start ' + name)
        b_origin = shared / 'B-origin'
        g(shared, 'clone', '-q', str(a_origin), str(b_origin))
        g(b_origin, 'fetch', '-q', str(unrelated), 'HEAD')
        g(b_origin, 'merge', '-q', '--allow-unrelated-histories', '-m', 'Adopt X', 'FETCH_HEAD')
        env = fresh('enrollment', origins={'A': a_origin, 'B': b_origin})
        for repository in ('A', 'B'):
            enable(env, 'specification', 'VELDO', 'specs/{alias}-{slug}.md', repository=repository)
        allocate(env, 'enrolled-a', 'specification', 'from-a', b'A document\n', repository='A')

        def publisher_for(checkout):
            publisher, error = attempt(lambda: doc.Publisher(env.service, checkout, **bindings))
            return publisher, (publisher.repository if publisher else code(error))

        bound = {}
        pre_merge = checkout_of(env, 'B', 'b-pre-merge', enrolled=False)
        g(pre_merge, 'checkout', '-q', 'HEAD^1')
        _, bound['pre-merge-unenrolled'] = publisher_for(pre_merge)
        moved = checkout_of(env, 'B', 'b-enrolled-then-moved')
        g(moved, 'checkout', '-q', 'HEAD^1')
        _, bound['enrolled-then-moved'] = publisher_for(moved)
        forged = checkout_of(env, 'B', 'b-forged')
        binding_file = _s37_Path(enrollment.binding_path(forged))
        binding_file.write_text(_s37_json.dumps(dict(_s37_json.loads(binding_file.read_text()), repository_uuid='A')))
        _, bound['forged-binding'] = publisher_for(forged)
        elsewhere = checkout_of(env, 'A', 'a-other-store', enrolled=False)
        enroll(elsewhere, 'A', env.base / 'another-store' / 'control.sqlite3')
        _, bound['other-store'] = publisher_for(elsewhere)
        b_old = checkout_of(env, 'B', 'b-old', enrolled=False)
        g(b_old, 'checkout', '-q', 'HEAD^1')
        enroll(b_old, 'B', env.db)
        publisher_b, bound['enrolled-pre-merge'] = publisher_for(b_old)
        _, crossed = publish_by(publisher_b, 'A', 'VELDO-0001')
        bound['publish-A-into-B'] = code(crossed)
        bound['A-file-in-B'] = (b_old / 'specs/VELDO-0001-from-a.md').exists()
        a_checkout = checkout_of(env, 'A')
        publisher_a, bound['A-checkout'] = publisher_for(a_checkout)
        own, _ = publish_by(publisher_a, 'A', 'VELDO-0001')
        bound['publish-A'] = bool(own)
        read_a, _ = read_by(env, 'A', 'VELDO-0001', a_checkout)
        bound['read-A'] = (read_a or {}).get('body')
        _, read_wrong = read_by(env, 'A', 'VELDO-0001', b_old)
        bound['read-A-from-B'] = code(read_wrong)
        defects['enrollment'] = dict(bound, **{'read-A': None if bound['read-A'] is None else bound['read-A'].decode()})
        expect('publication/bound-by-enrollment', bound == {
               'pre-merge-unenrolled': 'wrong_repository', 'enrolled-then-moved': 'wrong_repository',
               'forged-binding': 'wrong_repository', 'other-store': 'wrong_repository', 'enrolled-pre-merge': 'B',
               'publish-A-into-B': 'wrong_repository', 'A-file-in-B': False, 'A-checkout': 'A', 'publish-A': True,
               'read-A': b'A document\n', 'read-A-from-B': 'wrong_repository'})
        env.conn.close()

        # 14. An accepted revision names a commit the store's bound repository holds at acceptance
        # time. The first attach binds each repository uuid to its accepted repository in the store;
        # a revision service attached to another repository (an unrelated one, or a clone holding
        # an unpushed commit) is refused by name, and accept_revision registered straight from a
        # Revisions object refuses a commit the bound repository lacks. The floor counts only
        # revisions whose commit the bound repository holds, so a revision it could never have
        # accepted (written around every command, by raw SQL) cannot make enabling refuse.
        env = fresh('enrolled', {'repository': [{'specs/VELDO-0002-held.md': b'# held\n'}]})
        bound_origin = env.origins['repository']
        foreign = env.base / 'unrelated-origin'
        foreign.mkdir()
        g(foreign, 'init', '-q')
        (foreign / 'specs').mkdir()
        (foreign / 'specs/VELDO-0040-foreign.md').write_bytes(b'# not in the bound repository\n')
        g(foreign, 'add', '-A')
        g(foreign, 'commit', '-qm', 'Unrelated history')
        foreign_commit = g(foreign, 'rev-parse', 'HEAD')
        clone = env.base / 'working-clone'
        g(env.base, 'clone', '-q', str(bound_origin), str(clone))
        (clone / 'specs/VELDO-0007-clone.md').write_bytes(b'# pushed later\n')
        g(clone, 'add', '-A')
        g(clone, 'commit', '-qm', 'Local, unpushed')
        clone_commit = g(clone, 'rev-parse', 'HEAD')
        enrolled = {}
        handles = []

        def accept_through(label, repository_path, commit, direct):
            connection = st.open_store(env.db)
            handles.append(connection)
            if direct:
                # accept_revision's own code, registered without attach_revisions.
                accepting = rs.Revisions(st, connection, 'domain', {'repository': str(repository_path)})
                connection.command_registry['accept_revision'] = {
                    'transaction_transition': accepting.transition, 'writes': ('entities', 'journal', 'commands', 'nonces')}
            else:
                accepting, error = attempt(lambda: rs.attach_revisions(st, connection, 'domain',
                                                                       {'repository': str(repository_path)}))
                if error is not None:
                    enrolled[label] = code(error)
                    return
            _, error = attempt(lambda: accepting.accept('revision/' + label, 'repository', commit, 'operator', **signing))
            enrolled[label] = code(error)

        accept_through('foreign-attach', foreign, foreign_commit, direct=False)
        accept_through('foreign-direct', foreign, foreign_commit, direct=True)
        accept_through('clone-attach', clone, clone_commit, direct=False)
        accept_through('clone-unpushed', clone, clone_commit, direct=True)
        g(bound_origin, 'fetch', '-q', str(clone), 'HEAD:refs/heads/accepted-next')
        _, error = attempt(lambda: env.accepting.accept('revision/clone-pushed', 'repository', clone_commit, 'operator',
                                                        **signing))
        enrolled['clone-after-push'] = code(error)
        _, error = enable(env, 'specification', 'VELDO', 'specs/{alias}-{slug}.md', first=None)
        enrolled['enable-after'] = code(error)
        allocated, _ = allocate(env, 'enrolled-first', 'specification', 'first', b'first after the floor\n')
        enrolled['allocated'] = (allocated or {}).get('alias')
        # A revision no command could have accepted, written around execute.
        env.conn.execute('INSERT INTO entities (id, kind, version, digest, data) VALUES (?,?,?,?,?)', (
            'revision/raw', 'accepted_revision', 1, 'sha256:' + '0' * 64, _s37_json.dumps({
                'domain_uuid': 'domain', 'repository_uuid': 'repository', 'commit': foreign_commit,
                'documents': {}, 'statuses': {}}, sort_keys=True)))
        _, error = enable(env, 'plan', 'PLAN', 'plans/{alias}-{slug}.md', first=None)
        enrolled['enable-beside-raw'] = code(error)
        plan = env.service.current(al.kind_id('repository', 'plan'))[1] or {}
        enrolled['plan-floor-commits'] = foreign_commit not in plan.get('floor_commits', [foreign_commit]) \
            and clone_commit in plan.get('floor_commits', [])
        # The allocation side: its own attach to another repository is refused by name, and
        # Allocations registered without attach reads no repository but the bound one.
        elsewhere = st.open_store(env.db)
        handles.append(elsewhere)
        _, error = attempt(lambda: al.attach(st, elsewhere, 'domain', {'repository': str(clone)}))
        enrolled['allocation-attach-elsewhere'] = code(error)
        direct = st.open_store(env.db)
        handles.append(direct)
        allocations, error = attempt(lambda: al.Allocations(st, direct, 'domain', {'repository': str(clone)}))
        if allocations is not None:
            direct.command_registry['enable_artifact_kind'] = {
                'transaction_transition': allocations._transition(allocations._t_enable),
                'writes': ('entities', 'journal', 'commands', 'nonces')}
            serial[0] += 1
            _, error = attempt(lambda: allocations.enable_kind({'request_id': 'enable-%d' % serial[0], 'principal': 'operator',
                'repository_uuid': 'repository', 'kind': 'decision', 'prefix': 'DEC', 'width': 4,
                'path_template': 'decisions/{alias}-{slug}.md', 'revision_id': 'revision/repository'}, **signing))
        enrolled['allocation-direct-elsewhere'] = code(error)
        for handle in handles:
            handle.close()
        defects['enrolled-repository'] = enrolled
        expect('aliases/revision-in-enrolled-repository', enrolled == {
               'foreign-attach': 'repository_binding_conflict', 'foreign-direct': 'unenrolled_commit',
               'clone-attach': 'repository_binding_conflict', 'clone-unpushed': 'unenrolled_commit',
               'clone-after-push': None, 'enable-after': None, 'allocated': 'VELDO-0008', 'enable-beside-raw': None,
               'plan-floor-commits': True, 'allocation-attach-elsewhere': 'repository_binding_conflict',
               'allocation-direct-elsewhere': 'wrong_repository'})
        env.conn.close()
    observations['elapsed_seconds'] = _s37_time.monotonic() - started
    return observations


_s37_observations = _s37_run()
