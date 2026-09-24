"""VELDO-0134: the architecture record's one writer, its schema, and the reader held to it.

Only shared ROOT and expect are consumed. The installed .veldo is a temporary copy of the engine with
the production anchors below, so a registered mutation of a production module reaches the writer, the
store and the Gate that load it. One real Git repository holds a commit per contract state (LF, CRLF
line endings, no final newline, a byte order mark, a weakened contract, every refused contract kind); a
second repository is a decoy the environment points at. Real SQLite stores, one per region, seeded
with membership and keys; every accept command is signed with a real OpenSSH key through
`ssh-keygen -Y sign` and applied through the authority's command path. The writer and the Gate are
each judged against the schema table read from the specification's Notes and against the operating
system's sha256sum over the blob Git returns, never against each other. Rows red by assertion: every
region reds its own rows on a raise and a `ran/` row says whether it did.
"""


def _v134_suite():
    import contextlib
    import hashlib
    import hmac
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import stat
    import subprocess
    import tempfile

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_architecture.py': ROOT / ".veldo" / "control_architecture.py",
        'control_store.py': ROOT / ".veldo" / "control_store.py",
        'control_eligibility.py': ROOT / ".veldo" / "control_eligibility.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    emitted, raised, regions = set(), [], []
    observed = {}

    def check(label, condition):
        emitted.add(label)
        expect('VELDO-0134 ' + label, condition)

    @contextlib.contextmanager
    def region(*labels):
        regions.append(labels[0])
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            raised.append((labels[0], repr(error)))
            for label in labels:
                if label not in emitted:
                    check(label, False)

    # The schema table, read from the specification's Notes: the oracle's fields and named invalid forms.
    spec_text = next((ROOT / 'specs').glob('VELDO-0134-*.md')).read_text()
    notes = spec_text.split('\n## Notes\n', 1)[1].split('\n## ', 1)[0]
    SCHEMA_NAME = re.search(r'The record schema, `([^`]+)`', notes).group(1)
    TABLE = {}
    for line in notes.splitlines():
        if line.startswith('| `'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            TABLE[cells[0].strip('`')] = [f.strip() for f in cells[2].split(',') if f.strip()]
    CONTRACT_PATH = '.veldo/architecture.yaml'
    OUTSIDE = ['sha256sum'] if shutil.which('sha256sum') else ['shasum', '-a', '256']

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v134-', dir=fast) as directory:
        top = Path(directory)
        mods = top / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if source.exists():
                shutil.copyfile(source, mods / name)
        GP = load('v134_git', mods / 'git_process.py')
        S = load('v134_store', mods / 'control_store.py')
        CM = load('v134_membership', mods / 'control_membership.py')
        AC = CM.AC
        CL = load('v134_loader', mods / 'contract_loader.py')
        EL = load('v134_eligibility', mods / 'control_eligibility.py')
        AR = load('v134_architecture', mods / 'control_architecture.py') if (mods / 'control_architecture.py').exists() else None
        _git_process = GP
        OP = getattr(S, 'ARCHITECTURE_OPERATION', 'accept_architecture')
        WRITES = ('entities', 'journal', 'commands', 'nonces')
        DOMAIN, REPO, STORE = 'domain-134', 'repository-134', 'store-134'
        IDS = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid=STORE)
        AID = 'architecture:' + REPO
        IDENTITY = ('Fixture', 'fixture@example.invalid')

        def git(repo, *args, **kwargs):
            return _git_process.run(['git', '-C', str(repo)] + list(args), capture_output=True, **kwargs)

        # The contracts, one commit each, in one real repository.
        VALID = ('schema: veldo.arch/v1\nid: ARCH-9134\ntitle: Fixture architecture\nstatus: draft\nversion: 1\n'
                 'areas:\n  - id: floor\n    title: Floor\n    includes: ["src/**", "specs/**"]\n')
        WEAKENED = VALID.replace('version: 1\n', 'version: 2\n') + '  - id: anything\n    title: Anything\n    includes: ["**"]\n'
        CONTRACTS = {
            'lf': VALID.encode(),
            'crlf': VALID.replace('\n', '\r\n').encode(),
            'nofinal': VALID.rstrip('\n').encode(),
            'bom': b'\xef\xbb\xbf' + VALID.encode(),
            'weakened': WEAKENED.encode(),
            'wrong_fields': b'schema: veldo.arch/v1\nid: ARCH-9134\ntitle: Fixture\nstatus: draft\nversion: one\nareas: none\n',
            'list': b'- floor\n- fleet\n',
            'outside': b'schema: veldo.arch/v1\nareas: [unclosed\n',
            'tree': None, 'symlink': None, 'absent': None,
        }
        repo = top / 'repo'
        (repo / '.veldo').mkdir(parents=True)
        git(repo, 'init', '-q', check=True)
        C = {}
        target = repo / '.veldo' / 'architecture.yaml'
        for name, body in CONTRACTS.items():
            if os.path.lexists(str(target)):
                if os.path.isdir(str(target)) and not os.path.islink(str(target)):
                    shutil.rmtree(str(target))
                else:
                    os.unlink(str(target))
            if body is not None:
                target.write_bytes(body)
            elif name == 'tree':
                target.mkdir()
                (target / 'inside.yaml').write_bytes(CONTRACTS['lf'])
            elif name == 'symlink':
                os.symlink('elsewhere.yaml', str(target))
            (repo / 'state.txt').write_text(name + '\n')
            git(repo, 'add', '-A', check=True)
            git(repo, 'commit', '-q', '-m', 'contract ' + name, check=True, identity=IDENTITY)
            C[name] = git(repo, 'rev-parse', 'HEAD', check=True).stdout.decode().strip()
        decoy = top / 'decoy'
        (decoy / '.veldo').mkdir(parents=True)
        git(decoy, 'init', '-q', check=True)
        (decoy / '.veldo' / 'architecture.yaml').write_bytes(WEAKENED.replace('Fixture', 'Decoy').encode())
        git(decoy, 'add', '-A', check=True)
        git(decoy, 'commit', '-q', '-m', 'decoy', check=True, identity=IDENTITY)
        C['decoy'] = git(decoy, 'rev-parse', 'HEAD', check=True).stdout.decode().strip()

        def blob(commit, where=repo):
            got = git(where, 'cat-file', 'blob', '%s:%s' % (commit, CONTRACT_PATH))
            return got.stdout if got.returncode == 0 else None

        def outside(body):
            # The digest from an implementation outside Veldo, over the bytes Git returned.
            out = subprocess.run(OUTSIDE, input=body, capture_output=True, check=True).stdout.split()[0].decode()
            return 'sha256:' + out

        B = {name: blob(commit) for name, commit in C.items() if name != 'decoy'}
        B['decoy'] = blob(C['decoy'], decoy)
        D = {name: outside(body) for name, body in B.items() if body is not None}

        # Keys: one OpenSSH key per principal, made on first use.
        keys = top / 'keys'
        keys.mkdir()
        public = {}

        def key(who):
            if who not in public:
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v134-' + who, '-f', str(keys / who)],
                               check=True, capture_output=True, timeout=30)
                public[who] = (keys / (who + '.pub')).read_text().strip()
            return public[who]

        def sign_as(who, message):
            key(who)
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / who), '-n', AC.SIGNATURE_NAMESPACE],
                                  input=message, capture_output=True, check=True, timeout=30).stdout.decode()

        journal_key = os.urandom(32)

        def journal_sign(message):
            return hmac.new(journal_key, message, hashlib.sha256).hexdigest()

        serial = [0]

        def execute(conn, operation, parameters, expected, principal='authority'):
            serial[0] += 1
            return S.execute(conn, dict(command_id='fixture-%d' % serial[0], principal=principal, operation=operation,
                                        parameters=parameters, expected_versions=expected, artifact_digests=[],
                                        nonce='fixture-n-%d' % serial[0]), 'authority', journal_sign, 1)

        def version(conn, eid):
            row = conn.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
            return row[0] if row else 0

        OWNER = dict(principal_type='person', roles=['project_owner'], scope=[REPO])
        ws = top / 'workspace'
        (ws / '.veldo').mkdir(parents=True)
        worlds = []

        class World:
            pass

        def world(tag, members):
            w = World()
            db = top / 'stores' / tag / 'control.sqlite3'
            w.conn = S.open_store(str(db))
            for who, spec in members.items():
                spec = dict(spec)
                revoked = spec.pop('key_revoked', False)
                execute(w.conn, 'upsert_entity', dict(entity_id=who, kind='membership',
                                                      data=dict(spec, revoked_at=None, expires_at=None)), {who: 0})
                execute(w.conn, 'upsert_entity', dict(entity_id='key-' + who, kind='verification_key',
                                                      data=dict(principal=who, public_key=key(who), effective_at=0,
                                                                revoked_at=1 if revoked else None)), {'key-' + who: 0})
            w.authority = (AR.ArchitectureAuthority(S, CM, w.conn, IDS, str(repo), 'authority', journal_sign)
                           if AR is not None else None)
            # The suite's own connection, with the suite's own writer of records in any shape registered
            # under the one operation the store lets write the record.
            w.suite = S.open_store(str(db))
            w.suite.command_registry[OP] = {
                'transition': lambda params, before: {params['entity_id']: {'kind': params['kind'], 'data': params['data']}},
                'writes': WRITES}
            w.reader = S.open_store(str(db), mode='r')
            w.gate = EL.Gate(S, w.reader, domain_uuid=DOMAIN, repository_uuid=REPO, workspace=str(ws))
            worlds.append(w)
            return w

        def suite_write(w, eid, kind, data):
            return execute(w.suite, OP, dict(entity_id=eid, kind=kind, data=data), {eid: version(w.suite, eid)}, 'suite')

        def frozen(w):
            row = w.conn.execute('SELECT version, digest, data FROM entities WHERE id=?', (AID,)).fetchone()
            count = w.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
            head = w.conn.execute('SELECT record_digest FROM journal ORDER BY seq DESC LIMIT 1').fetchone()
            nonces = tuple(r[0] for r in w.conn.execute('SELECT nonce FROM nonces ORDER BY nonce'))
            return (tuple(row) if row else None, count, head[0] if head else None, nonces)

        def record(w):
            row = w.conn.execute('SELECT data FROM entities WHERE id=?', (AID,)).fetchone()
            return json.loads(row[0]) if row else None

        def current_version(w):
            rec = record(w)
            return rec.get('contract_version', 0) if isinstance(rec, dict) else 0

        counter = [0]

        def command(who='owner', name='lf', replaces=0, **over):
            counter[0] += 1
            c = dict(IDS, operation='accept', principal=who, command_id='accept-%d' % counter[0],
                     nonce='nonce-%d' % counter[0], commit=C.get(name, name), digest=D.get(name, D['lf']),
                     replaces=replaces)
            c.update(over)
            return c

        def packet(cmd, signer=None):
            return {'command': cmd, 'signature': sign_as(signer or cmd['principal'], S.canonical_bytes(cmd))}

        def drive(w, pkt):
            if w.authority is None:
                return {'ok': False, 'reason': 'no_writer'}
            return w.authority.apply(pkt)

        def refused_unchanged(w, pkt, reason):
            before = frozen(w)
            got = drive(w, pkt)
            return got.get('ok') is False and got.get('reason') == reason and frozen(w) == before, got.get('reason')

        def judge(w, body, policy='optional'):
            contract, flag = ws / '.veldo' / 'architecture.yaml', ws / '.veldo' / 'policy.yaml'
            for p_ in (contract, flag):
                if os.path.lexists(str(p_)):
                    if os.path.isdir(str(p_)) and not os.path.islink(str(p_)):
                        shutil.rmtree(str(p_))
                    else:
                        os.unlink(str(p_))
            if policy is not None:
                flag.write_text('architecture_contract: %s\n' % policy)
            if body is not None:
                contract.write_bytes(body)
            return w.gate.architecture(EL.SN.entity(S, w.reader, AID))

        def gate_says(found, refusals, basis='accepted'):
            return found.get('basis') == basis and found.get('refusals') == refusals

        def entry(version_, name, cmd):
            return dict(contract_version=version_, digest=D[name], source=dict(commit=C[name], path=CONTRACT_PATH),
                        accepted_by=cmd['principal'], command_id=cmd['command_id'])

        def writer_problems(rec, history):
            """The written record against the schema table and the outside digest: `history` is the
            accepted (contract name, command) of every version, oldest first."""
            if not isinstance(rec, dict) or not history:
                return ['no record']
            n = len(history)
            name, cmd = history[-1]
            wanted = dict(schema=SCHEMA_NAME, repository_uuid=REPO, state='accepted', contract_version=n,
                          digest=outside(blob(C[name])), source=dict(commit=C[name], path=CONTRACT_PATH),
                          accepted_by=cmd['principal'], command_id=cmd['command_id'],
                          superseded=[entry(i + 1, *history[i]) for i in range(n - 1)])
            problems = [] if set(wanted) == set(TABLE) else ['the oracle does not cover the table']
            problems += ['fields %s' % sorted(set(rec) ^ set(TABLE))] if set(rec) != set(TABLE) else []
            for field, value in wanted.items():
                if json.dumps(rec.get(field), sort_keys=True) != json.dumps(value, sort_keys=True) \
                        or type(rec.get(field)) is not type(value):
                    problems.append(field)
            return problems

        # -- AC1: the first acceptance ------------------------------------------------------------
        with region('acceptance/first'):
            w = world('first', {'owner': OWNER})
            before = frozen(w)
            # The owner's front door (`veldo architecture accept`) names an abbreviated commit, computes the
            # digest of the blob there and signs the command with his key.
            front, code = {}, None
            if AR is not None:
                printed = io.StringIO()
                with contextlib.redirect_stdout(printed):
                    code = AR.main(['accept', '--repo', str(repo), '--commit', C['lf'][:12], '--principal', 'owner',
                                    '--key', str(keys / 'owner'), '--domain-uuid', DOMAIN, '--repository-uuid', REPO,
                                    '--store-uuid', STORE])
                front = json.loads(printed.getvalue()) if code == 0 else {}
            cmd = front.get('command') or command()
            got = drive(w, front if front.get('command') else packet(cmd))
            after = frozen(w)
            first = dict(front_door=code, result=got.get('reason'), problems=writer_problems(record(w), [('lf', cmd)]))
            ok = cmd.get('digest') == D['lf'] and cmd.get('commit') == C['lf'] and cmd.get('replaces') == 0
            ok &= got.get('ok') is True and not first['problems']
            ok &= after[1] == before[1] + 1 and cmd['nonce'] in after[3] and cmd['nonce'] not in before[3]
            present = judge(w, B['lf'])
            absent = judge(w, None)
            first['gate'] = [present.get('refusals'), absent.get('refusals'), absent.get('required')]
            ok &= gate_says(present, []) and gate_says(absent, ['missing_evidence:architecture/required_absence'])
            observed['first'] = first
            check('acceptance/first', ok)

        # -- AC1: who may sign, derived from authority_contract ------------------------------------
        with region('acceptance/signers'):
            TYPE_ACCEPTS = {'person': True, 'service': False, 'policy': False, 'agent_run': False}
            ROLE_ACCEPTS = {'membership_steward': False, 'project_owner': True, 'admission_authority': False,
                            'priority_authority': False, 'technical_authority': False, 'security_authority': False,
                            'operations_authority': False}
            ok = set(TYPE_ACCEPTS) == set(AC.PRINCIPAL_TYPES) and set(ROLE_ACCEPTS) == set(AC.ROLES)
            cases = [('type-' + t, dict(principal_type=t, roles=['project_owner'], scope=[REPO]), TYPE_ACCEPTS.get(t),
                      'not_authorized:principal_type') for t in AC.PRINCIPAL_TYPES]
            cases += [('role-' + r, dict(principal_type='person', roles=[r], scope=[REPO]), ROLE_ACCEPTS.get(r),
                       'not_authorized:role') for r in AC.ROLES]
            cases += [('no-role', dict(principal_type='person', roles=[], scope=[REPO]), False, 'not_authorized:role'),
                      ('universal', dict(principal_type='person', roles=['project_owner'], scope='*'), True, None),
                      ('scope-other', dict(principal_type='person', roles=['project_owner'], scope=['repository-other']),
                       False, 'not_authorized:scope'),
                      ('scope-domain', dict(principal_type='person', roles=['project_owner'], scope=[DOMAIN]), False,
                       'not_authorized:scope')]
            outcomes = {}
            for who, member, accepts, refusal in cases:
                if accepts is None:
                    ok = False
                    outcomes[who] = 'no expected outcome'
                    continue
                w = world('signer-' + who, {who: member})
                before = frozen(w)
                got = drive(w, packet(command(who)))
                outcomes[who] = got.get('reason')
                if accepts:
                    ok &= got.get('ok') is True and frozen(w) != before
                else:
                    ok &= got.get('ok') is False and got.get('reason') == refusal and frozen(w) == before
            observed['signers'] = outcomes
            check('acceptance/signers', ok)

        # -- AC1: the signature and the key --------------------------------------------------------
        with region('acceptance/signature'):
            w = world('signature', {'owner': OWNER, 'revoked': dict(OWNER, key_revoked=True)})
            key('stranger')
            tampered = packet(command())
            tampered['command'] = dict(tampered['command'], digest=D['weakened'], commit=C['weakened'])
            forms = {'another key': (packet(command(), signer='stranger'), 'not_authorized:signature'),
                     'changed after signing': (tampered, 'not_authorized:signature'),
                     'revoked key': (packet(command('revoked')), 'not_authorized:key')}
            outcomes = {name: refused_unchanged(w, pkt, reason) for name, (pkt, reason) in forms.items()}
            ok = all(v[0] for v in outcomes.values())
            ok &= drive(w, packet(command())).get('ok') is True
            observed['signature'] = {k: v[1] for k, v in outcomes.items()}
            check('acceptance/signature', ok)

        # -- AC1: the digest and the commit --------------------------------------------------------
        with region('acceptance/evidence'):
            w = world('evidence', {'owner': OWNER})
            tree_id = git(repo, 'rev-parse', C['lf'] + '^{tree}', check=True).stdout.decode().strip()
            forms = {'digest of other bytes': (command(digest=D['weakened']), 'invalid_input:digest_mismatch'),
                     'commit that does not exist': (command(commit='0123456789abcdef' * 2 + '01234567'), 'missing_evidence:commit'),
                     'a tree, not a commit': (command(commit=tree_id), 'missing_evidence:commit'),
                     'abbreviated commit': (command(commit=C['lf'][:12]), 'invalid_input:commit'),
                     'uppercase commit': (command(commit=C['lf'].upper()), 'invalid_input:commit'),
                     'commit with no contract': (command(commit=C['absent']), 'missing_evidence:contract')}
            outcomes = {name: refused_unchanged(w, packet(cmd), reason) for name, (cmd, reason) in forms.items()}
            ok = all(v[0] for v in outcomes.values())
            ok &= drive(w, packet(command())).get('ok') is True
            observed['evidence'] = {k: v[1] for k, v in outcomes.items()}
            check('acceptance/evidence', ok)

        # -- AC1: one row per refused contract kind of contract_loader ------------------------------
        with region('acceptance/contract-kinds'):
            KIND_COMMITS = {'required_absence': ['absent'], 'unreadable': ['tree', 'symlink'],
                            'parse_failure': ['list', 'outside'], 'invalid_structure': ['wrong_fields']}
            KIND_REFUSAL = {'required_absence': 'missing_evidence:contract', 'unreadable': 'invalid_contract:unreadable',
                            'parse_failure': 'invalid_contract:parse_failure',
                            'invalid_structure': 'invalid_contract:invalid_structure'}
            # Not refused, with the reason: the acceptance itself, and absence, which the writer judges required.
            NOT_REFUSED = {'valid': 'acceptance/first', 'optional_absence': 'the writer requires the contract'}
            ok = set(CL.CONTRACT_KINDS) == set(KIND_COMMITS) | set(NOT_REFUSED) and set(KIND_COMMITS) == set(KIND_REFUSAL)
            w = world('kinds', {'owner': OWNER})
            outcomes = {}
            for kind in CL.CONTRACT_KINDS:
                if kind in NOT_REFUSED:
                    continue
                for name in KIND_COMMITS.get(kind, []):
                    outcomes[name] = refused_unchanged(w, packet(command(name=name)), KIND_REFUSAL.get(kind))
                ok &= bool(KIND_COMMITS.get(kind))
            ok &= bool(outcomes) and all(v[0] for v in outcomes.values())
            ok &= drive(w, packet(command())).get('ok') is True
            observed['contract_kinds'] = {k: v[1] for k, v in outcomes.items()}
            check('acceptance/contract-kinds', ok)

        # -- AC1: a consumed nonce and other coordinates -------------------------------------------
        with region('acceptance/replay-and-coordinates'):
            w = world('replay', {'owner': OWNER})
            first_cmd = command()
            ok = drive(w, packet(first_cmd)).get('ok') is True
            forms = {'consumed nonce': (command(name='weakened', replaces=1, nonce=first_cmd['nonce']), 'nonce_consumed'),
                     'another domain': (command(name='weakened', replaces=1, domain_uuid='domain-other'), 'invalid_input:coordinates'),
                     'another repository': (command(name='weakened', replaces=1, repository_uuid='repository-other'),
                                            'invalid_input:coordinates'),
                     'another store': (command(name='weakened', replaces=1, store_uuid='store-other'), 'invalid_input:coordinates')}
            outcomes = {name: refused_unchanged(w, packet(cmd), reason) for name, (cmd, reason) in forms.items()}
            ok &= all(v[0] for v in outcomes.values())
            ok &= drive(w, packet(command(name='weakened', replaces=1))).get('ok') is True
            observed['replay'] = {k: v[1] for k, v in outcomes.items()}
            check('acceptance/replay-and-coordinates', ok)

        # -- AC2: the reader against the schema table ---------------------------------------------
        with region('acceptance/schema-oracle'):
            w = world('oracle', {'owner': OWNER})
            history = [('lf', command()), ('weakened', command()), ('crlf', command())]

            def oracle_record(n):
                name, cmd = history[n - 1]
                return dict(schema=SCHEMA_NAME, repository_uuid=REPO, state='accepted', **entry(n, name, cmd),
                            superseded=[entry(i + 1, *history[i]) for i in range(n - 1)])

            def drop(field):
                return lambda d: {k: v for k, v in d.items() if k != field}

            def put(field, value):
                return lambda d: dict(d, **{field: value})

            def entries(fn):
                return lambda d: dict(d, superseded=fn([dict(e) for e in d['superseded']]))

            def source(**change):
                return lambda d: dict(d, source=dict(d['source'], **change))

            hexdigest = D['crlf'][len('sha256:'):]
            # Each named invalid form of the table: (base contract_version, record change) variants.
            FORMS = {
                'schema': {'missing': [(3, drop('schema'))], 'another string': [(3, put('schema', SCHEMA_NAME + 'x'))],
                           'not a string': [(3, put('schema', 1))]},
                'repository_uuid': {'missing': [(3, drop('repository_uuid'))],
                                    'not matching the id': [(3, put('repository_uuid', 'repository-other'))],
                                    'not a string': [(3, put('repository_uuid', 134))]},
                'state': {'missing': [(3, drop('state'))],
                          'any other value': [(3, put('state', 'withdrawn')), (3, put('state', 'ACCEPTED')), (3, put('state', None))]},
                'contract_version': {'missing': [(1, drop('contract_version'))], 'zero': [(1, put('contract_version', 0))],
                                     'negative': [(1, put('contract_version', -1))],
                                     'a boolean': [(1, put('contract_version', True))],
                                     'not an integer': [(1, put('contract_version', 1.0)), (1, put('contract_version', '1'))]},
                'digest': {'missing': [(3, drop('digest'))], 'no prefix': [(3, put('digest', hexdigest))],
                           'another prefix': [(3, put('digest', 'sha512:' + hexdigest)), (3, put('digest', 'md5:' + hexdigest))],
                           'uppercase hex': [(3, put('digest', 'sha256:' + hexdigest.upper()))],
                           'wrong length': [(3, put('digest', 'sha256:' + hexdigest[:-1])), (3, put('digest', D['crlf'] + '0'))],
                           'not a string': [(3, put('digest', None))]},
                'source': {'missing': [(3, drop('source'))],
                           'an abbreviated or uppercase commit': [(3, source(commit=C['crlf'][:12])),
                                                                  (3, source(commit=C['crlf'].upper()))],
                           'another path': [(3, source(path='architecture.yaml')), (3, source(path='.veldo/architecture.yml'))],
                           'an extra key': [(3, source(branch='main'))]},
                'accepted_by': {'missing': [(3, drop('accepted_by'))], 'not a string': [(3, put('accepted_by', None)),
                                                                                         (3, put('accepted_by', 7))]},
                'command_id': {'missing': [(3, drop('command_id'))], 'not a string': [(3, put('command_id', None)),
                                                                                       (3, put('command_id', 7))]},
                'superseded': {'missing': [(3, drop('superseded'))],
                               'out of order': [(3, entries(lambda es: es[::-1]))],
                               'a gap': [(3, entries(lambda es: [es[0], dict(es[1], contract_version=3)])),
                                         (3, entries(lambda es: es[1:]))],
                               'an entry with a changed or extra field': [
                                   (3, entries(lambda es: [dict({('acceptedBy' if k == 'accepted_by' else k): v
                                                                 for k, v in es[0].items()}), es[1]])),
                                   (3, entries(lambda es: [dict(es[0], digest=es[0]['digest'].upper()), es[1]])),
                                   (3, entries(lambda es: [dict(es[0], note='extra'), es[1]]))]},
            }
            # Record-level forms the table's preamble names: the closed mapping and the entity kind.
            ENTITY_FORMS = {'unknown extra field': [(3, put('accepted_at', 1790000000))]}
            KIND_FORMS = ['architecture_record', 'architecture']
            ok = set(FORMS) == set(TABLE) and all(set(FORMS.get(f, {})) == set(forms) for f, forms in TABLE.items())
            ok &= all(variants for field in FORMS.values() for variants in field.values())
            judged = {}
            for n in (1, 3):
                suite_write(w, AID, 'architecture_contract', oracle_record(n))
                found = judge(w, B[history[n - 1][0]])
                judged['valid v%d' % n] = found.get('refusals')
                ok &= gate_says(found, [])
            cases = [('%s: %s #%d' % (field, form, i), n, fn, 'architecture_contract')
                     for field, forms in FORMS.items() for form, variants in forms.items() for i, (n, fn) in enumerate(variants)]
            cases += [('record: %s #%d' % (form, i), n, fn, 'architecture_contract')
                      for form, variants in ENTITY_FORMS.items() for i, (n, fn) in enumerate(variants)]
            cases += [('entity kind: %s' % kind, 3, lambda d: d, kind) for kind in KIND_FORMS]
            for label, n, fn, kind in cases:
                suite_write(w, AID, kind, fn(oracle_record(n)))
                found = judge(w, B[history[n - 1][0]])
                judged[label] = found.get('refusals')
                ok &= found.get('refusals') == ['missing_authority:architecture']
            observed['schema_oracle'] = dict(fields=sorted(TABLE), judged=judged)
            check('acceptance/schema-oracle', ok)

        # -- AC2: the writer against the schema and the outside digest, and the round trip ----------
        with region('acceptance/writer-schema', 'acceptance/raw-digest-crlf', 'acceptance/raw-digest-no-final-newline',
                    'acceptance/raw-digest-bom'):
            w = world('writer', {'owner': OWNER})
            accepted, rows, problems = [], {}, {}
            for name in ('crlf', 'nofinal', 'bom'):
                cmd = command(name=name, replaces=current_version(w))
                got = drive(w, packet(cmd))
                if got.get('ok') is True:
                    accepted.append((name, cmd))
                rec = record(w)
                problems[name] = writer_problems(rec, accepted) if got.get('ok') is True else [got.get('reason')]
                trip = judge(w, blob(C[name]))
                rows[name] = (got.get('ok') is True and isinstance(rec, dict) and rec.get('digest') == outside(blob(C[name]))
                              and not problems[name] and gate_says(trip, []))
            observed['writer'] = dict(problems=problems, rows=rows)
            check('acceptance/writer-schema', len(accepted) == 3 and not any(problems.values()))
            check('acceptance/raw-digest-crlf', rows['crlf'])
            check('acceptance/raw-digest-no-final-newline', rows['nofinal'])
            check('acceptance/raw-digest-bom', rows['bom'])

        # -- AC3: replacement is a new version -----------------------------------------------------
        with region('acceptance/version-history', 'acceptance/replacement-refusals', 'acceptance/previous-bytes'):
            w = world('history', {'owner': OWNER})
            steps = ('lf', 'weakened', 'crlf')
            accepted, captured = [], []
            history_ok = refusals_ok = previous_ok = True
            detail = []
            for step, name in enumerate(steps, 1):
                before = frozen(w)
                cmd = command(name=name, replaces=current_version(w))
                got = drive(w, packet(cmd))
                accepted.append((name, cmd))
                rec = record(w)
                after = frozen(w)
                history_ok &= got.get('ok') is True and isinstance(rec, dict) and rec.get('contract_version') == step
                history_ok &= after[1] == before[1] + 1 and not writer_problems(rec, accepted)
                superseded = rec.get('superseded') if isinstance(rec, dict) else None
                history_ok &= isinstance(superseded, list) and len(superseded) == step - 1 and all(
                    json.dumps(superseded[i], sort_keys=True) == captured[i] for i in range(min(len(captured), len(superseded))))
                if isinstance(rec, dict) and all(f in rec for f in ('contract_version', 'digest', 'source', 'accepted_by', 'command_id')):
                    captured.append(json.dumps({f: rec[f] for f in ('contract_version', 'digest', 'source', 'accepted_by',
                                                                    'command_id')}, sort_keys=True))
                journal = S.export_journal(w.conn)
                wrote = [r['command_id'] for r in journal if AID in r['transition']]
                history_ok &= wrote == [c['command_id'] for _, c in accepted]
                # The refused forms against this current version.
                now = current_version(w)
                forms = {'a replaced version that is not current': (command(name='nofinal', replaces=now - 1 if now > 1 else now + 1),
                                                                   'stale_subject'),
                         'none when a record exists': (command(name='nofinal', replaces=0), 'stale_subject'),
                         'the digest already current': (command(name=name, replaces=now), 'invalid_input:current_digest'),
                         'a changed retry': (dict(cmd, nonce=cmd['nonce'] + '-changed'), 'command_content_conflict')}
                outcomes = {k: refused_unchanged(w, packet(c), reason) for k, (c, reason) in forms.items()}
                refusals_ok &= all(v[0] for v in outcomes.values())
                replay_before = frozen(w)
                replay = drive(w, packet(cmd))
                refusals_ok &= replay.get('ok') is True and replay.get('reason') == 'replayed' and frozen(w) == replay_before
                for earlier, _ in accepted[:-1]:
                    previous_ok &= gate_says(judge(w, B[earlier]), ['missing_authority:architecture/unaccepted_artifact'])
                previous_ok &= gate_says(judge(w, B[name]), [])
                detail.append(dict(step=step, result=got.get('reason'), refused={k: v[1] for k, v in outcomes.items()},
                                   replay=replay.get('reason')))
            observed['history'] = detail
            check('acceptance/version-history', history_ok)
            check('acceptance/replacement-refusals', refusals_ok)
            check('acceptance/previous-bytes', previous_ok)

        # -- AC4: no other store operation writes the record ---------------------------------------
        with region('acceptance/generic-write'):
            w = world('generic', {'owner': OWNER})
            ok = drive(w, packet(command())).get('ok') is True
            # An operation registered at run time by some later service, writing whatever it is told.
            w.conn.command_registry['suite_later_write'] = {
                'transition': lambda params, before: {params['target']: {'kind': 'architecture_contract',
                                                                         'data': params['data']}},
                'writes': WRITES}
            SHADOW = 'shadow:architecture'
            suite_write(w, SHADOW, 'architecture_contract', {'shadow': True})
            valid = dict(record(w) or {}, contract_version=1)
            PARAMS = {
                'upsert_entity': lambda t: (dict(entity_id=t, kind='architecture_contract', data=valid), {t: version(w.conn, t)}),
                'retire_entity': lambda t: (dict(entity_id=t), {t: version(w.conn, t)}),
                'record_receipt': lambda t: (dict(receipt_id=t, subject=t, digest=D['lf']), {t: version(w.conn, t)}),
                'reserve': lambda t: (dict(reservation_id=t, ceiling='unit', delta=1.0), {}) if t != SHADOW else None,
                'record_effect': lambda t: (dict(effect_id=t, kind='architecture_contract', target=t), {}) if t != SHADOW else None,
                'suite_later_write': lambda t: (dict(target=t, data=valid), {t: version(w.conn, t)}),
            }
            registry = sorted((set(S.COMMAND_REGISTRY) | set(w.conn.command_registry)) - {OP})
            ok &= set(registry) == set(PARAMS)
            outcomes = {}
            for operation in registry:
                for t in (AID, 'architecture:repository-new', SHADOW):
                    made = PARAMS[operation](t) if operation in PARAMS else None
                    if made is None:
                        continue
                    before = frozen(w)
                    shadow = version(w.conn, SHADOW)
                    serial[0] += 1
                    try:
                        S.execute(w.conn, dict(command_id='generic-%d' % serial[0], principal='owner', operation=operation,
                                               parameters=made[0], expected_versions=made[1], artifact_digests=[],
                                               nonce='generic-n-%d' % serial[0]), 'authority', journal_sign, 1)
                        code = 'committed'
                    except S.StoreRefused as error:
                        code = error.code
                    outcomes['%s %s' % (operation, t)] = code
                    ok &= code == 'entity_owned' and frozen(w) == before and version(w.conn, SHADOW) == shadow
            ok &= len(outcomes) >= 2 * len(registry)
            observed['generic_write'] = outcomes
            check('acceptance/generic-write', ok)

        # -- AC4: every input a worker controls, enumerated ----------------------------------------
        with region('acceptance/worker-inputs'):
            w = world('inputs', {'owner': OWNER, 'agent': dict(OWNER, principal_type='agent_run'),
                                 'service': dict(OWNER, principal_type='service')})
            ok = drive(w, packet(command())).get('ok') is True
            accepted_state = frozen(w)
            decoy_packet = packet(command(commit=C['decoy'], digest=D['decoy'], replaces=1))
            invalid_packet = packet(command(name='wrong_fields', replaces=1))
            stub = 'def validate_contract(*a, **k):\n    return 0\n'
            outcomes = {}
            elsewhere = top / 'elsewhere.yaml'
            elsewhere.write_bytes(B['weakened'])

            def workspace_case(name, arrange, refusals):
                judge(w, B['lf'])
                arrange()
                found = w.gate.architecture(EL.SN.entity(S, w.reader, AID))
                got = [drive(w, decoy_packet).get('reason'), drive(w, invalid_packet).get('reason')]
                outcomes[name] = got + [found.get('refusals')]
                return (got == ['missing_evidence:commit', 'invalid_contract:invalid_structure']
                        and gate_says(found, refusals) and frozen(w) == accepted_state)

            contract, flag = ws / '.veldo' / 'architecture.yaml', ws / '.veldo' / 'policy.yaml'

            def stubs():
                for module in ('validate.py', 'validate_checks.py', 'contract_loader.py', 'arch.py'):
                    (ws / '.veldo' / module).write_text(stub)
                contract.write_bytes(CONTRACTS['wrong_fields'])

            WORKSPACE = {
                'policy optional': (lambda: flag.write_text('architecture_contract: optional\n'), []),
                'policy absent': (lambda: flag.unlink(), []),
                'policy unreadable': (lambda: os.chmod(str(flag), 0), []),
                'contract edited': (lambda: contract.write_bytes(B['weakened']),
                                    ['missing_authority:architecture/unaccepted_artifact']),
                'contract deleted': (lambda: contract.unlink(), ['missing_evidence:architecture/required_absence']),
                'contract replaced by a symlink': (lambda: (contract.unlink(), os.symlink(str(elsewhere), str(contract))),
                                                   ['missing_authority:architecture/unaccepted_artifact']),
                'validator copy replaced by a success stub': (stubs, ['invalid_input:architecture/invalid_structure']),
            }
            for name, (arrange, refusals) in WORKSPACE.items():
                ok &= workspace_case(name, arrange, refusals)
            for module in ('validate.py', 'validate_checks.py', 'contract_loader.py', 'arch.py'):
                if (ws / '.veldo' / module).exists():
                    (ws / '.veldo' / module).unlink()
            # The environment: every VELDO_ and GIT_ variable the installed engine names, every one this
            # process carries, the variables that select a Git repository or object store, and HOME.
            named = set()
            for source in mods.glob('*.py'):
                named |= set(re.findall(r'\b(?:VELDO|GIT)_[A-Z0-9_]*[A-Z0-9]\b', source.read_text()))
            named |= {k for k in os.environ if k.startswith(('VELDO_', 'GIT_'))}
            named |= {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                      'GIT_INDEX_FILE', 'GIT_COMMON_DIR', 'GIT_NAMESPACE', 'GIT_CEILING_DIRECTORIES', 'GIT_EXEC_PATH',
                      'GIT_TEMPLATE_DIR', 'GIT_CONFIG', 'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_SYSTEM', 'GIT_REPLACE_REF_BASE',
                      'HOME'}
            home = top / 'decoy-home'
            home.mkdir()
            (home / '.gitconfig').write_text('[safe]\n\tdirectory = *\n[core]\n\tbare = false\n')
            VALUES = {'GIT_DIR': decoy / '.git', 'GIT_COMMON_DIR': decoy / '.git', 'GIT_OBJECT_DIRECTORY': decoy / '.git' / 'objects',
                      'GIT_ALTERNATE_OBJECT_DIRECTORIES': decoy / '.git' / 'objects', 'GIT_INDEX_FILE': decoy / '.git' / 'index',
                      'GIT_CONFIG_GLOBAL': home / '.gitconfig', 'GIT_CONFIG': home / '.gitconfig', 'HOME': home}
            judge(w, B['lf'])
            env_ok, env_seen = True, {}
            for variable in sorted(named):
                prior = os.environ.get(variable)
                os.environ[variable] = str(VALUES.get(variable, decoy))
                try:
                    got = drive(w, decoy_packet).get('reason')
                    found = w.gate.architecture(EL.SN.entity(S, w.reader, AID))
                finally:
                    if prior is None:
                        os.environ.pop(variable, None)
                    else:
                        os.environ[variable] = prior
                env_seen[variable] = got
                env_ok &= got == 'missing_evidence:commit' and gate_says(found, []) and frozen(w) == accepted_state
            ok &= env_ok and len(env_seen) > 20
            for who in ('agent', 'service'):
                reason = drive(w, packet(command(who, name='weakened', replaces=1))).get('reason')
                outcomes['signed by ' + who] = reason
                ok &= reason == 'not_authorized:principal_type' and frozen(w) == accepted_state
            observed['worker_inputs'] = dict(workspace=outcomes, environment=env_seen)
            check('acceptance/worker-inputs', ok)

        for first in regions:
            check('ran/' + first, first not in {label for label, _ in raised})
        observed['raised'] = raised
        observed['authority_status'] = [w.authority.status() for w in worlds if w.authority is not None][:3]
        globals()['_V134_OBSERVED'] = observed
        flag = ws / '.veldo' / 'policy.yaml'
        if os.path.lexists(str(flag)) and not os.path.islink(str(flag)):
            os.chmod(str(flag), stat.S_IRUSR | stat.S_IWUSR)
        for w in worlds:
            w.reader.close()
            w.suite.close()
            w.conn.close()


_v134_started = __import__('time').monotonic()
_v134_suite()
_V134_SECONDS = __import__('time').monotonic() - _v134_started
