#!/usr/bin/env python3
"""VELDO-0262 AC1 falsifier 3 in the form the spec states: "the step count is not advanced for a node that
failed". Applies exactly that mutation to a scratch copy of .veldo (every failure end of an ordinary node keeps
the step it entered with) and replays the corpus on it, then reads every recorded failure answer's fields.

  python3 proof/VELDO-0262/falsifier3_literal.py [--write]

Prints one JSON report; --write also stores it as proof/VELDO-0262/falsifier3-literal.json. Exit 0 when the
premise recorded in the README holds: the literal mutation leaves every replayed answer identical and no
recorded failure answer carries a step (so the declared form cannot red the replay row); exit 1 otherwise.
"""
import collections
import json
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import corpus  # noqa: E402

ANCHOR = "return self.end('failure', step=step, position=name"
MUTANT = "return self.end('failure', step=self.step, position=name"


def main(argv):
    with tempfile.TemporaryDirectory(prefix='v262-f3-') as scratch:
        shutil.copytree(ROOT / '.veldo', Path(scratch) / '.veldo', ignore=shutil.ignore_patterns('__pycache__'))
        runner = Path(scratch) / '.veldo' / 'control_graph_steps.py'
        source = runner.read_text()
        sites = source.count(ANCHOR)
        runner.write_text(source.replace(ANCHOR, MUTANT))
        text, first = corpus.replay(scratch)
    shapes, codes, failures = collections.Counter(), collections.Counter(), 0
    for record in corpus.read():
        answer = record['answer']
        if answer.get('outcome') == 'failure':
            failures += 1
            shapes[','.join(sorted(answer))] += 1
            shapes['failure:' + ','.join(sorted(answer['failure']))] += 1
            codes[answer['failure']['code']] += 1
    carries_step = sum(n for shape, n in shapes.items() if 'step' in shape.split(':')[-1].split(','))
    report = {'mutation': {'anchor': ANCHOR, 'mutant': MUTANT, 'sites': sites},
              'replayed': text.count('\n') + 1 if text else 0, 'first_difference': first,
              'failure_answers': failures, 'failure_shapes': dict(shapes), 'failure_codes': dict(codes),
              'failure_answers_carrying_a_step': carries_step,
              'premise_holds': sites == 3 and first is None and failures > 0 and carries_step == 0}
    body = json.dumps(report, indent=1, sort_keys=True) + '\n'
    if '--write' in argv:
        (HERE / 'falsifier3-literal.json').write_text(body)
    print(body, end='')
    return 0 if report['premise_holds'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
