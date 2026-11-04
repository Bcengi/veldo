#!/usr/bin/env python3
"""Run every AC1 and AC2 falsifier of VELDO-0248 on scratch copies (never on the repository's own files).

    TOOL/bin/python -I -B proof/VELDO-0248/falsify.py SCRATCH_DIR WHEELS_DIR

TOOL is the throwaway venv lock.py runs in (its vendored packaging is needed to import lock.py).
WHEELS_DIR holds the 38 locked wheels records.py downloaded; SCRATCH_DIR is created empty and holds every
copy. Registry reads come from proof/VELDO-0248/registry, so no case needs the network. Activation cases
run control_runtime from a copy of .veldo (its own assets), against the account's installed 1.2.19 runtime
read only, or against a copy of that runtime under a scratch home. Prints one JSON line per case and exits
non-zero if any case did not go red the way the spec names.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'proof/VELDO-0248/registry'
CLOSURE = 'proof/VELDO-0248/dependency-closure.json'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cache(target, wheels):
    target.mkdir(parents=True)
    for item in REGISTRY.iterdir():
        if item.name != 'reads.json':
            shutil.copy(item, target / item.name)
    for wheel in Path(wheels).glob('*.whl'):
        shutil.copy(wheel, target / wheel.name)
    return target


def tree(target, lock_text=None):
    """A minimal tree records.py runs in: the lock, records.py and the reviewed closure."""
    for rel in ('.veldo/control_graph_lock.py', 'proof/VELDO-0045/records.py', CLOSURE):
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, target / rel)
    if lock_text is not None:
        (target / '.veldo/control_graph_lock.py').write_text(lock_text)
    return target


def records(target, scratch):
    proc = subprocess.run([sys.executable, '-I', '-B', str(target / 'proof/VELDO-0045/records.py'), str(scratch), CLOSURE],
                          capture_output=True, text=True)
    lines = proc.stderr.strip().splitlines()
    return proc.returncode, lines[-1][:300] if lines else proc.stdout.strip()[:300]


def installation(target, lock_text=None, records_text=None):
    shutil.copytree(ROOT / '.veldo', target, ignore=shutil.ignore_patterns('__pycache__'))
    if lock_text is not None:
        (target / 'control_graph_lock.py').write_text(lock_text)
    if records_text is not None:
        (target / 'runtime/langgraph-records.json').write_text(records_text)
    return load('control_runtime_' + target.name.replace('-', '_'), target / 'control_runtime.py')


def main(scratch, wheels):
    scratch = Path(scratch)
    scratch.mkdir(parents=True)
    lock_text = (ROOT / '.veldo/control_graph_lock.py').read_text()
    lock = load('lock', ROOT / '.veldo/control_graph_lock.py')
    results = []

    def case(name, passed, observed):
        results.append({'case': name, 'red_as_named': bool(passed), 'observed': observed})
        print(json.dumps(results[-1]))

    # AC1: one lock sha256 changed.
    name, version, wheel, sha = lock.PACKAGES[0]
    bad = sha[:-1] + ('0' if sha[-1] != '0' else '1')
    altered = lock_text.replace(repr(sha), repr(bad), 1)
    assert altered != lock_text
    code, line = records(tree(scratch / 'ac1-hash-tree', altered), cache(scratch / 'ac1-hash-cache', wheels))
    case('AC1 lock sha256 changed: records.py stops', code != 0 and name in line, {'exit': code, 'stderr': line})
    runtime = installation(scratch / 'ac1-hash-veldo', lock_text=altered)
    report = runtime.activation()
    case('AC1 lock sha256 changed: activation answers hash_mismatch',
         report['outcome'] == 'refused' and 'hash_mismatch:' + name in report['problems'], report['problems'][:4])

    # AC1: one wheel member changed in the scratch download.
    name, version, wheel, sha = next(row for row in lock.PACKAGES if row[0] == 'langgraph')
    downloads = cache(scratch / 'ac1-member-cache', wheels)
    original = downloads / wheel
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(downloads / (wheel + '.new'), 'w') as out:
        changed = next(n for n in source.namelist() if n.endswith('.py'))
        for info in source.infolist():
            data = source.read(info.filename)
            out.writestr(info, data + b'\n# altered\n' if info.filename == changed else data)
    (downloads / (wheel + '.new')).replace(original)
    code, line = records(tree(scratch / 'ac1-member-tree'), downloads)
    case('AC1 wheel member changed: records.py stops', code != 0 and name in line,
         {'member': changed, 'exit': code, 'stderr': line})

    # AC1: an installed file changed together with its RECORD row (a hash-bypassed install) in a copy of
    # the runtime under a scratch home: content_mismatch; the file alone changed: file_mismatch.
    home = scratch / 'ac1-home'
    copy = lock.runtime_directory(home)
    shutil.copytree(lock.runtime_directory(), copy, symlinks=True)
    site = copy / 'lib' / ('python' + lock.PYTHON) / 'site-packages'
    info = next(site.glob('langgraph-1.2.19.dist-info'))
    rows = (info / 'RECORD').read_text().splitlines()
    path = next(r.split(',')[0] for r in rows if r.startswith('langgraph/') and r.split(',')[0].endswith('.py'))
    target = site / path
    target.write_bytes(target.read_bytes() + b'\n# altered\n')
    runtime = installation(scratch / 'ac1-content-veldo')
    report = runtime.activation(home)
    case('AC1 installed file changed: activation answers file_mismatch',
         report['outcome'] == 'refused' and 'file_mismatch:langgraph:' + path in report['problems'], report['problems'][:4])
    digest = runtime._record_hash(target.read_bytes())
    size = target.stat().st_size
    (info / 'RECORD').write_text('\n'.join('%s,sha256=%s,%d' % (path, digest, size) if r.startswith(path + ',') else r
                                           for r in rows) + '\n')
    report = runtime.activation(home)
    case('AC1 installed file and its RECORD row changed: activation answers content_mismatch',
         report['outcome'] == 'refused' and report['problems'] == ['content_mismatch:langgraph'], report['problems'][:4])

    # AC1: a records file left at the 1.2.12 digest.
    stale = subprocess.run(['git', '-C', str(ROOT), 'show', '67594919:engine/runtime/langgraph-records.json'],
                           capture_output=True, text=True, check=True).stdout
    runtime = installation(scratch / 'ac1-stale-veldo', records_text=stale)
    report = runtime.activation()
    expected = 'records_stale:' + json.loads(stale)['lock_digest']
    case('AC1 records at the 1.2.12 digest: activation answers records_stale',
         report['outcome'] == 'refused' and expected in report['problems'], report['problems'][:4])

    # AC1: a pin below its latest release with no requirement capping it: lock.py stops, writes nothing.
    tool = load('lock_tool', ROOT / 'proof/VELDO-0248/lock.py')
    out = scratch / 'ac1-cap-out'
    out.mkdir()
    tool.HERE, tool.LOCKS = out, (out / 'a.py', out / 'b.py')
    reads = cache(scratch / 'ac1-cap-cache', wheels)
    report = json.loads((reads / 'pip-report.json').read_text())
    for item in report['install']:
        if item['metadata']['name'] == 'pydantic':
            item['metadata']['requires_dist'] = [r for r in item['metadata']['requires_dist'] if not r.startswith('pydantic-core')]
    (reads / 'pip-report.json').write_text(json.dumps(report))
    try:
        tool.main(reads, 'langgraph==1.2.19')
        observed = 'lock.py finished'
    except AssertionError as error:
        observed = 'AssertionError ' + str(error)
    case('AC1 pin below latest with no why_not_latest: lock.py stops',
         observed.startswith('AssertionError') and 'pydantic_core' in observed and not list(out.iterdir()), observed)

    # AC2: a fake package in the resolved closure with no reviewed entry.
    fake = ('veldo-fake-package', '1.0.0', 'veldo_fake_package-1.0.0-py3-none-any.whl', '0' * 64)
    rows = lock_text.split('\nPACKAGES = (\n', 1)
    faked = rows[0] + '\nPACKAGES = (\n    (%r, %r,\n     %r,\n     %r),\n' % fake + rows[1]
    code, line = records(tree(scratch / 'ac2-fake-tree', faked), cache(scratch / 'ac2-fake-cache', wheels))
    case('AC2 fake package: records.py stops naming it', code != 0 and fake[0] in line and 'no reviewed entry' in line,
         {'exit': code, 'stderr': line})
    out = scratch / 'ac2-fake-out'
    out.mkdir()
    tool.HERE, tool.LOCKS = out, (out / 'a.py', out / 'b.py')
    reads = cache(scratch / 'ac2-fake-reads', wheels)
    report = json.loads((reads / 'pip-report.json').read_text())
    report['install'].append({'metadata': {'name': fake[0], 'version': fake[1], 'requires_dist': []},
                              'download_info': {'url': 'https://files.example.invalid/' + fake[2],
                                                'archive_info': {'hashes': {'sha256': fake[3]}}}})
    (reads / 'pip-report.json').write_text(json.dumps(report))
    info = {'license_expression': 'MIT', 'license': None, 'version': fake[1], 'project_urls': {}}
    for file, body in (('%s-%s.json' % fake[:2], {'info': info, 'urls': [{'filename': fake[2], 'digests': {'sha256': fake[3]}}]}),
                       ('%s-latest.json' % fake[0], {'info': info})):
        (reads / file).write_text(json.dumps(body))
        (reads / (file + '.status')).write_text('200')
    code = tool.main(reads, 'langgraph==1.2.19')
    diff = json.loads((out / 'closure-diff.json').read_text())
    case('AC2 fake package: the diff lists it as added and the build stops',
         code == 3 and diff['added'] == [fake[0]] and [s['name'] for s in diff['owner_approval_needed']] == [fake[0]]
         and sorted(p.name for p in out.iterdir()) == ['closure-diff.json'],
         {'exit': code, 'added': diff['added'], 'owner_approval_needed': diff['owner_approval_needed']})

    # AC2: one package's registry license expression changed to one outside the approved set.
    out = scratch / 'ac2-license-out'
    out.mkdir()
    tool.HERE, tool.LOCKS = out, (out / 'a.py', out / 'b.py')
    reads = cache(scratch / 'ac2-license-reads', wheels)
    release = reads / 'tenacity-9.2.1.json'
    body = json.loads(release.read_text())
    body['info']['license_expression'] = 'GPL-3.0-only'
    release.write_text(json.dumps(body))
    code = tool.main(reads, 'langgraph==1.2.19')
    diff = json.loads((out / 'closure-diff.json').read_text())
    listed = [c for c in diff['license_changed'] if c['name'] == 'tenacity']
    case('AC2 license outside the approved set: the diff lists it and the build stops',
         code == 3 and listed and listed[0]['spdx_changed'] and 'tenacity' in [s['name'] for s in diff['owner_approval_needed']],
         {'exit': code, 'license_changed': listed, 'owner_approval_needed': diff['owner_approval_needed']})
    target = tree(scratch / 'ac2-license-tree')
    code, line = records(target, reads)
    produced = (target / 'engine/runtime/langgraph-records.json').read_text()
    runtime = installation(scratch / 'ac2-license-veldo', records_text=produced)
    report = runtime.activation()
    case('AC2 license outside the approved set: activation answers license_unapproved',
         code == 0 and report['outcome'] == 'refused' and 'license_unapproved:tenacity:GPL-3.0-only' in report['problems'],
         report['problems'][:4])

    # Control: the unaltered installation accepts the runtime.
    runtime = installation(scratch / 'control-veldo')
    report = runtime.activation()
    case('control: the unaltered lock, records and runtime are accepted', report['outcome'] == 'accepted', report['problems'])
    return 0 if all(r['red_as_named'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
