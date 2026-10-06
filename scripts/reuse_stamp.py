"""Reduce validated stage receipts to the reuse fields carried by the gate."""
import json
import sys
from mutation_reuse import truthy


def fields(receipt, force):
    if (receipt.get('status') != 'passed' or type(receipt.get('reused')) is not int
            or receipt['reused'] < 0 or type(receipt.get('force_fresh')) is not bool
            or receipt['force_fresh'] != force or (force and receipt['reused'])):
        raise ValueError('missing or inconsistent mutation reuse receipt')
    return {'force_fresh': force, 'reused': {'unit': 0, 'mutation': receipt['reused']}}


if __name__ == '__main__':
    with open(sys.argv[1]) as stream:
        receipt = json.load(stream)
    print(json.dumps(fields(receipt, truthy(sys.argv[2])), separators=(',', ':'))[1:-1])
