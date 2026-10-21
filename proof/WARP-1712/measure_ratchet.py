#!/usr/bin/env python3
"""Read core only; evaluate hypothetical push ranges on a temporary corpus mirror."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
CORE = Path('/home/dmitry/projects/core')
loader = importlib.util.spec_from_file_location('ratchet_validator', ROOT / '.veldo/validate.py')
validator = importlib.util.module_from_spec(loader)
loader.loader.exec_module(validator)
debt = validator.evidence_debt_module()
prior = json.loads(Path(__file__).with_name('core-blast-radius.json').read_text())


def snapshot():
    paths = list((CORE / 'specs').glob('*.md'))
    paths += list(validator._CORPUS.corpus_in_dir(CORE / 'proof', validator._CORPUS.MANIFEST_PATTERN))
    paths += list(validator._CORPUS.corpus_in_dir(CORE / 'proof', validator._CORPUS.DESIGN_VERDICT_PATTERN))
    return {str(path.relative_to(CORE)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(set(paths))}


before = snapshot()
assert all(before[path] == digest for path, digest in prior['input_sha256'].items())
current_manifests = {str(p.relative_to(CORE)) for p in validator._CORPUS.corpus_in_dir(
    CORE / 'proof', validator._CORPUS.MANIFEST_PATTERN)}
assert current_manifests == {row['proof'] for row in prior['pairs']}
valid, parser_errors = [], []
for row in prior['pairs']:
    try:
        validator.front_matter((CORE / row['spec']).read_text())
    except ValueError as exc:
        assert row['new'] == 'parse_error'
        parser_errors.append({'spec': row['spec'], 'proof': row['proof'], 'error': str(exc)})
    else:
        valid.append(row)

with tempfile.TemporaryDirectory(prefix='warp1712-core-ratchet-') as directory:
    mirror = Path(directory)
    for relative in before:
        target = mirror / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((CORE / relative).read_bytes())
    matched = [(mirror / row['spec'], mirror / row['proof']) for row in valid]
    rows = debt.compute(validator, mirror, matched)
    assert len(rows) == 107
    assert {row['proof'] for row in rows} == {row['proof'] for row in prior['pairs']
                                            if row['old'] == 'pass' and row['new'] == 'fail'}
    register = debt.render(rows)
    (mirror / debt.REGISTER).parent.mkdir(parents=True, exist_ok=True)
    (mirror / debt.REGISTER).write_text(register)
    with contextlib.redirect_stdout(io.StringIO()):
        untouched = debt.check(validator, mirror, rows, {'README.md'}, register)
    assert untouched == 0
    refusals = []
    for row in rows:
        for touched in (row['spec'], row['proof']):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                errors = debt.check(validator, mirror, rows, {touched}, register)
            assert errors == 1
            refusals.append({'touched': touched, 'errors': errors, 'diagnostic': output.getvalue().strip()})
    # The register is an artifact of this measurement, never written into core.
    Path(__file__).with_name('round3-core-debt.jsonl').write_text(register)
assert before == snapshot(), 'core input changed during measurement'
report = {'root': str(CORE), 'method': 'Read-only input digests and declared corpus reconciliation; actual strict predicate and ratchet check on a byte-identical temporary corpus mirror. Hypothetical changed-path sets, not a core gate invocation.',
          'implementation_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                                    for p in ('.veldo/validate.py', '.veldo/evidence_debt.py')},
          'inputs_unchanged': True, 'input_sha256': before,
          'matched_pairs': len(prior['pairs']), 'strict_pass': len(valid) - len(rows),
          'historical_debt': len(rows), 'unchanged_ratchet_errors': untouched,
          'single_pair_touch_refusals': len(refusals), 'parser_errors': parser_errors,
          'refusals': refusals,
          'limitations': 'Five existing pair parser errors remain errors, excluded from ratchet scenarios and reported separately. No whole-core gate pass is claimed.'}
Path(__file__).with_name('round3-core-ratchet.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ('matched_pairs', 'strict_pass', 'historical_debt',
                                      'unchanged_ratchet_errors', 'single_pair_touch_refusals', 'inputs_unchanged')}, indent=2))
