"""VELDO-0358: Load-proof graph propagation (AC13). Independent scheduler closure with red and green controls.

Each closure runs independently; mutation targets retain their original row labels.
"""


def _v358d_load_graph():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import select
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    import types

    # The subjects, each named once so the mutation driver can put a mutant copy in its place.
    load_source = ROOT / "scripts" / "gate_load.py"
    legs_source = ROOT / "scripts" / "gate_legs.py"
    gate_source = ROOT / "scripts" / "verify.sh"
    schedule_source = ROOT / "scripts" / "gate_schedule.py"
    dispatcher_source = ROOT / "scripts" / "selftest.py"
    candidate_source = ROOT / "scripts" / "gate_candidate.py"
    sandbox_source = ROOT / "scripts" / "agent_sandbox.py"

    def row(name, problems):
        problems = [p for p in problems if p]
        expect('VELDO-0358 ' + name + (': ' + '; '.join(problems) if problems else ''), not problems)

    def module(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        return loaded

    env = {k: v for k, v in os.environ.items()
           if not k.startswith('VELDO_GATE_') and k not in ('VELDO_OPENED_LEDGER_FD', 'VELDO_SUITE_ORDER')}
    top = Path(tempfile.mkdtemp(prefix='v358d-'))
    python = sys.executable

    # ------------------------------------------------- AC13 under the graph scheduler: leg/graph-blocks
    # With scripts/gate_graph.json present the stages run as nodes of scripts/gate_schedule.py. The leg is
    # the node load (every other node before it, the mutation node after it). The scheduler below is the
    # real one from a fixture authority whose gate_legs.py answers --load-proof by the row's choice and
    # whose mutation stage only leaves a mark that it started; the graph and the catalog are the fixture's.
    authority = top / 'graph/authority'
    (authority / 'scripts').mkdir(parents=True)
    shutil.copyfile(str(schedule_source), str(authority / 'scripts/gate_schedule.py'))
    shutil.copyfile(str(legs_source), str(authority / 'scripts/gate_legs_real.py'))
    for name in ('gate_candidate.py', 'agent_sandbox.py', 'gate_fixtures.py', 'agent_sandbox.json'):  # how a catalog stage runs
        shutil.copyfile(str(ROOT / 'scripts' / name), str(authority / 'scripts' / name))
    shutil.copytree(str(ROOT / '.veldo'), str(authority / '.veldo'),
                    ignore=shutil.ignore_patterns('__pycache__', 'events.jsonl', 'last_verify'))
    (authority / 'scripts/gate_legs.py').write_text(
        'import json, os, sys\n'
        'from pathlib import Path\n'
        'if __name__ == "__main__" and "--load-proof" in sys.argv:\n'
        '    record = sys.argv[sys.argv.index("--record") + 1]\n'
        '    red = os.environ.get("V358G_LEG") == "red"\n'
        '    Path(record).write_text(json.dumps({"schema": "veldo.load-proof/v1", "state": "ran",\n'
        '                                        "verdict": "FAIL" if red else "pass"}) + "\\n")\n'
        '    print("fixture leg:", "red" if red else "green", flush=True)\n'
        '    sys.exit(1 if red else 0)\n'
        '_real = Path(__file__).with_name("gate_legs_real.py")\n'
        'exec(compile(_real.read_text(), str(_real), "exec"))\n')
    marks = top / 'graph/marks'
    marks.mkdir()
    (authority / 'scripts/check_gate_mutations.py').write_text(
        'import json, os, sys\n'
        'from pathlib import Path\n'
        'Path(os.environ["V358G_MARKS"], "mutation-started").write_text("started\\n")\n'
        'receipt = sys.argv[sys.argv.index("--receipt") + 1]\n'
        'Path(receipt).write_text(json.dumps({"status": "passed"}))\n')
    gscheduler = module('v358g_gate_schedule', authority / 'scripts/gate_schedule.py')

    class FixtureMeter:
        def __init__(self, name):
            self.name = name

        def command(self, argv):
            return argv

        def sample(self):
            return {'cpu_seconds': 0.01, 'peak_anon_bytes': 1024, 'metrics_source': 'fixture'}

        def finish(self):
            return dict(self.sample(), live_descendants=False)

    gnodes = {'lint': [], 'load': ['lint'], 'mutation': ['load']}
    graph_path = authority / 'scripts/gate_graph.json'
    graph_path.write_text(json.dumps({'schema': 'veldo.gate-graph/v1', 'nodes': {
        n: {'depends_on': d, 'writes_candidate': False, 'manager': 'none', 'ports': []} for n, d in gnodes.items()},
        'reserve': {'cpu': 0, 'memory': 0}, 'mutation_floor': {'cpu': 1, 'memory': 1024}}))
    candidate = top / 'graph/candidate'
    candidate.mkdir()

    def graph_gate(tag, leg, lint_code):
        for mark in marks.iterdir():
            mark.unlink()
        out = top / 'graph' / tag
        catalog = {'lint': '%s -c "raise SystemExit(%d)"' % (python, lint_code),
                   'load': 'authority load-proof leg', 'mutation': 'authority mutation stage'}
        saved = {k: os.environ.get(k) for k in ('V358G_LEG', 'V358G_MARKS')}
        os.environ.update(V358G_LEG=leg, V358G_MARKS=str(marks))
        try:
            receipt = gscheduler.run(catalog, candidate, out, out / 'legs', out / 'mutation-receipt',
                                     graph_path=graph_path, capacity={'cpu': 4, 'memory': 1 << 30, 'manager': 4},
                                     measurement_store=top / 'graph/store', meter_factory=FixtureMeter,
                                     guard_factory=lambda root: (lambda: True))
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        return receipt, (marks / 'mutation-started').exists(), out

    red, red_started, red_out = graph_gate('red', 'red', 0)
    green, green_started, _ = graph_gate('green', 'green', 0)
    before, before_started, _ = graph_gate('before', 'red', 1)
    real_graph = json.loads((ROOT / 'scripts' / 'gate_graph.json').read_text())['nodes']
    row('leg/graph-blocks', [
        red['stages'] != {'lint': 'pass', 'load': 'FAIL', 'mutation': 'not_started'}
        and 'a red leg under the scheduler: stages %s' % red['stages'],
        red_started and 'a red leg under the scheduler: the mutation stage started',
        not (red_out / 'load.record').is_file() and 'the leg left no record beside the scheduler\'s results',
        'not started: the load-proof leg is red' not in (red_out / 'mutation.log').read_text()
        and 'the held mutation node does not say why',
        green['stages'] != {'lint': 'pass', 'load': 'pass', 'mutation': 'pass'}
        and 'control: a green leg under the scheduler: stages %s' % green['stages'],
        not green_started and 'control: a green leg did not let the mutation stage start',
        before['stages'] != {'lint': 'FAIL', 'load': 'not_run', 'mutation': 'pass'}
        and 'a stage before the leg red: stages %s (the leg is not run, the mutation stage runs as on the '
            'serial path)' % before['stages'],
        not before_started and 'a stage before the leg red: the mutation stage did not start',
        real_graph.get('mutation', {}).get('depends_on') != ['load']
        and 'the real graph does not put the mutation node after the leg',
        set(real_graph.get('load', {}).get('depends_on', ())) != set(real_graph) - {'load', 'mutation'}
        and 'the real graph does not put the leg after every other node'])

    shutil.rmtree(str(top), ignore_errors=True)


_v358d_load_graph()
