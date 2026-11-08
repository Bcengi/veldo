#!/usr/bin/env python3
"""VELDO-0262 AC4: exchange time on the LangGraph runner and on the step runner, measured, not assumed.

  python3 proof/VELDO-0262/measure.py --python <langgraph interpreter> [--samples N] [--steps-runner FILE]
                                      [--sleep-ms MS] [--out FILE]

Both runners are driven through the PRODUCTION adapter (control_graph.Adapter over control_graph.exchange):
the same staging, environment, deadline and answer checks. The step runner is launched as production
launches it (the resolved base interpreter, -I -S -B); the LangGraph runner as the adapter launched it
before VELDO-0262 (its locked interpreter, -I -B). Samples are interleaved on one host, one runner then
the other, for three workloads: the default code definition (control_workflow_unit.CODE), the runtime
qualification workflow and a VELDO-0247 fan-out of 4, each a start and an advance. The LangGraph runner's
import and graph build time is measured in its own child: python -X importtime over a real exchange, and
perf_counter around its imports and its _build of the same workflow.

The claim holds when, for every workload and operation, the step runner's median is lower than the
LangGraph runner's median by at least 80 percent of the measured import and build time. --steps-runner
replaces the step runner's source; --sleep-ms MS makes the step runner sleep MS milliseconds at start (the
falsifier: MS is the measured LangGraph import and build time, so the claim must come out false). A case
where nothing ran on the LangGraph runner either (its answer says NO_RUNTIME, so it never imported
LangGraph) is reported as not applicable and left out of the claim.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
VELDO = ROOT / '.veldo'
GUARD = "\nif __name__ == '__main__':\n"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(text):
    return 'sha256:' + hashlib.sha256(text.encode()).hexdigest()


def p95(values):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, -(-95 * len(ordered) // 100) - 1))]


FAN = {'id': 'fan-4', 'entry': 'g', 'fields': {}, 'nodes': dict(
    {'g': {'kind': 'grooming', 'config': {}}, 'j': {'kind': 'join', 'config': {'inputs': ['t0', 't1', 't2', 't3']}},
     'done': {'kind': 'result_handling', 'config': {}}},
    **{'a%d' % i: {'kind': 'assignment', 'config': {}} for i in range(4)}),
    'transitions': [{'id': 't%d' % i, 'from': 'g', 'port': 'groomed', 'to': 'a%d' % i} for i in range(4)]
    + [{'id': 'u%d' % i, 'from': 'a%d' % i, 'port': 'done', 'to': 'j'} for i in range(4)]
    + [{'id': 'v', 'from': 'j', 'port': 'done', 'to': 'done'}]}


def sources(kind, steps_runner=None):
    """{workload: (runner source, workflow reference)} for one runner kind."""
    base = (VELDO / 'control_graph_langgraph.py').read_text() if kind == 'langgraph' else (
        Path(steps_runner).read_text() if steps_runner else (VELDO / 'control_graph_steps.py').read_text())
    if kind == 'steps' and SLEEP_MS:
        base = base.replace('\nimport sys\n', '\nimport sys\nimport time as _mutant_time\n_mutant_time.sleep(%r)\n'
                            % (SLEEP_MS / 1000), 1)
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'))
    unit = load('m262_unit', VELDO / 'control_workflow_unit.py')
    out = {}
    for name, definition in (('code', unit.CODE), ('fan-4', FAN)):
        text = canonical(definition)
        if kind == 'langgraph':
            block = (VELDO / 'control_workflow_langgraph.py').read_text() + '\nveldo_register_workflow(%r, 1)\n' % text
        else:
            block = (VELDO / 'control_workflow_steps.py').read_text() + '\nVELDO_DEFINITION = (%r, 1)\n' % text
        out[name] = (base.replace(GUARD, '\n' + block + GUARD, 1), {'id': definition['id'], 'version': 1, 'digest': sha(text)})
    runtime = load('m262_runtime', VELDO / 'control_runtime.py')
    out['qualification'] = (base.replace(GUARD, '\n' + runtime.QUALIFICATION + GUARD, 1),
                            {'id': runtime.QUALIFICATION_WORKFLOW, 'version': 1, 'digest': sha(runtime.QUALIFICATION)})
    return out


SLEEP_MS = 0
SNAPSHOT = {'id': 'measure-snapshot', 'version': 1, 'digest': sha('measure-snapshot')}
SUPPLIED = [{'id': 'qualification-rank', 'version': 1, 'digest': sha('rank'), 'value': {'rank': 7}},
            {'id': 'subject', 'version': 1, 'digest': sha('subject'), 'value': {'unit': 'unit-m', 'state': 'ready'}}]


def one(graph, runtime, flags, workflow, cycle):
    """A start then an advance through the production adapter; [(operation, elapsed ms, outcome)]."""
    graph.FLAGS = flags
    adapter = graph.Adapter(runtime, 'measure-domain', 'measure-repository')
    started = adapter.start(cycle, cycle + '.1', SNAPSHOT, workflow)
    resume = started.get('resume') or {'position': 'none', 'step': 0, 'notes': '{}'}
    adapter.advance(cycle, cycle + '.2', SNAPSHOT, workflow, resume, SUPPLIED)
    return [(o['operation'], o['elapsed_ms'], o['outcome'], o['runtime']) for o in adapter.observations]


def importtime(python, flags, source, request, scratch):
    """The child's own python -X importtime over a real exchange: [(module, self us, cumulative us)]."""
    runner = Path(scratch) / ('importtime-%s.py' % hashlib.sha256(source.encode()).hexdigest()[:12])
    runner.write_text(source)
    proc = subprocess.run([python, *flags, '-X', 'importtime', str(runner)], input=json.dumps(request).encode(),
                          capture_output=True, cwd=scratch, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, timeout=120)
    rows = []
    for line in proc.stderr.decode().splitlines():
        if line.startswith('import time:') and '|' in line and 'self [us]' not in line:
            own, cumulative, module = [part.strip() for part in line[len('import time:'):].split('|')]
            rows.append((module, int(own), int(cumulative)))
    return rows


BUILD = r'''
import json, sys, time
source = open(sys.argv[1]).read().replace("\nif __name__ == '__main__':\n", "\nif False:\n")
t0 = time.perf_counter()
import langgraph.graph, langgraph.types, langgraph.config, langgraph.errors
t1 = time.perf_counter()
namespace = {'__name__': 'measure'}
exec(compile(source, 'runner', 'exec'), namespace)
workflow = list(namespace['WORKFLOWS'].values())[0]
builds = []
for _ in range(int(sys.argv[2])):
    t2 = time.perf_counter()
    namespace['_build'](workflow)
    builds.append((time.perf_counter() - t2) * 1000)
print(json.dumps({'import_ms': (t1 - t0) * 1000, 'build_ms': builds}))
'''


def main(argv):
    options = dict(zip(argv[1::2], argv[2::2]))
    global SLEEP_MS
    python, samples = options['--python'], int(options.get('--samples', '50'))
    SLEEP_MS = float(options.get('--sleep-ms', '0'))
    graph = load('m262_graph', VELDO / 'control_graph.py')
    stdlib_flags, old_flags = ('-I', '-S', '-B'), ('-I', '-B')
    old, new = sources('langgraph'), sources('steps', options.get('--steps-runner'))
    data = {'samples': {}, 'import_build': {}, 'importtime': {}}
    with tempfile.TemporaryDirectory(prefix='veldo-measure-') as scratch:
        stage = Path(scratch) / 'stage'
        files = {}
        for kind, table in (('langgraph', old), ('steps', new)):
            for workload, (source, _) in table.items():
                path = Path(scratch) / ('%s-%s.py' % (kind, workload))
                path.write_text(source)
                files[(kind, workload)] = path
        runtimes = {'langgraph': (python, old_flags), 'steps': (graph.base_interpreter(), stdlib_flags)}
        for number in range(samples):
            for workload in ('code', 'qualification', 'fan-4'):
                for kind in (('langgraph', 'steps') if number % 2 == 0 else ('steps', 'langgraph')):
                    interpreter, flags = runtimes[kind]
                    runtime = {'python': interpreter, 'runner': str(files[(kind, workload)]), 'stage': str(stage)}
                    workflow = (old if kind == 'langgraph' else new)[workload][1]
                    for operation, elapsed, outcome, label in one(graph, runtime, flags, workflow, 'm%d' % number):
                        data['samples'].setdefault('%s/%s/%s' % (kind, workload, operation), []).append(elapsed)
                        data.setdefault('outcomes', {})['%s/%s/%s' % (kind, workload, operation)] = [outcome, label]
        graph.FLAGS = stdlib_flags
        request = {'schema': 'veldo.graph/v1', 'operation': 'start', 'cycle_id': 'c', 'command_id': 'c.1',
                   'domain_uuid': 'd', 'repository_uuid': 'r', 'snapshot': SNAPSHOT}
        for workload in ('code', 'qualification', 'fan-4'):
            proc = subprocess.run([python, '-I', '-B', '-c', BUILD, str(files[('langgraph', workload)]), str(samples)],
                                  capture_output=True, cwd=scratch, env={'PATH': '/usr/bin:/bin'}, timeout=600)
            data['import_build'][workload] = json.loads(proc.stdout)
            for kind, interpreter, flags in (('langgraph', python, old_flags), ('steps', graph.base_interpreter(), stdlib_flags)):
                rows = importtime(interpreter, flags, (old if kind == 'langgraph' else new)[workload][0],
                                  dict(request, workflow=(old if kind == 'langgraph' else new)[workload][1]), scratch)
                foreign = sorted({m.strip().split('.')[0] for m, _, _ in rows} - set(sys.stdlib_module_names))
                data['importtime'][kind + '/' + workload] = {
                    'modules': len(rows), 'total_self_ms': sum(r[1] for r in rows) / 1000,
                    'langgraph_cumulative_ms': sum(r[2] for r in rows if r[0].strip() == 'langgraph') / 1000,
                    'non_stdlib_top_level': foreign[:40]}
    summary, claims = {}, {}
    for key, values in sorted(data['samples'].items()):
        summary[key] = {'count': len(values), 'median': statistics.median(values), 'p95': p95(values)}
    for workload in ('code', 'qualification', 'fan-4'):
        measured = data['import_build'][workload]
        cost = measured['import_ms'] + statistics.median(measured['build_ms'])
        for operation in ('start', 'advance'):
            old_median = summary['langgraph/%s/%s' % (workload, operation)]['median']
            new_median = summary['steps/%s/%s' % (workload, operation)]['median']
            if data['outcomes']['langgraph/%s/%s' % (workload, operation)][1] == graph.NO_RUNTIME:
                claims['%s/%s' % (workload, operation)] = {
                    'applicable': False, 'reason': 'nothing ran on the LangGraph runner (NO_RUNTIME): it never imported '
                    'LangGraph', 'langgraph_median_ms': old_median, 'steps_median_ms': new_median}
                continue
            claims['%s/%s' % (workload, operation)] = {'applicable': True,
                'langgraph_median_ms': old_median, 'steps_median_ms': new_median, 'import_build_ms': cost,
                'saved_ms': old_median - new_median, 'required_ms': 0.8 * cost,
                'holds': old_median - new_median >= 0.8 * cost}
    try:
        load_average = os.getloadavg()
    except OSError:
        load_average = None
    cpu = next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                if line.startswith('model name')), platform.processor()) if Path('/proc/cpuinfo').is_file() else platform.processor()
    report = {'schema': 'veldo.measure/v1', 'method': __doc__.split('\n\n')[2].replace('\n', ' '),
              'host': platform.node(), 'cpu': cpu, 'cpus': os.cpu_count(), 'load_average': load_average,
              'python': platform.python_version(), 'samples_per_case': samples,
              'steps_runner': options.get('--steps-runner') or '.veldo/control_graph_steps.py',
              'summary': summary, 'claims': claims, 'claim_holds': all(c['holds'] for c in claims.values() if c['applicable']),
              'sleep_ms': SLEEP_MS,
              'import_build': data['import_build'], 'importtime': data['importtime'], 'outcomes': data['outcomes'],
              'samples': {k: [round(v, 3) for v in values] for k, values in sorted(data['samples'].items())}}
    out = options.get('--out')
    if out:
        Path(out).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'claim_holds': report['claim_holds'], 'claims': claims}, indent=1, sort_keys=True))
    return 0 if report['claim_holds'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
