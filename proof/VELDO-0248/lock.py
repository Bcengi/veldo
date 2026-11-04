#!/usr/bin/env python3
"""Regenerate the LangGraph lock, its reviewed closure and the closure diff from the registry (VELDO-0248 AC1, AC2).

    TOOL/bin/python -I -B proof/VELDO-0248/lock.py SCRATCH_DIR ROOT_REQUIREMENT

TOOL is a throwaway CPython 3.12 virtual environment with its bundled pip (24.0 here); its pip resolves
the closure and its vendored packaging evaluates the requirement specifiers. Steps:

1. Resolution. Unless SCRATCH_DIR already holds pip-report.json (a cached read), runs
   `pip install --dry-run --only-binary=:all: --report SCRATCH/pip-report.json ROOT_REQUIREMENT` in TOOL:
   the closure ROOT_REQUIREMENT resolves to for CPython 3.12 on linux x86_64, binary wheels only, each
   package at the newest release the closure allows.
2. Registry. For every resolved package reads PyPI JSON for its exact release and for the project
   (through proof/VELDO-0045/records.py's fetch, so the reads are cached in SCRATCH_DIR under the same
   names records.py uses), and refuses a wheel whose registry sha256 differs from the one pip resolved.
   The latest release is the registry's info.version, as records.py records it. A pin below it gets
   why_not_latest: every requirement in the resolved closure whose specifier excludes the latest.
3. Approval stop. Every package must have a reviewed entry in proof/VELDO-0043/dependency-closure.json
   (origin and approval are carried from it, never invented), and its SPDX license must keep the same
   expression and stay inside control_runtime.APPROVED_LICENSES. Otherwise the closure diff is written,
   the package is named, and the script exits 3 WITHOUT writing the lock or the closure.
4. Output. Writes proof/VELDO-0248/closure-diff.json, proof/VELDO-0248/dependency-closure.json and the
   lock (.veldo/control_graph_lock.py and engine/.veldo/control_graph_lock.py, byte-identical): RESOLVED,
   ROOT_REQUIREMENT and the PACKAGES rows are regenerated; the rest of the module is kept.

The registry license fields of the reviewed closure are read from the records at the base commit
(engine/runtime/langgraph-records.json at BASE), which recorded the registry for the 1.2.12 lock.
Needs the network unless every read is cached; never run by a suite or the gate.
"""
import datetime
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'proof/VELDO-0248'
BASE = '67594919'
LOCKS = (ROOT / '.veldo/control_graph_lock.py', ROOT / 'engine/.veldo/control_graph_lock.py')
REVIEWED = ROOT / 'proof/VELDO-0043/dependency-closure.json'


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve(scratch, root):
    report = scratch / 'pip-report.json'
    if not report.is_file():
        env = {'PATH': '/usr/bin:/bin', 'PIP_CONFIG_FILE': '/dev/null', 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
               'PIP_NO_INPUT': '1'}
        subprocess.run([sys.executable, '-I', '-m', 'pip', 'install', '--dry-run', '--only-binary=:all:',
                        '--report', str(report), '-q', root], env=env, check=True)
    return json.loads(report.read_text())


def license_of(info, spdx_map):
    expression, text = info.get('license_expression') or None, info.get('license') or None
    return {'registry_license': text, 'registry_license_expression': expression,
            'spdx': expression or spdx_map.get(text, text)}


def source_of(info):
    urls = {key.lower(): value for key, value in (info.get('project_urls') or {}).items()}
    return next((urls[k] for k in ('source', 'source code', 'repository', 'code', 'github', 'homepage') if urls.get(k)),
                info.get('home_page'))


def main(scratch, root):
    scratch = Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    records_tool = _load('records', ROOT / 'proof/VELDO-0045/records.py')
    runtime = _load('control_runtime', ROOT / '.veldo/control_runtime.py')
    report = resolve(scratch, root)
    environment = dict(report['environment'], extra='')
    resolved = sorted(report['install'], key=lambda i: i['metadata']['name'].lower())
    versions = {canonicalize_name(i['metadata']['name']): i['metadata']['version'] for i in resolved}
    reviewed = json.loads(REVIEWED.read_text())
    old = {c['name']: c for c in reviewed['closure']}
    base_records = json.loads(subprocess.run(['git', '-C', str(ROOT), 'show', BASE + ':engine/runtime/langgraph-records.json'],
                                             capture_output=True, text=True, check=True).stdout)
    old_records = {p['name']: p for p in base_records['packages']}

    closure, stops, moved, licenses, wheels, sources = [], [], [], [], [], []
    for item in resolved:
        meta, download = item['metadata'], item['download_info']
        name, version = meta['name'], meta['version']
        wheel = download['url'].rsplit('/', 1)[1]
        sha256 = download['archive_info']['hashes']['sha256']
        status, body = records_tool.fetch('https://pypi.org/pypi/%s/%s/json' % (name, version), scratch,
                                          '%s-%s.json' % (name, version))
        assert status == 200, (name, status)
        release = json.loads(body)
        served = [u for u in release['urls'] if u['filename'] == wheel]
        assert len(served) == 1 and served[0]['digests']['sha256'] == sha256, (name, wheel, 'registry sha256 differs')
        _, latest_body = records_tool.fetch('https://pypi.org/pypi/%s/json' % name, scratch, '%s-latest.json' % name)
        latest = json.loads(latest_body)['info']['version']
        requires, caps = [], []
        for text in meta.get('requires_dist') or []:
            requirement = Requirement(text)
            if requirement.marker is not None and 'extra' in str(requirement.marker):
                continue
            requires.append(requirement.name)
        for other in resolved:
            for text in other['metadata'].get('requires_dist') or []:
                requirement = Requirement(text)
                if canonicalize_name(requirement.name) != canonicalize_name(name):
                    continue
                if requirement.marker is not None and not requirement.marker.evaluate(environment):
                    continue
                if not requirement.specifier.contains(latest, prereleases=True):
                    caps.append('%s %s requires "%s"' % (other['metadata']['name'], other['metadata']['version'],
                                                         str(requirement.name) + str(requirement.specifier)))
        license = license_of(release['info'], records_tool.SPDX)
        entry = old.get(name)
        if entry is None:
            stops.append({'name': name, 'version': version, 'reason': 'no reviewed closure entry (new package)',
                          'license': license})
        before = old_records.get(name)
        if before is not None:
            if entry['pinned'] != version:
                moved.append({'name': name, 'old': entry['pinned'], 'new': version})
            if (before['license']['registry_license'], before['license']['registry_license_expression']) != (
                    license['registry_license'], license['registry_license_expression']):
                change = {'name': name, 'old': before['license'], 'new': license,
                          'spdx_changed': before['license']['spdx'] != license['spdx']}
                licenses.append(change)
                if change['spdx_changed']:
                    stops.append({'name': name, 'version': version, 'reason': 'SPDX license changed',
                                  'old': before['license']['spdx'], 'new': license['spdx']})
            if before['wheel'].split('-', 2)[2:] != wheel.split('-', 2)[2:]:
                wheels.append({'name': name, 'old': before['wheel'], 'new': wheel})
            if before['source'] != source_of(release['info']):
                sources.append({'name': name, 'old': before['source'], 'new': source_of(release['info'])})
        unapproved = runtime.license_problems(name, {'license': license})
        if unapproved:
            stops.append({'name': name, 'version': version, 'reason': 'license outside the approved set',
                          'problems': unapproved})
        if entry is None:
            continue
        row = {'name': name, 'license': license['spdx'], 'origin': entry['origin'], 'requires': requires,
               'status': entry['status'], 'pinned': version, 'latest_on_pypi': latest, 'wheel': wheel,
               'sha256': sha256}
        if latest != version:
            assert caps, (name, version, latest, 'below the latest with no requirement capping it')
            row['why_not_latest'] = '; '.join(caps)
        closure.append(row)

    names = {i['metadata']['name'] for i in resolved}
    diff = {
        'schema': 'veldo.closure-diff/v1',
        'base': {'closure': 'proof/VELDO-0043/dependency-closure.json', 'root': base_records['root'],
                 'read': base_records['read'], 'registry_license_fields': 'engine/runtime/langgraph-records.json at ' + BASE},
        'new': {'closure': 'proof/VELDO-0248/dependency-closure.json', 'root': root,
                'read': datetime.date.today().isoformat()},
        'packages': len(resolved),
        'added': sorted(names - set(old)), 'removed': sorted(set(old) - names), 'moved': moved,
        'unchanged': sorted(n for n in names & set(old) if old[n]['pinned'] == versions[canonicalize_name(n)]),
        'license_changed': licenses, 'wheel_tag_changed': wheels, 'source_changed': sources,
        'not_latest': {r['name']: {'pinned': r['pinned'], 'latest': r['latest_on_pypi'], 'why_not_latest': r['why_not_latest']}
                       for r in closure if 'why_not_latest' in r},
        'owner_approval_needed': stops,
    }
    (HERE / 'closure-diff.json').write_text(json.dumps(diff, indent=1) + '\n')
    if stops:
        print(json.dumps({'stopped': stops}, indent=1))
        return 3

    pip_version = subprocess.run([sys.executable, '-I', '-m', 'pip', '--version'], capture_output=True, text=True,
                                 check=True).stdout.split()[1]
    new_closure = {
        'schema': reviewed['schema'],
        'how': ('pip install --dry-run --only-binary=:all: --report for %s in a throwaway venv, Python %s, pip %s, '
                'linux x86_64 (proof/VELDO-0248/lock.py; the report is proof/VELDO-0248/registry/pip-report.json); '
                'latest_on_pypi is info.version in https://pypi.org/pypi/<name>/json, read %s. Licenses from PyPI '
                'metadata as SPDX; origin and approval carried from proof/VELDO-0043/dependency-closure.json. The same '
                'pins and hashes are .veldo/control_graph_lock.py.'
                % (root, report['environment']['python_full_version'], pip_version, diff['new']['read'])),
        'closure': closure,
    }
    (HERE / 'dependency-closure.json').write_text(json.dumps(new_closure, indent=1) + '\n')

    text = LOCKS[0].read_text()
    head, rest = text.split('\nPACKAGES = (\n', 1)
    _, tail = rest.split('\n)\n', 1)
    lines = []
    for line in head.split('\n'):
        if line.startswith('RESOLVED = '):
            line = 'RESOLVED = %r' % diff['new']['read']
        elif line.startswith('ROOT_REQUIREMENT = '):
            line = 'ROOT_REQUIREMENT = %r' % root
        lines.append(line)
    rows = ''.join("    (%r, %r,\n     %r,\n     %r),\n" % (r['name'], r['pinned'], r['wheel'], r['sha256'])
                   for r in closure)
    out = '\n'.join(lines) + '\nPACKAGES = (\n' + rows + ')\n' + tail
    for target in LOCKS:
        target.write_text(out)
    lock = _load('lock', LOCKS[0])
    print(json.dumps({'packages': len(lock.PACKAGES), 'root': lock.ROOT_REQUIREMENT, 'resolved': lock.RESOLVED,
                      'lock_digest': lock.digest(), 'moved': len(moved), 'added': diff['added'],
                      'removed': diff['removed'], 'not_latest': diff['not_latest']}))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
