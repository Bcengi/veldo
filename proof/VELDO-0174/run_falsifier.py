"""Run one VELDO-0174 falsifier with only suite 107, restoring the source in finally.

Reads the gate's declared substitutions as AST data; never executes its mutation
driver. Logs stay in --log-dir. A red target is not a green gate or a host result.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case')
    parser.add_argument('--log-dir', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    cases = {}
    for node in ast.walk(ast.parse((root / 'scripts/check_teeth_mutations.py').read_text())):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'add'
                and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 174):
            name = ast.literal_eval(node.args[1])
            cases[name] = tuple(ast.literal_eval(node.args[i]) for i in (3, 4, 5, 6))
    cases['v174-record-memory-only'][3].append('AC1/durable-store')
    cases['v174-ignore-record-version'] = ('control_conversation.py',
        "        if type(params.get('version')) is not int or params['version'] != record.get('version'):\n",
        '        if False:\n', ['AC1/versioned-mutations'])
    cases['v174-drop-skills'] = ('control_agent_config_handoff.py',
        "    for item in selected(revision, 'skills'):\n",
        '    for item in ():\n', ['AC2/role-skills'])
    if args.case not in cases:
        parser.error('unknown case: ' + args.case)
    filename, before, after, targets = cases[args.case]
    path = root / '.veldo' / filename
    original = path.read_bytes()
    source = original.decode()
    if source.count(before) != 1:
        raise RuntimeError('expected exactly one mutation anchor: ' + filename)
    args.log_dir.mkdir(parents=True, exist_ok=True)
    log = args.log_dir / (args.case + '.log')
    argv = ['python3', 'scripts/selftest.py', '--suite', '107_veldo_0174_conversations']
    started = time.monotonic()
    try:
        path.write_text(source.replace(before, after))
        with log.open('w') as output:
            process = subprocess.run(argv, cwd=root, stdout=output, stderr=subprocess.STDOUT, timeout=120)
    finally:
        path.write_bytes(original)
    lines = log.read_text().splitlines()
    failures = [line.strip().split('VELDO-0174 ', 1)[1] for line in lines
                if 'SELFTEST FAIL: VELDO-0174 ' in line]
    result = dict(case=args.case, source=filename, command=argv, exit_code=process.returncode,
                  seconds=round(time.monotonic()-started, 2), target_rows=targets,
                  failed_rows=failures, targets_red=all(row in failures for row in targets),
                  source_restored=path.read_bytes() == original,
                  log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
    (args.log_dir / (args.case + '.json')).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
    return 0 if result['targets_red'] and process.returncode != 0 and result['source_restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
