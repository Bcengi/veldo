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
    models = list(engine.MODEL_TOOL_MODES)
    # Two disjoint factories, including SQLite connections and fault files. Each
    # still launches every singleton grant and retains its actual wire evidence.
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(delivery.run, ROOT, TREE, PRODUCTION, models[i::2]) for i in range(2)]
        rows = {}
        for future in futures:
            for row, values in future.result().items():
                rows.setdefault(row, []).extend(values)
    seconds = time.monotonic() - started
    rows['delivery/runtime'] = [seconds < 60]
    print('  VELDO-0127 delivery/runtime seconds: %.3f' % seconds)
    for row, values in rows.items():
        expect('VELDO-0127 ' + row, bool(values) and all(values))

_v127_delivery()
