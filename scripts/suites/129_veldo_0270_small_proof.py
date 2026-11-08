"""VELDO-0270: proof is small summaries, never raw bulk.

AC1: the contract check and the push guard refuse a proof file over proof.max_file_bytes and a
base64 encoded archive; the guard judges every commit a push to a protected ref sends.
AC2: the proof writers write summaries; an incomplete summary is refused.
AC3: the files over the limit left the tree, each summary's sha256 matches the removed bytes.
AC4: the rule paragraph is stated where builders and reviewers read.
Each AC1 and AC2 row runs on a scratch repository this suite builds; nothing in ROOT is written.
"""
import base64 as _p270_b64
import gzip as _p270_gzip
import hashlib as _p270_hl
import importlib.util as _p270_ilu
import io as _p270_io
import json as _p270_json
import os as _p270_os
import shutil as _p270_shutil
import subprocess as _p270_sp
import sys as _p270_sys
import tempfile as _p270_tmp
from pathlib import Path as _p270_Path


def _p270_load(name, path):
    spec = _p270_ilu.spec_from_file_location(name, str(path))
    mod = _p270_ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_p270_git = _p270_load('p270_git', ROOT / '.veldo/git_process.py')
_P270_ID = ('VELDO test', 'veldo-test@example.invalid')
_P270_LIMIT = 1048576


def _p270_run(repo, *args):
    return _p270_git.run(['git', '-C', str(repo), *args], check=True, capture_output=True,
                         identity=_P270_ID).stdout.decode().strip()


# The proof size rules under test (.veldo/proof_size.py, which validate.py loads from beside itself),
# spelled as the mutation observer's production-copy anchor so a teeth run substitutes its mutant
# here. The rows run the modules from a temporary .veldo tree: a copy of this tree's .veldo (every
# sibling module validate.py and proof_size.py load, policy.yaml and the data beside them) with the
# file at that path laid over proof_size.py, so a mutant the driver supplies is the module the rows
# load. The validate.py in that tree is the one every row drives, and that tree is the .veldo every
# scratch repository gets.
_P270_PROOF_SIZE = ROOT / ".veldo" / "proof_size.py"
_P270_IGNORE = _p270_shutil.ignore_patterns('__pycache__', 'events.jsonl', 'last_verify')
_p270_modules = _p270_tmp.TemporaryDirectory(prefix='veldo-0270-modules-')
_p270_shutil.copytree(ROOT / '.veldo', _p270_Path(_p270_modules.name) / '.veldo', ignore=_P270_IGNORE)
_p270_shutil.copyfile(_P270_PROOF_SIZE, _p270_Path(_p270_modules.name) / '.veldo' / 'proof_size.py')
_P270_VALIDATE = _p270_Path(_p270_modules.name) / '.veldo' / 'validate.py'


def _p270_scratch(base, name, policy_proof=None):
    """A scratch repository with this tree's .veldo (the one holding the validate.py under test)
    and guard, a policy holding policy_proof (a list of YAML lines under proof:, or None for no
    proof key), and one root commit."""
    repo = base / name
    _p270_shutil.copytree(_P270_VALIDATE.parent, repo / '.veldo', ignore=_P270_IGNORE)
    (repo / 'scripts').mkdir()
    _p270_shutil.copy(ROOT / 'scripts/veldo-guard.sh', repo / 'scripts/veldo-guard.sh')
    (repo / 'hooks').mkdir()
    _p270_shutil.copy(ROOT / 'packs/claude/hooks/pre-push', repo / 'hooks/pre-push')
    text = (ROOT / '.veldo/policy.yaml').read_text()
    start = text.index('\nproof:\n')
    end = text.index('\nmerge_rule:', start)
    block = '' if policy_proof is None else '\nproof:\n' + ''.join('  ' + l + '\n' for l in policy_proof).rstrip('\n')
    (repo / '.veldo/policy.yaml').write_text(text[:start] + block + text[end:])
    (repo / 'proof').mkdir()
    (repo / 'proof/README.md').write_text('scratch\n')
    _p270_git.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True, capture_output=True)
    _p270_run(repo, 'add', '-A')
    _p270_run(repo, 'commit', '-qm', 'root')
    return repo


def _p270_check(V, repo):
    """(errors, printed) of the contract check over repo's proof/."""
    buf = _p270_io.StringIO()
    old_out, old_err = _p270_sys.stdout, _p270_sys.stderr
    _p270_sys.stdout = _p270_sys.stderr = buf
    try:
        errs = V.check_proof_files(repo, quiet=True)
    finally:
        _p270_sys.stdout, _p270_sys.stderr = old_out, old_err
    return errs, buf.getvalue()


def _p270_commit_file(repo, rel, data, msg):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    _p270_run(repo, 'add', '-A')
    _p270_run(repo, 'commit', '-qm', msg)
    return _p270_run(repo, 'rev-parse', 'HEAD')


def _p270_ascii_b64(n):
    raw = ('plain ascii text, nothing compressed here. ' * 200).encode()
    return (_p270_b64.encodebytes(raw).decode()[:n]).encode()


def _p270_gzip_b64(n):
    raw = _p270_gzip.compress(_p270_os.urandom(4096))
    return (_p270_b64.encodebytes(raw).decode()[:n]).encode()


_p270_V = _p270_load('p270_validate', _P270_VALIDATE)
with _p270_tmp.TemporaryDirectory(prefix='veldo-0270-') as _p270_d:
    _p270_base = _p270_Path(_p270_d)

    # ---- AC1 (a): the contract check, default limit (no proof key in the policy).
    _p270_r = _p270_scratch(_p270_base, 'default', None)
    _p270_Vd = _p270_load('p270_validate_default', _p270_r / '.veldo/validate.py')
    (_p270_r / 'proof/X/big.bin').parent.mkdir(parents=True)
    (_p270_r / 'proof/X/big.bin').write_bytes(b'x\n' * (_P270_LIMIT // 2) + b'y')
    _p270_run(_p270_r, 'add', '-A')
    _p270_e, _p270_out = _p270_check(_p270_Vd, _p270_r)
    expect('p270/contract/over-limit-refused-naming-file-and-source',
           _p270_e == 1 and 'proof_file_over_limit' in _p270_out and 'proof/X/big.bin' in _p270_out
           and str(_P270_LIMIT + 1) in _p270_out and 'proof.max_file_bytes is absent' in _p270_out)
    (_p270_r / 'proof/X/big.bin').write_bytes(b'x\n' * (_P270_LIMIT // 2))
    _p270_e, _p270_out = _p270_check(_p270_Vd, _p270_r)
    expect('p270/contract/exactly-the-limit-passes', _p270_e == 0)

    # ---- AC1 (a): base64 archives at any size; base64 of plain ASCII passes.
    (_p270_r / 'proof/X/big.bin').unlink()
    (_p270_r / 'proof/X/archive.txt').write_bytes(b'{"blob": "' + _p270_gzip_b64(2048) + b'"}\n')
    _p270_run(_p270_r, 'add', '-A')
    _p270_e, _p270_out = _p270_check(_p270_Vd, _p270_r)
    expect('p270/contract/base64-gzip-refused',
           _p270_e >= 1 and 'proof_encoded_archive' in _p270_out and 'proof/X/archive.txt' in _p270_out
           and 'gzip' in _p270_out)
    (_p270_r / 'proof/X/archive.txt').write_bytes(_p270_ascii_b64(2048))
    _p270_e, _p270_out = _p270_check(_p270_Vd, _p270_r)
    expect('p270/contract/base64-ascii-passes', _p270_e == 0)

    # ---- AC1: the limit is read from policy; an invalid key is a refusal, never the default.
    _p270_r2 = _p270_scratch(_p270_base, 'small', ['max_file_bytes: 2048'])
    _p270_V2 = _p270_load('p270_validate_small', _p270_r2 / '.veldo/validate.py')
    (_p270_r2 / 'proof/three.txt').write_bytes(b'z\n' * 1536)
    _p270_run(_p270_r2, 'add', '-A')
    _p270_e, _p270_out = _p270_check(_p270_V2, _p270_r2)
    expect('p270/contract/policy-limit-is-read',
           _p270_e == 1 and 'proof_file_over_limit' in _p270_out and 'limit 2048 bytes' in _p270_out
           and '.veldo/policy.yaml key proof.max_file_bytes' in _p270_out)
    (_p270_r2 / '.veldo/policy.yaml').write_text((_p270_r2 / '.veldo/policy.yaml').read_text()
                                                 .replace('max_file_bytes: 2048', 'max_file_bytes: "big"'))
    _p270_e, _p270_out = _p270_check(_p270_V2, _p270_r2)
    expect('p270/contract/policy-invalid-key-refused', _p270_e >= 1 and 'proof_policy_invalid' in _p270_out)

    # ---- AC1 (b): the push guard judges every commit a push sends, not only the tip.
    _p270_r3 = _p270_scratch(_p270_base, 'push', None)
    _p270_root = _p270_run(_p270_r3, 'rev-parse', 'HEAD')
    _p270_first = _p270_commit_file(_p270_r3, 'proof/Y/raw.log', b'x\n' * (1024 * 1024), 'add 2 MB')
    (_p270_r3 / 'proof/Y/raw.log').unlink()
    _p270_run(_p270_r3, 'add', '-A')
    _p270_run(_p270_r3, 'commit', '-qm', 'delete it')
    _p270_tip = _p270_run(_p270_r3, 'rev-parse', 'HEAD')
    _p270_zero = '0' * 40
    _p270_env = {k: v for k, v in _p270_os.environ.items() if k not in ('CLAUDE_PROJECT_DIR', 'VELDO_EMERGENCY')}

    def _p270_hook(remote_ref):
        line = 'refs/heads/work %s %s %s\n' % (_p270_tip, remote_ref, _p270_zero)
        return _p270_sp.run(['bash', str(_p270_r3 / 'hooks/pre-push'), 'origin', '/nonexistent.git'],
                            cwd=str(_p270_r3), input=line, capture_output=True, text=True, env=_p270_env,
                            timeout=300)

    def _p270_pushproof(remote_ref):
        line = 'refs/heads/work %s %s %s\n' % (_p270_tip, remote_ref, _p270_zero)
        return _p270_sp.run([_p270_sys.executable, str(_p270_r3 / '.veldo/validate.py'), 'push-proof', 'origin'],
                            cwd=str(_p270_r3), input=line, capture_output=True, text=True, timeout=300)

    _p270_h = _p270_hook('refs/heads/main')
    expect('p270/guard/push-to-main-refused-naming-first-commit',
           _p270_h.returncode == 2 and 'proof_file_over_limit' in _p270_h.stderr
           and _p270_first in _p270_h.stderr and 'refs/heads/main' in _p270_h.stderr)
    _p270_p = _p270_pushproof('refs/heads/feature')
    expect('p270/guard/push-to-unprotected-branch-passes',
           _p270_p.returncode == 0 and 'proof_file_over_limit' not in _p270_p.stdout + _p270_p.stderr)
    _p270_h2 = _p270_hook('refs/heads/feature')
    expect('p270/guard/hook-on-unprotected-branch-not-refused-for-proof',
           'proof_file_over_limit' not in _p270_h2.stderr)

    # Landing round 1: this repository's own proof policy size checks every ref 0268's protected_refs
    # protects; a push to refs/heads/release sending the 2 MB commit is refused.
    _p270_own = (ROOT / '.veldo/policy.yaml').read_text().split('\nproof:\n', 1)[1]
    _p270_own = [l.strip() for l in _p270_own.splitlines()[:next(i for i, l in enumerate(_p270_own.splitlines())
                                                                 if not l.startswith('  '))]]
    _p270_r5 = _p270_scratch(_p270_base, 'release', _p270_own)
    _p270_first5 = _p270_commit_file(_p270_r5, 'proof/Y/raw.log', b'x\n' * (1024 * 1024), 'add 2 MB')
    _p270_line5 = 'refs/heads/work %s refs/heads/release %s\n' % (_p270_first5, _p270_zero)
    _p270_p5 = _p270_sp.run([_p270_sys.executable, str(_p270_r5 / '.veldo/validate.py'), 'push-proof', 'origin'],
                            cwd=str(_p270_r5), input=_p270_line5, capture_output=True, text=True, timeout=300)
    expect('p270/guard/push-to-release-size-checked',
           _p270_p5.returncode != 0 and 'proof_file_over_limit' in _p270_p5.stdout + _p270_p5.stderr
           and _p270_first5 in _p270_p5.stdout + _p270_p5.stderr)

    # ---- AC2 (1)(2): each writer, on a fixture whose raw output exceeds the limit, writes a summary
    # under the limit with the deciding numbers, command, environment and the raw bytes' sha256;
    # the contract check over the bundle stays clean (a writer copying raw output reds it).
    _p270_r4 = _p270_scratch(_p270_base, 'writers', ['max_file_bytes: 4096'])
    _p270_V4 = _p270_load('p270_validate_writers', _p270_r4 / '.veldo/validate.py')
    (_p270_r4 / 'proof/W').mkdir()

    def _p270_summary_ok(path, raw, deciding_ok):
        try:
            text = _p270_Path(path).read_bytes()
            s = _p270_json.loads(text)
            _p270_run(_p270_r4, 'add', '-A')
            errs, _out = _p270_check(_p270_V4, _p270_r4)
            return (len(text) <= 4096 and len(raw) > 4096 and errs == 0
                    and isinstance(s.get('command'), str) and s['command']
                    and s.get('environment', {}).get('commit')
                    and s['discarded'][0]['sha256'] == _p270_hl.sha256(raw).hexdigest()
                    and s['discarded'][0]['bytes'] == len(raw) and deciding_ok(s.get('deciding') or {}))
        except Exception as exc:  # a writer that crashes has not written its summary
            print('  VELDO-0270 detail: %s: %r' % (path, exc))
            return False

    _p270_transcript = _p270_base / 'gate-transcript.txt'
    _p270_transcript.write_text(''.join('   detail line %d of the transcript\n' % i for i in range(400))
                                + '   lint: pass\n   unit: confined leg: FAIL (12.5s)\n'
                                '  SELFTEST FAIL: some/row\nGATE: RED (abc)\n')
    try:
        _p270_V4.write_gate_summary(_p270_transcript, _p270_r4 / 'proof/W/gate.summary.json', root=_p270_r4)
    except Exception as exc:
        print('  VELDO-0270 detail: gate summary: %r' % (exc,))
    expect('p270/writers/gate-transcript-writes-stage-table',
           _p270_summary_ok(_p270_r4 / 'proof/W/gate.summary.json', _p270_transcript.read_bytes(),
                            lambda d: d.get('gate') == 'GATE: RED (abc)'
                            and {'stage': 'unit: confined leg', 'verdict': 'FAIL', 'seconds': 12.5} in d.get('stages', [])
                            and d.get('first_failing_row', '').startswith('SELFTEST FAIL: some/row')))

    _p270_receipt = {'schema': 'veldo.mutation-stage/v1', 'status': 'failed', 'registered': 21, 'executed': 21,
                     'reused': 0, 'rejected': 0, 'worker_invocations': 21, 'elapsed': 3.5,
                     'results': [{'case': {'name': 'case-%d' % i, 'identity': 'id-%d' % i}, 'source': 'fresh',
                                  'mutant': {'count': 5, 'failed': ['row/%d' % i] * 40}} for i in range(20)],
                     'invalid_results': [{'case': {'name': 'case-20'}, 'error': 'mutation_survived',
                                          'detail': 'no row went red'}]}
    _p270_raw_results = _p270_json.dumps(_p270_receipt['results'], sort_keys=True, separators=(',', ':')).encode()
    for _p270_label, _p270_path in (('scripts', ROOT / "scripts" / "check_gate_mutations.py"),
                                    ('engine', ROOT / 'engine/scripts/check_gate_mutations.py')):
        _p270_out_path = _p270_r4 / ('proof/W/mutations-%s.summary.json' % _p270_label)
        try:
            _p270_M = _p270_load('p270_gate_mutations_' + _p270_label, _p270_path)
            _p270_M.write_summary(_p270_out_path, _p270_receipt, _p270_r4)
        except Exception as exc:
            print('  VELDO-0270 detail: mutation summary %s: %r' % (_p270_label, exc))
        expect('p270/writers/mutation-writer-writes-summary/' + _p270_label,
               _p270_summary_ok(_p270_out_path, _p270_raw_results,
                                lambda d: d.get('results_count') == 20
                                and d.get('results_sha256') == _p270_hl.sha256(_p270_raw_results).hexdigest()
                                and d.get('counts', {}).get('status') == 'failed'
                                and {'case': 'case-20', 'expected': 'killed', 'observed': 'mutation_survived',
                                     'red': 'no row went red'} in d.get('rows', [])))
    expect('p270/writers/teeth-writer-uses-the-summary-writer',
           'coordinator.write_summary(args.summary, receipt, ROOT)' in (ROOT / 'scripts/check_teeth_mutations.py').read_text())

    _p270_wreport = {'baseline_documents': 3, 'documents': 300, 're_emitted': 299, 'oracle': 'checked', 'failures': 1,
                     'corpus': [{'path': 'specs/S-%d.md' % i, 'sha256': '0' * 64, 'differences': [],
                                 'status': 're-emitted'} for i in range(299)]
                     + [{'path': 'specs/bad.md', 'sha256': '1' * 64, 'differences': [{'field': '$.x'}]}]}
    try:
        if str(ROOT / 'scripts') not in _p270_sys.path:
            _p270_sys.path.insert(0, str(ROOT / 'scripts'))
        import writer_corpus_audit as _p270_wca
        _p270_wca.write_summary(_p270_wreport, _p270_r4 / 'proof/W/writer-corpus.summary.json', _p270_r4)
        _p270_wraw = _p270_wca.raw_report(_p270_wreport).encode()
    except Exception as exc:
        print('  VELDO-0270 detail: writer corpus summary: %r' % (exc,))
        _p270_wraw = b''
    expect('p270/writers/writer-corpus-audit-writes-counts-and-differing',
           _p270_summary_ok(_p270_r4 / 'proof/W/writer-corpus.summary.json', _p270_wraw,
                            lambda d: d.get('documents') == 300 and d.get('failures') == 1
                            and [r['path'] for r in d.get('differing', [])] == ['specs/bad.md']))

    _p270_preport = {'baseline': 'abc1234', 'parser_commit': 'def5678', 'documents': 10, 'with_front_matter': 10,
                     'different': 1, 'additional_yaml': [{'path': 'a.yaml', 'comparisons': {}}],
                     'corpus': [{'path': 'specs/S-%d.md' % i, 'sha256': '2' * 64, 'has_front_matter': True,
                                 'comparisons': {'validate.front_matter': [{'field': '$.value.x', 'old': 'o' * 3000,
                                                                            'new': 'n' * 3000}] if i == 0 else []}}
                                for i in range(10)]}
    try:
        _p270_pca = _p270_load('p270_parser_audit', ROOT / 'scripts/parser_corpus_audit.py')
        _p270_pca.write_summary(_p270_preport, _p270_r4 / 'proof/W/parser-corpus.summary.json', _p270_r4)
        _p270_praw = (_p270_json.dumps(_p270_preport, indent=2, ensure_ascii=True) + '\n').encode()
    except Exception as exc:
        print('  VELDO-0270 detail: parser corpus summary: %r' % (exc,))
        _p270_praw = b''
    expect('p270/writers/parser-corpus-audit-writes-counts-and-differing',
           _p270_summary_ok(_p270_r4 / 'proof/W/parser-corpus.summary.json', _p270_praw,
                            lambda d: d.get('documents') == 10 and d.get('different') == 1
                            and [r['path'] for r in d.get('corpus', []) if r['differing_readers']] == ['specs/S-0.md']))

    # ---- AC2 (3): a summary without its command, or without a discarded file's sha256, is refused.
    _p270_good = _p270_json.loads((_p270_r4 / 'proof/W/gate.summary.json').read_text()) \
        if (_p270_r4 / 'proof/W/gate.summary.json').is_file() else {}
    _p270_nocmd = dict(_p270_good)
    _p270_nocmd.pop('command', None)
    _p270_nosha = dict(_p270_good, discarded=[{'name': 'raw.log', 'bytes': 10}])
    (_p270_r4 / 'proof/W/nocmd.summary.json').write_text(_p270_json.dumps(_p270_nocmd))
    _p270_run(_p270_r4, 'add', '-A')
    _p270_e, _p270_out = _p270_check(_p270_V4, _p270_r4)
    expect('p270/summary/missing-command-refused',
           bool(_p270_good) and _p270_e >= 1 and 'proof_summary_incomplete' in _p270_out and 'no command' in _p270_out)
    (_p270_r4 / 'proof/W/nocmd.summary.json').unlink()
    (_p270_r4 / 'proof/W/nosha.summary.json').write_text(_p270_json.dumps(_p270_nosha))
    _p270_run(_p270_r4, 'add', '-A')
    _p270_e, _p270_out = _p270_check(_p270_V4, _p270_r4)
    expect('p270/summary/missing-discarded-sha256-refused',
           bool(_p270_good) and _p270_e >= 1 and 'raw.log has no sha256' in _p270_out)

    # ---- AC3: a proof file still naming a removed file instead of its summary is refused.
    _p270_r5 = _p270_scratch(_p270_base, 'dangling', None)
    _p270_V5 = _p270_load('p270_validate_dangling', _p270_r5 / '.veldo/validate.py')
    (_p270_r5 / 'proof/Z').mkdir()
    (_p270_r5 / 'proof/Z/gate.log.summary.json').write_text(_p270_json.dumps(dict(
        _p270_good, original_path='proof/Z/gate.log', sha256='3' * 64)))
    (_p270_r5 / 'proof/Z/manifest.json').write_text('{"ref": "proof/Z/gate.log"}\n')
    _p270_run(_p270_r5, 'add', '-A')
    _p270_e, _p270_out = _p270_check(_p270_V5, _p270_r5)
    expect('p270/dangling/manifest-naming-removed-file-refused',
           _p270_e == 1 and 'proof_reference_dangling' in _p270_out and 'proof/Z/manifest.json' in _p270_out)
    (_p270_r5 / 'proof/Z/manifest.json').write_text('{"ref": "proof/Z/gate.log.summary.json"}\n')
    _p270_e, _p270_out = _p270_check(_p270_V5, _p270_r5)
    expect('p270/dangling/manifest-naming-summary-passes', _p270_e == 0)

# ---- AC3 on this tree: zero files over the limit, zero archives, zero dangling references; each
# summary's sha256 equals the removed bytes, read back at the commit where they remain.
_p270_e, _p270_out = _p270_check(_p270_V, ROOT)
expect('p270/tree/contract-check-green', _p270_e == 0)
_P270_REMOVED = ['proof/VELDO-0110/corpus-before.json', 'proof/VELDO-0121/results/AC4-red.json.gz',
                 'proof/VELDO-0121/earlier-attempt/results/AC4-red.json.gz', 'proof/VELDO-0230/gate.log',
                 'proof/VELDO-0189/older/971186ac.tar.gz', 'proof/VELDO-0189/older/8bc34e94.tar.gz',
                 'proof/VELDO-0123/removed-teeth.json', 'proof/VELDO-0215/full-gate.log.gz']
for _p270_path in _P270_REMOVED:
    _p270_ok = False
    try:
        _p270_s = _p270_json.loads((ROOT / (_p270_path + '.summary.json')).read_text())
        _p270_bytes = _p270_git.run(['git', '-C', str(ROOT), 'show', _p270_s['readable_at'] + ':' + _p270_path],
                                    check=True, capture_output=True).stdout
        _p270_ok = (not (ROOT / _p270_path).exists() and _p270_s['original_path'] == _p270_path
                    and _p270_hl.sha256(_p270_bytes).hexdigest() == _p270_s['sha256']
                    and len(_p270_bytes) == _p270_s['bytes']
                    and _p270_git.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', _p270_s['readable_at'],
                                       'HEAD'], capture_output=True).returncode == 0)
    except Exception as exc:
        print('  VELDO-0270 detail: %s: %r' % (_p270_path, exc))
    expect('p270/tree/summary-sha256-matches-removed-bytes/' + _p270_path, _p270_ok)
_p270_digests = _p270_json.loads((ROOT / 'proof/VELDO-0189/older/digests.json').read_text())['files']
_p270_m215 = _p270_json.loads((ROOT / 'proof/VELDO-0215/manifest.json').read_text())['artifact_digests']
expect('p270/tree/recorded-digests-kept-under-the-summary-name',
       _p270_digests['971186ac.tar.gz.summary.json']['sha256']
       == _p270_json.loads((ROOT / 'proof/VELDO-0189/older/971186ac.tar.gz.summary.json').read_text())['sha256']
       and _p270_m215['proof/VELDO-0215/full-gate.log.gz.summary.json'].split(':')[1]
       == _p270_json.loads((ROOT / 'proof/VELDO-0215/full-gate.log.gz.summary.json').read_text())['sha256'])

# ---- AC4: the paragraph, verbatim, where builders and reviewers read.
_P270_RULE = (
    "Proof is small summaries, never raw bulk. No file under proof/ may be larger than the limit read from "
    "`.veldo/policy.yaml` key `proof.max_file_bytes` (1,048,576 bytes when the key is absent), and a base64 "
    "encoded archive is refused at any size; the gate's contract check and the push guard both refuse them. A "
    "summary carries the numbers that decide pass or fail with their bounds and verdicts, the exact command that "
    "produced them, the environment (commit, tree, host, tool versions, and host load when the result is timing "
    "sensitive) and, for every raw file the run produced, its name, size in bytes and sha256. Raw data is "
    "discarded, not stored elsewhere.")
for _p270_doc, _p270_docpath in (('CLAUDE.md', ROOT / 'CLAUDE.md'), ('VELDO.md', ROOT / 'VELDO.md'),
                                  ('engine/VELDO.md', ROOT / "engine" / "VELDO.md")):
    expect('p270/rule/paragraph-verbatim/' + _p270_doc,
           _P270_RULE in _p270_docpath.read_text().splitlines())
_p270_briefs = sorted(ROOT.glob('packs/*/agents/veldo-reviewer.md')) + sorted(ROOT.glob('packs/*/.*/agents/veldo-reviewer.md')) \
    + sorted(ROOT.glob('packs/*/.*/agent/veldo-reviewer.md'))
expect('p270/rule/reviewer-briefs-carry-paragraph-and-question',
       len(_p270_briefs) == len(list(ROOT.glob('packs/*/hooks/pre-push')))
       and all(_P270_RULE in b.read_text().splitlines()
               and 'does it hold anything a reviewer does not need?' in b.read_text() for b in _p270_briefs))

# The temporary .veldo tree the rows ran from is removed.
_p270_modules.cleanup()
