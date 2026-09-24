#!/usr/bin/env python3
"""Drive every finding-42 mutation and record what each one turned red, and why.

Uses the registry and file materializer of scripts/check_teeth_mutations.py unchanged. Each run is a
fresh interpreter executing the shared preamble and the VELDO-0042 suite, with the suite's
production-copy anchor pointed at the baseline source, an unmutated (no-op) copy or the mutant. Rows
and the suite's own region-completion rows are retained, with source digests and the wall time of
every run. Writes proof/VELDO-0042/mutations.json and one exact applied diff per mutation beside it.

    python3 -B proof/VELDO-0042/drive.py

With `--red COMMIT` it instead runs the current suite once against the whole tree of COMMIT, extracted
read-only with `git archive` into a temporary directory, and writes proof/VELDO-0042/red-at-COMMIT.json.
Nothing in that tree is changed. At 18ecd6f the isolated-clone provisioner did not exist, so the
suite's control_clone anchor is pointed at proof/VELDO-0042/prefix/control_clone.py, a stand-in that
refuses every provision; every other module is the commit's own, byte-identical. Each row then reds by
its own assertion (the capability is absent, and the commit's init_scaffold installs neither asset).
At 2f643d0 (the allow-list confinement the review refused) every module is the commit's own.

    python3 -B proof/VELDO-0042/drive.py --red 18ecd6f
    python3 -B proof/VELDO-0042/drive.py --red 2f643d0

With `--observe` it runs the suite once and writes observations.json: every row, the suite's own run
time and everything the suite observed (what the kernel allowed each probe, what each engine
requested and wrote, the groups, the chain cost the provisioner recorded).

With `--engines` it measures, with strace, every file operation the kernel refuses the installed
`claude` and `codex` CLIs when they run confined through the clone adapter in production's layout (a
home directory holding their state layout and the bound repository, so the home directory is on the
write chain; the store, keys, clones and caches in a state directory of their own), each pointed at a
local listener that answers nothing, and writes engine-denials.json. A write-and-rename of a file
directly in the home directory is measured beside them as the mechanism.
"""
import ast
import contextlib
import difflib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = '66_veldo_0042_clones.py'
PREFIX = 'VELDO-0042 '
FINDING = 42
MODULES = ('control_clone.py', 'env_provision.py', 'init_scaffold.py')


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Every Git call goes through the repository's one neutralized boundary.
_git_process = _load('v42_drive_git_process', ROOT / '.veldo' / 'git_process.py')


def _driver():
    spec = importlib.util.spec_from_file_location('ctm', ROOT / 'scripts/check_teeth_mutations.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one(paths, root, observe=False):
    """Run the shared preamble of `root` and the current suite once, in this interpreter."""
    shared = Path(root) / 'scripts/suites/shared.py'
    rows = []
    ns = {'__file__': str(shared),
          '__observe__': lambda name, condition: rows.append([name.split(':', 1)[0], bool(condition)])}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        source = (ROOT / 'scripts/suites' / SUITE).read_text()
        for module, path in paths.items():
            anchor = 'ROOT / ".veldo" / "' + module + '"'
            if source.count(anchor) != 1:
                raise RuntimeError('suite production-copy anchor moved: ' + module)
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(str(path)) + ')')
        exec(compile(source, SUITE, 'exec'), ns)
    mine = [r for r in rows if r[0].startswith(PREFIX)]
    ran = [r[0] for r in mine if r[0].startswith(PREFIX + 'ran/') and not r[1]]
    found = {'rows': mine, 'failed_rows': [r[0] for r in mine if not r[1]],
             'regions_that_raised': ran, 'preamble_rows': len(rows) - len(mine)}
    if observe:
        found.update(observed=ns.get('_V42_OBSERVED'), suite_seconds=round(ns.get('_V42_SECONDS') or 0, 3))
    return found


def run(paths=None, root=None, observe=False):
    started = time.monotonic()
    command = [sys.executable, '-B', __file__, '--one-observe' if observe else '--one', json.dumps(paths or {}),
               str(root or ROOT)]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if proc.returncode:
        raise RuntimeError('run did not complete its assertions: ' + proc.stderr[-2000:])
    return dict(json.loads(proc.stdout), seconds=round(time.monotonic() - started, 3))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


def red(commit):
    """Run the current suite once against the whole tree of COMMIT, extracted with git archive; the
    control_clone anchor points at the prefix stand-in only when the module is absent at COMMIT."""
    resolved = _git_process.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', commit + '^{commit}'],
                                capture_output=True, text=True, check=True).stdout.strip()
    prefix = HERE / 'prefix' / 'control_clone.py'
    with tempfile.TemporaryDirectory(prefix='v42-red-') as directory:
        tree = Path(directory) / 'tree'
        tree.mkdir()
        archive = _git_process.run(['git', '-C', str(ROOT), 'archive', resolved], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True)
        modules = {'.veldo/' + m: dict(at_commit=_sha(tree / '.veldo' / m), now=_sha(ROOT / '.veldo' / m)) for m in MODULES}
        absent = not (tree / '.veldo' / 'control_clone.py').is_file()
        observed = run({'control_clone.py': str(prefix)} if absent else {}, tree)
    described = ('with control_clone absent (proof/VELDO-0042/prefix/control_clone.py stands in)' if absent
                 else 'with every module the commit\'s own')
    report = dict(schema='veldo.proof-red/v1', spec_id='VELDO-0042', suite='scripts/suites/' + SUITE, commit=resolved,
                  tree='git archive %s, unchanged; the current suite run against it %s' % (resolved, described),
                  control_clone_at_commit='absent' if absent else 'present', modules=modules,
                  by_assertion=not observed['regions_that_raised'], **observed)
    name = 'red-at-%s.json' % commit
    (HERE / name).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'commit': resolved, 'failed_rows': observed['failed_rows'],
                      'by_assertion': report['by_assertion'], 'written': name}))


def observations():
    """One run of the current suite with everything it observed: observations.json."""
    observed = run(observe=True)
    report = dict(schema='veldo.proof-observations/v1', spec_id='VELDO-0042', suite='scripts/suites/' + SUITE,
                  by_assertion=not observed['regions_that_raised'], **observed)
    (HERE / 'observations.json').write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + '\n')
    print(json.dumps({'failed_rows': observed['failed_rows'], 'rows': len(observed['rows']),
                      'suite_seconds': observed['suite_seconds'], 'written': 'observations.json'}))


ENGINE_ARGV = {'claude': ['claude', '-p', 'reply with one word', '--model', 'veldo-unreachable-model'],
               'codex': ['codex', 'exec', '--skip-git-repo-check', '-m', 'veldo-unreachable-model', 'reply with one word']}
REFUSED = ('EACCES', 'EPERM', 'EXDEV')


def _normal(text, replacements):
    for old, new in replacements:
        text = text.replace(old, new)
    text = re.sub(r'\.tmp\.\d+\.[0-9a-f]+', '.tmp.<pid>.<hex>', text)
    return re.sub(r'/\d{3,}(?=[./"])', '/<n>', text)


def engines():
    """Measure what the kernel refuses the installed engines when confined in production's layout."""
    load = _load
    mods = ROOT / '.veldo'
    S, CL = load('v42e_store', mods / 'control_store.py'), load('v42e_clone', mods / 'control_clone.py')
    D, SIG = load('v42e_dispatch', mods / 'control_dispatch.py'), load('v42e_signer', mods / 'control_signer.py')
    runtime = os.environ.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
    strace = shutil.which('strace')
    report = {'schema': 'veldo.proof-engine-denials/v1', 'spec_id': 'VELDO-0042', 'strace': bool(strace),
              'layout': {'home': '~ (a temporary HOME holding .claude/, .claude.json, .codex/, .cache/, .config/, '
                                 '.local/ and projects/source, the bound repository)',
                         'state': '<state> (authority/ store, keys/, clones/, caches/)'},
              'engines': {}}
    with tempfile.TemporaryDirectory(prefix='v42-engines-', dir=runtime if os.path.isdir(runtime) else None) as d:
        base = Path(d)
        home, state = base / 'home', base / 'state'
        for entry in ('.claude', '.codex', '.cache', '.config', '.local/share', '.local/state', 'projects'):
            (home / entry).mkdir(parents=True)
        (home / '.claude.json').write_text('{}\n')
        (home / '.probe').write_text('before\n')
        keys, logs = state / 'keys', base / 'logs'
        keys.mkdir(parents=True, mode=0o700)
        logs.mkdir()
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(keys / 'journal')], check=True,
                       capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
        src = home / 'projects' / 'source'
        _git_process.run(['git', 'init', '-q', str(src)], check=True, capture_output=True)
        (src / 'a').write_text('accepted\n')
        _git_process.run(['git', '-C', str(src), 'add', 'a'], check=True, capture_output=True)
        _git_process.run(['git', '-C', str(src), 'commit', '-q', '-m', 'accepted'], check=True, capture_output=True,
                         identity=('Fixture', 'fixture@example.invalid'))
        commit = _git_process.run(['git', '-C', str(src), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        tree = _git_process.run(['git', '-C', str(src), 'rev-parse', 'HEAD^{tree}'], capture_output=True,
                                text=True).stdout.strip()
        writer = S.open_store(str(state / 'authority' / 'control.sqlite3'))
        sign = lambda data: SIG.sign_bytes(keys / 'journal', data, 'veldo-journal')  # noqa: E731
        S.bind_repositories(writer, 'domain-42e', {'repository-42e': str(src)})
        dispatches = D.Dispatches(S, writer, domain='domain-42e', repository='repository-42e', principal='runner',
                                  signer='runner', sign=sign)
        clones = CL.Clones(dispatches, clones=str(state / 'clones'), caches=str(state / 'caches'), protected=[str(keys)])
        dispatch_id = 'dispatch/VELDO-9490/engines'
        handle = clones.create({'dispatch_id': dispatch_id, 'domain': 'domain-42e', 'repository': 'repository-42e',
                                'unit': 'VELDO-9490', 'source': {'commit': commit, 'tree': tree},
                                'input': {'payload': {'attachments': []}}})
        manifest = json.loads((Path(handle.paths['root']) / 'clone.json').read_text())
        report['ancestors'] = {k: [_normal(p, [(str(home), '~'), (str(state), '<state>'), (str(base), '<base>'),
                                              (runtime, '<runtime>')]) for p in v]
                               for k, v in manifest['ancestors'].items()}
        replacements = [(str(home), '~'), (manifest['work'], '<clone work>'), (str(state), '<state>'),
                        (str(base), '<base>'), (runtime, '<runtime>')]
        rename = [sys.executable, '-B', '-c',
                  'import os\np = os.path.expanduser("~/.probe")\nopen(p + ".tmp", "w").write("after\\n")\n'
                  'os.replace(p + ".tmp", p)\n']
        for name, argv in list(ENGINE_ARGV.items()) + [('home-write-and-rename', rename)]:
            found = shutil.which(argv[0])
            if not found or not strace:
                report['engines'][name] = {'installed': bool(found), 'strace': bool(strace)}
                continue
            version = subprocess.run([argv[0], '--version'], capture_output=True, text=True, timeout=30,
                                     stdin=subprocess.DEVNULL).stdout.strip() if name in ENGINE_ARGV else sys.version.split()[0]
            seen, listener = [], socket.socket()
            listener.bind(('127.0.0.1', 0))
            listener.listen(16)

            def serve(server=listener, lines=seen):
                while True:
                    try:
                        connection, _ = server.accept()
                    except OSError:
                        return
                    with contextlib.suppress(OSError):
                        connection.settimeout(2)
                        lines.append(' '.join(connection.recv(4096).split(b'\r\n', 1)[0].decode('latin-1').split(' ')[:2]))
                    connection.close()

            threading.Thread(target=serve, daemon=True).start()
            proxy = 'http://127.0.0.1:%d' % listener.getsockname()[1]
            env = {'PATH': os.environ.get('PATH', os.defpath), 'HOME': str(home), 'LANG': 'C.UTF-8', 'TERM': 'dumb',
                   'VELDO_DISPATCH_ID': dispatch_id, 'XDG_RUNTIME_DIR': str(logs), 'DISABLE_AUTOUPDATER': '1',
                   'NO_PROXY': '', 'no_proxy': ''}
            env.update({k: proxy for k in ('HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY', 'https_proxy', 'http_proxy')})
            trace = logs / (name + '.strace')
            command = clones.adapter([strace, '-f', '-qq', '--seccomp-bpf', '-e', 'trace=%file', '-e', 'status=failed',
                                      '-o', str(trace), *argv])
            before = {str(p) for p in home.rglob('*') if p.is_file()}
            begun = time.monotonic()
            proc = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            end = begun + 60
            while proc.poll() is None and time.monotonic() < end:
                wrote = {str(p) for p in home.rglob('*') if p.is_file()} - before
                if name == 'codex' and any('/.codex/sessions/' in w for w in wrote) and any(
                        line.startswith('CONNECT api.openai.com') for line in seen):
                    break
                time.sleep(0.1)
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
            output = proc.communicate()[0].decode(errors='replace')
            listener.close()
            wrote = sorted({str(p) for p in home.rglob('*') if p.is_file()} - before)
            refused = {}
            for line in (trace.read_text(errors='replace').splitlines() if trace.exists() else []):
                code = next((c for c in REFUSED if '= -1 ' + c + ' ' in line), None)
                call = re.match(r'\d+\s+(\w+)\(', line)
                path = re.findall(r'"([^"]*)"', line)
                if code and call and path:
                    key = '%s %s %s' % (call.group(1), _normal(path[0], replacements), code)
                    refused[key] = refused.get(key, 0) + 1
            report['engines'][name] = {
                'installed': True, 'version': version, 'seconds': round(time.monotonic() - begun, 2),
                'requests': seen[:6], 'reached_network': any(r.startswith('CONNECT ') for r in seen),
                'state_written': len(wrote), 'state_dirs': sorted({os.path.relpath(w, home).split('/')[0] for w in wrote}),
                'saved': ({'~/.claude.json rewritten': (home / '.claude.json').read_text().strip() != '{}'}
                          if name == 'claude' else {'~/.probe replaced': (home / '.probe').read_text().strip() == 'after'}
                          if name == 'home-write-and-rename' else {}),
                'permission_denied_in_output': 'permission denied' in output.lower(),
                'refused': dict(sorted(refused.items()))}
        writer.close()
    (HERE / 'engine-denials.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({name: {'refused': list((e.get('refused') or {}).keys()),
                             'reached_network': e.get('reached_network')} for name, e in report['engines'].items()},
                     indent=1))


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--red':
        red(sys.argv[2])
        return
    if len(sys.argv) >= 2 and sys.argv[1] == '--observe':
        observations()
        return
    if len(sys.argv) >= 2 and sys.argv[1] == '--engines':
        engines()
        return
    if len(sys.argv) >= 4 and sys.argv[1] in ('--one', '--one-observe'):
        print(json.dumps(one(json.loads(sys.argv[2]), sys.argv[3], observe=sys.argv[1] == '--one-observe'),
                         default=str))
        return
    ctm = _driver()
    cases = [c for c in ctm.cases() if c['finding'] == FINDING]
    report = {'schema': 'veldo.proof-mutations/v1', 'spec_id': 'VELDO-0042', 'suite': 'scripts/suites/' + SUITE,
              'registry': 'scripts/check_teeth_mutations.py --finding %d' % FINDING, 'baseline': run(), 'noop': None,
              'mutants': []}
    with tempfile.TemporaryDirectory(prefix='v42-drive-') as directory:
        report['noop'] = {}
        for module in sorted({c['module'] for c in cases}):
            case = next(c for c in cases if c['module'] == module)
            noop = ctm.materialize(case, 'noop', Path(directory) / ('noop-' + module))
            report['noop'][module] = dict(run({module: str(noop['mutant'])}), source_sha256=noop['old_digest'],
                                          copy_sha256=noop['new_digest'])
        for case in cases:
            prepared = ctm.materialize(case, 'mutant', Path(directory) / case['name'])
            source = prepared['source'].read_text()
            (HERE / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                source.splitlines(keepends=True), ctm.mutate(source, case).splitlines(keepends=True),
                n=0, fromfile='a/.veldo/' + case['module'], tofile='b/.veldo/' + case['module'])))
            observed = run({case['module']: str(prepared['mutant'])})
            report['mutants'].append(dict(name=case['name'], module='.veldo/' + case['module'], named_rows=case['rows'],
                                          diff='proof/VELDO-0042/%s.diff' % case['name'],
                                          edits=1 + len(case.get('also', ())),
                                          source_sha256=prepared['old_digest'], mutant_sha256=prepared['new_digest'],
                                          named_row_red=all(PREFIX + r in observed['failed_rows'] for r in case['rows']),
                                          by_assertion=not observed['regions_that_raised'], **observed))
    report['all_named_rows_red'] = all(m['named_row_red'] for m in report['mutants'])
    report['all_by_assertion'] = all(m['by_assertion'] for m in report['mutants'])
    report['controls_green'] = not report['baseline']['failed_rows'] and all(
        not n['failed_rows'] for n in report['noop'].values())
    per_row = {}
    for m in report['mutants']:
        for r in m['named_rows']:
            per_row.setdefault(r, []).append(m['name'])
    report['mutations_per_row'] = per_row
    report['serial_seconds'] = round(report['baseline']['seconds'] + sum(n['seconds'] for n in report['noop'].values())
                                     + sum(m['seconds'] for m in report['mutants']), 3)
    (HERE / 'mutations.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'mutants': len(report['mutants']), 'all_named_rows_red': report['all_named_rows_red'],
                      'all_by_assertion': report['all_by_assertion'], 'controls_green': report['controls_green'],
                      'mutations_per_row': {k: len(v) for k, v in per_row.items()},
                      'serial_seconds': report['serial_seconds']}))


if __name__ == '__main__':
    main()
