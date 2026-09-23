"""VELDO-0054: decision-record dependency evaluation at every enabled consumer, over a real store.

Only shared ROOT and expect are consumed. One temporary tree is both the repository the plan and
frontier readers read and the installed .veldo they run from, so a registered mutation of any
production module reaches every consumer that loads it. Real SQLite store with keyed journal
signatures; settlements are signed by real OpenSSH Ed25519 keys (ssh-keygen -Y sign) and verified by
the production SettlementTrust. Signed fixtures test consumption only: they authenticate no live owner.
The fixture spells every digest and the signed bytes itself, so the reader is judged against an
independent writer, never against its own spelling.
"""


def _v54_suite():
    import ast
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
    import subprocess
    import tempfile

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_decision_dependency.py': ROOT / ".veldo" / "control_decision_dependency.py",
        'control_eligibility.py': ROOT / ".veldo" / "control_eligibility.py",
        'plan.py': ROOT / ".veldo" / "plan.py",
        'frontier.py': ROOT / ".veldo" / "frontier.py",
    }
    # The modules whose call sites the consumer registration is derived from. runstatus.py is read
    # too: a consumer that exists and is not wired must be visible, never silently outside the scan.
    SCANNED = ('plan.py', 'frontier.py', 'control_eligibility.py', 'runstatus.py')

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # The fixture's own spellings (independent of the reader's): canonical JSON, sha256, the signed
    # settlement fields and the lifecycle fields a subject digest leaves out.
    def fx_digest(value):
        blob = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        return 'sha256:' + hashlib.sha256(blob).hexdigest()

    FX_FIELDS = ('schema', 'domain_uuid', 'decision_id', 'decision_revision', 'framing_digest', 'subject',
                 'scope_digest', 'ruling', 'request_id', 'request_version', 'principals', 'settled_at')
    FX_LIFECYCLE = {'spec': ('state',), 'plan': ('status',)}

    def fx_bytes(body):
        return json.dumps({k: body.get(k) for k in FX_FIELDS}, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=True).encode()

    def fx_subject(kind, data):
        return fx_digest({k: v for k, v in data.items() if k not in FX_LIFECYCLE[kind]})

    def fx_scope(scope):
        return fx_digest({'operation': scope.get('operation'), 'target': scope.get('target'),
                          'parameters': scope.get('parameters')})

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v54-', dir=fast) as directory:
        base = Path(directory) / 'repo'
        mods = base / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        GP = load('v54_git', mods / 'git_process.py')
        GP.run(['git', '-C', str(base), 'init', '-q'], check=True, capture_output=True)
        EL = load('v54_eligibility', mods / 'control_eligibility.py')
        DD = EL.DD
        S = load('v54_store', mods / 'control_store.py')
        CLM = EL._organ('control_claim')
        DOMAIN, REPOSITORY = 'domain-54', 'repository-54'
        db = base / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        journal_key = os.urandom(32)

        def journal_sign(message):
            return hmac.new(journal_key, message, hashlib.sha256).hexdigest()

        serial = [0]
        written = {}

        def put(identity, kind, data):
            serial[0] += 1
            row = writer.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            S.execute(writer, dict(command_id='c%d' % serial[0], principal='owner', operation='upsert_entity',
                                   nonce='n%d' % serial[0], artifact_digests=[],
                                   expected_versions={identity: row[0] if row else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)),
                      'authority', journal_sign, 1)
            written[identity] = json.loads(json.dumps(data))

        # The settlement authority's key (trusted by the host) and a key nobody trusts.
        host = Path(directory) / 'host'
        host.mkdir()
        keys = {}
        for name in ('trusted', 'rogue'):
            keys[name] = host / (name + '_key')
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', name, '-f', str(keys[name])],
                           check=True, capture_output=True)
        public = (host / 'trusted_key.pub').read_text().split()[:2]
        signers = host / 'settlement_signers'
        signers.write_text('veldo-settlement namespaces="%s" %s %s\n' % (DD.SETTLEMENT_NAMESPACE, public[0], public[1]))

        def ssh_sign(message, key='trusted'):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys[key]), '-n', 'veldo-decision-settlement'],
                                  input=message, capture_output=True, check=True).stdout.decode()

        GOVERNING, SETTLEMENT = 'veldo.governing_decision/v1', 'veldo.decision_settlement/v1'
        records = {}

        def decision(rid, kind, subject_id, blocks, framing=None, revision=1, scope=None, **extra):
            entity = subject_id if kind == 'spec' else 'plan:' + subject_id
            data = written.get(entity)
            record = dict(schema=GOVERNING, decision_id=rid.split(':', 1)[1], revision=revision,
                          framing_digest=framing or fx_digest({'framing': rid}),
                          subject=dict(kind=kind, id=subject_id,
                                       digest=fx_subject(kind, data) if kind in FX_LIFECYCLE and data else 'sha256:none'),
                          scope=scope or dict(operation='proceed', target=subject_id, parameters={'approach': 'A'}),
                          blocks=list(blocks), obligations=[])
            record.update(extra)
            records[rid] = record
            put(rid, 'decision', record)
            return record

        def settle(rid, n=1, ruling='approve', key='trusted', edit=None, after=None, signed=True, record=None):
            rec = record or records[rid]
            body = dict(schema=SETTLEMENT, domain_uuid=DOMAIN, decision_id=rec['decision_id'],
                        decision_revision=rec['revision'], framing_digest=rec['framing_digest'],
                        subject=dict(rec['subject']), scope_digest=fx_scope(rec['scope']), ruling=ruling,
                        request_id='request/' + rec['decision_id'], request_version=rec['revision'],
                        principals=['dmitry'], settled_at='2026-09-23T00:00:%02dZ' % n)
            if edit:
                edit(body)
            data = dict(schema=SETTLEMENT, decision=rid, settlement=body, signer='veldo-settlement',
                        signature=ssh_sign(fx_bytes(body), key) if signed else None)
            if after:
                after(data)
            put('settlement:%s:%d' % (rid, n), 'decision_settlement', data)
            return data

        def unit(sid, plan='PLAN-9401', scope='sha256:scope'):
            put(sid, 'execution_unit', dict(state='CLAIMED', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + sid,
                                            requirements=[], eligible_holders=['worker-a'], plan=plan, project='p1',
                                            depends_on=[], scope_digest=scope, revision=1, producer='builder-a',
                                            approvals_required=['owner']))
            put('backlog:' + sid, 'backlog_item', dict(state='ACTIVE', repository_uuid=REPOSITORY))
            put('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest=scope))
            put('approval:%s:owner' % sid, 'approval', dict(unit=sid, name='owner', state='granted', revision=1))
            put(CLM.claim_id(REPOSITORY, sid), 'claim', dict(unit_id=sid, holder='worker-a', generation=1,
                                                             state='owned', heartbeat_at=CLM.CL._now()))

        put('project:p1', 'project', dict(name='decisions'))
        put('authority:' + DOMAIN, 'authority', dict(state='active', generation=1))
        # Every unit is admitted, claimed, approved and dependency-free under a ready plan: the ONLY
        # thing that can hold one back is the governing decision its scenario sets up.
        PLANS = {'PLAN-9401': [], 'PLAN-9402': [], 'PLAN-9403': [], 'PLAN-9404': [], 'PLAN-9405': []}
        # unit: (plan, mode, expected blocker codes after every change). mode 'all' is decided by every
        # consumer; 'files' is a reference only the plan file carries, which the store-backed stations
        # cannot see and every file reader must honor.
        SCEN = {}

        def scenario(sid, codes, plan='PLAN-9401', mode='all'):
            SCEN[sid] = (plan, mode, set(codes))
            PLANS[plan].append(sid)

        # AC1: exact current binding, for spec and plan subjects.
        for sid, codes in (('VELDO-9401', ()),
                           ('VELDO-9402', ('unbound_decision:decision:D-9402/subject_digest',)),
                           ('VELDO-9403', ('unbound_decision:decision:D-9403/subject',)),
                           ('VELDO-9404', ('unbound_decision:decision:D-9404/framing',)),
                           ('VELDO-9405', ('unbound_decision:decision:D-9405/revision',)),
                           ('VELDO-9408', ('decision_ruling:decision:D-9408/reject',)),
                           ('VELDO-9411', ('unbound_decision:decision:D-9411/framing',)),
                           ('VELDO-9412', ('unbound_decision:decision:D-9412/framing',)),
                           ('VELDO-9413', ('unbound_decision:decision:D-9413/framing',))):
            scenario(sid, codes)
        scenario('VELDO-9406', (), plan='PLAN-9402')
        scenario('VELDO-9407', ('unbound_decision:decision:P-9403/subject_digest',), plan='PLAN-9403')
        # AC2: missing, ambiguous and unsupported decisions, unresolved and valid ones.
        for sid, codes, mode in (('VELDO-9421', ('missing_decision:DEC-MISSING',), 'all'),
                                 ('VELDO-9422', ('missing_decision:DEC-FILE-ONLY',), 'files'),
                                 ('VELDO-9423', ('ambiguous_decision:DEC-AMB',), 'all'),
                                 ('VELDO-9424', ('ambiguous_decision:decision:D-9424',), 'all'),
                                 ('VELDO-9425', ('unsupported_decision:decision:D-9425/obligation:tripwire',), 'all'),
                                 ('VELDO-9426', ('unsupported_decision:decision:D-9426/obligation:adversarial_decision_review',), 'all'),
                                 ('VELDO-9427', ('unsupported_decision:decision:D-9427/subject_kind:contract',), 'all'),
                                 ('VELDO-9428', ('unresolved_decision:decision:D-9428',), 'all'),
                                 ('VELDO-9429', (), 'all'),
                                 # AC2: no inline or unsigned resolution substitutes for settlement.
                                 ('VELDO-9431', ('unresolved_decision:decision:D-9431',), 'all'),
                                 ('VELDO-9432', ('unsigned_decision:decision:D-9432',), 'all'),
                                 ('VELDO-9433', ('unsigned_decision:decision:D-9433',), 'all'),
                                 ('VELDO-9434', ('unsigned_decision:decision:D-9434',), 'all'),
                                 ('VELDO-9435', ('unresolved_decision:decision:D-9435',), 'all'),
                                 ('VELDO-9436', ('missing_decision:DEC-INLINE',), 'files')):
            scenario(sid, codes, mode=mode)
        # AC3: a ruling authorizes only its recorded subject and scope.
        for sid, codes in (('VELDO-9441', ('unbound_decision:decision:D-9441/subject', 'unbound_decision:decision:D-9441/scope')),
                           ('VELDO-9442', ('unbound_decision:decision:D-9442/decision', 'unbound_decision:decision:D-9442/framing',
                                           'unbound_decision:decision:D-9442/subject', 'unbound_decision:decision:D-9442/scope')),
                           ('VELDO-9443', ('unbound_decision:decision:D-9443/scope',)),
                           ('VELDO-9444', ('unbound_decision:decision:D-9444/scope',)),
                           ('VELDO-9445', ('unbound_decision:decision:D-9445/scope',)),
                           ('VELDO-9448', ('unbound_decision:decision:D-9448/scope',)),
                           ('VELDO-9447', ())):
            scenario(sid, codes)
        scenario('VELDO-9446', ('unbound_decision:decision:P-9446/subject', 'unbound_decision:decision:P-9446/scope'),
                 plan='PLAN-9405')
        put('VELDO-9440', 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, revision=1, scope_digest='sha256:9440'))
        for sid in SCEN:
            unit(sid, plan=SCEN[sid][0])

        # The accepted plans. PLAN-9401's record carries the inline references the store-backed stations
        # read; its file carries the same plus the file-only ones.
        store_refs = [dict(id='DEC-MISSING', blocks=['VELDO-9421']), dict(id='DEC-AMB', blocks=['VELDO-9423']),
                      dict(id='DEC-9429', blocks=['VELDO-9429']),
                      dict(id='D-9435', blocks=['VELDO-9435'], status='resolved', ruling='approve')]
        put('plan:PLAN-9401', 'plan', dict(status='ready', revision=1, open_decisions=store_refs))
        for pid in ('PLAN-9402', 'PLAN-9403', 'PLAN-9404', 'PLAN-9405'):
            put('plan:' + pid, 'plan', dict(status='ready', revision=1, charter='charter of ' + pid))

        # AC1 subjects and settlements, every one the current exact binding before its change.
        for sid in ('VELDO-9401', 'VELDO-9402', 'VELDO-9403', 'VELDO-9404', 'VELDO-9405', 'VELDO-9408'):
            rid = 'decision:D-' + sid[-4:]
            decision(rid, 'spec', sid, [sid])
            settle(rid, ruling='reject' if sid == 'VELDO-9408' else 'approve')
        decision('decision:P-9402', 'plan', 'PLAN-9402', ['plan:PLAN-9402'])
        settle('decision:P-9402')
        decision('decision:P-9403', 'plan', 'PLAN-9403', ['plan:PLAN-9403'])
        settle('decision:P-9403')
        # AC1 wrong framing: a receipt without its framing digest, one for another framing, an empty one.
        for sid, edit in (('VELDO-9411', lambda b: b.pop('framing_digest')),
                          ('VELDO-9412', lambda b: b.update(framing_digest=fx_digest({'framing': 'another question'}))),
                          ('VELDO-9413', lambda b: b.update(framing_digest=''))):
            rid = 'decision:D-' + sid[-4:]
            decision(rid, 'spec', sid, [sid])
            settle(rid, edit=edit)
        # AC2.
        decision('decision:D-AMB-1', 'spec', 'VELDO-9423', [], decision_id='DEC-AMB')
        decision('decision:D-AMB-2', 'spec', 'VELDO-9423', [], decision_id='DEC-AMB')
        settle('decision:D-AMB-1')
        settle('decision:D-AMB-2')
        decision('decision:D-9424', 'spec', 'VELDO-9424', ['VELDO-9424'])
        settle('decision:D-9424', 1)
        settle('decision:D-9424', 2)
        decision('decision:D-9425', 'spec', 'VELDO-9425', ['VELDO-9425'], obligations=['tripwire'])
        settle('decision:D-9425')
        decision('decision:D-9426', 'spec', 'VELDO-9426', ['VELDO-9426'], obligations=['adversarial_decision_review'])
        settle('decision:D-9426')
        decision('decision:D-9427', 'contract', 'CONTRACT-1', ['VELDO-9427'],
                 scope=dict(operation='proceed', target='CONTRACT-1', parameters={}))
        settle('decision:D-9427')
        decision('decision:D-9428', 'spec', 'VELDO-9428', ['VELDO-9428'])
        decision('decision:D-9429', 'spec', 'VELDO-9429', [], decision_id='DEC-9429')
        settle('decision:D-9429')
        # The inline status edit: the record SAYS it is settled and approved, and nothing settled it.
        decision('decision:D-9431', 'spec', 'VELDO-9431', ['VELDO-9431'], state='settled', ruling='approve', resolved=True)
        decision('decision:D-9432', 'spec', 'VELDO-9432', ['VELDO-9432'])
        settle('decision:D-9432', signed=False)
        decision('decision:D-9433', 'spec', 'VELDO-9433', ['VELDO-9433'])
        settle('decision:D-9433', key='rogue')
        decision('decision:D-9434', 'spec', 'VELDO-9434', ['VELDO-9434'])
        settle('decision:D-9434', ruling='reject', after=lambda d: d['settlement'].update(ruling='approve'))
        decision('decision:D-9435', 'spec', 'VELDO-9435', ['VELDO-9435'], decision_id='D-9435', state='settled')
        # AC3. D-9441 was ruled on VELDO-9440; D-9442's settlement is a copy of D-9441's signed ruling.
        decision('decision:D-9441', 'spec', 'VELDO-9440', ['VELDO-9441'], framing=fx_digest({'framing': 'generic'}))
        ruling_9441 = settle('decision:D-9441')
        decision('decision:D-9442', 'spec', 'VELDO-9442', ['VELDO-9442'])
        put('settlement:decision:D-9442:1', 'decision_settlement', dict(ruling_9441, decision='decision:D-9442'))
        for sid in ('VELDO-9443', 'VELDO-9444', 'VELDO-9445', 'VELDO-9447'):
            decision('decision:D-' + sid[-4:], 'spec', sid, [sid])
            settle('decision:D-' + sid[-4:])
        # D-9448 is ruled, consistently signed, on VELDO-9448 with a scope whose target is another spec.
        decision('decision:D-9448', 'spec', 'VELDO-9448', ['VELDO-9448'],
                 scope=dict(operation='proceed', target='VELDO-9447', parameters={'approach': 'A'}))
        settle('decision:D-9448')
        decision('decision:P-9446', 'plan', 'PLAN-9404', ['plan:PLAN-9405'], framing=fx_digest({'framing': 'generic'}))
        settle('decision:P-9446')

        # The checkout: every scenario is a ready planned spec at its plan's frontier, so a file reader
        # alone would offer every one of them; every hold-back below is the decision evaluation's.
        (base / 'specs').mkdir()
        (base / 'plans').mkdir()
        works = {}
        for pid, sids in PLANS.items():
            lines = []
            for n, sid in enumerate(sids, 1):
                works[sid] = 'W%d' % n
                (base / 'specs' / (sid + '-fixture.md')).write_text('\n'.join([
                    '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Decision fixture ' + sid, 'status: ready',
                    'risk: low', 'owner: dmitry', 'lane: planned', 'plan: ' + pid, 'work: W%d' % n, 'plan_revision: 1',
                    'depends_on: []', '---', '', 'Fixture.', '']))
                lines += ['  - item: W%d' % n, '    spec: ' + sid, '    order: %d' % n]
            decisions_block = []
            if pid == 'PLAN-9401':
                decisions_block = ['open_decisions:']
                for entry in store_refs + [dict(id='DEC-FILE-ONLY', blocks=['VELDO-9422']),
                                           dict(id='DEC-INLINE', blocks=['VELDO-9436'], status='resolved', ruling='approve')]:
                    decisions_block += ['  - id: ' + entry['id'], '    blocks: [%s]' % ', '.join(entry['blocks'])]
                    decisions_block += ['    %s: %s' % (k, v) for k, v in entry.items() if k not in ('id', 'blocks')]
            (base / 'plans' / (pid + '-fixture.md')).write_text('\n'.join(
                ['---', 'schema: veldo.plan/v1', 'id: ' + pid, 'title: Decision fixture plan', 'status: ready',
                 'revision: 1', 'work:'] + lines + decisions_block + ['---', '', 'Fixture plan.', '']))

        reader = S.open_store(str(db), mode='r')
        trust = DD.SettlementTrust(signers.read_text())
        gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, settlement_trust=trust)
        PL = load('v54_plan', mods / 'plan.py')
        FR = load('v54_frontier', mods / 'frontier.py')
        claims = base / 'claims'
        DECIDING = [s for s in EL.FLOOR_STATIONS if 'decisions_settled' in EL.STATION_PREDICATES[s]]
        CONTEXT = {'build': {'holder': 'worker-a'}, 'publication': {'holder': 'worker-a'},
                   'review': {'holder': 'worker-a', 'reviewer': 'reviewer-b'}}

        def plan_path(pid):
            return str(base / 'plans' / (pid + '-fixture.md'))

        def sweep(sids):
            """Every enabled consumer's answer for every unit: the shared floor stations, the frontier,
            plan._decision_blocks, item_state through the plan burn-down, and run-check."""
            out = {sid: {'stations': {}} for sid in sids}
            for station in DECIDING:
                for sid in sids:
                    out[sid]['stations'][station] = sorted(gate.decide(station, sid, context=CONTEXT.get(station))['refusals'])
            offered = {u['spec'] for u in FR.claimable(repo_root=str(base), claims_root=str(claims), eligibility=gate)}
            for pid in PLANS:
                _, fm = PL.load_plan(plan_path(pid))
                blocks = PL._decision_blocks(fm, gate)
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    PL.cmd_status(plan_path(pid), eligibility=gate)
                burn = {m.group(1): m.group(2).strip() for m in re.finditer(r'^\s+W\d+\s+(VELDO-\d+)\s+(.*)$',
                                                                                   buffer.getvalue(), re.M)}
                status = PL._status(gate)
                shipped = PL._shipped_set(fm, status)
                states = {w['spec']: PL.item_state(w, status, shipped, blocks) for w in PL._work(fm)}
                for sid in PLANS[pid]:
                    if sid not in out:
                        continue
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        rc = PL.cmd_run_check(plan_path(pid), sid, eligibility=gate)
                    out[sid].update(offered=sid in offered, blocks=sorted(blocks.get(sid, [])), burn=burn.get(sid),
                                    item_state=states.get(sid), run_check=rc,
                                    run_codes=sorted(set(re.findall(r'refused: (\S+)', buffer.getvalue()))))
            return out

        def verdict(o, codes, mode='all'):
            """True when the unit is held back by exactly `codes` at every consumer that can see its
            decision (all of them for a store decision, the file readers for a file-only reference) and
            clear at every other one; with no codes, clear everywhere."""
            stations_expected = codes if mode == 'all' else set()
            stations_ok = all(set(r) == stations_expected for r in o['stations'].values())
            if not codes:
                return (stations_ok and o['offered'] and not o['blocks'] and o['burn'].endswith('(frontier)')
                        and o['item_state'].endswith('(frontier)') and o['run_check'] == 0 and not o['run_codes'])
            return (stations_ok and not o['offered'] and set(o['blocks']) == codes
                    and o['burn'].startswith('blocked: decision') and o['item_state'].startswith('blocked: decision')
                    and o['run_check'] == 1 and set(o['run_codes']) == codes)

        emitted, raised, regions = set(), [], []
        observed = {}

        def check(label, condition):
            emitted.add(label)
            expect('VELDO-0054 ' + label, condition)

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

        # --- AC1: the enabled consumers, from the actual call sites -----------------------------------
        def calls_in(path, names):
            found = set()
            tree = ast.parse(Path(path).read_text())

            def walk(node, prefix):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        walk(child, prefix + [child.name])
                        continue
                    if isinstance(child, ast.Call) and prefix:
                        f = child.func
                        if (f.attr if isinstance(f, ast.Attribute) else getattr(f, 'id', None)) in names:
                            found.add((Path(path).name, '.'.join(prefix)))
                    walk(child, prefix)
            walk(tree, [])
            return found

        with region('decisions/consumers-from-call-sites'):
            derived = set()
            for name in SCANNED:
                derived |= calls_in(mods / name, DD.CONSUMER_CALLS)
            # The one reader this item's footprint cannot wire: runstatus's burn-down display still reads
            # inline entries without a Gate. It is listed so the scan names it rather than hiding it.
            unwired = {('runstatus.py', '_burndown')}
            deciding = {s for s in EL.FLOOR_STATIONS if 'decisions_settled' in EL.CC.ENTRY_PREDICATES[s]}
            observed['consumers'] = sorted('%s:%s' % c for c in derived)
            check('decisions/consumers-from-call-sites',
                   derived == set(DD.CONSUMERS) | unwired
                   and set(DECIDING) == deciding == {'selection', 'direct_execution', 'build', 'review', 'publication'}
                   and DD.SETTLEMENT_FIELDS == FX_FIELDS)

        rows = ('decisions/exact-binding', 'decisions/wrong-framing', 'decisions/named-blockers',
                'decisions/unsigned-resolution', 'decisions/scope-binding')
        with region(*rows):
            before_ids = ['VELDO-9401', 'VELDO-9402', 'VELDO-9403', 'VELDO-9404', 'VELDO-9405', 'VELDO-9406',
                          'VELDO-9407', 'VELDO-9441', 'VELDO-9446', 'VELDO-9443', 'VELDO-9444', 'VELDO-9445']
            before = sweep(before_ids)
            # AC1 "change either digest": the subject's accepted record changes (and, for 9403, the
            # record follows it while the signed ruling does not); the framing is revised in place or as
            # a new revision; a plan subject changes.
            for sid in ('VELDO-9402', 'VELDO-9403'):
                data = dict(written[sid], scope_digest='sha256:scope-v2')
                put(sid, 'execution_unit', data)
                put('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest='sha256:scope-v2'))
            put('decision:D-9403', 'decision', dict(records['decision:D-9403'], subject=dict(
                records['decision:D-9403']['subject'], digest=fx_subject('spec', written['VELDO-9403']))))
            put('decision:D-9404', 'decision', dict(records['decision:D-9404'], framing_digest=fx_digest({'framing': 'revised'})))
            put('decision:D-9405', 'decision', dict(records['decision:D-9405'], revision=2,
                                                    framing_digest=fx_digest({'framing': 'revision 2'})))
            put('plan:PLAN-9403', 'plan', dict(written['plan:PLAN-9403'], charter='revised charter'))
            # AC3: the ruling on VELDO-9440 re-pointed at VELDO-9441 (same framing, decision and
            # revision); the operation, the target and the parameters of three rulings changed; the plan
            # ruling on PLAN-9404 re-pointed at PLAN-9405.
            put('decision:D-9441', 'decision', dict(records['decision:D-9441'], subject=dict(
                kind='spec', id='VELDO-9441', digest=fx_subject('spec', written['VELDO-9441'])),
                scope=dict(operation='proceed', target='VELDO-9441', parameters={'approach': 'A'})))
            for sid, change in (('VELDO-9443', dict(operation='land')),
                                ('VELDO-9444', dict(target='VELDO-9447')),
                                ('VELDO-9445', dict(parameters={'approach': 'B'}))):
                rid = 'decision:D-' + sid[-4:]
                put(rid, 'decision', dict(records[rid], scope=dict(records[rid]['scope'], **change)))
            put('decision:P-9446', 'decision', dict(records['decision:P-9446'], subject=dict(
                kind='plan', id='PLAN-9405', digest=fx_subject('plan', written['plan:PLAN-9405'])),
                scope=dict(operation='proceed', target='PLAN-9405', parameters={'approach': 'A'})))
            # What is accepted before the consumers run over the refused scenarios.
            def artifacts():
                return (writer.execute('SELECT COALESCE(MAX(seq),0) FROM journal').fetchone()[0],
                        writer.execute('SELECT id, version, digest FROM entities ORDER BY id').fetchall(),
                        {p.name: p.read_bytes() for p in sorted((base / 'specs').glob('*.md')) + sorted((base / 'plans').glob('*.md'))})
            accepted_before = artifacts()
            after = sweep(sorted(SCEN))
            preserved = artifacts() == accepted_before
            observed['after'] = {sid: {'stations': o['stations']['build'], 'blocks': o['blocks'], 'run_codes': o['run_codes'],
                                       'item_state': o['item_state'], 'offered': o['offered']} for sid, o in after.items()}
            ok = {sid: verdict(after[sid], SCEN[sid][2], SCEN[sid][1]) for sid in SCEN}
            observed['mismatched'] = sorted(sid for sid, good in ok.items() if not good)

            def group(*sids):
                return all(ok[s] for s in sids)
            check('decisions/exact-binding',
                   all(verdict(before[s], set()) for s in before_ids)
                   and group('VELDO-9401', 'VELDO-9402', 'VELDO-9403', 'VELDO-9404', 'VELDO-9405', 'VELDO-9406',
                             'VELDO-9407', 'VELDO-9408')
                   and {s for s in SCEN if not SCEN[s][2]} == {'VELDO-9401', 'VELDO-9406', 'VELDO-9429', 'VELDO-9447'})
            check('decisions/wrong-framing', group('VELDO-9411', 'VELDO-9412', 'VELDO-9413'))
            check('decisions/named-blockers',
                   group('VELDO-9421', 'VELDO-9422', 'VELDO-9423', 'VELDO-9424', 'VELDO-9425', 'VELDO-9426',
                         'VELDO-9427', 'VELDO-9428', 'VELDO-9429'))
            check('decisions/unsigned-resolution',
                   group('VELDO-9431', 'VELDO-9432', 'VELDO-9433', 'VELDO-9434', 'VELDO-9435', 'VELDO-9436'))
            check('decisions/scope-binding',
                   group('VELDO-9441', 'VELDO-9442', 'VELDO-9443', 'VELDO-9444', 'VELDO-9445', 'VELDO-9446',
                         'VELDO-9447', 'VELDO-9448')
                   and all(verdict(before[s], set()) for s in ('VELDO-9441', 'VELDO-9443', 'VELDO-9444', 'VELDO-9445', 'VELDO-9446'))
                   and preserved)

        with region('decisions/production-gate-verifies'):
            # The production construction: an enrolled workspace's Gate verifies settlements against
            # the settlement signers the HOST trusts (outside the workspace); a host naming none trusts no
            # settlement, and signers inside the workspace or named relatively are refused by name.
            enroll_key = host / 'enroll_key'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'dmitry', '-f', str(enroll_key)],
                           check=True, capture_output=True)
            kt, kb = (host / 'enroll_key.pub').read_text().split()[:2]
            enrollment_signers = host / 'enrollment_signers'
            enrollment_signers.write_text('dmitry namespaces="veldo-enrollment" %s %s\n' % (kt, kb))

            def enrollment_sign(message):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(enroll_key), '-n', 'veldo-enrollment'],
                                      input=message, capture_output=True, check=True).stdout.decode()
            GP.run(['git', '-C', str(base), 'commit', '-q', '--allow-empty', '-m', 'enrolled fixture'], check=True,
                   capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
            EL.E.enroll(str(base), DOMAIN, 'store-54', str(db), 'host-54', 1, enrollment_sign, 'dmitry',
                        '2026-09-23T00:00:00Z', repository_uuid=REPOSITORY)
            carried = base / 'carried_signers'
            carried.write_text(signers.read_text())

            def attempt(settlement_signers):
                try:
                    record = {'schema': 'veldo.host_trust/v1', 'host_identity': 'host-54',
                              'enrollment_signers': str(enrollment_signers)}
                    if settlement_signers is not None:
                        record['settlement_signers'] = settlement_signers
                    path = host / 'trust.json'
                    path.write_text(json.dumps(record))
                    built = EL.entry_gate(str(base), trust=EL.load_host_trust(str(path)))
                    try:
                        return ('ok', sorted(built.decide('selection', 'VELDO-9401')['refusals']))
                    finally:
                        built.close()
                except EL.Stopped as stop:
                    return ('stopped', stop.reason)
            try:
                production = {'host': attempt(str(signers)), 'none': attempt(None),
                              'inside': attempt(str(carried)), 'relative': attempt('carried_signers')}
            finally:
                for path in (Path(EL.E.binding_path(str(base))), Path(EL.E.clone_uuid_path(str(base))), carried):
                    if path.exists():
                        path.unlink()
            observed['production'] = production
            check('decisions/production-gate-verifies',
                   production == {'host': ('ok', []), 'none': ('ok', ['unsigned_decision:decision:D-9401']),
                                  'inside': ('stopped', 'host_trust_refused:settlement_signers_inside_workspace'),
                                  'relative': ('stopped', 'host_trust_refused:settlement_signers_not_absolute')})

        with region('decisions/observations'):
            # Every refusal is named in the error taxonomy (never unknown), every decision-dependency
            # read is recorded with its identity, inputs and outcome, and the pending work is exposed.
            families = {'missing_decision': 'missing_authority', 'ambiguous_decision': 'missing_authority',
                        'unsupported_decision': 'missing_authority', 'unresolved_decision': 'missing_authority',
                        'unsigned_decision': 'missing_authority', 'unbound_decision': 'stale_subject',
                        'decision_ruling': 'missing_authority'}
            seen = {c for e in gate.observations for c in e['refusals']}
            reads = [e for e in gate.observations if e['operation'] == 'decision_dependency']
            status = gate.status()
            observed['taxonomy'] = {c: EL.taxonomy(c) for c in sorted(seen)}
            observed['decision_status'] = status['decisions']
            check('decisions/observations',
                   {c.split(':', 1)[0] for c in seen} >= set(families)
                   and all(EL.taxonomy(c) == families[c.split(':', 1)[0]] for c in seen if c.split(':', 1)[0] in families)
                   and all(t != 'unknown_outcome' for e in gate.observations for t in e['taxonomy'])
                   and reads and all({'operation', 'unit', 'domain_uuid', 'repository_uuid', 'references', 'watermark',
                                      'accepted_inputs', 'outcome', 'refusals', 'taxonomy'} <= set(e) for e in reads)
                   and status['decisions']['accepted'] > 0 and status['decisions']['refused'] > 0
                   and {s for s in SCEN if SCEN[s][1] == 'all' and SCEN[s][2]} <= set(status['decisions']['blocked']))

        for first in regions:
            check('ran/' + first, first not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V54_OBSERVED'] = observed
        reader.close()
        writer.close()


_v54_started = __import__('time').monotonic()
_v54_suite()
_V54_SECONDS = __import__('time').monotonic() - _v54_started
