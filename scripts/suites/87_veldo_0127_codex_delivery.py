"""Real pinned Codex wire, accepted role writes and the production receiver preflight."""
def _v127_delivery():
    import importlib.util
    from concurrent.futures import ThreadPoolExecutor
    import time
    from pathlib import Path

    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts/suites/x.py'))).resolve().parents[2]
    PRODUCTION = {
        'control_agent_config.py': ROOT / ".veldo" / "control_agent_config.py",
        'control_agent_config_handoff.py': ROOT / ".veldo" / "control_agent_config_handoff.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
    }
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    started = time.monotonic()
    delivery = load('v127_delivery_cases', ROOT / "proof/VELDO-0127" / "delivery_fixture.py")
    engine = load('v127_delivery_models', PRODUCTION['control_engine_codex.py'])
    # VELDO-0230: the qualified binary's models, from its record's bundled catalog.
    models = list(engine.model_tool_modes(ROOT / '.veldo' / 'runtime' / 'codex-qualification.json'))
    # Two disjoint factories, including SQLite connections and fault files. Each
    # still launches every singleton grant and retains its actual wire evidence.
    # VELDO-0261: each worker registers every row it will judge before its first case, and judges each one,
    # a row its cases never reached included, so a row is red or green, never absent.
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(delivery.run, ROOT, TREE, PRODUCTION, models[i::2]) for i in range(2)]
        rows, registered, slowest = {}, [], {}
        for future in futures:
            result = future.result()
            registered += result['registered']
            slowest.update(result['slowest'])
            for row, values in result['rows'].items():
                rows.setdefault(row, []).extend(values)
    seconds = time.monotonic() - started
    print('  VELDO-0127 delivery seconds: %.3f' % seconds)
    for name, (step, took) in sorted(slowest.items()):
        print('  VELDO-0127 delivery slowest step of %s: %s %.3f s' % (name, step, took))
    for row, values in rows.items():
        failed = [detail for passed, detail in values if not passed]
        expect('VELDO-0127 ' + row + (': ' + ' ; '.join(failed) if failed else ''), bool(values) and not failed)
    unjudged = [row for row in registered if not rows.get(row)]
    expect('VELDO-0127 delivery/completed' + (': not judged ' + ', '.join(unjudged) if unjudged else ''),
           bool(registered) and not unjudged)

_v127_delivery()
