"""Reduce validated stage receipts to the reuse fields carried by the gate."""
import json
import importlib.util
from pathlib import Path
import sys
def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

truthy = load('mutation_reuse').truthy
E = load('gate_reuse').E


def fields(receipt, force, commit=None):
    if (receipt.get('status') != 'passed' or type(receipt.get('reused')) is not int
            or receipt['reused'] < 0 or type(receipt.get('force_fresh')) is not bool
            or receipt['force_fresh'] != force or (force and receipt['reused'])):
        raise ValueError('missing or inconsistent mutation reuse receipt')
    answer = {'force_fresh': force, 'reused': {'unit': 0, 'mutation': receipt['reused']}}
    if not receipt['reused']:
        return answer
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('landing reuse requires a gate commit')
    _, config = E.configuration()
    directory = Path(config['store'])
    secret = E.probe(directory)
    records, seen = [], set()
    spec = importlib.util.spec_from_file_location('gate', Path(__file__).with_name('check_gate_mutations.py'))
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    results = receipt['results']
    if (len(results) != receipt['registered']
            or sum(r['source'] == 'fresh' for r in results) != receipt['executed']
            or receipt['executed'] + receipt['reused'] != receipt['registered']):
        raise ValueError('incomplete mutation receipt')
    for result in results:
        identity = result['case']['identity']
        if identity in seen or result['source'] not in ('fresh', 'reused'):
            raise ValueError('duplicate case or invalid execution source')
        seen.add(identity)
        if result['source'] != 'reused':
            continue
        key = result['reuse_key']
        stored = E.record(directory, key, secret)
        gate.validate_result(stored, result['case'])
        original = {k: v for k, v in result.items() if k not in ('reuse_key', 'source', 'reuse_reason')}
        if original != stored or stored['input_digest'] != key:
            raise ValueError('reused observation differs from declared case key')
        records.append(dict(key=key, identity=identity, result_digest=E.digest(stored)))
    if len(records) != receipt['reused']:
        raise ValueError('reuse count differs from authenticated records')
    payload = dict(schema='veldo.landing-reuse/v1', provenance=E.PROVENANCE, authority=E.authority_identity(),
                   commit=commit, records=records, **answer)
    answer['reuse_evidence'] = E.sign(payload, secret)
    return answer


if __name__ == '__main__':
    with open(sys.argv[1]) as stream:
        receipt = json.load(stream)
    print(json.dumps(fields(receipt, truthy(sys.argv[2]), sys.argv[3]), separators=(',', ':'))[1:-1])
