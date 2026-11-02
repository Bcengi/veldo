"""Ticket-only bug-fix journey, consuming AC1's signed admission in the same store.

Builder and reviewer are separate Python processes with distinct principals and
keys. Dispatch exit records contain their actual PIDs, exit codes and outputs;
this fixture does not qualify the Runner or any live model. The real proof,
floor, candidate observation, effect executor and landing services judge them.
Only scratch Git repositories are published. No repository gate is executed.
"""
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys


def check(ROOT, f, admitted, observed):
    iid, uid = admitted
    work, base, mods = f.work, f.base, f.mods
    load, put = f.load, f.fixture
    GP = load('v80_git', mods / 'git_process.py')
    DSP = load('v80_dispatch', mods / 'dispatch.py')
    CP = load('v80_proof', mods / 'control_proof.py')
    CV = load('v80_verification', mods / 'control_verification.py')
    LG = load('v80_landing', mods / 'control_landing.py')
    D = load('v80_dispatch_record', mods / 'control_dispatch.py')
    identity = ('Defect fixture', 'defect@example.invalid')

    def need(condition, detail):
        if not condition:
            raise AssertionError(detail)

    def git(repo, *args):
        result = GP.run(['git', '-C', str(repo), *args], capture_output=True, text=True, identity=identity)
        need(result.returncode == 0, result.stderr)
        return result.stdout.strip()

    def sha(body):
        return 'sha256:' + hashlib.sha256(body).hexdigest()

    def refused(call, reason):
        try:
            result = call()
        except Exception as error:
            need(getattr(error, 'code', None) == reason, repr(error))
            return reason
        raise AssertionError('Expected %s, got %r' % (reason, result))

    need(f.executable(uid) == [], 'only admitted and prioritized work enters the build')
    # Withhold each authority separately at the real claim entry, then restore
    # the original signed records for the positive journey.
    import copy
    original_item, original_unit = copy.deepcopy(f.item(iid)), copy.deepcopy(f.data_of(uid))
    original_item.pop('version', None)
    claims = f.claims.Receiver(f.conn, f.ids, 'authority', f.journal_sign)
    missing = {}
    for field, state in (('admission', 'AWAITING_GROOMING'), ('priority', 'ADMITTED')):
        put(iid, 'backlog_item', dict(original_item, state=state, **{field: None}))
        put(uid, 'execution_unit', dict(original_unit, state='PLANNED'))
        command = dict(f.ids, operation='claim', unit_id=uid, principal='w-build', command_id=f.next_id('no-' + field),
                       nonce=f.next_id('no-nonce'), generation=0, capabilities=[])
        result = claims.apply(f.signed('w-build', command))
        missing[field] = result
        need(not result.get('ok') and result.get('reason') == 'not_admitted', 'missing ' + field + ': ' + str(result))
    put(iid, 'backlog_item', original_item)
    put(uid, 'execution_unit', original_unit)
    observed['withheld_authority'] = missing

    GP.run(['git', 'init', '-q', '-b', 'main', str(work)], check=True, capture_output=True)
    (work / 'scripts').mkdir()
    (work / '.veldo').mkdir()
    # Stored catalog only. The owner forbids running scripts/verify.sh.
    catalog = 'CHECK_unit="required:python3 -B check.py"\nORDER="unit"\n'
    verifier = '#!/bin/bash\n' + CV.INTERFACE + '\n' + catalog + '''
set -eu
cd "$2"
echo '== unit'
python3 -B check.py
commit=$(git rev-parse HEAD)
python3 - "$4" "$commit" <<'STAMP'
import json, pathlib, sys
sink, commit = pathlib.Path(sys.argv[1]), sys.argv[2]
(sink / 'last_verify').write_text(json.dumps({'commit': commit, 'status': 'green', 'force_fresh': True, 'reused': {'unit': 0, 'mutation': 0}}))
(sink / 'events.jsonl').write_text(json.dumps({'commit': commit, 'type': 'gate.passed', 'producer': 'verify.sh', 'force_fresh': True, 'reused': {'unit': 0, 'mutation': 0}}) + '\\n')
STAMP
echo '   unit: pass'
echo "GATE: GREEN ($commit)"
'''
    (work / 'scripts/verify.sh').write_text(verifier)
    (work / 'checkout.py').write_text('def total(price, quantity):\n    return price + quantity\n')
    (work / 'check.py').write_text('from checkout import total\nassert total(7, 3) == 21\nassert total(7, 0) == 0\n')
    (work / '.gitignore').write_text('__pycache__/\n')
    git(work, 'add', '-A')
    git(work, 'commit', '-q', '-m', 'Accepted checkout behavior and failing reproduction')
    baseline = git(work, 'rev-parse', 'HEAD')
    red = subprocess.run([sys.executable, '-B', 'check.py'], cwd=work, capture_output=True, text=True)
    need(red.returncode != 0 and 'AssertionError' in red.stderr, 'actual defect must reproduce')
    remote = base / 'defect-remote.git'
    GP.run(['git', 'clone', '-q', '--bare', str(work), str(remote)], check=True, capture_output=True)
    git(work, 'checkout', '-q', '-b', 'bug-fix')
    builder = subprocess.Popen([sys.executable, '-c',
        "from pathlib import Path; Path('checkout.py').write_text('def total(price, quantity):\\n    return price * quantity\\n')"],
        cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    build_out, build_err = builder.communicate()
    need(builder.returncode == 0, build_err)
    git(work, 'add', 'checkout.py')
    git(work, 'commit', '-q', '-m', 'Fix checkout multiplication')
    implementation = git(work, 'rev-parse', 'HEAD')
    spec_path = 'specs/%s-grooming-fixture.md' % uid
    manifest = {'schema': 'veldo.proof/v1', 'spec_id': uid, 'producer': 'w-build', 'commit': implementation,
                'spec_revision': sha((work / spec_path).read_bytes()),
                'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [
                    {'type': 'unit', 'path': 'check.py', 'digest': sha((work / 'check.py').read_bytes())}]}],
                'checks': [{'name': 'unit', 'status': 'passed'}], 'rollback': 'git revert'}
    proof = work / 'proof' / uid / 'manifest.json'
    proof.parent.mkdir(parents=True)
    proof.write_text(json.dumps(manifest, sort_keys=True) + '\n')
    git(work, 'add', 'proof/' + uid)
    git(work, 'commit', '-q', '-m', 'Proof of restored checkout behavior')
    evidence = git(work, 'rev-parse', 'HEAD')
    installed = base / 'ticket-verifier'
    (installed / 'scripts').mkdir(parents=True)
    (installed / 'scripts/defect-check.sh').write_text(verifier)
    # Only the verifier path varies. All observation and acceptance logic is real.
    CV.GATE_PATH = 'scripts/defect-check.sh'
    observation, reference = CV.observe_gate(work, {'root': str(installed), 'source': 'VELDO-0080 ticket verifier'},
                                             base / 'build-observation', bind_refs=True)
    need(observation['green'], str(observation['refusals']) + observation['stderr'])
    runpy.run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))['bind'](
        mods, f.conn, f.DOMAIN, f.REPO, work, identity)
    authority = CP.ProofService(f.S, f.conn, domain=f.DOMAIN, repository=f.REPO, repo=str(work),
                             principal='pm', signer='authority', sign=f.journal_sign)
    reference_store = authority.record_observation(observation, uid)
    bundle = authority.accept(uid, commit=evidence, base=baseline, spec_path=spec_path,
                              manifest=manifest, observation=reference_store, builder='w-build')
    claims = f.claims.Receiver(f.conn, f.ids, 'authority', f.journal_sign)
    command = dict(f.ids, operation='claim', unit_id=uid, principal='w-build', command_id=f.next_id('claim'),
                   nonce=f.next_id('claim-nonce'), generation=0, capabilities=[])
    claimed = claims.apply(f.signed('w-build', command))
    need(claimed.get('ok'), 'claim: ' + str(claimed))
    generation = claimed['claim']['generation']
    put('authority:' + f.DOMAIN, 'authority', {'state': 'active', 'generation': 1})
    # Staffing metadata is a fixture input; admission and priority came from AC1.
    put(uid, 'execution_unit', dict(f.data_of(uid), risk='standard'))
    put(DSP.review_policy_id(f.REPO), 'review_policy', {'tiers': {'standard': 1}})
    dispatch = 'defect-build'
    put(D.record_id(dispatch), 'dispatch', {'dispatch_id': dispatch, 'state': 'exited',
        'contract': {'domain': f.DOMAIN, 'repository': f.REPO, 'unit': uid, 'station': 'build', 'attempt': 1,
                     'claim': {'holder': 'w-build', 'generation': generation}},
        'process': {'pid': builder.pid}, 'termination': {'returncode': builder.returncode,
            'signal': None, 'deadline_stop': False, 'output_digest': sha(build_out)}})
    floor = DSP.FloorAuthority(f.S, f.conn, domain=f.DOMAIN, repository=f.REPO, repo=str(work),
                              projections=str(base / 'floor'), principal='pm', signer='authority', sign=f.journal_sign)
    try:
        refused(lambda: floor.accept_build(uid, commit=evidence, gate={'green': False}, holder='w-build',
                                            generation=generation), 'missing_evidence:gate')
        floor.accept_build(uid, commit=evidence, gate=observation, holder='w-build', generation=generation)
        no_review = refused(lambda: floor.handoff(uid), 'awaiting_reviews:0/1')
        refused(lambda: floor.assign_review(uid, 'w-build'), 'reviewer_not_independent')
        assignment = floor.assign_review(uid, 'w-rev')
        # A fresh process receives only the assigned source/proof context, reads the
        # committed artifacts and signs its own verdict with its distinct key.
        reviewer_code = '''import hashlib, json, os, subprocess, sys
from pathlib import Path
payload = json.loads(sys.stdin.read())
source = subprocess.run(['git', 'show', payload['source']['commit'] + ':checkout.py'], check=True, capture_output=True).stdout
namespace = {}
exec(source, namespace)
assert namespace['total'](7, 3) == 21 and namespace['total'](7, 0) == 0
proof = subprocess.run(['git', 'show', payload['source']['commit'] + ':proof/' + payload['unit'] + '/manifest.json'], check=True, capture_output=True).stdout
assert 'sha256:' + hashlib.sha256(proof).hexdigest() == payload['proof']['digest']
body = dict(schema='veldo.review_receipt/v1', assignment=payload['assignment'], unit=payload['unit'], reviewer=payload['reviewer'], source=payload['source']['commit'], proof=payload['proof']['digest'], verdict='pass', findings=[])
signature = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', sys.argv[1], '-n', 'veldo-review'], input=json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode(), check=True, capture_output=True).stdout.decode()
print(json.dumps({'body': body, 'signature': signature}))
'''
        reviewer = subprocess.Popen([sys.executable, '-B', '-c', reviewer_code, str(f.keyfile['w-rev'])], cwd=work,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        review_out, review_err = reviewer.communicate(json.dumps(assignment).encode())
        need(reviewer.returncode == 0, review_err)
        review_dispatch = 'defect-review'
        put(D.record_id(review_dispatch), 'dispatch', {'dispatch_id': review_dispatch, 'state': 'exited',
            'contract': {'domain': f.DOMAIN, 'repository': f.REPO, 'unit': uid, 'station': 'review', 'attempt': 1,
                         'source': {'commit': evidence}, 'input': {'payload': assignment, 'context': {'reviewer': 'w-rev'}}},
            'process': {'pid': reviewer.pid}, 'termination': {'returncode': reviewer.returncode,
                'signal': None, 'deadline_stop': False, 'output_digest': sha(review_out)}})
        floor.record_review(uid, assignment['assignment'], {'dispatch': review_dispatch, 'output': review_out.decode()})
        floor.handoff(uid)
        need(floor.record(uid)['handoff']['reviewers'] == ['w-rev'], 'independent reviewer')
        # The candidate is a disposable clone at this evidence commit. Main has not
        # advanced in this fixture, so its exact-tree candidate needs no merge.
        candidate = base / 'defect-candidate'
        GP.run(['git', 'clone', '-q', str(work), str(candidate)], check=True, capture_output=True)
        candidate_observation, candidate_reference = CV.observe_gate(candidate,
            {'root': str(installed), 'source': 'VELDO-0080 ticket verifier'}, base / 'candidate-observation', bind_refs=True)
        need(candidate_observation['green'], 'candidate gate')
        need(CV.accept(candidate_reference, candidate, evidence, bind_refs=True) == [], 'exact candidate observation')
        wire = runpy.run_path(str(ROOT / 'scripts/suites/support/identity_wire.py'))['Wire'](base / 'wire')
        url = wire.remote('defects', remote)
        git(candidate, 'remote', 'set-url', 'origin', url)
        runpy.run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))['bind'](
            mods, f.conn, f.DOMAIN, f.REPO, work, identity)
        effects = base / 'defect-effects.json'
        effects.write_text(json.dumps({'store': str(f.db), 'journal_key': str(f.keyfile['authority']),
            'domain_uuid': f.DOMAIN, 'repository_uuid': f.REPO,
            'receivers': {'git-defect': {'kind': 'publication', 'repository': str(candidate), 'remote': url, 'ref': 'refs/heads/main'}}}))
        events = base / 'events'
        (events / '.veldo').mkdir(parents=True)
        landing = LG.Landing(f.S, f.conn, domain=f.DOMAIN, repository=f.REPO, effects=effects, target='git-defect',
            principal='pm', connection_key=f.keyfile['pm'], floor=floor, events_root=events,
            signer='authority', sign=f.journal_sign)
        record = {'id': 'defect-candidate', 'unit': uid, 'commit': evidence, 'tree': git(candidate, 'rev-parse', 'HEAD^{tree}'),
                  'watermark': baseline, 'evidence': evidence, 'implementation': implementation,
                  'proof': {'digest': sha(proof.read_bytes())}, 'workspace': str(candidate), 'remote_url': url,
                  'gate': {'observation': candidate_reference}}
        unit = {'spec': uid, 'dispatch': 'defect-land'}
        with wire.active():
            result = landing.publish(unit, record)
        need(result.get('ok'), 'landing: ' + str(result))
        receipt = f.data_of(result['receipt'])
        chain = receipt['publication_receipt']
        need(git(remote, 'rev-parse', 'refs/heads/main') == evidence, 'remote confirmation')
        need(chain['tested_tree'] == git(remote, 'rev-parse', 'refs/heads/main^{tree}')
             and chain['implementation_commit'] == implementation and chain['proof_digest'] == sha(proof.read_bytes())
             and chain['reviewed_source'] == evidence and chain['reviewers'] == ['w-rev']
             and chain['old_remote_tip'] == baseline and chain['unit_id'] == uid, 'completion evidence chain')
        need(f.bop('pm', 'complete', iid).get('ok') and f.item(iid)['state'] == 'DONE', 'ordinary backlog completion')
        observed['completion'] = {'red_reproduction_exit': red.returncode, 'build_pid': builder.pid,
                                  'review_pid': reviewer.pid, 'missing_review_refusal': no_review,
                                  'proof_bundle': bundle, 'floor': floor.record(uid), 'receipt': receipt,
                                  'candidate_observation': candidate_observation, 'result': result}
    finally:
        floor.close()
