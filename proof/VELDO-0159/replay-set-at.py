#!/usr/bin/env python3
"""VELDO-0159 review F1: the credential write answers with the STORED record's set at and set by.

Builds the browser rows' factory harness (engine/ui/e2e/harness.py: the real store, the real VELDO-0144
credential commands, the real API) on the repository's engine/.veldo modules, then:
1. through the API's credential routes (set, replace, delete): each answer's set_at and set_by equal the
   stored record's exactly, and no answer carries the value;
2. at the authority: an identical retry of a committed set (same command id), made after the clock has moved,
   answers with the ORIGINAL record's set_at and set_by, and writes nothing; the same for a delete.
Prints one line per check and exits 0 only if every check passed. Usage: python3 proof/VELDO-0159/replay-set-at.py
"""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('harness159', ROOT / 'engine/ui/e2e/harness.py')
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)
results = []


def check(name, ok, detail=''):
    results.append(bool(ok))
    print('%s %s %s' % ('PASS' if ok else 'FAIL', name, detail), flush=True)


def main():
    with tempfile.TemporaryDirectory(prefix='v159-replay-') as directory:
        factory = H.Factory(Path(directory), ROOT / 'engine/ui/dist', str(ROOT / 'engine/.veldo'))
        stored = lambda ident: factory.on_thread(factory.mcp_state)['credentials'][ident]
        journal = lambda: factory.on_thread(lambda: factory.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0])

        cookie, token = factory.session('owner')
        prefix = '/api/v1/domains/%s/mcp/credentials/' % H.DOMAIN
        value = 'replay-proof-value-4b7e'
        for step, path, body in (('set', 'set', dict(id='via-api', label='Via API', base=0, value=value)),
                                 ('replace', 'set', dict(id='via-api', label='Via API', base=1, value=value + '-2')),
                                 ('delete', 'delete', dict(id='via-api', base=2))):
            status, _headers, answer = factory.call('POST', prefix + path, body, cookie=cookie, token=token)
            record = stored('via-api')
            check('api/' + step, status == 200 and answer.get('set_at') == record['set_at']
                  and answer.get('set_by') == record['set_by'] == 'owner'
                  and value not in json.dumps(answer),
                  json.dumps({k: answer.get(k) for k in ('outcome', 'set_at', 'set_by')}) + ' record ' + str(record['set_at']))

        apply = lambda op, params, cid: factory.on_thread(
            factory.authority.mcp_credentials.apply, op, params, principal='owner', command_id=cid)
        params = dict(id='replayed', label='Replayed', base=0, value='replay-proof-value-9d01')
        first = apply('set_mcp_credential', params, 'replay-set-1')
        record = stored('replayed')
        before = journal()
        time.sleep(1.5)
        again = apply('set_mcp_credential', params, 'replay-set-1')
        check('authority/set-replay', first['set_at'] == again['set_at'] == record['set_at']
              and first['set_by'] == again['set_by'] == record['set_by'] == 'owner'
              and journal() == before and stored('replayed') == record and time.time() - again['set_at'] >= 1.5,
              'first %r replay %r record %r' % (first['set_at'], again['set_at'], record['set_at']))
        gone = apply('delete_mcp_credential', dict(id='replayed', base=1), 'replay-delete-1')
        record = stored('replayed')
        before = journal()
        time.sleep(1.5)
        gone_again = apply('delete_mcp_credential', dict(id='replayed', base=1), 'replay-delete-1')
        check('authority/delete-replay', gone['set_at'] == gone_again['set_at'] == record['set_at']
              and gone_again['set_by'] == record['set_by'] == 'owner' and record.get('deleted')
              and journal() == before and gone['set_at'] > first['set_at'],
              'first %r replay %r record %r' % (gone['set_at'], gone_again['set_at'], record['set_at']))
        check('authority/no-value', all('value' not in r and params['value'] not in json.dumps(r)
                                        for r in (first, again, gone, gone_again)))
    print('replay-set-at: %d of %d checks passed' % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
