"""VELDO-0045 as VELDO-0262 leaves it: the step runner's runtime journey (check, qualify, enforcement)
with no lock, no records and no install, the journey's installed assets, and enforcement with the step runner
hidden.

Only shared ROOT and expect are consumed. The reference installation is laid by the production
scaffolder from the canonical engine, and the production copies the mutation driver substitutes are laid
over it from their anchors. Everything the rows judge runs as a real command in that installation:
`control_runtime.py install | check | qualify | enforcement`, traced by an audit hook where a row needs to
know what the journey opened. The step runner runs in the resolved base interpreter (-I -S -B). The rows
of the removed LangGraph runtime (records against the lock, an altered lock hash, an altered wheel, an
omitted dependency) are removed with it, each listed in proof/VELDO-0262/removed-rows.json. Each region
reds its own rows on a raise, and a `ran/` row says whether it did, so a row that is red is red by its
assertion.
"""


def _v45_suite():
    import contextlib
    import hashlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import sys
    import sysconfig
    import tempfile

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_runtime.py': ROOT / ".veldo" / "control_runtime.py",
        'authorization.py': ROOT / ".veldo" / "authorization.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    OVERLAID = ('control_runtime.py', 'authorization.py')

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def run(command, cwd=None, env=None, stdin=None, timeout=300):
        return subprocess.run([str(c) for c in command], cwd=None if cwd is None else str(cwd), env=env,
                              input=stdin, stdin=None if stdin is not None else subprocess.DEVNULL,
                              capture_output=True, timeout=timeout)

    def report(proc):
        try:
            value = json.loads(proc.stdout.decode())
        except (ValueError, UnicodeDecodeError):
            return None
        return value if type(value) is dict else None

    emitted, raised, regions, observed = set(), [], [], {}

    def check(label, condition):
        emitted.add(label)
        expect('VELDO-0045 ' + label, bool(condition))

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

    graph_source = load('v45_graph_source', ROOT / '.veldo/control_graph.py')
    base_python = graph_source.base_interpreter()
    FIXED = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}

    # One audit hook traces a real command: every file it opens (absolute, as the process resolved it) and
    # every process it launches. It writes its log and nothing else.
    TRACE = r'''
import json, os, runpy, sys
log, script = sys.argv[1], sys.argv[2]
opened, launched = [], []
def hook(event, args):
    if event == 'open' and args and isinstance(args[0], (str, bytes)):
        opened.append([os.path.abspath(os.fsdecode(args[0])), str(args[1]) if len(args) > 1 else 'r'])
    elif event == 'subprocess.Popen':
        launched.append([str(a) for a in (args[1] if isinstance(args[1], (list, tuple)) else [args[1]])][:3])
sys.addaudithook(hook)
sys.argv = sys.argv[2:]
code = 0
try:
    runpy.run_path(script, run_name='__main__')
except SystemExit as error:
    code = error.code if type(error.code) is int else (0 if error.code is None else 1)
except BaseException as error:
    code = 'raised ' + type(error).__name__
done = list(opened)
with open(log, 'w') as out:
    json.dump({'exit': code, 'opened': done, 'launched': launched}, out)
'''

    def traced(tmp, name, script, argv, cwd, stdin=None, python=None, env=None):
        log = tmp / ('trace-' + name + '.json')
        proc = run([python or sys.executable, '-I', '-B', '-c', TRACE, log, script, *argv], cwd=cwd,
                   env=dict(env or FIXED, HOME=str(tmp)), stdin=stdin)
        try:
            trace = json.loads(log.read_text())
        except (OSError, ValueError):
            trace = {'exit': 'no trace', 'opened': [], 'launched': []}
        return proc, trace

    def under(path, base):
        path, base = os.path.realpath(path), os.path.realpath(str(base))
        return path == base or path.startswith(base + os.sep)

    with tempfile.TemporaryDirectory(prefix='v45-') as directory:
        tmp = Path(directory)
        installed = tmp / 'installed'
        stage = tmp / 'stage'
        state = {}

        # the reference installation, laid by the production scaffolder from the canonical engine
        regions.append('setup')
        try:
            scaffold = load('v45_scaffold', PRODUCTION['init_scaffold.py'])
            laid = scaffold.scaffold(installed, templates=ROOT / 'engine')
            laid_from = {}
            for rel in laid['created']:
                template = rel[len('.veldo/'):] if rel.startswith('.veldo/runtime/') else rel
                source = ROOT / 'engine' / template
                laid_from[rel] = digest(source) if source.is_file() else None
            for name in OVERLAID:
                if PRODUCTION[name].is_file():
                    shutil.copyfile(PRODUCTION[name], installed / '.veldo' / name)
                    laid_from['.veldo/' + name] = digest(PRODUCTION[name])
            state.update(created=set(laid['created']), laid_from=laid_from)
            runtime_py = installed / '.veldo' / 'control_runtime.py'
            state['cr'] = runtime_py
            evidence = load('v45_graph_installed', installed / '.veldo/control_graph.py').runtime_evidence()
        except Exception as error:  # noqa: BLE001 - recorded, then every row below reds by its assertion
            raised.append(('setup', repr(error)))
            evidence = None

        def cr(*argv, cwd=None, home=None):
            extra = ['--home', str(home)] if home is not None else []
            proc = run([sys.executable, '-B', state['cr'], *argv, *extra], cwd=cwd or installed,
                       env=dict(FIXED, HOME=str(tmp)))
            return proc, report(proc)

        # VELDO-0262: install answers runtime_removed, the step runner needs no install
        with region('runtime/install-removed'):
            proc, removed = cr('install')
            removed = removed or {}
            observed['install'] = {k: removed.get(k) for k in ('outcome', 'problems', 'taxonomy')}
            check('runtime/install-removed', proc.returncode == 1 and removed.get('outcome') == 'refused'
                  and removed.get('taxonomy') == ['unsupported_configuration']
                  and [p.split(':', 1)[0] for p in removed.get('problems') or []] == ['runtime_removed']
                  and 'needs no install' in (removed.get('problems') or [''])[0])

        # AC1: the actual nonpersistent adapter workload on the step runner
        with region('runtime/workload'):
            proc, qualified = cr('qualify', '--stage', tmp / 'qualify-stage')
            work = (qualified or {}).get('workload') or {}
            steps = work.get('steps') or []
            observed['workload'] = {k: work.get(k) for k in ('passed', 'steps', 'proposals', 'counts', 'pending', 'refused')}
            check('runtime/workload', evidence is not None and proc.returncode == 0 and (qualified or {}).get('outcome') == 'accepted'
                  and [(s.get('operation'), s.get('outcome')) for s in steps] == [
                      ('start', 'suspended'), ('suspend', 'suspended'), ('advance', 'proposal'),
                      ('start-second', 'suspended'), ('cancel', 'canceled')]
                  and all(s.get('runtime') == evidence for s in steps)
                  and work.get('proposals') == [{'type': 'priority', 'proposal_id': 'qualification-priority',
                                                 'subject': 'qualify-cycle', 'priority': 7}]
                  and work.get('counts') == {'accepted': 5, 'refused': 0} and work.get('pending') == []
                  and len(work.get('observations') or []) == 5)

        # observability: every activation says what it judged, and a refusal keeps its taxonomy
        with region('runtime/observations'):
            proc, fine = cr('check')
            broken = tmp / 'unreadable'
            shutil.copytree(installed, broken, symlinks=True)
            (broken / '.veldo/control_graph_steps.py').write_text('VERSION = None\n')
            proc_broken = run([sys.executable, '-B', broken / '.veldo/control_runtime.py', 'check'], cwd=broken,
                              env=dict(FIXED, HOME=str(tmp)))
            unreadable = report(proc_broken) or {}
            fields = {'schema', 'operation', 'journey', 'runtime', 'problems', 'outcome', 'taxonomy', 'counts'}
            fine = fine or {}
            observed['observations'] = {'accepted': {k: fine.get(k) for k in ('outcome', 'taxonomy', 'counts', 'runtime')},
                                        'unreadable': {k: unreadable.get(k) for k in ('problems', 'taxonomy')}}
            check('runtime/observations', all(set(a) == fields for a in (fine, unreadable))
                  and all(a.get('operation') == 'activate' for a in (fine, unreadable))
                  and fine.get('outcome') == 'accepted' and fine.get('taxonomy') == []
                  and fine.get('counts') == {'accepted': 1, 'refused': 0}
                  and (fine.get('runtime') or {}).get('python') == base_python
                  and (fine.get('runtime') or {}).get('version') == (evidence or {}).get('version')
                  and unreadable.get('outcome') == 'refused' and unreadable.get('taxonomy') == ['unavailable_service']
                  and unreadable.get('problems') == ['runtime_unreadable:ValueError']
                  and unreadable.get('counts') == {'accepted': 0, 'refused': 1})

        # AC2: the journey's every reached asset is installed, with the digest it was laid with
        with region('journey/assets-installed'):
            proc, trace = traced(tmp, 'journey', state['cr'], ['qualify', '--stage', stage], cwd=installed)
            answer = report(proc) or {}
            journey = set((answer.get('activation') or {}).get('journey') or [])
            reached, fallback, elsewhere, wrote, probed, bytecode = set(), [], [], [], 0, {}
            for path, mode in trace['opened']:
                # The audit event comes before the open, so a probe for a file that is not there (bytecode
                # the interpreter looks for first) is an attempt, not a reach. Any attempt under the source
                # tree is a fallback, whether or not it found something.
                if under(path, ROOT):
                    fallback.append(path)
                    continue
                if not os.path.isfile(path):
                    probed += 1
                    continue
                if under(path, installed):
                    rel = os.path.relpath(os.path.realpath(path), os.path.realpath(str(installed)))
                    if 'w' in mode or 'a' in mode:
                        wrote.append(rel)
                        continue
                    parts = rel.split('/')
                    if len(parts) > 2 and parts[-2] == '__pycache__' and parts[-1].endswith('.pyc'):
                        # Bytecode the installation compiled from its own source (the scaffolder's index run
                        # writes it): the reach is that source, and the interpreter's own rule (the source's
                        # mtime and size in the header) says whether the bytecode is its compiled form.
                        source = '/'.join(parts[:-2] + [parts[-1].split('.')[0] + '.py'])
                        header, facts = Path(path).read_bytes()[:16], os.stat(installed / source)
                        bytecode[rel] = (int.from_bytes(header[4:8], 'little') == 0
                                         and int.from_bytes(header[8:12], 'little') == int(facts.st_mtime) & 0xFFFFFFFF
                                         and int.from_bytes(header[12:16], 'little') == facts.st_size & 0xFFFFFFFF)
                        rel = source
                    reached.add(rel)
                elif not (under(path, stage) or under(path, sysconfig.get_path('stdlib'))
                          or under(path, tempfile.gettempdir()) or path.startswith(('/dev/', '/proc/'))):
                    elsewhere.append(path)
            mismatched = sorted(rel for rel in reached if rel not in state['laid_from']
                                or state['laid_from'][rel] != digest(installed / rel))
            # The runner child the adapter launched, run again under the runtime with the same tracer.
            staged = sorted((stage / 'runners').glob('*.py')) if (stage / 'runners').is_dir() else []
            child = {'staged': len(staged)}
            if staged:
                graph = load('v45_graph', installed / '.veldo/control_graph.py')
                request = {'schema': 'veldo.graph/v1', 'operation': 'start', 'cycle_id': 'trace-cycle',
                           'command_id': 'trace-command', 'domain_uuid': 'trace-domain', 'repository_uuid': 'trace-repository',
                           'snapshot': {'id': 'trace-snapshot', 'version': 1, 'digest': 'sha256:' + 'c' * 64},
                           'workflow': (answer.get('workload') or {}).get('workflow')}
                empty_cwd = tmp / 'runner-cwd'
                empty_cwd.mkdir()
                run_proc, run_trace = traced(tmp, 'runner', staged[0], [], cwd=empty_cwd, python=base_python,
                                             stdin=json.dumps(request).encode(), env=dict(graph.ENVIRONMENT))
                stdlib = [p.decode().strip() for p in run([base_python, '-I', '-S', '-c',
                          'import sysconfig; print(sysconfig.get_path("stdlib"))'], env=FIXED).stdout.splitlines()]
                child_other = []
                for path, _mode in run_trace['opened']:
                    if not os.path.isfile(path) and not under(path, ROOT) and not under(path, installed):
                        continue  # an attempt at a file that is not there reaches nothing
                    if not (under(path, staged[0]) or any(under(path, s) for s in stdlib) or under(path, tmp / 'trace-runner.json')
                              or path.startswith(('/dev/', '/proc/'))):
                        child_other.append(path)
                child.update(answer=(report(run_proc) or {}).get('outcome'), runtime_label=(report(run_proc) or {}).get('runtime'),
                             outside=sorted(child_other)[:20], exit=run_trace['exit'])
            observed['journey'] = {'exit': proc.returncode, 'outcome': answer.get('outcome'), 'trace_exit': trace['exit'],
                                   'reached_installed': sorted(reached), 'declared': sorted(journey), 'fallback': fallback[:20],
                                   'elsewhere': elsewhere[:20], 'wrote': wrote, 'mismatched': mismatched, 'probed': probed,
                                   'bytecode': bytecode, 'runner_child': child}
            check('journey/assets-installed', proc.returncode == 0 and answer.get('outcome') == 'accepted'
                  and answer.get('operation') == 'qualify' and trace['exit'] == 0
                  and reached == journey and {'.veldo/control_graph.py', '.veldo/control_graph_steps.py'} <= reached
                  and reached <= state['created'] and not mismatched and not fallback and not elsewhere and not wrote
                  and all(bytecode.values())
                  and child.get('answer') == 'suspended' and child.get('runtime_label') == evidence
                  and not child.get('outside'))

        # AC2: an omitted asset is a named failure, never a read of the source tree
        with region('journey/omitted-asset-named'):
            named = {}
            for rel in ('.veldo/control_graph_steps.py', '.veldo/control_graph.py'):
                tree = tmp / ('omitted-' + Path(rel).name)
                shutil.copytree(installed, tree, symlinks=True)
                (tree / rel).unlink(missing_ok=True)
                # From the source tree, where every omitted asset has a canonical copy to fall back to.
                proc, trace = traced(tmp, 'omitted-' + Path(rel).name, tree / '.veldo/control_runtime.py', ['check'], cwd=ROOT)
                answer = report(proc) or {}
                named[rel] = {'exit': trace['exit'], 'problems': answer.get('problems'),
                              'source_tree_reads': [p for p, _m in trace['opened'] if under(p, ROOT)][:10],
                              'traceback': b'Traceback' in proc.stderr}
            observed['omitted_asset'] = named
            check('journey/omitted-asset-named', all(
                n['exit'] == 1 and n['problems'] == ['missing_asset:' + rel] and not n['source_tree_reads'] and not n['traceback']
                for rel, n in named.items()))

        # AC3: every enabled installed enforcement entry, with the runtime hidden
        with region('enforcement/entries-enumerated', 'enforcement/no-runtime', 'enforcement/graph-unavailable'):
            proc = run([sys.executable, '-B', state['cr'], 'enforcement', '--root', installed], cwd=installed,
                       env=dict(FIXED, HOME=str(tmp)))
            verdict = report(proc) or {}
            entries = verdict.get('entries') or []
            derived = set()
            for script in ('scripts/verify.sh', 'scripts/veldo-guard.sh'):
                for line in (installed / script).read_text().splitlines():
                    if line.lstrip().startswith('#') or re.match(r'\s*CHECK_\w+="(na|waived):', line):
                        continue
                    # Shell operators are words of their own, so an argument list stops at them.
                    words = re.findall(r'[;|&()<>`]|[^\s;|&()<>`"=$]+', line)
                    for at, word in enumerate(words[:-1]):
                        if word in ('python3', 'required:python3') and words[at + 1].endswith('.py'):
                            argv = []
                            for following in words[at + 2:]:
                                if not re.fullmatch(r'[a-z][a-z-]*', following):
                                    break
                                argv.append(following)
                            derived.add((words[at + 1], tuple(argv)))
            if (installed / '.veldo/authorization.py').is_file():
                derived.add(('.veldo/authorization.py', ()))
            listed = {(e['module'], tuple(e['argv'])) for e in entries}
            observed['enforcement'] = {'exit': proc.returncode, 'passed': verdict.get('passed'), 'hidden': verdict.get('hidden'),
                                       'entries': [{k: e.get(k) for k in ('module', 'argv', 'status', 'exit', 'refused_imports',
                                                                         'hidden_hits', 'static_violations', 'exception')}
                                                   for e in entries],
                                       'derived': sorted(map(list, derived)), 'graph': verdict.get('graph')}
            check('enforcement/entries-enumerated', listed == derived and ('.veldo/validate.py', ('all',)) in listed
                  and ('.veldo/authorization.py', ()) in listed and ('.veldo/shape_gate.py', ()) in listed)
            check('enforcement/no-runtime', entries and all(
                e.get('status') == 'pass' and e.get('exit') in (e.get('verdicts') or []) and not e.get('refused_imports')
                and not e.get('hidden_hits') and not e.get('static_violations') and e.get('exception') is None for e in entries)
                and verdict.get('hidden') == [os.path.realpath(str(installed / '.veldo/control_graph_steps.py'))])
            probe = verdict.get('graph') or {}
            answers = [a for a in probe.get('answers') or [] if type(a) is dict]
            proc_present, present = cr('check')
            check('enforcement/graph-unavailable', probe.get('status') == 'pass'
                  and [(a.get('home'), a.get('refusal')) for a in answers] == [('absent', 'runtime_unavailable'),
                                                                               ('hidden', 'runtime_unavailable')]
                  and 'asset is absent' in answers[0].get('detail', '') and 'runtime_unreadable' in answers[1].get('detail', '')
                  and probe.get('hidden_hits') and (present or {}).get('outcome') == 'accepted')

        for first in regions:
            check('ran/' + first, first not in {label for label, _ in raised})
        observed['raised'] = raised
    globals()['_V45_OBSERVED'] = observed


_v45_started = __import__('time').monotonic()
_v45_suite()
_V45_SECONDS = __import__('time').monotonic() - _v45_started
