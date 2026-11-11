"""Write the proof summary of one suite 141 run for VELDO-0292 (veldo.proof-summary/v1).

Usage: python3 proof/VELDO-0292/summarize.py MODE EXIT_CODE LOG COMMAND [OUT_DIR]

MODE is red-before (suite 141 over the guard as it was at 646ff7c8) or green-after (suite 141 over
this tree). LOG is the run's output with VELDO_0268_DETAILS=1, so every row prints one line saying
whether it held. The summary keeps the row names and the verdict; the log is recorded by name, size
and sha256 and is not stored. OUT_DIR defaults to this directory.
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# The VELDO-0292 rows that must be red over the guard at 646ff7c8, with the reason the spec gives.
RED_BEFORE = {
    'text/incident': 'the guard exits 2',
    'text/quoted': 'the guard exits 2',
    'text/heredoc-stdin': 'the guard exits 2',
    'text/comment': 'the guard exits 2',
    'text/message': 'the guard exits 2',
    'live/shell-string': 'the line does not say what was found',
    'live/pipeline': 'the line does not say what was found',
    'live/outside-subset': 'the line does not say what was found',
    'live/interpreter': 'the line does not say what was found',
    'live/stored': 'the line does not say what was found',
    'live/config-write': 'the line does not say what was found',
    'live/config-include': 'the line does not say what was found',
    'live/construct': 'the line does not say what was found',
    'live/mixed': 'the line does not say what was found',
    'live/remap': 'the line does not say what was found',
    'live/quoted-command-word': 'the guard exits 0',
    'subset/builtin-list': 'the guard has no list',
}
# The VELDO-0292 rows that already hold there: the guard refuses any text with the words of a push.
GREEN_BEFORE = ('live/scanner-edges', 'live/git-args')
ROWS, MUTATION_ROWS = 19, 37  # the VELDO-0292 rows, and one mutation row per row a mutation must turn red
ROW =re.compile(r'^\s*(VELDO-0(?:268|292)) (\S+) (observed|detail): (.*)$')


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    mode, code, log, command = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
    out = Path(sys.argv[5]) if len(sys.argv) > 5 else Path(__file__).resolve().parent
    raw = log.read_bytes()
    rows = {}
    for line in raw.decode('utf-8', 'replace').splitlines():
        found = ROW.match(line)
        if found:
            rows[(found.group(1), found.group(2))] = (found.group(3) == 'observed', found.group(4)[:160])
    new = {name: held for (spec, name), held in rows.items() if spec == 'VELDO-0292'}
    old = {name: held for (spec, name), held in rows.items() if spec == 'VELDO-0268'}
    red_new = sorted(name for name, (ok, _) in new.items() if not ok)
    red_old = sorted(name for name, (ok, _) in old.items() if not ok)
    mutations = sorted(name for name in new if name.startswith('mutation/'))
    if mode == 'red-before':
        expected = sorted(RED_BEFORE) + mutations
        bound = ('exactly the %d named rows and every mutation row of VELDO-0292 red; %s green; '
                 'every VELDO-0268 row green' % (len(RED_BEFORE), ' and '.join(GREEN_BEFORE)))
    elif mode == 'green-after':
        expected = []
        bound = ('no row red, %d VELDO-0292 rows and %d VELDO-0292 mutation rows present, selftest reports 0 failed'
                 % (ROWS, MUTATION_ROWS))
    else:
        raise SystemExit('unknown mode: ' + mode)
    tail = [line.strip() for line in raw.decode('utf-8', 'replace').splitlines()
            if line.startswith('selftest (') or '141_veldo_0268_protected_refs  ' in line][-2:]
    complete = len(new) - len(mutations) == ROWS and len(mutations) == MUTATION_ROWS and bool(old)
    ok = complete and red_new == sorted(expected) and not red_old
    if mode == 'green-after':
        ok = ok and any(', 0 failed' in line for line in tail)
    deciding = {
        'run': mode,
        'exit_code': code,
        'exit_code_note': 'a run of one suite never exits 0; 2 with 0 failed is the partial run convention',
        'rows_veldo_0292': {'present': len(new) - len(mutations), 'bound': ROWS},
        'mutation_rows_veldo_0292': {'present': len(mutations), 'bound': MUTATION_ROWS},
        'rows_veldo_0268': {'present': len(old), 'red': red_old, 'bound': 'none red'},
        'red_veldo_0292': {'observed': red_new, 'expected': sorted(expected), 'bound': bound},
        'red_reasons': {name: new[name][1] for name in red_new},
        'selftest_lines': tail,
        'verdict': 'pass' if ok else 'fail',
    }
    if mode == 'red-before':
        deciding['expected_reasons'] = dict(RED_BEFORE, **{'mutation/*': 'the anchor is absent from the old guard'})
    bash = subprocess.run(['bash', '--version'], capture_output=True, text=True).stdout.splitlines()[:1]
    validate = load(ROOT / '.veldo' / 'validate.py')
    target = out / (mode + '.summary.json')
    validate.write_proof_summary(target, command, deciding, discarded=[(log.name, raw)], root=ROOT,
                                 extra={'tools': {'bash': bash[0] if bash else 'unknown'}})
    print('%s: verdict %s, %d VELDO-0292 rows red, %d VELDO-0268 rows red; wrote %s'
          % (mode, deciding['verdict'], len(red_new), len(red_old), target))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
