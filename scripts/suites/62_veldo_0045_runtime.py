"""VELDO-0045: the pinned isolated LangGraph runtime, its license and provenance records, the journey's
installed assets, and enforcement with the runtime hidden.

Only shared ROOT and expect are consumed. The reference installation is laid by the production
scaffolder (the literal init_scaffold anchor below) from the canonical engine templates, and the two
production modules the mutation driver substitutes (control_runtime.py and authorization.py) are laid
over it from their anchors. Everything the rows judge runs as a real command in that installation:
`control_runtime.py install | check | qualify | enforcement`, traced by an audit hook where a row
needs to know what the journey opened. The runtime is the one this account installed from
control_graph_lock.py with control_graph_install.py (real pip --require-hashes). The suite never
installs from an index and never touches that runtime: every tampered scenario is a copy under a
temporary home, changed with a real pip (a throwaway environment's bundled pip, offline, with
--no-index) the way an installation would be changed, and pip check is the outside judge of the
dependency scenarios. When the account has no runtime every runtime row fails by name, with the
install command in its observation. Each region reds its own rows on a raise, and a `ran/` row says
whether it did, so a row that is red is red by its assertion.
"""


def _v45_suite():
    import base64
    import contextlib
    import csv
    import email.parser
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
    import zipfile

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_runtime.py': ROOT / ".veldo" / "control_runtime.py",
        'authorization.py': ROOT / ".veldo" / "authorization.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    OVERLAID = ('control_runtime.py', 'authorization.py')
    APPROVED = {'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'MPL-2.0', 'PSF-2.0'}
    ALTERED = 'typing_extensions'
    MARKER = b'\nVELDO_0045_ALTERED_WHEEL = True\n'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def record_hash(data):
        return 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()

    def canonical(name):
        return re.sub(r'[-_.]+', '-', name).lower()

    def run(command, cwd=None, env=None, stdin=None, timeout=300):
        return subprocess.run([str(c) for c in command], cwd=None if cwd is None else str(cwd), env=env,
                              input=stdin, stdin=None if stdin is not None else subprocess.DEVNULL,
                              capture_output=True, timeout=timeout)

    def read_json(path):
        """A JSON file's object, or {} when it is absent or not one (a pre-fix tree has no records)."""
        try:
            value = json.loads(Path(path).read_text())
        except (OSError, ValueError):
            return {}
        return value if type(value) is dict else {}

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

    lock = load('v45_lock', ROOT / '.veldo/control_graph_lock.py')
    account = lock.runtime_directory()
    site_of = lambda runtime: Path(runtime) / 'lib' / ('python' + lock.PYTHON) / 'site-packages'  # noqa: E731
    have_runtime = (account / 'bin' / 'python').is_file()
    if not have_runtime:
        observed['runtime_absent'] = ('no locked runtime at %s; install it with: python3 .veldo/control_runtime.py '
                                      'install (the runtime rows fail by name)' % account)
    FIXED = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}
    evidence = {'name': 'langgraph', 'version': dict((r[0], r[1]) for r in lock.PACKAGES)['langgraph']}

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
            tool = tmp / 'tool'
            made = run([sys.executable, '-I', '-m', 'venv', tool], env=dict(FIXED, HOME=str(tmp)))
            state['pip_env'] = dict(FIXED, HOME=str(tmp), PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK='1',
                                    PIP_NO_INPUT='1', PIP_NO_CACHE_DIR='1', PYTHONDONTWRITEBYTECODE='1')
            state['tool'] = tool / 'bin' / 'python'
            observed['tool_venv'] = made.returncode
        except Exception as error:  # noqa: BLE001 - recorded, then every row below reds by its assertion
            raised.append(('setup', repr(error)))

        def cr(*argv, cwd=None, home=None):
            extra = ['--home', str(home)] if home is not None else []
            proc = run([sys.executable, '-B', state['cr'], *argv, *extra], cwd=cwd or installed,
                       env=dict(FIXED, HOME=str(tmp)))
            return proc, report(proc)

        def pip(*argv):
            return run([state['tool'], '-I', '-m', 'pip', *argv], env=state['pip_env'])

        def runtime_copy(home, name=None):
            target = Path(home) / '.local/share/veldo/langgraph' / (name or lock.digest())
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(account, target, symlinks=True)
            return target

        def variant(name, edit):
            """A copy of the installation whose one file `edit` changes (a lock or the records)."""
            tree = tmp / name
            shutil.copytree(installed / '.veldo', tree / '.veldo', symlinks=True)
            edit(tree / '.veldo')
            return tree

        def variant_lock(tree):
            return load('v45_lock_' + tree.name, tree / '.veldo' / 'control_graph_lock.py')

        def altered_wheel(out, consistent):
            """A typing_extensions wheel rebuilt from the installed files with one line added: its RECORD
            regenerated to match (consistent) or left claiming the genuine hashes."""
            site = site_of(account)
            info = site / 'typing_extensions-4.16.0.dist-info'
            rows = [r for r in csv.reader(io.StringIO((info / 'RECORD').read_text())) if r]
            kept = [r for r in rows if r[1] and not r[0].startswith('../')
                    and r[0].split('/')[-1] not in ('INSTALLER', 'REQUESTED', 'RECORD', 'direct_url.json')]
            out.mkdir(parents=True, exist_ok=True)
            wheel = out / 'typing_extensions-4.16.0-py3-none-any.whl'
            record = []
            with zipfile.ZipFile(wheel, 'w', zipfile.ZIP_DEFLATED) as archive:
                for path, hashed, size in kept:
                    data = (site / path).read_bytes()
                    if path == 'typing_extensions.py':
                        data += MARKER
                    archive.writestr(path, data)
                    record.append([path, record_hash(data), str(len(data))] if consistent else [path, hashed, size])
                record.append(['typing_extensions-4.16.0.dist-info/RECORD', '', ''])
                text = io.StringIO()
                csv.writer(text, lineterminator='\n').writerows(record)
                archive.writestr('typing_extensions-4.16.0.dist-info/RECORD', text.getvalue())
            return wheel

        # AC1: records against the lock, the registry and the installed metadata
        with region('runtime/records-cover-lock'):
            proc, accepted = cr('check')
            records = read_json(installed / '.veldo/runtime/langgraph-records.json')
            packages = {canonical(p['name']): p for p in records.get('packages') or []}
            locked = {canonical(row[0]): row for row in lock.PACKAGES}
            spdx = {k: [t for t in re.findall(r'[A-Za-z0-9.+-]+', p['license']['spdx'] or '') if t not in ('AND', 'OR', 'WITH')]
                    for k, p in packages.items()}
            covered = (set(packages) == set(locked) and records['lock_digest'] == lock.digest()
                       and all(packages[k]['version'] == row[1] and packages[k]['wheel'] == row[2]
                               and packages[k]['sha256'] == row[3] for k, row in locked.items())
                       and all(spdx[k] and set(spdx[k]) <= APPROVED for k in packages)
                       and all(p['approval'] and str(p['source']).startswith('https://')
                               and re.fullmatch(r'[0-9a-f]{64}', p['content']['sha256']) for p in packages.values()))
            metadata = {}
            for info in site_of(account).glob('*.dist-info'):
                meta = email.parser.Parser().parsestr((info / 'METADATA').read_text(), headersonly=True)
                metadata[canonical(meta['Name'])] = (meta['Version'], meta.get('License') or None,
                                                     meta.get('License-Expression') or None)
            agrees = set(metadata) == set(locked) == set(packages) and all(
                metadata[k] == (packages[k]['version'], packages[k]['license']['registry_license'],
                                packages[k]['license']['registry_license_expression']) for k in locked)

            def relicense(veldo):
                path = veldo / 'runtime/langgraph-records.json'
                if not path.is_file():
                    return  # a tree without records has nothing to relicense
                data = json.loads(path.read_text())
                for entry in data['packages']:
                    if entry['name'] == 'certifi':
                        entry['license']['spdx'] = 'LicenseRef-Proprietary'
                data['packages'] = [e for e in data['packages'] if e['name'] != 'sniffio']
                path.write_text(json.dumps(data))
            bad = variant('relicensed', relicense)
            proc_bad = run([sys.executable, '-B', bad / '.veldo/control_runtime.py', 'check'], cwd=bad,
                           env=dict(FIXED, HOME=str(tmp)))
            refused = report(proc_bad) or {}
            observed['records'] = {'accepted': (accepted or {}).get('outcome'), 'problems': (accepted or {}).get('problems'),
                                   'covered': covered, 'installed_metadata_agrees': agrees,
                                   'relicensed': refused.get('problems'), 'attested': sum(1 for p in packages.values() if p['attestation'])}
            check('runtime/records-cover-lock', have_runtime and proc.returncode == 0 and accepted
                  and accepted['outcome'] == 'accepted' and accepted['packages'] == len(lock.PACKAGES)
                  and accepted['lock_digest'] == lock.digest() and covered and agrees
                  and proc_bad.returncode == 1 and refused.get('outcome') == 'refused'
                  and refused.get('problems') == ['license_unapproved:certifi:LicenseRef-Proprietary',
                                                  'unrecorded_package:sniffio'])

        # AC1: the actual nonpersistent adapter workload on the activated runtime
        with region('runtime/workload'):
            proc, qualified = cr('qualify', '--stage', tmp / 'qualify-stage')
            work = (qualified or {}).get('workload') or {}
            steps = work.get('steps') or []
            observed['workload'] = {k: work.get(k) for k in ('passed', 'steps', 'proposals', 'counts', 'pending', 'refused')}
            check('runtime/workload', have_runtime and proc.returncode == 0 and (qualified or {}).get('outcome') == 'accepted'
                  and [(s.get('operation'), s.get('outcome')) for s in steps] == [
                      ('start', 'suspended'), ('suspend', 'suspended'), ('advance', 'proposal'),
                      ('start-second', 'suspended'), ('cancel', 'canceled')]
                  and all(s.get('runtime') == evidence for s in steps)
                  and work.get('proposals') == [{'type': 'priority', 'proposal_id': 'qualification-priority',
                                                 'subject': 'qualify-cycle', 'priority': 7}]
                  and work.get('counts') == {'accepted': 5, 'refused': 0} and work.get('pending') == []
                  and len(work.get('observations') or []) == 5)

        # AC1: an altered artifact hash in the lock refuses activation
        with region('runtime/altered-hash-refused'):
            pinned = dict((r[0], r[3]) for r in lock.PACKAGES)[ALTERED]
            flipped = pinned[:-1] + ('0' if pinned[-1] != '0' else '1')

            def alter_hash(veldo):
                path = veldo / 'control_graph_lock.py'
                path.write_text(path.read_text().replace(pinned, flipped))
            tree = variant('altered-hash', alter_hash)
            home = tmp / 'home-altered-hash'
            target = home / '.local/share/veldo/langgraph' / variant_lock(tree).digest()
            target.parent.mkdir(parents=True)
            os.symlink(account, target)  # the genuine runtime, read only, at the altered lock's address
            proc = run([sys.executable, '-B', tree / '.veldo/control_runtime.py', 'check', '--home', home], cwd=tree,
                       env=dict(FIXED, HOME=str(tmp)))
            answer = report(proc) or {}
            observed['altered_hash'] = answer.get('problems')
            check('runtime/altered-hash-refused', have_runtime and proc.returncode == 1 and answer.get('outcome') == 'refused'
                  and 'hash_mismatch:' + ALTERED in (answer.get('problems') or [])
                  and not any(p.startswith('runtime_absent') for p in answer.get('problems') or []))

        # AC1: a wheel installed with hash enforcement bypassed; the runtime-integrity check refuses it
        with region('runtime/altered-wheel-refused'):
            outcomes = {}
            requirement = tmp / 'one-locked-requirement.txt'
            requirement.write_text('%s==4.16.0 --hash=sha256:%s\n' % (ALTERED, dict((r[0], r[3]) for r in lock.PACKAGES)[ALTERED]))
            for kind in ('consistent', 'genuine'):
                home = tmp / ('home-wheel-' + kind)
                copy = runtime_copy(home)
                wheel = altered_wheel(tmp / ('wheel-' + kind), kind == 'consistent')
                enforced = pip('--python', copy / 'bin/python', 'install', '--quiet', '--require-hashes', '--no-deps',
                               '--no-index', '--find-links', wheel.parent, '--only-binary=:all:', '--force-reinstall',
                               '-r', requirement)
                bypassed = pip('--python', copy / 'bin/python', 'install', '--quiet', '--no-deps', '--no-index',
                               '--force-reinstall', wheel)
                present = MARKER in (site_of(copy) / 'typing_extensions.py').read_bytes()
                proc, answer = cr('check', home=home)
                outcomes[kind] = {'enforced_exit': enforced.returncode,
                                  'enforced_says': b'DO NOT MATCH THE HASHES' in enforced.stderr,
                                  'bypassed_exit': bypassed.returncode, 'altered_code_installed': present,
                                  'check_exit': proc.returncode, 'problems': (answer or {}).get('problems')}
            observed['altered_wheel'] = outcomes
            check('runtime/altered-wheel-refused', have_runtime
                  and all(o['enforced_exit'] != 0 and o['enforced_says'] and o['bypassed_exit'] == 0
                          and o['altered_code_installed'] and o['check_exit'] == 1 for o in outcomes.values())
                  and outcomes['consistent']['problems'] == ['content_mismatch:' + ALTERED]
                  and outcomes['genuine']['problems'] == ['file_mismatch:%s:%s.py' % (ALTERED, ALTERED)])

        # AC1: an omitted dependency refuses activation; pip check is the outside judge
        with region('runtime/omitted-dependency-refused'):
            omitted = {}
            home = tmp / 'home-no-sniffio'
            copy = runtime_copy(home)
            removed = pip('--python', copy / 'bin/python', 'uninstall', '--quiet', '-y', 'sniffio')
            judged = pip('--python', copy / 'bin/python', 'check')
            proc, answer = cr('check', home=home)
            omitted['uninstalled'] = {'removed': removed.returncode, 'pip_check_exit': judged.returncode,
                                      'pip_check_says': b'requires sniffio, which is not installed' in judged.stdout,
                                      'check_exit': proc.returncode, 'problems': (answer or {}).get('problems')}

            def drop_sniffio(veldo):
                path = veldo / 'control_graph_lock.py'
                text = path.read_text()
                row = re.search(r"    \('sniffio', '[^']*',\n[^\n]*\n[^\n]*\n", text).group(0)
                path.write_text(text.replace(row, ''))
            tree = variant('lock-omits-sniffio', drop_sniffio)
            home_b = tmp / 'home-lock-omits'
            (home_b / '.local/share/veldo/langgraph').mkdir(parents=True)
            os.rename(copy, home_b / '.local/share/veldo/langgraph' / variant_lock(tree).digest())
            proc = run([sys.executable, '-B', tree / '.veldo/control_runtime.py', 'check', '--home', home_b], cwd=tree,
                       env=dict(FIXED, HOME=str(tmp)))
            answer = report(proc) or {}
            omitted['lock_omits'] = {'check_exit': proc.returncode, 'problems': answer.get('problems')}
            home_c = tmp / 'home-no-langgraph'
            copy_c = runtime_copy(home_c)
            removed = pip('--python', copy_c / 'bin/python', 'uninstall', '--quiet', '-y', 'langgraph')
            judged = pip('--python', copy_c / 'bin/python', 'check')
            proc, answer = cr('check', home=home_c)
            omitted['root_uninstalled'] = {'removed': removed.returncode, 'pip_check_exit': judged.returncode,
                                           'check_exit': proc.returncode, 'problems': (answer or {}).get('problems')}
            genuine = pip('--python', account / 'bin/python', 'check')
            omitted['genuine_pip_check_exit'] = genuine.returncode
            observed['omitted_dependency'] = omitted
            check('runtime/omitted-dependency-refused', have_runtime and genuine.returncode == 0
                  and omitted['uninstalled']['removed'] == 0 and omitted['uninstalled']['pip_check_exit'] == 1
                  and omitted['uninstalled']['pip_check_says'] and omitted['uninstalled']['check_exit'] == 1
                  and omitted['uninstalled']['problems'] == ['missing_dependency:sniffio']
                  and omitted['lock_omits']['check_exit'] == 1
                  and 'missing_dependency:sniffio' in (omitted['lock_omits']['problems'] or [])
                  and 'unlocked_record:sniffio' in (omitted['lock_omits']['problems'] or [])
                  and omitted['root_uninstalled']['removed'] == 0 and omitted['root_uninstalled']['pip_check_exit'] == 0
                  and omitted['root_uninstalled']['check_exit'] == 1
                  and omitted['root_uninstalled']['problems'] == ['missing_dependency:langgraph'])

        # observability: every activation says what it judged, and a refusal keeps its taxonomy
        with region('runtime/observations'):
            proc, fine = cr('check')
            empty = tmp / 'home-empty'
            empty.mkdir()
            proc_absent, absent = cr('check', home=empty)
            wheel_home = tmp / 'home-wheel-consistent'
            proc_wheel, altered = cr('check', home=wheel_home)
            fields = {'schema', 'operation', 'journey', 'lock_digest', 'records_digest', 'runtime', 'packages',
                      'problems', 'outcome', 'taxonomy', 'counts'}
            records_file = installed / '.veldo/runtime/langgraph-records.json'
            records_digest = 'sha256:' + digest(records_file) if records_file.is_file() else None
            observed['observations'] = {'accepted': {k: (fine or {}).get(k) for k in ('outcome', 'taxonomy', 'counts')},
                                        'absent': {k: (absent or {}).get(k) for k in ('problems', 'taxonomy')},
                                        'altered': {k: (altered or {}).get(k) for k in ('problems', 'taxonomy')}}
            answers = [fine or {}, absent or {}, altered or {}]
            fine, absent, altered = fine or {}, absent or {}, altered or {}
            check('runtime/observations', have_runtime and all(set(a) == fields for a in answers)
                  and all(a.get('operation') == 'activate' and a.get('lock_digest') == lock.digest()
                          and a.get('records_digest') == records_digest for a in answers)
                  and fine.get('outcome') == 'accepted' and fine.get('taxonomy') == []
                  and fine.get('counts') == {'accepted': 1, 'refused': 0}
                  and absent.get('outcome') == 'refused' and absent.get('taxonomy') == ['unavailable_service']
                  and absent.get('problems') == ['runtime_absent:' + lock.digest()]
                  and altered.get('taxonomy') == ['invalid_input'] and altered.get('counts') == {'accepted': 0, 'refused': 1})

        # AC2: the journey's every reached asset is installed, with the digest it was laid with
        with region('journey/assets-installed'):
            proc, trace = traced(tmp, 'journey', state['cr'], ['install', '--stage', stage], cwd=installed)
            answer = report(proc) or {}
            journey = set((answer.get('activation') or {}).get('journey') or [])
            reached, fallback, elsewhere, wrote, probed, bytecode = set(), [], [], [], 0, {}
            runtime_opened = set()
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
                elif under(path, account):
                    runtime_opened.add(os.path.realpath(path))
                elif not (under(path, stage) or under(path, sysconfig.get_path('stdlib'))
                          or under(path, tempfile.gettempdir()) or path.startswith(('/dev/', '/proc/'))):
                    elsewhere.append(path)
            recorded = {}
            for info in site_of(account).glob('*.dist-info'):
                for row in csv.reader(io.StringIO((info / 'RECORD').read_text())):
                    if row:
                        recorded[os.path.realpath(str(site_of(account) / row[0]))] = row[1]

            def runtime_file_ok(path):
                if path == os.path.realpath(str(account / 'pyvenv.cfg')):
                    return True
                if path not in recorded:
                    return False
                return not recorded[path] or record_hash(Path(path).read_bytes()) == recorded[path]
            bad_runtime = sorted(p for p in runtime_opened if not runtime_file_ok(p))
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
                run_proc, run_trace = traced(tmp, 'runner', staged[0], [], cwd=empty_cwd, python=account / 'bin/python',
                                             stdin=json.dumps(request).encode(), env=dict(graph.ENVIRONMENT))
                stdlib = [p.decode().strip() for p in run([account / 'bin/python', '-I', '-c',
                          'import sysconfig; print(sysconfig.get_path("stdlib"))'], env=FIXED).stdout.splitlines()]
                child_runtime, child_other = set(), []
                for path, _mode in run_trace['opened']:
                    if not os.path.isfile(path) and not under(path, ROOT) and not under(path, installed):
                        continue  # an attempt at a file that is not there reaches nothing
                    if under(path, account):
                        child_runtime.add(os.path.realpath(path))
                    elif not (under(path, staged[0]) or any(under(path, s) for s in stdlib) or under(path, tmp / 'trace-runner.json')
                              or path.startswith(('/dev/', '/proc/'))):
                        child_other.append(path)
                child.update(answer=(report(run_proc) or {}).get('outcome'), runtime_label=(report(run_proc) or {}).get('runtime'),
                             runtime_files=len(child_runtime), bad_runtime=sorted(p for p in child_runtime if not runtime_file_ok(p)),
                             outside=sorted(child_other)[:20], exit=run_trace['exit'])
            observed['journey'] = {'exit': proc.returncode, 'outcome': answer.get('outcome'), 'trace_exit': trace['exit'],
                                   'reached_installed': sorted(reached), 'declared': sorted(journey), 'fallback': fallback[:20],
                                   'elsewhere': elsewhere[:20], 'wrote': wrote, 'mismatched': mismatched, 'probed': probed,
                                   'bytecode': bytecode,
                                   'runtime_files': len(runtime_opened), 'bad_runtime': bad_runtime[:20], 'runner_child': child}
            check('journey/assets-installed', have_runtime and proc.returncode == 0 and answer.get('outcome') == 'accepted'
                  and answer.get('operation') == 'install' and trace['exit'] == 0
                  and reached == journey and {'.veldo/control_graph_lock.py', '.veldo/runtime/langgraph-records.json'} <= reached
                  and reached <= state['created'] and not mismatched and not fallback and not elsewhere and not wrote
                  and all(bytecode.values())
                  and len(runtime_opened) > 1000 and not bad_runtime
                  and child.get('answer') == 'suspended' and child.get('runtime_label') == evidence
                  and child.get('runtime_files', 0) > 100 and not child.get('bad_runtime') and not child.get('outside'))

        # AC2: an omitted asset is a named failure, never a read of the source tree
        with region('journey/omitted-asset-named'):
            named = {}
            for rel in ('.veldo/runtime/langgraph-records.json', '.veldo/control_graph_lock.py'):
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
                and verdict.get('hidden') == [os.path.realpath(str(account.parent))])
            probe = verdict.get('graph') or {}
            answers = [a for a in probe.get('answers') or [] if type(a) is dict]
            proc_present, present = cr('check')
            check('enforcement/graph-unavailable', have_runtime and probe.get('status') == 'pass'
                  and [(a.get('home'), a.get('refusal')) for a in answers] == [('absent', 'runtime_unavailable'),
                                                                               ('hidden', 'runtime_unavailable')]
                  and 'runtime_absent' in answers[0].get('detail', '') and 'runtime_unreadable' in answers[1].get('detail', '')
                  and probe.get('hidden_hits') and (present or {}).get('outcome') == 'accepted')

        for first in regions:
            check('ran/' + first, first not in {label for label, _ in raised})
        observed['raised'] = raised
    globals()['_V45_OBSERVED'] = observed


_v45_started = __import__('time').monotonic()
_v45_suite()
_V45_SECONDS = __import__('time').monotonic() - _v45_started
