"""VELDO-0271: the gate runs every stage as one leg, with no namespace sandbox and no root helper.

Run: python3 scripts/selftest.py --suite 141_veldo_0271_gate_without_sandbox

Only shared ROOT and expect are consumed. Every gate here is a fixture: this repository's verify.sh,
gate_candidate.py, selftest.py, run_scope.py, check_gate_mutations.py and gate_host.py over scratch
repositories with stub stages. The literal paths below are the anchors the registered mutation driver
replaces with its copy, so a mutation of any of them reaches the rows. The fixture unit stage starts a
transient unit in the systemd user manager and traces a child with strace; the host rows take a scratch
lock and a real user scope. Nothing is written outside temporary directories.

Rows, by acceptance criterion:
  AC1 one-leg/user-manager-and-strace-in-one-stage, one-leg/stamp-has-no-unconfined-field,
      one-leg/unit-stage-reports-every-suite, one-leg/stdin-is-end-of-file
  AC2 kept/authority-scripts-judge, kept/host-lock-not-started, kept/scope-memory-limit,
      kept/no-credential-variable
  AC3 mutation/every-run-fresh
  AC4 removed/seven-names-gone, removed/lease-not-loaded, removed/lease-only,
      removed/leftover-reported, removed/leftover-silent-without, removed/gate-never-calls-sudo,
      removed/table-lists-every-removed-row
"""


def _v271_gate_without_sandbox():
    import contextlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import socket
    import subprocess
    import sys
    import tempfile
    from unittest.mock import patch

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    GATE = ROOT / "scripts" / "verify.sh"
    CANDIDATE_RUNNER = ROOT / "scripts" / "gate_candidate.py"
    DISPATCHER = ROOT / "scripts" / "selftest.py"
    COORDINATOR = ROOT / "scripts" / "check_gate_mutations.py"
    LEASE = ROOT / "scripts" / "agent_sandbox.py"
    TABLE = ROOT / "proof/VELDO-0271" / "removed.json"
    HOST = ROOT / 'scripts' / 'gate_host.py'
    SELF = Path(globals().get('__suite_file__', __file__)).name
    DELETED = ('agent_sandbox.json', 'mutation_sandbox.py', 'veldo_userns.c', 'veldo-userns.apparmor',
               'gate_legs.py', 'gate_unconfined.json', 'veldo-userns-setup.txt')
    HELPER, PROFILE = '/usr/local/lib/veldo/veldo-userns', '/etc/apparmor.d/veldo-userns'
    REMOVAL = ('sudo rm /usr/local/lib/veldo/veldo-userns; sudo apparmor_parser -R /etc/apparmor.d/veldo-userns; '
               'sudo rm /etc/apparmor.d/veldo-userns')

    def row(name, condition, detail=''):
        expect('VELDO-0271 ' + name + (': ' + str(detail)[:1800] if detail and not condition else ''), condition)

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # A fixture gate sees only its own configuration: every variable a real gate hands its children is
    # dropped, so running inside a real gate changes nothing. A mutation worker starts with a clean
    # environment, so the owner's runtime directory is named for the user manager rows.
    clean = {k: v for k, v in os.environ.items() if not k.startswith('VELDO_')}
    clean['XDG_RUNTIME_DIR'] = clean.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
    manifest = json.loads((ROOT / 'scripts/suites/manifest.json').read_text())
    # The manifest also enumerates the shared namespace; a suite is every other entry.
    entries = [s for s in manifest['suites'] if s['file'] != manifest['shared']]
    names = [s['name'] for s in entries]

    STUBS = {
        'scripts/check_gate_mutations.py': 'import sys\nsys.exit(0)\n',
        'scripts/reuse_stamp.py': 'print(\'"force_fresh":false,"reused":{"mutation":0,"unit":0}\')\n',
        'scripts/check_lint.sh': 'exit 0\n', 'scripts/secret_inventory.py': '',
        'scripts/check_install_and_run.py': '', 'scripts/check_personal_setup.py': '',
        'scripts/check_generated.sh': 'exit 0\n', 'scripts/check_docs.sh': 'exit 0\n',
        'scripts/check_template_sync.sh': 'exit 0\n',
        '.veldo/validate.py': '', '.veldo/shape_gate.py': '', '.veldo/events.py': '',
    }
    SHARED = '''import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
PASS = FAIL = 0
SCOPE = None
RAN = []
def expect(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print('  SELFTEST FAIL: ' + name)
def report():
    print('fixture suites ran: ' + ','.join(RAN))
    print(SCOPE.aggregate_line(PASS, FAIL))
    return SCOPE.exit_code(FAIL)
'''
    PLAIN = "RAN.append(Path(__suite_file__).stem)\nexpect(Path(__suite_file__).stem + ' ran', True)\n"
    # One suite starts a transient unit in the systemd user manager, one traces a child with strace, and
    # one writes down the environment it was started with. The two first are suites the deleted leg list
    # named; before VELDO-0271 neither could run in the same leg as the rest.
    MANAGER = PLAIN + '''import subprocess, os
_unit = 'v271-fixture-%d-%s' % (os.getpid(), os.urandom(4).hex())
_done = subprocess.run(['systemd-run', '--user', '--quiet', '--collect', '--wait', '--unit', _unit, '/bin/true'],
                       capture_output=True, text=True, timeout=120)
expect('fixture transient unit ran in the user manager: ' + _done.stderr[-200:], _done.returncode == 0)
'''
    TRACED = PLAIN + '''import subprocess, os
_trace = os.path.join(os.environ['V271_OUT'], 'child.trace')
_done = subprocess.run(['/usr/bin/strace', '-f', '-o', _trace, '-e', 'trace=execve', '/bin/true'],
                       capture_output=True, text=True, timeout=120)
expect('fixture child traced: ' + _done.stderr[-200:],
       _done.returncode == 0 and 'execve(' in open(_trace).read())
'''
    ENVIRONMENT = PLAIN + '''import json, os
with open(os.path.join(os.environ['V271_OUT'], 'environment.json'), 'w') as _handle:
    json.dump(sorted(os.environ), _handle)
'''
    # The first stage reads its standard input and writes down what it got.
    STDIN = ('python3 -c "import os, sys; open(os.path.join(os.environ[\'V271_OUT\'], \'stdin\'), \'wb\')'
             '.write(os.read(0, 16))"\n')
    special = {'114_veldo_0220_gate_scope': MANAGER, '100_veldo_0207_case_reuse': TRACED, names[0]: ENVIRONMENT}

    def repository(root, stages=None, failing=False):
        """A fixture checkout that is its own authority: the real gate, candidate runner and dispatcher,
        a stub of every other stage, and one stub suite for every suite of this repository's manifest."""
        for relative, text in dict(STUBS, **(stages or {})).items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(text)
        shutil.copyfile(GATE, root / 'scripts/verify.sh')
        shutil.copyfile(CANDIDATE_RUNNER, root / 'scripts/gate_candidate.py')
        shutil.copyfile(DISPATCHER, root / 'scripts/selftest.py')
        shutil.copyfile(ROOT / 'scripts/run_scope.py', root / 'scripts/run_scope.py')
        # What the candidate runner reads its credential names from, as the authority holds them.
        for name in ('control_launch.py', 'substrate.py', 'installation.py', 'yamlish.py', 'git_process.py',
                     'git_identity_transport.py'):
            if (ROOT / '.veldo' / name).is_file():
                shutil.copyfile(ROOT / '.veldo' / name, root / '.veldo' / name)
        suites = root / 'scripts/suites'
        suites.mkdir()
        shutil.copyfile(ROOT / 'scripts/suites/manifest.json', suites / 'manifest.json')
        (suites / 'shared.py').write_text(SHARED)
        for entry in entries:
            body = special.get(entry['name'], PLAIN)
            if failing and entry['name'] == names[0]:
                body = PLAIN + "expect('fixture failing row', False)\n"
            (suites / entry['file']).write_text(body)
        return root

    def gate(script, cwd, env, arguments=(), stdin=subprocess.DEVNULL, timeout=600):
        done = subprocess.run(['bash', str(script), *arguments], cwd=str(cwd), env=env, stdin=stdin,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return done.returncode, done.stdout

    def stamp_of(directory):
        path = Path(directory) / 'last_verify'
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            return None

    with tempfile.TemporaryDirectory(prefix='v271-') as temporary:
        top = Path(temporary)

        # ---- One fixture gate, twice: once on a host that still holds the helper and its profile, with
        # canary credentials in the caller, a sudo shim first on PATH and a socket on standard input; once
        # on a clean host. AC1, AC2's credential row and AC4's leftover and sudo rows read these two runs.
        fixture_host = top / 'host'
        for path in (HELPER, PROFILE):
            (fixture_host / path.lstrip('/')).parent.mkdir(parents=True)
            (fixture_host / path.lstrip('/')).write_text('leftover fixture\n')
        shim, called = top / 'shim', top / 'sudo-called'
        shim.mkdir()
        (shim / 'sudo').write_text('#!/bin/sh\necho "$@" >> %s\nexit 0\n' % called)
        (shim / 'sudo').chmod(0o755)
        installation = top / 'installation'
        installation.mkdir()
        (installation / 'installation.yaml').write_text(
            'schema: veldo.installation/v1\nchannels:\n  fixture:\n    token: {secret: v271_keystore_item}\n')
        canaries = {'V271_KEYSTORE_ITEM': 'keystore name', 'CHANNELS_FIXTURE_TOKEN': 'settings name',
                    'GH_TOKEN': 'secret-name pattern', 'SSH_AUTH_SOCK': 'launch strip list'}
        runs = {}
        for label in ('leftover', 'clean'):
            root = repository(top / label, {'scripts/check_lint.sh': STDIN})
            out = top / (label + '-out')
            out.mkdir()
            env = dict(clean, V271_OUT=str(out), V271_PLAIN='arrives', VELDO_INSTALLATION=str(installation))
            ours, theirs = socket.socketpair()
            try:
                if label == 'leftover':
                    env.update(VELDO_HOST_ROOT=str(fixture_host), PATH=str(shim) + os.pathsep + env.get('PATH', ''),
                               **{name: 'canary-' + name.lower() for name in canaries})
                    ours.sendall(b'caller bytes')
                    code, text = gate(root / 'scripts/verify.sh', root, env, stdin=theirs)
                else:
                    # A host that holds neither: an empty fixture root, whatever this host has installed.
                    (top / 'clean-host').mkdir()
                    env.update(VELDO_HOST_ROOT=str(top / 'clean-host'))
                    code, text = gate(root / 'scripts/verify.sh', root, env)
            finally:
                ours.close()
                theirs.close()
            seen = {}
            for name in ('environment.json', 'stdin'):
                seen[name] = (out / name).read_bytes() if (out / name).is_file() else None
            runs[label] = dict(code=code, text=text, stamp=stamp_of(root / '.veldo'), seen=seen,
                               lines=text.splitlines())
        first, second = runs['leftover'], runs['clean']
        unit_lines = [l for l in first['lines'] if re.match(r'\s+unit: ', l)]
        said = next((l for l in first['lines'] if l.startswith('fixture suites ran: ')), '')
        reported = [n for n in said[len('fixture suites ran: '):].split(',') if n]
        row('one-leg/user-manager-and-strace-in-one-stage',
            first['code'] == 0 and first['text'].rstrip().endswith('GATE: GREEN (no-git)')
            and unit_lines == ['   unit: pass'] and not re.search(r'\bleg\b|unconfined', first['text'], re.I)
            and {'114_veldo_0220_gate_scope', '100_veldo_0207_case_reuse'} <= set(reported)
            and 'SELFTEST FAIL' not in first['text'],
            repr((first['code'], unit_lines, first['text'][first['text'].find('== unit'):][:1500])))
        row('one-leg/stamp-has-no-unconfined-field',
            all(isinstance(r['stamp'], dict) and r['stamp'].get('status') == 'green' and 'unconfined' not in r['stamp']
                for r in (first, second)), repr((first['stamp'], second['stamp'])))
        aggregate = re.search(r'^selftest: (\d+) passed, (\d+) failed$', first['text'], re.M)
        row('one-leg/unit-stage-reports-every-suite',
            sorted(reported) == sorted(names) and len(reported) == len(names) and aggregate is not None
            and int(aggregate.group(2)) == 0 and int(aggregate.group(1)) >= len(names),
            repr((len(names), len(reported), sorted(set(names) - set(reported))[:8], aggregate and aggregate.group(0))))
        row('one-leg/stdin-is-end-of-file',
            first['seen']['stdin'] == b'' and second['seen']['stdin'] == b'',
            repr((first['seen']['stdin'], second['seen']['stdin'])))
        try:
            environment = set(json.loads(first['seen']['environment.json'] or b'null') or [])
        except ValueError:
            environment = set()
        row('kept/no-credential-variable',
            'V271_PLAIN' in environment and 'V271_OUT' in environment
            and not [name for name in canaries if name in environment]
            and not [name for name in environment if re.search(r'token|secret|password|credential', name, re.I)],
            repr(sorted(n for n in canaries if n in environment) or sorted(environment)[:40]))
        leftover = [l for l in first['lines'] if l.startswith('leftover_namespace_helper')]
        row('removed/leftover-reported',
            first['code'] == 0 and len(leftover) == 1 and HELPER in leftover[0] and PROFILE in leftover[0]
            and REMOVAL in leftover[0] and first['stamp'] is not None and first['stamp'].get('status') == 'green',
            repr((first['code'], leftover)))
        row('removed/leftover-silent-without',
            second['code'] == 0 and 'leftover_namespace_helper' not in second['text']
            and second['text'].rstrip().endswith('GATE: GREEN (no-git)'), second['text'][-600:])
        row('removed/gate-never-calls-sudo', first['code'] == 0 and not called.exists(),
            called.read_text()[-300:] if called.exists() else '')

        # ---- AC2: the authority's scripts judge. A candidate carries its own gate_schedule.py and
        # check_gate_mutations.py, which always pass, and a unit stage that fails. The gate is the
        # authority's, run for that candidate: it is red, and only the authority's copies ran.
        marks = top / 'marks'
        marks.mkdir()
        scheduler = '''import os, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
a = sys.argv[1:]
root, directory, receipt = (a[a.index(flag) + 1] for flag in ('--root', '--directory', '--receipt'))
stages = [(a[i + 1], a[i + 2]) for i, word in enumerate(a) if word == '--stage']
open(os.path.join(os.environ['V271_OUT'], MARK), 'a').write('scheduler\\n')
failed = 0
for name, command in stages:
    if ALWAYS_PASS:
        code = 0
    elif name == 'mutation':
        code = subprocess.run([sys.executable, '-I', '-S', str(HERE / 'check_gate_mutations.py'), '--root', root,
                               '--receipt', receipt]).returncode
    else:
        code = subprocess.run([sys.executable, '-I', '-S', str(HERE / 'gate_candidate.py'), '--root', root, '--',
                               'bash', '-c', command], cwd=root).returncode
    Path(directory, name + '.status').write_text('pass' if code == 0 else 'FAIL')
    failed += code != 0
Path(directory, 'graph-field').write_text(',"graph":"fixture"')
sys.exit(1 if failed else 0)
'''
        mutations = ("import os, sys\nopen(os.path.join(os.environ['V271_OUT'], MARK), 'a').write('mutations\\n')\n"
                     "sys.exit(0)\n")
        authority = top / 'authority'
        for relative, text in {
                'scripts/gate_schedule.py': "MARK, ALWAYS_PASS = 'authority', False\n" + scheduler,
                'scripts/check_gate_mutations.py': "MARK = 'authority'\n" + mutations,
                'scripts/reuse_stamp.py': STUBS['scripts/reuse_stamp.py'], 'scripts/gate_graph.json': '{}\n',
                '.veldo/events.py': ''}.items():
            (authority / relative).parent.mkdir(parents=True, exist_ok=True)
            (authority / relative).write_text(text)
        shutil.copyfile(GATE, authority / 'scripts/verify.sh')
        shutil.copyfile(CANDIDATE_RUNNER, authority / 'scripts/gate_candidate.py')
        candidate = repository(top / 'candidate', {
            'scripts/gate_schedule.py': "MARK, ALWAYS_PASS = 'candidate', True\n" + scheduler,
            'scripts/check_gate_mutations.py': "MARK = 'candidate'\n" + mutations}, failing=True)
        sink = top / 'sink'
        sink.mkdir()
        code, text = gate(authority / 'scripts/verify.sh', top, dict(clean, V271_OUT=str(marks)),
                          arguments=('--candidate', str(candidate), '--sink', str(sink)))
        ran = {name: (marks / name).read_text().split() if (marks / name).is_file() else [] for name in
               ('authority', 'candidate')}
        judged = stamp_of(sink) or {}
        row('kept/authority-scripts-judge',
            code == 1 and '   unit: FAIL' in text.splitlines() and text.rstrip().endswith('GATE: RED (no-git)')
            and ran['authority'] == ['scheduler', 'mutations'] and ran['candidate'] == []
            and judged.get('status') == 'red',
            repr((code, ran, judged.get('status'), text[-800:])))

        # ---- AC2: the host lock and the gate's own scope with its memory limit (VELDO-0220), on a fixture
        # authority that names a scratch lock. While a holder keeps the lock the gate is NOT STARTED, exit
        # 75, and writes nothing; free, it runs in a scope whose memory.max is the configured limit.
        probe = '''import json, os
from pathlib import Path
scope = os.environ.get('VELDO_GATE_SCOPE') or ''
limit = None
if scope:
    limit = (Path('/sys/fs/cgroup') / scope.lstrip('/') / 'memory.max').read_text().strip()
Path(os.environ['V271_OUT'], 'scope.json').write_text(json.dumps({'scope': scope, 'memory_max': limit}))
'''
        hosted = repository(top / 'hosted', {'scripts/v271_probe.py': probe,
                                              'scripts/check_lint.sh': 'exec python3 scripts/v271_probe.py\n'})
        shutil.copyfile(HOST, hosted / 'scripts/gate_host.py')
        lock = top / 'locks' / '.gate.lock'
        (hosted / 'scripts/gate_host.json').write_text(json.dumps({
            'schema': 'veldo.gate-host/v1', 'authority': 'VELDO-0271 fixture', 'lock': str(lock),
            'scope': {'memory_max': '2G', 'oom_score_adj': 900},
            'load': {'cores': 1, 'memory': '1G', 'source': 'fixture'}}))
        configured = str(load('v271_host', HOST).load(hosted / 'scripts/gate_host.json')['scope']['memory_max'])
        lock.parent.mkdir(parents=True)
        lock.touch()
        scoped_out = top / 'hosted-out'
        scoped_out.mkdir()
        holder = subprocess.Popen([sys.executable, '-I', '-S', '-c',
                                   'import fcntl, sys, time\nf = open(sys.argv[1])\nfcntl.flock(f, fcntl.LOCK_EX)\n'
                                   'print("held", flush=True)\ntime.sleep(300)', str(lock)],
                                  stdout=subprocess.PIPE, text=True)
        try:
            holder.stdout.readline()
            code, text = gate(hosted / 'scripts/verify.sh', top, dict(clean, V271_OUT=str(scoped_out)))
        finally:
            holder.kill()
            holder.wait()
        row('kept/host-lock-not-started',
            code == 75 and 'GATE: NOT STARTED' in text and 'GATE: GREEN' not in text and 'GATE: RED' not in text
            and stamp_of(hosted / '.veldo') is None and not (scoped_out / 'scope.json').exists(),
            repr((code, text[-600:])))
        code, text = gate(hosted / 'scripts/verify.sh', top, dict(clean, V271_OUT=str(scoped_out)))
        try:
            scope = json.loads((scoped_out / 'scope.json').read_text())
        except (OSError, ValueError):
            scope = {}
        row('kept/scope-memory-limit',
            code == 0 and re.fullmatch(r'.*/veldo-gate-[0-9]+-[0-9a-f]+\.scope', scope.get('scope') or '') is not None
            and scope.get('memory_max') == configured == str(2 * 2**30),
            repr((code, scope, configured, text[-600:])))

        # ---- AC3: every case runs fresh. The real coordinator and real workers over a fixture repository
        # whose two cases qualify for reuse (a whole-tree closure profile), with a store beside it. The same
        # inputs twice: both runs execute both cases, reuse none and publish nothing.
        stage = top / 'stage'
        identity = load('v271_identity', ROOT / '.veldo/reuse_evidence.py')
        for name in identity.AUTHORITY_FILES:
            if (ROOT / name).is_file():
                (stage / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, stage / name)
        shutil.copyfile(COORDINATOR, stage / 'scripts/check_gate_mutations.py')
        registry = ("\ndef cases():\n    return [dict(name='fixture', finding=271, suite='fixture.py', "
                    "module='fixture.py', old='answer = True', new='answer = False', rows=['fixture/teeth'])]\n")
        (stage / 'scripts/check_teeth_mutations.py').write_text(
            (ROOT / 'scripts/check_teeth_mutations.py').read_text() + registry)
        (stage / 'scripts/check_review_mutations.py').write_text(registry)
        (stage / 'scripts/suites').mkdir(parents=True, exist_ok=True)
        (stage / 'scripts/suites/manifest.json').write_text(json.dumps({'suites': [{'file': 'fixture.py'}]}))
        (stage / 'scripts/suites/shared.py').write_text(
            'from pathlib import Path\nROOT = Path(__file__).resolve().parents[2]\n'
            'def expect(name, condition):\n    assert condition, name\n')
        (stage / 'scripts/suites/fixture.py').write_text(
            'module = ROOT / ".veldo" / "fixture.py"\n'
            "expect('fixture/teeth', 'answer = True' in module.read_text())\nexpect('fixture/control', True)\n")
        (stage / '.veldo/fixture.py').write_text('answer = True\n')
        (stage / 'proof').mkdir()
        git_env = dict(clean, GIT_AUTHOR_NAME='fixture', GIT_AUTHOR_EMAIL='fixture@example.test',
                       GIT_COMMITTER_NAME='fixture', GIT_COMMITTER_EMAIL='fixture@example.test',
                       GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')
        for arguments in (['init', '-q'], ['add', '.'], ['commit', '-qm', 'fixture']):
            subprocess.run(['git', '-C', str(stage), *arguments], env=git_env, check=True, capture_output=True)
        coordinator = load('v271_coordinator', stage / 'scripts/check_gate_mutations.py')
        common = load('v271_candidate_git', ROOT / '.veldo/candidate_git.py').common_directory(stage)
        whole_tree = load('v271_mutation_reuse', stage / 'scripts/mutation_reuse.py')
        whole_tree.required_runtime = lambda environment: [Path(sys.executable).resolve()]
        real_load = coordinator.load
        store = top / 'store'
        results, problem = [], ''
        try:
            with contextlib.redirect_stdout(io.StringIO()), \
                    patch.dict(os.environ, {'VELDO_GATE_CACHE': str(store)}), \
                    patch.object(coordinator, 'load', lambda path: whole_tree if Path(path).name == 'case_reuse.py'
                                 else real_load(path)):
                inventory = coordinator.inventory(stage, common)
                files = coordinator.read_inputs(stage, common)
                (stage / whole_tree.PROFILE).write_bytes(whole_tree.R.canonical({
                    'schema': 'veldo.mutation-closures/v1', 'profiles': {
                        case['identity']: {'tree_digest': whole_tree.qualification_digest(files),
                                           'case_digest': whole_tree.R.digest(case), 'non_file_inputs': 'none',
                                           'rationale': 'Controlled fixture closure for the fresh-run row.',
                                           'runtime_paths': [str(Path(sys.executable).resolve())]}
                        for case in inventory}}))
                for _ in range(2):
                    results.append(coordinator.run_stage(stage, common))
        except Exception as error:  # the row reports it; a crash here is a red row, never a silent pass
            problem = repr(error)
        published = sorted(p.name for p in store.glob('*.json*')) if store.is_dir() else []
        row('mutation/every-run-fresh',
            len(results) == 2 and all(
                r.get('status') == 'passed' and (r.get('registered'), r.get('executed'), r.get('reused')) == (2, 2, 0)
                and r.get('worker_invocations', 0) >= 4
                and all(c['source'] == 'fresh' and c['key'] is None and c['reason'] == 'reuse_off'
                        for c in r.get('case_receipts', []))
                and all('snapshot_root' not in json.dumps(o) for o in r.get('worker_outcomes', []))
                for r in results) and published == [],
            repr((problem, [(r.get('status'), r.get('executed'), r.get('reused'), r.get('error'),
                             str(r.get('detail'))[:300]) for r in results], published)))

    # ---- AC4: what is gone is gone everywhere, and the kept file is the lease only.
    listed = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'], capture_output=True, env=clean)
    tracked = [name for name in listed.stdout.decode('utf-8', 'surrogateescape').split('\0') if name]
    outside = [name for name in tracked
               if not name.startswith(('specs/', 'proof/', 'plans/', 'docs/design/'))
               and name != 'scripts/suites/' + SELF]
    hits = {}
    for name in outside:
        try:
            body = (ROOT / name).read_bytes()
        except OSError:
            continue
        found = sorted(word for word in DELETED if word.encode() in body)
        if found:
            hits[name] = found
    # Suite 127's config_missing row names the deleted configuration once, on purpose.
    allowed = 'scripts/suites/127_veldo_0254_secret_scan.py'
    if hits.get(allowed) == ['agent_sandbox.json'] \
            and (ROOT / allowed).read_text().count('agent_sandbox.json') == 1 \
            and 'config_missing' in (ROOT / allowed).read_text():
        del hits[allowed]
    row('removed/seven-names-gone', listed.returncode == 0 and len(tracked) > 100 and hits == {}
        and not [name for name in outside if Path(name).name in DELETED], repr(hits))

    scanned = [n for n in tracked if n in ('scripts/verify.sh', 'scripts/check_gate_mutations.py',
                                           'scripts/reuse_worker.py', 'scripts/selftest.py',
                                           'scripts/check_install_and_run.py', 'scripts/migrate_to_veldo.py',
                                           'scripts/suites/shared.py')
               or re.fullmatch(r'scripts/gate_[a-z_]+\.py', n) or re.fullmatch(r'\.veldo/[A-Za-z0-9_]+\.py', n)]
    loads = []
    for name in scanned:
        for number, line in enumerate((ROOT / name).read_text(errors='replace').splitlines(), 1):
            # A comment is no load, and neither is the scaffold's list of the files it lays down.
            if 'agent_sandbox' in line and not line.lstrip().startswith('#') \
                    and not line.startswith('_REUSE_AUTHORITY = ['):
                loads.append('%s:%d' % (name, number))
    row('removed/lease-not-loaded', len(scanned) > 100 and 'scripts/gate_candidate.py' in scanned
        and '.veldo/control_launch.py' in scanned and loads == [], repr(loads[:12]))

    kept = ('take_lease', 'release', 'borrowed_credentials', 'Borrow', 'borrow_journal', 'settle_borrow',
            'write_back', 'keep_recovery', 'recover_orphans', 'restore_login', 'CredentialRecovery',
            'recovery_message', 'RECOVERY_EXIT', 'borrow_root', 'Stop', 'Interrupted', 'STOP_SIGNALS')
    gone = ('landlock', 'fork_gate_domain', 'Broker', 'launch', 'run_tree', 'namespace_init', 'namespace_selftest',
            'launcher_fds', 'remove_stale_scratch', 'NAMESPACE_HELPER')
    try:
        lease = load('v271_lease', LEASE)
        defined = set(vars(lease))
    except Exception as error:
        defined = {'<not loadable: %r>' % error}
    row('removed/lease-only', not [n for n in gone if n in defined] and not [n for n in kept if n not in defined]
        and (ROOT / 'engine/scripts/agent_sandbox.py').read_bytes() == (ROOT / 'scripts/agent_sandbox.py').read_bytes(),
        repr(([n for n in gone if n in defined], [n for n in kept if n not in defined])))

    # ---- AC4: the proof table lists every suite row and mutation case that was present at 24c9f5b4 and
    # is absent now. The two inventories are recorded in the bundle (rows.json: the row names of every
    # suite and the registered case names, at 24c9f5b4 and after this change); the table is removed.json.
    try:
        table = json.loads(Path(TABLE).read_text())
        rows = json.loads((ROOT / 'proof/VELDO-0271/rows.json').read_text())
        entries = table['removed']
        named = {(e['kind'], e['name']) for e in entries}
        before, after = rows['at_24c9f5b4'], rows['after']
        absent = set()
        for suite, labels in before['rows'].items():
            if suite not in after['rows']:
                absent.add(('suite', suite))
            for label in set(labels) - set(after['rows'].get(suite, [])):
                absent.add(('row', label))
        for case in set(before['cases']) - set(after['cases']):
            absent.add(('case', case))
        unlisted = sorted(absent - named)
        shaped = all(isinstance(e.get('checked'), str) and e['checked'].strip()
                     and isinstance(e.get('now'), str) and e['now'].strip() for e in entries)
        # A row the table says still covers a removed one is a row this tree has.
        current = {label for labels in after['rows'].values() for label in labels}
        dangling = sorted(e['now'] for e in entries if e['now'] != 'confinement only' and e['now'] not in current)
        detail = repr((unlisted[:12], dangling[:8]))
        complete = bool(absent) and not unlisted and shaped and not dangling
    except Exception as error:
        complete, detail = False, repr(error)
    row('removed/table-lists-every-removed-row', complete, detail)


_v271_gate_without_sandbox()
