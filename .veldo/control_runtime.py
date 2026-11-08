#!/usr/bin/env python3
"""The step runner's runtime journey: check, qualify and enforcement (VELDO-0045, VELDO-0262). Standard library only.

  python3 .veldo/control_runtime.py check [--home DIR]                   the step runner asset and interpreter
  python3 .veldo/control_runtime.py qualify [--home DIR] [--stage DIR]   check and the workload
  python3 .veldo/control_runtime.py enforcement [--root REPOSITORY]      enforcement with the runner hidden
  python3 .veldo/control_runtime.py install                              answers runtime_removed

Built on VELDO-0043 and never a second copy of it: the adapter is control_graph.py, the runner is
control_graph_steps.py and the isolated-enforcement harness is control_graph_isolation.py. There is no
lock, no records and no install: the step runner is standard library only and runs in the resolved base
interpreter started -I -S -B, so `install` answers runtime_removed (unsupported_configuration): the step
runner needs no install.

CHECK. The runner may be used only when every check below passes; each failure is a named problem and
any problem refuses it (graph invocation then reports runtime_unavailable):
  - every journey asset (JOURNEY) is present in THIS installation, read from this installation's own
    .veldo and nowhere else (no source-tree fallback), else missing_asset;
  - the step runner declares its version, read statically and never imported, else runtime_unreadable;
  - control_graph.runtime_problems finds no repository behind the interpreter (runtime_isolation).

QUALIFICATION runs the actual nonpersistent adapter workload on the step runner: the production runner
with one deterministic workflow registered before its entry point (no model, no network), and start,
suspend, advance and cancel through the production adapter, each answer labelled by the step runner.

ENFORCEMENT enumerates the installation's enabled enforcement entries from its own gate and guard
(every `python3 <module>.py` they run) plus the installed authorization entry, and runs each real
command in an isolated -I -S child whose import finder refuses anything but the standard library and
the installed siblings (control_graph_isolation's harness) and whose audit hook refuses, and records,
any open, listing or launch of the step runner asset. Every entry must pass with the runner hidden;
graph invocation, asked the same way, must report runtime_unavailable, as it must with the runner absent.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SCHEMA = 'veldo.runtime-activation/v1'
RUNNER = 'control_graph_steps.py'
# Every installed asset the journey (check, qualify) reaches, relative to .veldo.
JOURNEY = ('control_runtime.py', 'control_graph.py', RUNNER, 'git_process.py')
TAXONOMY = {
    'missing_asset': 'missing_evidence', 'runtime_absent': 'unavailable_service',
    'runtime_unreadable': 'unavailable_service', 'runtime_isolation': 'invalid_input',
    'tooling_failed': 'unknown_outcome', 'runtime_removed': 'unsupported_configuration',
}
COUNTS = {'accepted': 0, 'refused': 0}
DOMAIN = REPOSITORY = 'runtime-qualification'
QUALIFICATION_WORKFLOW = 'veldo-runtime-qualification'
QUALIFICATION = r'''
# VELDO-0045 qualification: deterministic and nonpersistent, no model, no network
def _qualification_intake(view):
    return {'next': 'rank', 'suspend': True, 'notes': {'snapshot': view['snapshot']['id']}}


def _qualification_rank(view):
    ranks = [item['value'].get('rank') for item in view['supplied_results'] if type(item.get('value')) is dict]
    if len(ranks) != 1 or type(ranks[0]) is not int:
        return {'failure': {'code': 'invalid_input', 'detail': 'the qualification cycle takes one supplied rank'}}
    return {'next': None, 'proposals': [{'type': 'priority', 'proposal_id': 'qualification-priority',
                                          'subject': view['identity']['cycle_id'], 'priority': ranks[0]}]}


WORKFLOWS['veldo-runtime-qualification'] = {'version': 1, 'entry': 'intake',
                                            'nodes': {'intake': _qualification_intake, 'rank': _qualification_rank}}
'''
# Enforcement: the installed gate and guard name the gate imports; authorization is its own entry.
GATE, GUARD = 'scripts/verify.sh', 'scripts/veldo-guard.sh'
AUTHORIZATION = ('.veldo/authorization.py',)
VERDICTS = {'.veldo/policy_check.py': (0, 1), '.veldo/version.py': (0, 1, 2)}
INVOCATION = re.compile(r'\bpython3\s+((?:\./)?[\w./-]+\.py)((?:[ \t]+[a-z][a-z-]*)*)')
DECLARATION = re.compile(r'^\s*CHECK_\w+="([^"]*)"')
PROBE = ('.veldo/control_runtime.py', ('--probe-graph',))
# Prepended to control_graph_isolation's harness: the step runner asset is hidden, not merely unimported.
# The harness allows sys.stdlib_module_names, and CPython 3.12.3 leaves one standard library module out of
# that list: _wmi, the Windows-only extension platform.py imports inside try/except ImportError (reached
# by events.py through uuid). Without it the harness refuses a standard library import, so the list it
# reads is completed by exactly the names in STDLIB_OMITTED.
STDLIB_OMITTED = ('_wmi',)
HIDE = r'''
import atexit as _hide_atexit, json as _hide_json, os as _hide_os, sys as _hide_sys
_hide_sys.stdlib_module_names = frozenset(_hide_sys.stdlib_module_names | set(%r))
_HIDDEN = tuple(_hide_json.loads(_hide_sys.argv.pop(1)))
_HIDE_HITS = []
_HIDE_REPORT = _hide_sys.argv[3] + '.hidden'
def _hide_under(path):
    if isinstance(path, int) or path is None:
        return False
    try:
        text = _hide_os.path.realpath(_hide_os.fsdecode(path))
    except (TypeError, ValueError):
        return False
    return any(text == root or text.startswith(root + '/') for root in _HIDDEN)
def _hide_hook(event, args):
    if event not in ('open', 'os.listdir', 'os.scandir', 'subprocess.Popen', 'os.exec', 'os.posix_spawn', 'os.spawn'):
        return
    places = [args[0]] if args else []
    if event != 'open' and len(args) > 1 and isinstance(args[1], (list, tuple)) and args[1]:
        places.append(args[1][0])
    for place in places:
        if _hide_under(place):
            _HIDE_HITS.append([event, _hide_os.fsdecode(place)])
            raise PermissionError('the step runner is hidden: ' + _hide_os.fsdecode(place))
_hide_sys.addaudithook(_hide_hook)
def _hide_write():
    with open(_HIDE_REPORT, 'w') as out:
        out.write(_hide_json.dumps(_HIDE_HITS))
_hide_atexit.register(_hide_write)
''' % (STDLIB_OMITTED,)
_LOADED = {}


def _load(name, file):
    if file not in _LOADED:
        spec = importlib.util.spec_from_file_location(name, _asset(file))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _LOADED[file] = module
    return _LOADED[file]


def _asset(rel):
    """A journey asset of THIS installation: its own .veldo copy, never another tree's."""
    return HERE / rel


def _graph():
    return _load('veldo_runtime_control_graph', 'control_graph.py')


def sha256(data):
    return hashlib.sha256(data if type(data) is bytes else data.encode()).hexdigest()


def _finish(report, problems):
    report['problems'] = list(dict.fromkeys(problems))
    report['outcome'] = 'refused' if report['problems'] else 'accepted'
    report['taxonomy'] = sorted({TAXONOMY.get(p.split(':', 1)[0], 'unknown_outcome') for p in report['problems']})
    COUNTS[report['outcome']] += 1
    report['counts'] = dict(COUNTS)
    return report


def activation(home=None):
    """Whether the step runner may be used, as a report with every named problem."""
    report = {'schema': SCHEMA, 'operation': 'activate', 'journey': ['.veldo/' + rel for rel in JOURNEY],
              'runtime': None}
    missing = ['missing_asset:.veldo/' + rel for rel in JOURNEY if not _asset(rel).is_file()]
    if missing:
        return _finish(report, missing)
    graph = _graph()
    python = graph.base_interpreter()
    report['runtime'] = {'python': python, 'runner': '.veldo/' + RUNNER}
    problems = []
    try:
        report['runtime']['version'] = graph.declared_version(_asset(RUNNER))
        problems += ['runtime_isolation:' + text for text in graph.runtime_problems({'python': python})]
    except (OSError, RuntimeError, ValueError, SyntaxError) as error:
        problems.append('runtime_unreadable:' + (getattr(error, 'strerror', None) or type(error).__name__))
    return _finish(report, problems)


def adapter(domain_uuid, repository_uuid, home=None, stage=None, timeout=120):
    """The graph adapter over the step runner, only once the check accepts it."""
    graph = _graph()
    report = activation(home)
    if report['outcome'] != 'accepted':
        raise graph.Refused('runtime_unavailable', 'the step runner cannot be used ('
                            + '; '.join(report['problems'][:6]) + ')')
    return graph.Adapter.installed(domain_uuid, repository_uuid, home=home, timeout=timeout, stage=stage)


def qualification_runner():
    """The production runner with the qualification workflow registered before its entry point."""
    source = _asset(RUNNER).read_text()
    guard = "\nif __name__ == '__main__':\n"
    if source.count(guard) != 1:
        raise ValueError('the runner has no single entry point to register the qualification workflow before')
    return source.replace(guard, '\n' + QUALIFICATION + guard, 1)


def _workload(graph, runtime, workflow):
    adapter = graph.Adapter(runtime, DOMAIN, REPOSITORY, evidence=graph.runtime_evidence())
    snapshot = {'id': 'qualification-snapshot', 'version': 1, 'digest': 'sha256:' + sha256('qualification-snapshot')}
    supplied = [{'id': 'qualification-rank', 'version': 1, 'digest': 'sha256:' + sha256('rank-7'), 'value': {'rank': 7}}]
    answers = {}
    try:
        answers['start'] = adapter.start('qualify-cycle', 'qualify-start', snapshot, workflow)
        answers['suspend'] = adapter.suspend('qualify-cycle', 'qualify-suspend', workflow, answers['start'].get('resume'))
        answers['advance'] = adapter.advance('qualify-cycle', 'qualify-advance', snapshot, workflow,
                                             answers['suspend'].get('resume'), supplied)
        answers['start-second'] = adapter.start('qualify-second', 'qualify-start-second', snapshot, workflow)
        answers['cancel'] = adapter.cancel('qualify-second', 'qualify-cancel', workflow,
                                           answers['start-second'].get('resume'))
    except graph.Refused as error:
        answers['refused'] = {'code': error.code, 'detail': error.detail[:300]}
    evidence = graph.runtime_evidence()
    expected = {'start': 'suspended', 'suspend': 'suspended', 'advance': 'proposal', 'start-second': 'suspended',
                'cancel': 'canceled'}
    passed = ('refused' not in answers and all(answers[k]['outcome'] == v for k, v in expected.items())
              and all(answers[k]['runtime'] == evidence for k in expected)
              and answers['advance']['proposals'] == [{'type': 'priority', 'proposal_id': 'qualification-priority',
                                                       'subject': 'qualify-cycle', 'priority': 7}]
              and adapter.pending() == [])
    return {'workflow': workflow, 'passed': passed, 'evidence': evidence,
            'steps': [{'operation': k, 'outcome': v.get('outcome'), 'runtime': v.get('runtime')} for k, v in answers.items()
                      if k != 'refused'], 'refused': answers.get('refused'),
            'proposals': answers.get('advance', {}).get('proposals'), 'counts': dict(adapter.counts),
            'pending': adapter.pending(), 'observations': adapter.observations,
            'durations': graph.exchange_durations(adapter.observations)}


def qualify(home=None, stage=None):
    """The check, then the actual nonpersistent adapter workload on the step runner."""
    report = {'schema': SCHEMA, 'operation': 'qualify', 'activation': activation(home), 'workload': None}
    if report['activation']['outcome'] != 'accepted':
        return _finish(report, report['activation']['problems'])
    graph = _graph()
    base = graph.Adapter.installed(DOMAIN, REPOSITORY, home=home, stage=stage).runtime
    if base is None:
        return _finish(report, ['runtime_absent:.veldo/' + RUNNER])
    workflow = {'id': QUALIFICATION_WORKFLOW, 'version': 1, 'digest': 'sha256:' + sha256(QUALIFICATION)}
    with tempfile.TemporaryDirectory(prefix='veldo-qualify-') as scratch:
        runner = Path(scratch) / RUNNER
        runner.write_text(qualification_runner())
        report['workload'] = _workload(graph, dict(base, runner=str(runner)), workflow)
    return _finish(report, [] if report['workload']['passed'] else ['tooling_failed:qualification workload'])


def install(home=None, stage=None):
    """There is nothing to install: the answer is runtime_removed."""
    return _finish({'schema': SCHEMA, 'operation': 'install'},
                   ['runtime_removed:the step runner is standard library only and needs no install'])


def enforcement_entries(root):
    """Every enabled enforcement entry of an installation: each `python3 <module>.py` its gate and guard
    run (a catalog slot only when it is required), then the installed authorization entry."""
    root, entries = Path(root), {}
    for script in (GATE, GUARD):
        path = root / script
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            if line.lstrip().startswith('#'):
                continue
            declared = DECLARATION.match(line)
            if declared and not declared.group(1).startswith('required:'):
                continue
            for found in INVOCATION.finditer(line):
                module = found.group(1)[2:] if found.group(1).startswith('./') else found.group(1)
                entries.setdefault((module, tuple(found.group(2).split())), script)
    for module in AUTHORIZATION:
        if (root / module).is_file():
            entries.setdefault((module, ()), 'authorization')
    return [{'module': module, 'argv': list(argv), 'source': source, 'verdicts': list(VERDICTS.get(module, (0,)))}
            for (module, argv), source in sorted(entries.items())]


def _hidden_roots():
    return [os.path.realpath(str(_asset(RUNNER)))]


def run_hidden(root, module, argv, hidden, timeout=120):
    """One real command in the isolated harness with the step runner hidden."""
    isolation = _load('veldo_runtime_isolation', 'control_graph_isolation.py')
    veldo = root / '.veldo'
    entry = os.path.relpath(root / module, veldo)
    with tempfile.TemporaryDirectory(prefix='veldo-hidden-') as scratch:
        report = Path(scratch) / 'report.json'
        env = dict(isolation.ENVIRONMENT, HOME=scratch, TMPDIR=scratch)
        proc = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', HIDE + isolation.HARNESS, json.dumps(hidden),
                               str(veldo), entry, str(report), *argv], cwd=root, env=env, capture_output=True,
                              stdin=subprocess.DEVNULL, timeout=timeout)
        hits = Path(str(report) + '.hidden')
        if proc.returncode or not report.is_file():
            return {'exit': None, 'exception': 'harness_failed', 'refused': [], 'hidden': [],
                    'stdout': proc.stdout.decode(errors='replace')[-2000:]}
        ran = json.loads(report.read_text())
        ran['hidden'] = json.loads(hits.read_text()) if hits.is_file() else ['hidden report missing']
        ran['stdout'] = proc.stdout.decode(errors='replace')[-2000:]
        return ran


def enforcement(root=None):
    """Every enabled enforcement entry, run with the runner hidden; graph invocation reports unavailable."""
    isolation = _load('veldo_runtime_isolation', 'control_graph_isolation.py')
    root = Path(root or HERE.parent).resolve()
    veldo, hidden = root / '.veldo', _hidden_roots()
    results = []
    for entry in enforcement_entries(root):
        if not (root / entry['module']).is_file():
            results.append(dict(entry, status='not_installed'))
            continue
        static = isolation.closure(veldo, os.path.relpath(root / entry['module'], veldo))
        ran = run_hidden(root, entry['module'], entry['argv'], hidden)
        ok = (not static['violations'] and not ran['refused'] and ran['exception'] is None
              and ran['exit'] in entry['verdicts'] and not ran['hidden'])
        results.append(dict(entry, status='pass' if ok else 'fail', closure=static['modules'],
                            static_violations=static['violations'], refused_imports=ran['refused'],
                            hidden_hits=ran['hidden'], exception=ran['exception'], exit=ran['exit']))
    probe = {'module': PROBE[0], 'argv': list(PROBE[1]), 'status': 'not_installed'}
    if (root / PROBE[0]).is_file():
        ran = run_hidden(root, PROBE[0], PROBE[1], hidden)
        try:
            answers = json.loads(ran['stdout'].strip().splitlines()[-1])['probe']
        except (ValueError, IndexError, KeyError, TypeError):
            answers = []
        ok = ran['exception'] is None and not ran['refused'] and ran['exit'] == 0
        probe.update(status='pass' if ok else 'fail', answers=answers, refused_imports=ran['refused'],
                     exception=ran['exception'], exit=ran['exit'], hidden_hits=ran['hidden'])
    passed = all(r['status'] != 'fail' for r in results) and probe['status'] == 'pass'
    return {'schema': 'veldo.runtime-enforcement/v1', 'operation': 'enforcement', 'root': str(root),
            'hidden': hidden, 'entries': results, 'graph': probe, 'passed': passed}


def probe_graph():
    """Graph invocation with the runner asset absent and, inside the hidden harness, hidden: both must
    report runtime_unavailable. Outside the harness the runner is not hidden, so the second answer is not
    a refusal and the probe fails, as it should."""
    graph = _graph()
    answers = []
    version = {'id': 'probe', 'version': 1, 'digest': 'sha256:' + '0' * 64}
    with tempfile.TemporaryDirectory(prefix='veldo-no-runtime-') as empty:
        for label in ('absent', 'hidden'):
            try:
                if label == 'absent':
                    graph.Adapter(graph.resolve_runtime(empty, runner=Path(empty) / RUNNER), 'probe-domain',
                                  'probe-repository').start(
                        'probe-cycle', 'probe-command', version, version)
                else:
                    adapter('probe-domain', 'probe-repository', home=empty, stage=Path(empty) / 'stage').start(
                        'probe-cycle', 'probe-command', version, version)
                answers.append({'home': label, 'refusal': None})
            except graph.Refused as error:
                answers.append({'home': label, 'refusal': error.code, 'detail': error.detail[:300]})
    print(json.dumps({'probe': answers}))
    return 0 if [a['refusal'] for a in answers] == ['runtime_unavailable'] * 2 else 1


def main(argv):
    if argv[1:] == ['--probe-graph']:
        return probe_graph()
    command, options = (argv[1] if len(argv) > 1 else None), dict(zip(argv[2::2], argv[3::2]))
    allowed = {'install': {'--home', '--stage'}, 'check': {'--home'}, 'qualify': {'--home', '--stage'},
               'enforcement': {'--root'}}
    if command not in allowed or len(argv[2:]) % 2 or not set(options) <= allowed[command]:
        print(__doc__.split('\n\n')[0])
        return 2
    home, stage = options.get('--home'), options.get('--stage')
    if command == 'enforcement':
        report = enforcement(options.get('--root'))
        print(json.dumps(report, indent=1, sort_keys=True))
        return 0 if report['passed'] else 1
    report = {'install': lambda: install(home, stage), 'check': lambda: activation(home),
              'qualify': lambda: qualify(home, stage)}[command]()
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if report['outcome'] == 'accepted' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
