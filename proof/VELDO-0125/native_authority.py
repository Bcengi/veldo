#!/usr/bin/env python3
"""Owner-run disposable Linux authority for the real Mac probe; no deployed state.

setup <candidate.json> <new-directory> <Linux-SSH-alias>
serve <directory>
compare <directory> <Mac-result.json>
The SSH alias must authenticate from the Mac to this Linux account. The relay
command is fixed to this checkout and this disposable authority's existing socket.
"""
import json
import sqlite3
import sys
from pathlib import Path
import checks as T


def setup(candidate, directory, alias, fixed_socket, transport_key):
    data = json.loads(Path(candidate).read_text())
    directory = Path(directory).resolve()
    if directory.exists():
        raise ValueError('use a new disposable directory')
    f = T.Fixture(directory, remote=data)
    try:
        if not Path(fixed_socket).is_absolute():
            raise ValueError('the forced relay socket must be absolute')
        f.config['socket'] = fixed_socket
        dispatch = 'dispatch/native/' + data['engine']
        prepared = f.prepare(dispatch, ['macos', 'ios-build'], source=data['source'], engine=data['engine'], deadline_seconds=600)
        assert prepared['state'] == 'prepared'
        f.res.configure('other-policy', 'unit', 'other', dict(capacity=2, invocations=2, wall_seconds=1800), now=__import__('time').time())
        other = dispatch + '/other'
        f.prepare(other, ['ios-build'], source=data['source'], engine=data['engine'], deadline_seconds=600, unit='other')
        # Transfer has a ten minute accepted deadline; execution has a five second cap.
        contract = prepared['contract']
        config_path = directory / 'config.json'
        config_path.write_text(json.dumps(f.config, indent=2))
        config_path.chmod(0o600)
        client = dict(workspace=str(f.repo), binding=f.binding, dispatch_id=dispatch,
            other_dispatch_id=other, dispatch_binding=dict(dispatch_id=dispatch, unit=contract['unit'],
                host=contract['input']['context']['host_route']['host'], contract_digest=T.D.digest(contract)),
            ssh_argv=['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-i', transport_key, alias])
        (directory / 'client.json').write_text(json.dumps(client, indent=2))
        return dict(config=str(config_path), client=str(directory / 'client.json'), dispatch=contract['dispatch_id'])
    finally:
        f.close()


def compare(directory, result_path):
    directory = Path(directory)
    result = json.loads(Path(result_path).read_text())
    with sqlite3.connect(directory / 'authority.sqlite3') as conn:
        record = json.loads(conn.execute('SELECT data FROM entities WHERE id=?',
                                        ('worker:' + result['binding']['dispatch_id'],)).fetchone()[0])
        assert record == result['record']
        for request in result['signed_requests']:
            cmd = request['command']['command']
            journal = conn.execute('SELECT command_digest FROM journal WHERE command_id=?', (cmd['command_id'],)).fetchone()
            assert journal, 'signed remote command has no committed record'
            audit = next(c for c in record['commands'] if c['command_id'] == cmd['command_id'])
            assert audit['digest'] == T.S.digest_of(cmd) and audit['operation'] == cmd['operation']
            public = json.loads(conn.execute("SELECT data FROM entities WHERE id='key:mac'").fetchone()[0])['public_key']
            assert T.W.SV.AC.ssh_keygen_verify(T.S.canonical_bytes(cmd), request['command']['signature'],
                T.W.SV.AC.allowed_signers_line('mac', public, T.CL.COMMAND_NAMESPACE), 'mac', T.CL.COMMAND_NAMESPACE)[0]
            assert request['workspace'] == record['workspace']
            assert all(request[k] == record[k] for k in ('domain_uuid', 'repository_uuid', 'store_uuid'))
        assert len(result['rejected_requests']) == 1
        for request in result['rejected_requests']:
            cmd = request['command']['command']
            assert not conn.execute('SELECT 1 FROM journal WHERE command_id=?', (cmd['command_id'],)).fetchone()
            other = json.loads(conn.execute('SELECT data FROM entities WHERE id=?',
                ('dispatch:' + cmd['parameters']['dispatch_id'],)).fetchone()[0])
            assert other['state'] == 'running'
        assert record['state'] == 'exited' and record['charge'] == 'reported'
        spend = json.loads(conn.execute('SELECT data FROM entities WHERE id=?',
            ('worker-spend:' + record['dispatch_id'],)).fetchone()[0])
        assert all(spend[k] == record[k] for k in ('unit', 'host', 'dispatch_id', 'invocation', 'usage'))
        assert spend['receipt']['seq'] > 0
        invocation = json.loads(conn.execute('SELECT data FROM entities WHERE id=?',
            (T.RES.entity('invocation', ['domain', record['invocation']]),)).fetchone()[0])
        assert invocation['dispatch'] == record['dispatch_id'] and invocation['context']['unit'] == record['unit']
        assert invocation['observed']['tokens'] == record['usage']['tokens'] == 0
    return dict(rows=result['rows'], status='observed', binding=result['binding'], machine=record['host'],
                usage=record['usage'], terminal=record['observation'], references=record['references'])


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'serve':
        T.W.serve(str(Path(sys.argv[2]) / 'config.json'))
    else:
        print(json.dumps(setup(*sys.argv[2:]) if action == 'setup' else compare(*sys.argv[2:]), indent=2))
