#!/usr/bin/env python3
"""Explicit host qualification. Writes disposable branches on preexisting disposable GitHub repos.

Usage: python3 proof/VELDO-0153/host_check.py /absolute/path/to/host-config.json
Requires a working Secret Service and an SSH agent holding a different identity's key.
No login or repository creation. The operator provisions the disposable remotes first.
The candidate acceptance seam is controlled: this checks transport, never claims gate proof.
"""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location('host153_' + name, ROOT / '.veldo' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(config_path):
    config = json.loads(Path(config_path).read_text())
    entries = config['repositories']
    assert len(entries) >= 2, 'two identities and disposable remotes required'
    G, I, T, L, X = [load(n) for n in ('git_process', 'control_git_identity', 'control_git_identity_transport', 'lander', 'control_effect_executor')]
    assert len({e['identity']['id'] for e in entries}) == len(entries)
    assert {e['identity']['push_credential']['kind'] for e in entries} == {'token', 'ssh'}
    I.validate([e['identity'] for e in entries])
    # The planted agent must really hold another key, measured by public fingerprints.
    assert os.environ.get('SSH_AUTH_SOCK')
    agent = subprocess.run(['/usr/bin/ssh-add', '-l'], capture_output=True, text=True, timeout=10)
    assert agent.returncode == 0 and agent.stdout.strip(), 'planted agent has no accessible key'
    fingerprints = {line.split()[1] for line in agent.stdout.splitlines()}
    for entry in entries:
        if entry['identity']['push_credential']['kind'] == 'ssh':
            key_path = T.credential(entry['identity'])
            fingerprint = subprocess.run(['/usr/bin/ssh-keygen', '-lf', key_path], capture_output=True, text=True, timeout=10)
            assert fingerprint.returncode == 0 and fingerprint.stdout.split()[1] not in fingerprints
    results = {}
    with tempfile.TemporaryDirectory(prefix='veldo153-host-') as tmp:
        base = Path(tmp)
        marker, planted_global, planted_system = [base / name for name in ('helper-ran', 'global', 'system')]
        planted_global.write_text('[credential]\n\thelper = !touch ' + str(marker) + '\n')
        planted_system.write_text('[url "https://github.com/veldo-unrelated-owner/"]\n\tinsteadOf = https://github.com/\n')
        environment = dict(os.environ, GIT_CONFIG_GLOBAL=str(planted_global), GIT_CONFIG_SYSTEM=str(planted_system),
                           GIT_SSH_COMMAND='/bin/false', GIT_ASKPASS='/bin/false')
        with patch.dict(os.environ, environment, clear=True):
            for entry in entries:
                record, remote = entry['identity'], entry['remote']
                T.check_remote(record, remote)
                repo = base / record['id']; repo.mkdir()
                store = base / (record['id'] + '.db')
                conn = sqlite3.connect(store, isolation_level=None)
                I.configure_identities(conn, 'host153', [record], {record['id']: {'identity': record['id'], 'path': str(repo)}})
                def local(*args):
                    return G.run(['git', '-C', str(repo), *args], capture_output=True, text=True,
                                 check=True, identity=I.author(record)).stdout.strip()
                def transport(*args):
                    done = G.run(['git', '-C', str(repo), *args], capture_output=True, text=True, timeout=90,
                                 profile='identity', push_identity=record, remote_url=remote)
                    assert done.returncode == 0, 'identity transport failed (diagnostics withheld)'
                    return done.stdout.strip()
                local('init', '-q', '-b', 'main')
                local('commit', '--allow-empty', '-qm', 'VELDO-0153 host initial')
                local('config', 'remote.origin.url', remote)
                old = local('rev-parse', 'HEAD')
                prefix = 'refs/heads/veldo-0153-' + uuid.uuid4().hex
                refs = [prefix + '/' + leg for leg in ('direct', 'lander', 'executor')]
                # Empty expected tip makes each initial branch creation a CAS from absent.
                for ref in refs:
                    transport('push', '--force-with-lease=' + ref + ':', remote, old + ':' + ref)
                local('commit', '--allow-empty', '-qm', 'VELDO-0153 host candidate')
                tip, tree = local('rev-parse', 'HEAD'), local('rev-parse', 'HEAD^{tree}')
                transport('push', '--force-with-lease=' + refs[0] + ':' + old, remote, tip + ':' + refs[0])
                results['host/AC1/direct/' + record['id']] = transport('ls-remote', remote, refs[0]).split()[0] == tip
                ops = L.GitLandOps(repo, 'HEAD', trunk=refs[1][len('refs/heads/'):], domain='host153', repository=record['id'],
                                   identity_conn=conn, policy=lambda *args: {'ok': True})
                def candidate():
                    return dict(id='host-candidate', state='verified', workspace=str(repo), commit=tip, tree=tree, watermark=old, gate={})
                ops.candidate = candidate()
                with patch.object(L, 'verification_organ', lambda: SimpleNamespace(accept=lambda *args, **kwargs: [])):
                    result = ops.finalize({'id': 'host-unit'})
                    results['host/AC1/lander/' + record['id']] = result['ok'] and transport('ls-remote', remote, refs[1]).split()[0] == tip
                    for owner in entry['mismatched_owners']:
                        assert owner.casefold() != record['remote_owner'].casefold()
                        wrong = remote.replace('/' + record['remote_owner'] + '/', '/' + owner + '/').replace(':' + record['remote_owner'] + '/', ':' + owner + '/')
                        assert wrong != remote
                        local('config', 'remote.origin.url', wrong)
                        ops.candidate = candidate()
                        result = ops.finalize({'id': 'host-unit'})
                        results['host/AC2/lander/' + record['id'] + '/' + owner] = result.get('refusal') == 'binding_mismatch:remote_owner'
                        for operation in ('push', 'remote_creation', 'adoption'):
                            try:
                                T.check_remote(record, wrong, operation=operation)
                            except T.Refused as error:
                                results['host/AC2/' + operation + '/' + record['id'] + '/' + owner] = error.code == 'binding_mismatch:remote_owner'
                            else:
                                results['host/AC2/' + operation + '/' + record['id'] + '/' + owner] = False
                receiver = {'kind': 'publication', 'repository': str(repo), 'remote': remote, 'ref': refs[2]}
                contract = {'kind': 'publication', 'target': 'host', 'domain_uuid': 'host153', 'repository_uuid': record['id'],
                            'payload': {'old_tip': old, 'commit': tip, 'tree': tree}}
                result = X.receive({'store': str(store), 'receivers': {'host': receiver}}, contract,
                                   {'dispatch_id': 'host153', 'target': 'host', 'request_digest': 'host153'})
                results['host/AC1/executor/' + record['id']] = result['status'] == 'completed'
                conn.close()
                results['host/AC1/planted-helper/' + record['id']] = not marker.exists()
                assert len(entry['mismatched_owners']) >= 2
                # Kept for independent inspection. No branch deletion is performed by this check.
                print(json.dumps({'identity': record['id'], 'disposable_refs': refs, 'commit': tip}))
    print(json.dumps(results, sort_keys=True))
    assert all(results.values()), 'host assertion failed'


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Provide the absolute host-config.json path; no ambient credentials are inferred.')
    main(sys.argv[1])
