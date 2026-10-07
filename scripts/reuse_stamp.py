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
    if not isinstance(receipt, dict):
        raise ValueError('missing or inconsistent mutation reuse receipt')
    if receipt.get('status') == 'failed':
        # A failed stage is red on its own; its receipt is evidence of nothing, reuse included.
        raise ValueError('the mutation stage failed (%s)' % str(receipt.get('error', 'unnamed error'))[:200])
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


def not_run(force):
    """A gate whose mutation stage was declared na: or waived: ran no case and has no receipt:
    nothing was reused, and the freshness request is still reported."""
    return {'force_fresh': force, 'reused': {'unit': 0, 'mutation': 0}}


def main(argv):
    """Print the stamp's reuse fields. A receipt that cannot carry them (a failed stage, an empty
    or unreadable receipt, a reuse claim without evidence) is a one-line refusal and exit 1, never
    a traceback, and the fields printed are a RED stamp's: the requested mode and no reuse claimed
    (reused.mutation null). verify.sh stamps RED with them."""
    try:
        if argv[1] == '--not-run':
            answer = not_run(truthy(argv[2]))
        else:
            with open(argv[1]) as stream:
                try:
                    receipt = json.load(stream)
                except ValueError as error:
                    raise ValueError('unreadable mutation receipt (%s)' % error) from None
            answer = fields(receipt, truthy(argv[2]), argv[3])
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print('mutation reuse: no stamp fields: %s; the gate is RED and claims no reuse' % error,
              file=sys.stderr)
        try:
            print(json.dumps({'force_fresh': truthy(argv[2]), 'reused': {'mutation': None, 'unit': 0}},
                             separators=(',', ':'))[1:-1])
        except (ValueError, IndexError):
            pass
        return 1
    print(json.dumps(answer, separators=(',', ':'))[1:-1])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
