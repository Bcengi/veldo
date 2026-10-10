#!/usr/bin/env python3
"""Real Mac synthetic worker and relay probe. No real login or provider invocation.

prepare <engine>: create a private synthetic candidate and a worker signing key.
run <engine> <client.json>: sign all commands on this Mac and run the 0124 engine.
The candidate admission intentionally skips only qualification, as 0124's native
rows do. This measures the profile; it neither creates nor asserts qualification.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'proof/VELDO-0124'))
spec = importlib.util.spec_from_file_location('native124', ROOT / 'proof/VELDO-0124/native_checks.py')
N = importlib.util.module_from_spec(spec)
spec.loader.exec_module(N)
# Load only Mac/client code on the Mac. The Linux fixture imports the store; this driver does not.
W = N.T.load('control_worker')
CL = N.T.load('control_worker_client')
WORK = ROOT / 'runs-0125'


def paths(engine):
    return WORK / engine


def prepare(engine):
    base = paths(engine)
    host, local, request, config = N.setup(base, 'natural', engine, runtime=5)
    config.write_text(json.dumps(dict(scratch=str(local['scratch']))))
    key = local['authority'] / 'worker-signing'
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                   check=True, capture_output=True)
    facts = host.os.facts()
    route = dict(host=facts['host'], principal='mac', platform='darwin', revision=1,
                 capabilities=['shell', 'macos', 'ios-build'], available=True,
                 engines={e: request['contract']['capability']['configuration_digest'] for e in N.P.ENGINES},
                 runtime_profile=N.P.digest(host.profile))
    route['qualification'] = dict(kind='native', profile_digest=N.P.digest({k: v for k, v in route.items()
                                               if k != 'available'}), reference='SYNTHETIC CANDIDATE PROBE ONLY')
    candidate = dict(engine=engine, profile=route, source=request['contract']['source'],
                     public_key=key.with_suffix('.pub').read_text().strip(), facts=facts)
    (base / 'candidate.json').write_text(json.dumps(candidate, indent=2) + '\n')
    local_config = dict(profile=host.profile, request=request, key=str(key))
    (base / 'local.json').write_text(json.dumps(local_config))
    (base / 'local.json').chmod(0o600)
    return dict(row='native/prepared/' + engine, status='candidate', candidate=str(base / 'candidate.json'))


class Candidate(N.M.Supervisor):
    def preflight(self, request):
        return dict(probe=True, profile_digest=N.P.digest(self.profile)), self.admit(request)


def run(engine, client_path):
    base = paths(engine)
    local = json.loads((base / 'local.json').read_text())
    config = json.loads(Path(client_path).read_text())
    host = Candidate(local['profile'], None)
    def sign(data):
        return subprocess.run(['ssh-keygen', '-Y', 'sign', '-n', 'veldo-command', '-f', local['key']],
                              input=data, check=True, capture_output=True, timeout=10).stdout.decode()
    client = CL.Client(config['workspace'], config['binding'], 'mac', sign, config['ssh_argv'])
    account = dict(id='account', provider=engine, status='active', profiles={host.os.facts()['host']:
                   local['request']['login_profile']})
    dispatch = config['dispatch_id']
    before = sorted(str(p.relative_to(base)) for p in base.rglob('*.sqlite*'))
    try:
        # The natural synthetic engine has no provider spend. This explicit zero
        # receipt is probe data, never a real engine accounting measurement.
        result = W.run(client, host, dispatch, local['request']['clone'], local['request']['scratch'], account,
                       collect=lambda run, observed: ({'tokens': 0, 'messages': 0},
                         {'output': observed['termination']['output_digest'], 'proof': 'synthetic-natural/' + engine}))
        assert result['record']['state'] == 'exited' and result['record']['observation']['termination']['returncode'] == 0
        assert result['record']['host'] == host.os.facts()['host'] and result['record']['dispatch_id'] == dispatch
        assert {x['command']['command']['operation'] for x in client.sent} == set(CL.OPERATIONS)
        failed = CL.Client(config['workspace'], config['binding'], 'mac', sign, config['unavailable_ssh_argv'])
        for operation in CL.OPERATIONS:
            try:
                failed.send(operation, {'dispatch_id': dispatch})
            except CL.Refused as error:
                assert error.code.startswith('AUTHORITY_UNAVAILABLE:')
            else:
                raise AssertionError('missing relay endpoint accepted')
        assert sorted(str(p.relative_to(base)) for p in base.rglob('*.sqlite*')) == before == []
        result.update(rows=['native/AC1/signed-families/' + engine, 'native/AC3/real-work/' + engine],
                      signed_requests=client.sent, facts=host.os.facts(), no_local_store=True,
                      watermark=client.watermark, status='observed')
        (base / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        # The wrong dispatch is signed here too. SSH authentication must not admit it.
        try:
            client.result(dict(result['binding'], dispatch_id='dispatch/another'), result['record']['observation'])
        except CL.Refused as error:
            assert error.code.startswith('binding_mismatch:')
        else:
            raise AssertionError('another dispatch accepted')
        return dict(rows=result['rows'], status='observed', output=str(base / 'result.json'))
    finally:
        N.cleanup(host, dispatch)


def main():
    if sys.platform != 'darwin':
        print(json.dumps(dict(status='not_run', reason='real Mac required')))
        return 2
    mode, engine = sys.argv[1:3]
    if engine not in N.P.ENGINES:
        raise ValueError('unsupported synthetic engine')
    print(json.dumps(prepare(engine) if mode == 'prepare' else run(engine, sys.argv[3])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
