"""VELDO-0172: live capture, binary schema and every discovered fake engine agree.

The census runs each suite's real production launch path, then reads back its generated executable
before teardown. Four assertion rows, one report each; no real CLI, login or network is used.
"""


def _v172_suite():
    import ast
    import contextlib
    import copy
    import importlib.util
    import io
    import json
    from pathlib import Path
    import re

    HERE = Path(globals().get('__suite_file__', str(ROOT / 'scripts/suites/x.py'))).resolve().parents[2]
    ORACLE = HERE / 'proof/VELDO-0172'
    # Literal anchors consumed by the mutation registry. ROOT follows the red-record archived tree.
    EXTRACTOR = ROOT / "proof/VELDO-0062" / "extract_formats.py"
    SCRUBBER = ROOT / "proof/VELDO-0172" / "scrub.py"
    SUITE79 = ROOT / "scripts/suites" / "79_veldo_0061_codex_adapter.py"
    SUITE165 = ROOT / "scripts/suites" / "82_veldo_0165_launch_hygiene.py"
    # A mutated copy of a census suite is read in its place; its name is the suite's own.
    COPIES = {path.name: path for path in (SUITE79, SUITE165)}
    TABLE = ROOT / 'proof/VELDO-0062/cli-formats.json'
    CAPTURE = ROOT / 'proof/VELDO-0172/capture.json'
    rows = {name: [] for name in ('table/capture', 'fake/capture', 'capture/allowlist', 'capture/planted')}

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def check(row, condition, detail):
        rows[row].append((bool(condition), detail))

    comparison = load('v172_compare', ORACLE / 'compare_formats.py')
    oracle_scrub = load('v172_oracle_scrub', ORACLE / 'scrub.py')
    reference = json.loads((ORACLE / 'capture.json').read_text())
    table = json.loads(TABLE.read_text())
    extractor = load('v172_extract', EXTRACTOR)
    captured = json.loads(CAPTURE.read_text()) if CAPTURE.is_file() else None
    problems = []
    for engine, section in (('claude', 'claude_code'), ('codex', 'codex')):
        for number, line in enumerate(reference['streams'][engine], 1):
            event = comparison.event_name(line)
            schema = table[section]['events'].get(event)
            problems += comparison.conform(line, schema, event, True) if schema else [event + ':table:no-event']
    check('table/capture', not problems, ', '.join(problems))
    check('table/capture', table.get('capture', {}).get('sha256') == oracle_scrub.digest(ORACLE / 'capture.json'),
          'capture:digest-mismatch')
    if hasattr(extractor, 'reconcile'):
        regenerated = extractor.reconcile(comparison.binary_only(table), ORACLE / 'capture.json')
        regenerated_problems = []
        for engine, section in (('claude', 'claude_code'), ('codex', 'codex')):
            for line in reference['streams'][engine]:
                event = comparison.event_name(line)
                schema = regenerated[section]['events'].get(event)
                regenerated_problems += comparison.conform(line, schema, event, True) if schema else [event + ':table:no-event']
        check('table/capture', regenerated == table and not regenerated_problems,
              'table:regeneration-disagrees: ' + ', '.join(regenerated_problems))
        # A field the binary's emitter writes only under a condition the capture's run met (system/init's
        # messaging_socket_path: the run bound its own messaging inbox) may be absent from a worker's line:
        # each captured line with such a field removed still conforms, in the committed and the rebuilt table.
        conditional_absent, absent_problems = [], []
        for event, emitter in table['claude_code'].get('emitters', {}).items():
            for number, line in enumerate(reference['streams']['claude'], 1):
                if comparison.event_name(line) != emitter['path'][0]:
                    continue
                node = line
                for step in emitter['path'][1:]:
                    node = node.get(step) if isinstance(node, dict) else None
                for key in sorted(set(emitter['conditional']) & set(node or {})):
                    stripped = json.loads(json.dumps(line))
                    holder = stripped
                    for step in emitter['path'][1:]:
                        holder = holder[step]
                    del holder[key]
                    conditional_absent.append('.'.join(emitter['path'] + [key]))
                    for built in (table, regenerated):
                        schema = built['claude_code']['events'][emitter['path'][0]]
                        absent_problems += comparison.conform(stripped, schema, emitter['path'][0], True)
        check('table/capture', 'system/init.messaging_socket_path' in conditional_absent and not absent_problems,
              'table:conditional-field-required: %s %s' % (sorted(set(conditional_absent)), absent_problems[:4]))
    else:
        check('table/capture', False, 'table:no-capture-reconciliation')

    scrubber = load('v172_scrub', SCRUBBER) if SCRUBBER.is_file() else None
    if scrubber:
        # Its allowlist is supplied explicitly for a copied mutation module, never from an ambient profile.
        rules = json.loads((ROOT / 'proof/VELDO-0172/allowlist.json').read_text())
        planted = {'type': 'assistant', 'host': 'new-host.fixture.invalid', 'pid': 932471,
                   'home': '/home/fixture-owner/work', 'unrecognized': 'ordinary-prose-with-no-identity-pattern',
                   'fraction': 0.375, 'usage': {'input_tokens': 7}, 'nested': [True, None, {'host': 'second-host'}]}
        scrubbed = scrubber.scrub(planted, rules=rules)
        check('capture/planted', scrubbed == oracle_scrub.scrub(planted, rules=rules), 'scrubber:planted-values-survived')
        # The oracle is this suite's independent assertion, not the implementation under mutation.
        check('capture/planted', scrubbed['host'] == '<string>' and scrubbed['pid'] == 0
              and scrubbed['home'] == '<string>' and scrubbed['fraction'] == 0.0
              and scrubbed['usage']['input_tokens'] == 7, 'scrubber:host-pid-home-or-token-count')
    else:
        check('capture/planted', False, 'scrubber:absent')
    if captured and scrubber:
        check('capture/allowlist', scrubber.scrub(captured, rules=rules) == captured,
              'capture:value-outside-allowlist')
        check('capture/allowlist', set(captured) == {'streams', 'taps'}
              and set(captured['taps']) == {'claude_initialize', 'codex_login_status'}
              and captured['taps']['claude_initialize'] == captured['streams']['claude'][0], 'capture:tap-set')
        scanner = load('v172_scan', ROOT / '.veldo/secret_scan.py')
        check('capture/allowlist', not scanner.scan_text(CAPTURE.read_text()), 'capture:secret-scan')
        check('capture/allowlist', captured == reference, 'capture:committed-readback')
    else:
        check('capture/allowlist', False, 'capture:absent')

    census = comparison.census(ROOT / 'scripts/suites')
    check('fake/capture', bool(census), 'census:empty')
    traces = []
    for suite in census:
        observed = []
        def observer(local):
            try:
                issues, trace = comparison.observe_fake(local, suite, table, reference)
            except Exception as error:
                observed.append('observer:did-not-complete:' + type(error).__name__)
                return
            observed.extend(issues)
            traces.extend(trace)
        # Suite-local namespaces keep the real tests independent; their format assertions also cover
        # every scripted line and uncaptured event, including error states. Their rows are not re-reported.
        inner_rows = []
        namespace = {'ROOT': ROOT, '__file__': str(suite), '__suite_file__': str(suite),
                     'expect': lambda name, ok: inner_rows.append((name, bool(ok))), '__engine_observer__': observer}
        source = COPIES.get(suite.name, suite).read_text()
        # The red archive predates the observer hook. Instrument only teardown, leaving its writers intact.
        if '__engine_observer__' not in source:
            source = re.sub(r'^    finally:\n', "    finally:\n        __engine_observer__(locals())\n", source, count=1, flags=re.M)
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(source, str(suite), 'exec'), namespace)
        checks = [(name, ok) for name, ok in inner_rows if 'format/' in name]
        check('fake/capture', bool(checks) and all(ok for _, ok in checks), suite.name + ':schema-conformance')
        check('fake/capture', any(t['suite'] == suite.name for t in traces), suite.name + ':no-writer-observed')
        check('fake/capture', not observed, suite.name + ':' + ', '.join(observed))
    expected = {(engine, comparison.event_name(line)) for engine in reference['streams'] for line in reference['streams'][engine]}
    check('fake/capture', expected <= {(t['engine'], t['event']) for t in traces}, 'census:capture-event-not-printed')
    globals()['__v172_observations__'] = {'census': [p.name for p in census], 'fake_lines': traces,
                                        'field_metrics': table.get('capture', {}).get('metrics', {})}
    print('VELDO-0172 census: %d suites, %d fake lines' % (len(census), len(traces)))
    for row, observations in rows.items():
        for ok, detail in observations:
            if not ok:
                print('VELDO-0172 %s detail: %s' % (row, detail))
        expect('VELDO-0172 ' + row, bool(observations) and all(ok for ok, _ in observations))


_v172_suite()
