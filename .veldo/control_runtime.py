#!/usr/bin/env python3
"""The pinned, isolated LangGraph runtime as a distributed journey (VELDO-0045). Standard library only.

  python3 .veldo/control_runtime.py install [--home DIR] [--stage DIR]   install, activate, qualify
  python3 .veldo/control_runtime.py check [--home DIR]                   activation only
  python3 .veldo/control_runtime.py qualify [--home DIR] [--stage DIR]   activation and the workload
  python3 .veldo/control_runtime.py enforcement [--root REPOSITORY]      enforcement with the runtime hidden

Built on VELDO-0043 and never a second copy of it: the lock is control_graph_lock.py, the one
installer is control_graph_install.py (pip --require-hashes from that lock), the adapter is
control_graph.py and the isolated-enforcement harness is control_graph_isolation.py. What this module
adds is what they lack.

ACTIVATION. The runtime may be used only when every check below passes; each failure is a named
problem and any problem refuses activation (graph invocation then reports runtime_unavailable):
  - every journey asset (JOURNEY) is present in THIS installation, read from this installation's own
    .veldo and nowhere else (no source-tree fallback), else missing_asset;
  - the license and provenance records (RECORDS, a non-code asset, canonical at
    engine/runtime/langgraph-records.json) are bound to this lock's digest and record every locked
    package exactly: the registry-served sha256 (an altered lock hash is hash_mismatch), an SPDX
    license every identifier of which is approved, an approval and the wheel's content digest;
  - the installed distributions are exactly the locked ones at the locked versions, with the
    license fields the registry records;
  - every file each distribution's RECORD lists matches its digest (file_mismatch), and the rows
    that came from the wheel are exactly the genuine locked wheel's content (content_mismatch), so a
    wheel installed with hash enforcement bypassed is still refused;
  - the runtime's own interpreter, with the runtime's own importlib.metadata and packaging, evaluates
    every installed requirement for this Python and platform: one that no locked, installed
    distribution satisfies is missing_dependency or unsatisfied_dependency, and every sys.path entry
    lies in the runtime or the base interpreter's standard library;
  - control_graph.runtime_problems finds no repository behind the interpreter or pyvenv.cfg.

QUALIFICATION runs the actual nonpersistent adapter workload on the activated runtime: the production
runner with one deterministic workflow registered before its entry point (no model, no network), and
start, suspend, advance and cancel through the production adapter, each answer labelled by the locked
LangGraph that ran it.

ENFORCEMENT enumerates the installation's enabled enforcement entries from its own gate and guard
(every `python3 <module>.py` they run) plus the installed authorization entry, and runs each real
command in an isolated -I -S child whose import finder refuses anything but the standard library and
the installed siblings (control_graph_isolation's harness) and whose audit hook refuses, and records,
any open, listing or launch under the account's runtime directory. Every entry must pass with the
runtime hidden; graph invocation, asked the same way, must report runtime_unavailable.
"""
import base64
import csv
import email.parser
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SCHEMA = 'veldo.runtime-activation/v1'
RECORDS_SCHEMA = 'veldo.runtime-records/v1'
RECORDS = 'runtime/langgraph-records.json'
# Every installed asset the journey (install, activate, qualify) reaches, relative to .veldo. The
# VELDO-0045 suite traces the journey and requires this to be exactly what it reached.
JOURNEY = ('control_runtime.py', 'control_graph.py', 'control_graph_lock.py', 'control_graph_install.py',
           'control_graph_langgraph.py', 'git_process.py', RECORDS)
APPROVED_LICENSES = frozenset({'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'MPL-2.0', 'PSF-2.0'})
INSTALL_COMMAND = 'python3 .veldo/control_runtime.py install'
REBUILD_COMMAND = 'python3 .veldo/control_graph_install.py --rebuild'
TAXONOMY = {
    'missing_asset': 'missing_evidence', 'records_invalid': 'invalid_input', 'records_stale': 'stale_subject',
    'unrecorded_package': 'missing_evidence', 'unlocked_record': 'invalid_input', 'record_mismatch': 'invalid_input',
    'hash_mismatch': 'invalid_input', 'license_unrecorded': 'missing_evidence', 'license_unapproved': 'missing_authority',
    'approval_missing': 'missing_authority', 'license_mismatch': 'invalid_input', 'runtime_absent': 'unavailable_service',
    'runtime_unreadable': 'unavailable_service', 'runtime_isolation': 'invalid_input', 'install_failed': 'unavailable_service',
    'missing_dependency': 'missing_evidence', 'unsatisfied_dependency': 'invalid_input', 'version_mismatch': 'invalid_input',
    'unlocked_distribution': 'invalid_input', 'file_mismatch': 'invalid_input', 'content_mismatch': 'invalid_input',
    'path_outside_runtime': 'invalid_input', 'python_mismatch': 'invalid_input', 'tooling_failed': 'unknown_outcome',
}
# Rows pip writes beside a wheel's own: these dist-info files, the scripts it generates or rewrites
# outside site-packages, and the bytecode it compiles, which it records with no hash. Bytecode a wheel
# itself carries has a hash and is part of the wheel's content like any other file.
PIP_WRITTEN = ('INSTALLER', 'REQUESTED', 'RECORD', 'direct_url.json')
COUNTS = {'accepted': 0, 'refused': 0}
DOMAIN = REPOSITORY = 'runtime-qualification'
QUALIFICATION_WORKFLOW = 'veldo-runtime-qualification'
QUALIFICATION = r'''
# ---- VELDO-0045 activation qualification: deterministic and nonpersistent, no model, no network ----
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
# Run by the runtime's own interpreter: its importlib.metadata and its packaging are the tooling.
TRANSITIVE = r'''
import json, sys
from importlib import metadata
import os, sysconfig
report = {'python': '%d.%d' % sys.version_info[:2], 'prefix': sys.prefix, 'path': list(sys.path),
          'stdlib': sorted({sysconfig.get_path('stdlib'), sysconfig.get_path('platstdlib')}),
          'zip': os.path.join(sys.base_prefix, 'lib', 'python%d%d.zip' % sys.version_info[:2]),
          'tooling': None, 'requirements': []}
try:
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
except Exception as error:
    report['tooling'] = type(error).__name__
else:
    installed = {}
    for dist in metadata.distributions():
        installed.setdefault(canonicalize_name(dist.metadata['Name']), dist.version)
    for dist in metadata.distributions():
        for text in dist.requires or ():
            requirement = Requirement(text)
            if requirement.marker is not None and not requirement.marker.evaluate({'extra': ''}):
                continue
            name = canonicalize_name(requirement.name)
            version = installed.get(name)
            report['requirements'].append({
                'by': dist.metadata['Name'], 'name': requirement.name, 'canonical': name,
                'specifier': str(requirement.specifier), 'installed': version,
                'satisfied': version is not None and requirement.specifier.contains(version, prereleases=True)})
sys.stdout.write(json.dumps(report))
'''
# Enforcement: the installed gate and guard name the gate imports; authorization is its own entry.
GATE, GUARD = 'scripts/verify.sh', 'scripts/veldo-guard.sh'
AUTHORIZATION = ('.veldo/authorization.py',)
VERDICTS = {'.veldo/policy_check.py': (0, 1), '.veldo/version.py': (0, 1, 2)}
INVOCATION = re.compile(r'\bpython3\s+((?:\./)?[\w./-]+\.py)((?:[ \t]+[a-z][a-z-]*)*)')
DECLARATION = re.compile(r'^\s*CHECK_\w+="([^"]*)"')
PROBE = ('.veldo/control_runtime.py', ('--probe-graph',))
# Prepended to control_graph_isolation's harness: the runtime directory is hidden, not merely unimported.
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
            raise PermissionError('the graph runtime is hidden: ' + _hide_os.fsdecode(place))
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


def _lock():
    return _load('veldo_runtime_lock', 'control_graph_lock.py')


def canonical(name):
    """PEP 503 normalized distribution name."""
    return re.sub(r'[-_.]+', '-', str(name)).lower()


def sha256(data):
    return hashlib.sha256(data if type(data) is bytes else data.encode()).hexdigest()


def _record_hash(data):
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()


def content_digest(rows):
    """The content digest the records pin: sha256 over the sorted 'path,hash' rows of a wheel."""
    return sha256('\n'.join(sorted('%s,%s' % row for row in rows)))


def _finish(report, problems):
    report['problems'] = list(dict.fromkeys(problems))
    report['outcome'] = 'refused' if report['problems'] else 'accepted'
    report['taxonomy'] = sorted({TAXONOMY.get(p.split(':', 1)[0], 'unknown_outcome') for p in report['problems']})
    COUNTS[report['outcome']] += 1
    report['counts'] = dict(COUNTS)
    return report


def license_problems(name, entry):
    license = entry.get('license') if type(entry.get('license')) is dict else {}
    spdx = license.get('spdx')
    if type(spdx) is not str or not spdx.strip():
        return ['license_unrecorded:' + name]
    identifiers = [t for t in re.findall(r'[A-Za-z0-9.+-]+', spdx) if t not in ('AND', 'OR', 'WITH')]
    return ['license_unapproved:%s:%s' % (name, t) for t in identifiers if t not in APPROVED_LICENSES] or (
        [] if identifiers else ['license_unrecorded:' + name])


def record_problems(lock, records):
    """The records against the lock: bound to its digest, one record per locked package, exactly."""
    if (type(records) is not dict or records.get('schema') != RECORDS_SCHEMA
            or type(records.get('packages')) is not list):
        return ['records_invalid:schema']
    problems = [] if records.get('lock_digest') == lock.digest() else ['records_stale:' + str(records.get('lock_digest'))]
    recorded = {}
    for entry in records['packages']:
        if type(entry) is not dict or type(entry.get('name')) is not str:
            problems.append('records_invalid:package')
        elif canonical(entry['name']) in recorded:
            problems.append('records_invalid:duplicate:' + entry['name'])
        else:
            recorded[canonical(entry['name'])] = entry
    locked = {canonical(row[0]): row for row in lock.PACKAGES}
    for key, (name, version, wheel, pinned) in sorted(locked.items()):
        entry = recorded.get(key)
        if entry is None:
            problems.append('unrecorded_package:' + name)
            continue
        problems += ['record_mismatch:%s:%s' % (name, field) for field, value in (('version', version), ('wheel', wheel))
                     if entry.get(field) != value]
        if entry.get('sha256') != pinned:
            problems.append('hash_mismatch:' + name)
        problems += license_problems(name, entry)
        if type(entry.get('approval')) is not str or not entry['approval'].strip():
            problems.append('approval_missing:' + name)
        digest = (entry.get('content') or {}).get('sha256') if type(entry.get('content')) is dict else None
        if type(digest) is not str or not re.fullmatch(r'[0-9a-f]{64}', digest):
            problems.append('records_invalid:content:' + name)
    problems += ['unlocked_record:' + recorded[key]['name'] for key in sorted(set(recorded) - set(locked))]
    return problems


def _site(lock, directory):
    return directory / 'lib' / ('python' + lock.PYTHON) / 'site-packages'


def _pip_written(path, digest, info):
    return (path.startswith('../') or path in [info + '/' + name for name in PIP_WRITTEN]
            or (not digest and path.endswith('.pyc')))


def content_problems(name, site, info, entry):
    """Every RECORD row against its file, and the wheel's own rows against the genuine wheel."""
    problems, kept = [], []
    rows = [row for row in csv.reader(io.StringIO((info / 'RECORD').read_text(encoding='utf-8'))) if row]
    for row in rows:
        path, digest = row[0], row[1] if len(row) > 1 else ''
        if digest:
            algorithm, _, value = digest.partition('=')
            target = site / path
            if algorithm != 'sha256' or not target.is_file() or _record_hash(target.read_bytes()) != value:
                problems.append('file_mismatch:%s:%s' % (name, path))
        if not _pip_written(path, digest, info.name):
            kept.append((path, digest))
    if content_digest(kept) != entry['content'].get('sha256'):
        problems.append('content_mismatch:' + name)
    return problems


def installed_problems(lock, records, directory):
    """The installed distributions against the lock and records, their files against RECORD."""
    site = _site(lock, directory)
    installed = {}
    with os.scandir(site) as listing:
        for item in listing:
            if item.name.endswith('.dist-info') and item.is_dir(follow_symlinks=False):
                text = (Path(item.path) / 'METADATA').read_text(encoding='utf-8')
                meta = email.parser.Parser().parsestr(text, headersonly=True)
                installed[canonical(meta['Name'])] = (Path(item.path), meta)
    recorded = {canonical(e['name']): e for e in records['packages'] if type(e) is dict and 'name' in e}
    problems = []
    for name, version, _wheel, _hash in lock.PACKAGES:
        found = installed.get(canonical(name))
        if found is None:
            problems.append('missing_dependency:' + name)
            continue
        info, meta = found
        if meta['Version'] != version:
            problems.append('version_mismatch:%s:%s' % (name, meta['Version']))
        entry = recorded.get(canonical(name))
        if entry is None or type(entry.get('content')) is not dict:
            continue
        license = entry.get('license') or {}
        if ((meta.get('License') or None) != license.get('registry_license')
                or (meta.get('License-Expression') or None) != license.get('registry_license_expression')):
            problems.append('license_mismatch:' + name)
        problems += content_problems(name, site, info, entry)
    locked = {canonical(row[0]) for row in lock.PACKAGES}
    problems += ['unlocked_distribution:' + installed[key][1]['Name'] for key in sorted(set(installed) - locked)]
    return problems


def _under(path, base):
    path, base = os.path.realpath(path), os.path.realpath(base)
    return path == base or path.startswith(base + os.sep)


def metadata_problems(lock, directory):
    """The runtime's own tooling evaluates every installed requirement for this interpreter."""
    graph = _graph()
    with tempfile.TemporaryDirectory(prefix='veldo-runtime-metadata-') as empty:
        proc = subprocess.run([str(directory / 'bin' / 'python'), '-I', '-B', '-c', TRANSITIVE], cwd=empty,
                              env=dict(graph.ENVIRONMENT), stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
    if proc.returncode:
        return ['tooling_failed:exit %d' % proc.returncode]
    try:
        report = json.loads(proc.stdout)
    except ValueError:
        return ['tooling_failed:unreadable report']
    if report['tooling']:
        return ['tooling_failed:' + report['tooling']]
    problems = [] if report['python'] == lock.PYTHON else ['python_mismatch:' + report['python']]
    if not _under(report['prefix'], directory):
        problems.append('path_outside_runtime:' + report['prefix'])
    problems += ['path_outside_runtime:' + entry for entry in report['path']
                 if entry and entry != report['zip'] and not (_under(entry, directory)
                                                            or any(_under(entry, lib) for lib in report['stdlib']))]
    locked = {canonical(row[0]): row[0] for row in lock.PACKAGES}
    for requirement in report['requirements']:
        if requirement['canonical'] not in locked or requirement['installed'] is None:
            problems.append('missing_dependency:' + locked.get(requirement['canonical'], requirement['name']))
        elif not requirement['satisfied']:
            problems.append('unsatisfied_dependency:%s:%s' % (locked[requirement['canonical']], requirement['specifier']))
    return problems


def activation(home=None):
    """Whether this account's locked runtime may be used, as a report with every named problem."""
    report = {'schema': SCHEMA, 'operation': 'activate', 'journey': ['.veldo/' + rel for rel in JOURNEY],
              'lock_digest': None, 'records_digest': None, 'runtime': None, 'packages': 0}
    missing = ['missing_asset:.veldo/' + rel for rel in JOURNEY if not _asset(rel).is_file()]
    if missing:
        return _finish(report, missing)
    lock = _lock()
    raw = _asset(RECORDS).read_bytes()
    report.update(lock_digest=lock.digest(), records_digest='sha256:' + sha256(raw), packages=len(lock.PACKAGES))
    try:
        records = json.loads(raw)
    except ValueError:
        return _finish(report, ['records_invalid:json'])
    problems = record_problems(lock, records)
    if problems and problems[0] == 'records_invalid:schema':
        return _finish(report, problems)
    directory = lock.runtime_directory(home)
    report['runtime'] = str(directory)
    if not (directory / 'bin' / 'python').is_file():
        return _finish(report, problems + ['runtime_absent:' + lock.digest()])
    try:
        problems += installed_problems(lock, records, directory)
        problems += metadata_problems(lock, directory)
        problems += ['runtime_isolation:' + text for text in _graph().runtime_problems({'python': str(directory / 'bin' / 'python')})]
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        problems.append('runtime_unreadable:' + (getattr(error, 'strerror', None) or type(error).__name__))
    return _finish(report, problems)


def adapter(domain_uuid, repository_uuid, home=None, stage=None, timeout=120):
    """The graph adapter over this account's runtime, only once activation accepts it."""
    graph = _graph()
    report = activation(home)
    if report['outcome'] != 'accepted':
        raise graph.Refused('runtime_unavailable', 'the graph runtime is not activated (' + '; '.join(report['problems'][:6])
                            + '); install it with: ' + INSTALL_COMMAND + ', or rebuild it with: ' + REBUILD_COMMAND)
    return graph.Adapter.installed(domain_uuid, repository_uuid, home=home, timeout=timeout, stage=stage)


def qualification_runner():
    """The production runner with the qualification workflow registered before its entry point."""
    source = _asset('control_graph_langgraph.py').read_text()
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
            'pending': adapter.pending(), 'observations': adapter.observations}


def qualify(home=None, stage=None):
    """Activation, then the actual nonpersistent adapter workload on the activated runtime."""
    report = {'schema': SCHEMA, 'operation': 'qualify', 'activation': activation(home), 'workload': None}
    if report['activation']['outcome'] != 'accepted':
        return _finish(report, report['activation']['problems'])
    graph = _graph()
    base = graph.Adapter.installed(DOMAIN, REPOSITORY, home=home, stage=stage).runtime
    if base is None:
        return _finish(report, ['runtime_absent:' + _lock().digest()])
    workflow = {'id': QUALIFICATION_WORKFLOW, 'version': 1, 'digest': 'sha256:' + sha256(QUALIFICATION)}
    with tempfile.TemporaryDirectory(prefix='veldo-qualify-') as scratch:
        runner = Path(scratch) / 'control_graph_langgraph.py'
        runner.write_text(qualification_runner())
        report['workload'] = _workload(graph, dict(base, runner=str(runner)), workflow)
    return _finish(report, [] if report['workload']['passed'] else ['tooling_failed:qualification workload'])


def install(home=None, stage=None):
    """The one installer (control_graph_install.py), then activation and qualification."""
    missing = ['missing_asset:.veldo/' + rel for rel in JOURNEY if not _asset(rel).is_file()]
    if missing:
        return _finish({'schema': SCHEMA, 'operation': 'install'}, missing)
    try:
        _load('veldo_runtime_installer', 'control_graph_install.py').install(home=home, out=sys.stderr)
    except (subprocess.CalledProcessError, OSError, SystemExit) as error:
        return _finish({'schema': SCHEMA, 'operation': 'install'}, ['install_failed:' + type(error).__name__])
    return dict(qualify(home, stage), operation='install')


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
    return [os.path.realpath(str(_lock().runtime_directory().parent))]


def run_hidden(root, module, argv, hidden, timeout=120):
    """One real command in the isolated harness with the runtime hidden."""
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
    """Every enabled enforcement entry, run with the runtime hidden; graph invocation reports unavailable."""
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
    """Graph invocation with the runtime absent and, inside the hidden harness, hidden: both must
    report runtime_unavailable. Outside the harness an installed runtime is not hidden, so the second
    answer is not a refusal and the probe fails, as it should."""
    graph = _graph()
    answers = []
    version = {'id': 'probe', 'version': 1, 'digest': 'sha256:' + '0' * 64}
    with tempfile.TemporaryDirectory(prefix='veldo-no-runtime-') as empty:
        for label, home in (('absent', empty), ('hidden', None)):
            try:
                adapter('probe-domain', 'probe-repository', home=home, stage=Path(empty) / 'stage').start(
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
