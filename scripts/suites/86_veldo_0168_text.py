"""Telegram text through real signed inbox, framing, report and intake writers and loopback HTTP.

The renderer input probes start with writer-produced snapshots. Choice/scope/subject probes call the
renderers directly: unsupported decision choices are not publishable decisions. Intake's current
question writer accepts ASCII project ids only; arbitrary prompt text exercises its production
render_prompt seam, while the literal-escape project name exercises the real question send.
"""

def _v168_suite():
    import ast
    import copy
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import socket
    import tempfile
    import unicodedata

    production = {
        'control_channel_presentation.py': ROOT / ".veldo" / "control_channel_presentation.py",
        'control_channel_presentation_text.py': ROOT / ".veldo" / "control_channel_presentation_text.py",
        'control_channel_presentation_v1.py': ROOT / ".veldo" / "control_channel_presentation_v1.py",
        'control_channel_projection.py': ROOT / ".veldo" / "control_channel_projection.py",
        'control_telegram_report.py': ROOT / ".veldo" / "control_telegram_report.py",
        'control_intake.py': ROOT / ".veldo" / "control_intake.py",
    }
    names = ('lines/decision', 'lines/inbox', 'lines/report', 'lines/prompt',
             'escape/zero-width', 'escape/direction', 'escape/whitespace', 'escape/literal',
             'escape/categories', 'escape/fields', 'cuts/long-token', 'cuts/words',
             'receipts/earlier', 'receipts/new', 'receipts/unknown', 'observability/counters',
             'intake/delivery', 'inventory/sends-and-assets', 'lines/edges')
    rows = {name: [] for name in names}

    def check(name, label, condition):
        rows[name].append((label, bool(condition)))

    def attempt(fn, default=None):
        try:
            return fn()
        except Exception:
            return default

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def expected(text):
        text = text.replace('\r\n', '\n')
        return ''.join('<U+%04X>' % ord(ch) if (
            unicodedata.category(ch) in ('Cf', 'Zl', 'Zp') or
            unicodedata.category(ch) == 'Cc' and ch != '\n' or
            unicodedata.category(ch) == 'Zs' and ch != ' ' or text.startswith('<U+', i)) else ch
                       for i, ch in enumerate(text))

    proof = globals().get('V168_PROOF', ROOT / 'proof' / 'VELDO-0168')
    stop = None
    ing = authority = None
    real_connect = socket.create_connection

    def guarded(address, *args, **kwargs):
        if address[0] != '127.0.0.1':
            raise OSError('only loopback is allowed in this suite')
        return real_connect(address, *args, **kwargs)

    with tempfile.TemporaryDirectory(prefix='v168-', dir='/dev/shm') as directory:
        base = Path(directory)
        organs = base / 'organs'
        organs.mkdir()
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, organs / source.name)
        for name, source in production.items():
            if source.is_file():
                shutil.copyfile(source, organs / name)
        socket.create_connection = guarded
        try:
            H = load('v168_authority', ROOT / 'scripts/suites/support/v73_authority.py')
            token = 'fixture' + str(168)
            bot = {'id': 80168, 'is_bot': True, 'first_name': 'Veldo'}
            owner = {'id': 55168, 'is_bot': False, 'first_name': 'Owner'}
            url, api, stop = H.stand_in({token: bot})
            authority = A = H.build(base / 'authority', organs, owner['id'], url, token)
            for who in ('owner', 'pm'):
                entry = A.AC.membership_entry(A.CM.authority_state(A.S, A.conn)['membership'], who)
                A.admin('steward', 'change_roles', dict(principal=who, roles=entry['roles'], scope='*'))
            INGRESS = load('v168_ingress', organs / 'control_channel_ingress.py')
            V = load('v168_presentation', organs / 'control_channel_presentation.py')
            P = load('v168_projection', organs / 'control_channel_projection.py')
            R = load('v168_report', organs / 'control_telegram_report.py')
            IN = load('v168_intake', organs / 'control_intake.py')
            ing = INGRESS.open_ingress(str(A.config_path))
            A.authorize(ing.activations, 'qualify')
            reporter = R.Reporter(ing, owner='owner')
            projection = P.Projection(ing.inbox.store, ing.inbox,
                                     P.TelegramEdge(url, token, activation=ing.gate), ing.conn,
                                     ing.inbox.journal_signer, ing.inbox.sign)

            def opened(brief, risk=None, scope='project-a', choices=None, subject='subject'):
                alias = A.next_id('text')
                assignment = dict(kind='decision', owner='owner', scope=[scope], deadline='2026-10-01T17:00:00Z',
                                  budget={'owner_minutes': 1}, brief=brief, choices=choices or ['accept', 'reject'],
                                  subject=dict(kind='artifact', ref=subject, digest='sha256:' + 'a' * 64))
                answer = ing.inbox.apply(A.signed_command('pm', dict(A.ids, operation='open', alias=alias,
                    principal='pm', command_id=A.next_id('open'), nonce=A.next_id('nonce'), assignment=assignment)))
                rid = A.assignment_id(alias)
                if risk is not None:
                    ing.presenter.frame(A.signed_command('pm', dict(A.ids, operation='frame', alias=alias,
                        principal='pm', request_version=1, risk_statement=risk,
                        command_id=A.next_id('frame'), nonce=A.next_id('nonce'))))
                    ing.presenter.present(rid)
                return rid, ing.inbox.brief(rid), ing.presenter.current(rid)

            text = 'first  \tline\r\nsecond line\nthird  line'
            rid, brief, receipt = opened(text, risk=text)
            if os.environ.get('VELDO_0168_CAPTURE'):
                Path(os.environ['VELDO_0168_CAPTURE']).write_text(json.dumps(receipt, indent=1) + '\n')
            shown = '\n'.join((receipt or {}).get('rendered', []))
            check('lines/decision', 'brief and signed risk preserve three lines and spacing',
                  shown.count(expected(text)) == 2 and (receipt or {}).get('request', {}).get('brief') == text
                  and (receipt or {}).get('risk_statement') == text)
            nid, notice_brief, _ = opened(text)
            entry = next(e for e in ing.inbox.index()['entries'] if e['id'] == nid)
            projected = projection._project(entry)
            notice = projection.record(P.projection_id(nid, 1)) or {}
            check('lines/inbox', 'actual inbox send preserves three lines', projected.get('outcome') == 'sent'
                  and expected(text) in notice.get('platform_text', ''))
            source = next(s for s in reporter.sources(since=0) if s.get('request') == rid)
            reported = reporter.report(source)
            report = reporter.record(reported['report_id']) or {}
            check('lines/report', 'journal-derived report send preserves brief', reported.get('outcome') == 'sent'
                  and expected(text) in report.get('platform_text', ''))
            prompt = getattr(IN, 'render_prompt', lambda value: value)
            check('lines/prompt', 'the question send renderer preserves its input lines', prompt(text) == expected(text))

            def renders(value):
                # Start with accepted writer snapshots; these are renderer inputs, never stored receipts.
                decision = copy.deepcopy(receipt)
                decision['request']['brief'] = value
                inbox = copy.deepcopy(brief)
                inbox['content']['brief'] = value
                fact = dict(source, fact=value)
                return ['\n'.join(V.render(decision)), P.render(inbox), reporter.render(fact)[0], prompt(value)]

            samples = {'escape/zero-width': '\u200b\ufeff', 'escape/direction': '\u202e\u2066',
                       'escape/whitespace': '\t\r\u00a0\u2003\u2028\u2029',
                       'escape/literal': '<U+200B>\u200b<U+003C>'}
            for row, value in samples.items():
                sample = 'A' + value + 'B'
                check(row, 'all four renderers distinguish each invisible or literal escape',
                      all(expected(sample) in got and sample not in got for got in renders(sample)))
            chars = [chr(i) for i in range(0x110000) if unicodedata.category(chr(i)) in ('Cf', 'Cc', 'Zl', 'Zp', 'Zs')
                     and chr(i) not in ('\n', ' ')]
            # Small batches avoid presentation splitting through an escape while comparing whole strings.
            category_ok = []
            for start in range(0, len(chars), 80):
                sample = 'A' + 'X'.join(chars[start:start + 80]) + 'B'
                category_ok.append(all(expected(sample) in got for got in renders(sample)))
            check('escape/categories', 'entire running unicodedata category set, all renderers', all(category_ok))
            fields_ok = []
            for value in ('x\u200b', 'x\u202e', 'x\u2066', 'x\ty', 'x\u00a0y', 'x<U+200B>', 'x  y'):
                _, fb, _ = opened('field input', scope=value, choices=[value, 'reject'], subject=value)
                current = copy.deepcopy(receipt)
                current.update(request=fb['content'], choices=fb['content']['choices'],
                               subject_digests=V.subject_digests(fb['content']))
                for output in ('\n'.join(V.render(current)), P.render(fb)):
                    fields_ok.append(all(expected(value) in next(line for line in output.split('\n') if line.startswith(k))
                                         for k in ('Scope:', 'Subject:', 'Choices:')))
            check('escape/fields', 'writer-accepted choices, scopes and subject references keep their distinctions',
                  all(fields_ok))

            _, _, long = opened('z' * 9000, risk='ordinary')
            parts = (long or {}).get('rendered', [])
            cut, continued = '[cut inside a word, continues in the next part]', '[continued]'
            payload = [p.split('\n', 1)[-1] for p in parts]
            hard = [i for i, p in enumerate(payload) if p.endswith(cut)]
            check('cuts/long-token', 'every hard cut is marked on both sides within UTF-16 platform limits',
                  len(hard) >= 2 and all(payload[i + 1].startswith(continued) for i in hard)
                  and all(len(p.encode('utf-16-le')) // 2 <= 4096 for p in parts)
                  and ''.join(payload).replace(cut, '').replace(continued, '').count('z' * 9000) == 1
                  and (long or {}).get('outcome') == 'published')
            words = 'ordinary  words ' * 700
            _, _, soft = opened(words, risk='ordinary')
            if os.environ.get('VELDO_0168_CAPTURE_PARTS'):
                Path(os.environ['VELDO_0168_CAPTURE_PARTS']).write_text(json.dumps(soft, indent=1) + '\n')
            soft_parts = (soft or {}).get('rendered', [])
            joined = ''.join(p.split('\n', 1)[-1] for p in soft_parts)
            check('cuts/words', 'soft cuts keep original spaces and carry no hard-cut marker',
                  words in joined and cut not in joined and continued not in joined and len(soft_parts) > 1)
            # Receipts the renderer before this change recorded (captured from main's code, README.md): one
            # message, and several parts cut by its chunker. Neither names a renderer version.
            for fixture in ('renderer-1-receipt.json', 'renderer-1-parts-receipt.json'):
                earlier_path = Path(proof) / fixture
                earlier = json.loads(earlier_path.read_text()) if earlier_path.is_file() else None
                check('receipts/earlier', fixture + ' rechecks with its old bytes while the current rendering differs',
                      earlier is not None and 'renderer_version' not in earlier and earlier.get('outcome') == 'published'
                      and not V.receipt_problems(earlier, retrieved=False)
                      and V.render(earlier) != earlier['rendered'])
            check('receipts/new', 'new receipts name version 2 and bind retrieved platform bytes',
                  receipt.get('renderer_version') == 2 and not V.receipt_problems(receipt, retrieved=False)
                  and all(api['bots'][token]['messages'][(owner['id'], mid)]['text'] == part
                          for mid, part in zip(receipt['message_ids'], receipt['rendered'])))
            unknown = dict(receipt, renderer_version=999)
            changed = copy.deepcopy(receipt)
            changed['rendered'][0] += 'changed'
            check('receipts/unknown', 'unknown version is distinct from mismatched content',
                  V.receipt_problems(unknown, retrieved=False) == ['unknown_renderer_version']
                  and 'rendered bytes are not the rendering of the bound fields' in V.receipt_problems(changed, retrieved=False))
            observations = [ing.presenter.observations, projection.observations, reporter.observations]
            # The three-line text holds one tab: the decision presentation shows it in the brief and in the
            # risk statement (two), the inbox item and the report in the brief (one each).
            check('observability/counters', 'versions, escaped categories, hard cuts and part numbers are recorded',
                  all(any(o.get('renderer_version') == 2 and (o.get('render_stats') or {}).get('escaped', {}).get('Cc') == tabs
                              and o.get('parts') for o in group) for group, tabs in zip(observations, (2, 1, 1)))
                  and all((attempt(obj.metrics, {}).get('rendering') or {}).get('sent', 0) > 0
                          for obj in (ing.presenter, projection, reporter))
                  and ((long or {}).get('render_stats') or {}).get('hard_cuts') == len(hard))

            intake = IN.Intake(ing.inbox.store, ing.inbox.membership if hasattr(ing.inbox, 'membership') else A.CM,
                               A.AC, ing.acquirer, ing.conn, domain=A.ids['domain_uuid'],
                               projects=['project-a', 'literal<U+200B>'], api_edge='api-edge',
                               journal_signer=ing.inbox.journal_signer, sign=ing.inbox.sign, asker=ing.presenter.edge)
            H.deliver(api, token, owner, 'Please build a new calendar view')
            ing.acquirer.acquire()
            taken = intake.take_telegram()
            questions = [json.loads(r[0]) for r in ing.conn.execute("SELECT data FROM entities WHERE kind='intake_question'")]
            delivered = []
            for q in questions:
                d = q.get('delivery') or {}
                msg = api['bots'][token]['messages'].get((d.get('chat_id'), d.get('message_id')), {})
                delivered.append('literal<U+003C>U+200B>' in msg.get('text', '') and 'literal<U+200B>' in q['prompt'])
            check('intake/delivery', 'real question writer and send escape once, retaining original prompt',
                  bool(taken) and bool(delivered) and all(delivered))

            # Telegram trims the whitespace at both ends of a message: no message sent ends or begins in it,
            # and a brief whose ends are whitespace shows them escaped where it ends a message.
            edge_brief = ' edge brief\n  '
            eid, _, _ = opened(edge_brief)
            edge_entry = next(e for e in ing.inbox.index()['entries'] if e['id'] == eid)
            projection._project(edge_entry)
            edge_notice = projection.record(P.projection_id(eid, 1)) or {}
            # Its leading space is inside the message and stays a space; its final line break and spaces end it.
            check('lines/edges', 'an inbox item ending its message with whitespace shows it escaped',
                  edge_notice.get('outcome') == 'sent'
                  and edge_notice.get('platform_text', '').endswith('\n\n edge brief<U+000A><U+0020><U+0020>'))
            separate = None
            for n in range(700, 1100):
                decision = copy.deepcopy(receipt)
                decision['request']['brief'] = 'ordinary words ' * n
                shown_parts = V.render(decision)
                if shown_parts[-1].split('\n', 1)[-1].startswith('Choices: '):
                    separate = shown_parts
                    break
            check('lines/edges', 'a body part that ends its own message shows its final space escaped',
                  separate is not None and separate[-2].endswith('words<U+0020>'))
            sent_texts = [m.get('text', '') for m in api['bots'][token]['messages'].values()]
            check('lines/edges', 'no message sent begins or ends with a space or line break',
                  len(sent_texts) > 10 and all(t == t.strip(' \n') for t in sent_texts)
                  and all(p == p.strip(' \n') for p in soft_parts + parts + (separate or [])))

            # Inventory all engine Bot API endpoints and all calls into the four in-scope send seams, in the
            # engine's installed copies and in the production copies this suite runs.
            inventories = {}
            def walk(node, file, parents=()):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    parents += (node.name,)
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and '/sendMessage' in node.value and '\n' not in node.value:
                    endpoints.add((file, '.'.join(parents)))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'send':
                    receiver = ast.unparse(node.func.value)
                    if file in ('control_channel_presentation.py', 'control_channel_projection.py', 'control_telegram_report.py', 'control_intake.py'):
                        calls.add((file, '.'.join(parents), receiver))
                for child in ast.iter_child_nodes(node):
                    walk(child, file, parents)
            for label, folder in (('engine', ROOT / 'engine/.veldo'), ('production', organs)):
                endpoints, calls = set(), set()
                for file in sorted(folder.glob('*.py')):
                    walk(ast.parse(file.read_text()), file.name)
                inventories[label] = (endpoints, calls)
            wanted_endpoints = {('control_channel_projection.py', 'TelegramEdge.send'),
                                ('control_channel_presentation.py', 'TelegramPresentationEdge.send')}
            wanted_calls = {('control_channel_projection.py', 'Projection._send', 'self.edge'),
                            ('control_channel_presentation.py', 'Presenter._send', 'self.edge'),
                            ('control_telegram_report.py', 'Reporter._send', 'self.edge'),
                            ('control_intake.py', 'Intake._ask', 'self.asker')}
            # The repository's own doorbell (.veldo/request_doorbell.py, not installed into the engine) is
            # named outside the set by the specification.
            outside = {('request_doorbell.py', 'TelegramSink.send')}
            scaffold = load('v168_scaffold', ROOT / '.veldo/init_scaffold.py')
            assets = ['.veldo/control_channel_presentation_text.py', '.veldo/control_channel_presentation_v1.py']
            check('inventory/sends-and-assets', 'complete endpoint and send inventory; new renderer assets installed identically',
                  inventories['engine'] == (wanted_endpoints, wanted_calls)
                  and inventories['production'] == (wanted_endpoints | outside, wanted_calls)
                  and all(rel in scaffold._FILES and (ROOT / rel).is_file()
                          and (ROOT / rel).read_bytes() == (ROOT / 'engine' / rel).read_bytes() for rel in assets))
        except Exception as error:
            # Setup failures are assertion failures for unvisited rows; printed details make them visible.
            for name in names:
                if not rows[name]:
                    check(name, 'setup or section unavailable: %s: %s' % (type(error).__name__, str(error)[:180]), False)
        finally:
            if ing is not None:
                ing.conn.close()
            if authority is not None:
                authority.conn.close()
            if stop:
                stop()
            socket.create_connection = real_connect
    for name, checks in rows.items():
        for label, ok in checks:
            if not ok:
                print('VELDO-0168 detail: %s: %s' % (name, label))
        expect('VELDO-0168 ' + name, bool(checks) and all(ok for _, ok in checks))


_v168_suite()
