"""VELDO-0161 round 3, A: the enrollment signers factory setup writes, judged by suite 73's setup/lays-down
comparison, for a host where the suite cannot reach that row (setup refuses
unavailable_service:profile:user_manager before it writes anything).

The comparison below is a copy of the one in scripts/suites/73_veldo_0139_factory_setup.py (the round-3 row)
and of the one it replaced (the round-0 row); the full row, over a real setup, is the host's. Keys are real
ed25519 keys made here with setup's own _keygen; the texts are setup's own host_files, from the module as it is
and from each registered mutant (check_teeth_mutations materialize; the source is never edited).

    python3 proof/VELDO-0161/round3/probe_setup_signers.py <checkout> <output.json>
"""
import importlib.util, json, shutil, sys, tempfile
from pathlib import Path

root, out = Path(sys.argv[1]), Path(sys.argv[2])
spec = importlib.util.spec_from_file_location('teeth', root / 'scripts/check_teeth_mutations.py')
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)


def load(source, scratch, label):
    mods = Path(scratch) / label / '.veldo'
    shutil.copytree(root / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__', '*.jsonl'))
    shutil.copyfile(source, mods / 'control_factory_setup.py')
    spec = importlib.util.spec_from_file_location('v161r3_' + label, mods / 'control_factory_setup.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def new_row(signers, owner, owner_public, adoption_public, namespace):
    # Copy of suite 73's round-3 setup/lays-down signer comparison.
    return ([line.split() for line in signers.splitlines()]
            == [[owner, 'namespaces="%s"' % namespace] + owner_public.split(),
                ['adoption-signer', 'namespaces="%s"' % namespace] + adoption_public.split()]
            and bool(adoption_public) and adoption_public != owner_public)


def old_row(signers, owner, owner_public, namespace):
    # Copy of the round-0 comparison the host run failed at 7b60b7c0.
    return signers.split() == [owner, 'namespaces="%s"' % namespace] + owner_public.split()


with tempfile.TemporaryDirectory(prefix='v161r3-') as scratch:
    F = load(root / '.veldo/control_factory_setup.py', scratch, 'baseline')
    keys = Path(scratch) / 'keys'
    keys.mkdir(mode=0o700)
    owner, ns = 'owner', F.organ('control_eligibility').ENROLLMENT_NAMESPACE
    owner_public = F._keygen(keys / 'owner', 'v161r3-owner')
    settlement = F._keygen(keys / 'settlement', 'v161r3-settlement')
    adoption = F.adoption_signer(str(keys))
    plan = {'root': str(Path(scratch) / 'state'), 'owner': owner, 'owner_public': owner_public,
            'host_trust': str(Path(scratch) / 'host_trust.json'), 'host_identity': 'host-v161r3'}

    def signers(module, *args):
        texts = module.host_files(plan, *args)
        return next(text for path, text in texts.items() if path.endswith('/enrollment_signers'))
    results = {}
    as_is = signers(F, settlement, adoption)
    results['baseline: setup as it is'] = {
        'lines': len(as_is.splitlines()), 'round3_row': new_row(as_is, owner, owner_public, adoption, ns),
        'round0_row (the host failure)': old_row(as_is, owner, owner_public, ns)}
    # The text each line-544 mutant makes setup write: host_files called the way the mutant calls it.
    for name, args in (('setup161-adoption-signer-omitted', (settlement,)),
                       ('setup161-adoption-signer-wrong-key', (settlement, settlement))):
        text = signers(F, *args)
        results[name + ' (its host_files call)'] = {'lines': len(text.splitlines()),
                                                     'round3_row': new_row(text, owner, owner_public, adoption, ns)}
    # The host_files mutant, run as its own module.
    case = next(c for c in T.cases() if c['name'] == 'setup161-extra-enrollment-signer')
    m = T.materialize(case, 'mutant', scratch)
    text = signers(load(m['mutant'], scratch, 'extra'), settlement, adoption)
    results['setup161-extra-enrollment-signer (mutant module)'] = {
        'mutant_digest': m['new_digest'], 'lines': len(text.splitlines()),
        'round3_row': new_row(text, owner, owner_public, adoption, ns)}
out.write_text(json.dumps(results, indent=1, sort_keys=True) + '\n')
print(json.dumps(results, indent=1, sort_keys=True))
