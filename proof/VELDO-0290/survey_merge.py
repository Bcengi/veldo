#!/usr/bin/env python3
"""VELDO-0290: merge the eight survey parts into survey.json and the manifest's wall_clock fields.

    python3 proof/VELDO-0290/survey_merge.py PARTS_DIR COMMIT TREE

PARTS_DIR holds brief.md (what the survey looked for), chunk-1..8.json (the suites of each part with
the scan's hints) and survey-part-1..8.json (the bounds found by reading each suite). Those files
are the raw input: their names, sizes and digests are recorded and they are not stored. COMMIT and
TREE name the tree the suites were read at.

The decision is mechanical. A suite is declared when the survey lists a readiness wait, a deadline
or a window under 30 s for it, or when it is one of the seven suites the spec names because a
control of theirs has failed under the stage's load. A hang guard alone declares nothing.
"""
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'scripts/suites/manifest.json'
OUT = Path(__file__).with_name('survey.json')
PARTS = range(1, 9)
DECIDING = ('readiness_wait', 'deadline', 'window')
KINDS = dict(readiness_wait='readiness wait', deadline='deadline', window='window')
SEVEN = ('62_veldo_0039_dispatch.py', '63_veldo_0040_containment.py', '66_veldo_0047_authority.py',
         '82_veldo_0129_worker_wiring.py', '83_veldo_0154_factory_loop.py',
         '86_veldo_0189_engine_upgrade.py', '129_veldo_0254_canary_launch.py')
# A named suite for which the survey found no bound in the suite file itself.
NAMED_ONLY = {
    '82_veldo_0129_worker_wiring.py':
        'the contained live review run, which waits on the product\'s own stop and init bounds; '
        'declared because its control has failed under the stage\'s load',
}
# Suite 114 gained VELDO-0290 rows after its part was read; the bound moved with the text below it.
LINE_CORRECTIONS = {('114_veldo_0216_concurrent_stages.py', 330): 413}
NOTE = (' A suite whose rows hold a wall-clock bound under 30 s (a readiness wait, a deadline or a window)'
        ' carries wall_clock, a sentence naming the bound. Every mutation job of such a suite is claimed'
        ' as wall_clock, and while one is held the ledger grants CPU only up to wall_clock_ceiling in'
        ' scripts/gate_graph.json (VELDO-0290).')


def sentence(name, bounds):
    deciding = sorted((b for b in bounds if b['kind'] in DECIDING), key=lambda b: (b['seconds'], b['line']))
    if not deciding:
        return NAMED_ONLY[name]
    shown = ['the %g s %s (%s)' % (b['seconds'], KINDS[b['kind']], b['what']) for b in deciding[:2]]
    text = ' and '.join(shown)
    if len(deciding) > 2:
        text += '; %d bounds in all, listed in proof/VELDO-0290/survey.json' % len(deciding)
    return text


def main(parts_dir, commit, tree):
    parts_dir = Path(parts_dir)
    manifest = json.loads(MANIFEST.read_text())
    listed = [suite['file'] for suite in manifest['suites']]
    discarded, found, part_of = [], {}, {}
    for name in ['brief.md'] + ['chunk-%d.json' % n for n in PARTS] + ['survey-part-%d.json' % n for n in PARTS]:
        raw = (parts_dir / name).read_bytes()
        discarded.append(dict(name=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    for n in PARTS:
        chunk = json.loads((parts_dir / ('chunk-%d.json' % n)).read_text())
        part = json.loads((parts_dir / ('survey-part-%d.json' % n)).read_text())
        if set(chunk) != set(part):
            raise SystemExit('part %d does not cover its chunk: %s' % (n, sorted(set(chunk) ^ set(part))))
        for name, entry in part.items():
            if name in found:
                raise SystemExit('surveyed twice: ' + name)
            found[name], part_of[name] = entry, n
    if set(found) != set(listed) or len(listed) != len(set(listed)):
        raise SystemExit('survey and manifest differ: %s' % sorted(set(found) ^ set(listed)))
    suites, corrected = [], []
    for suite in manifest['suites']:
        name = suite['file']
        bounds = []
        for bound in found[name]['bounds']:
            if bound['kind'] not in DECIDING + ('hang_guard',) or not bound['what'].isascii():
                raise SystemExit('bad bound in %s: %r' % (name, bound))
            line = LINE_CORRECTIONS.get((name, bound['line']), bound['line'])
            if line != bound['line']:
                corrected.append(dict(file='scripts/suites/' + name, read_at=bound['line'], now=line))
            bounds.append(dict(file='scripts/suites/' + name, line=line, seconds=bound['seconds'],
                               kind=bound['kind'], what=bound['what']))
        deciding = [b for b in bounds if b['kind'] in DECIDING]
        declared = bool(deciding) or name in SEVEN
        suite.pop('wall_clock', None)
        entry = dict(file=name, part=part_of[name], bounds=bounds, notes=found[name].get('notes', ''))
        if declared:
            suite['wall_clock'] = sentence(name, bounds)
            entry['decision'] = 'declared'
            entry['reason'] = ('%d bound(s) under 30 s that are not hang guards' % len(deciding) if deciding
                               else 'named by the spec: its control has failed under the stage\'s load')
            if name in SEVEN:
                entry['named_by_spec'] = True
        else:
            entry['decision'] = 'not declared'
            entry['reason'] = 'only hang guards' if bounds else 'no wall-clock bound under 30 s'
        suites.append(entry)
    if not manifest['resource_note'].endswith(NOTE):
        manifest['resource_note'] += NOTE
    MANIFEST.write_text(json.dumps(manifest, indent=1) + '\n')
    declared = [s['file'] for s in suites if s['decision'] == 'declared']
    kinds = {kind: sum(b['kind'] == kind for s in suites for b in s['bounds']) for kind in DECIDING + ('hang_guard',)}
    summary = dict(
        schema='veldo.proof-summary/v1',
        command='python3 proof/VELDO-0290/survey_merge.py %s %s %s' % (parts_dir, commit, tree),
        environment=dict(commit=commit, tree=tree, host=platform.node(), python=platform.python_version()),
        discarded=discarded,
        deciding=dict(
            rule='declared when the suite file holds a readiness wait, a deadline or a window under 30 s, '
                 'or the spec names the suite; a hang guard alone declares nothing',
            suites_surveyed=len(suites), declared=len(declared), not_declared=len(suites) - len(declared),
            named_by_spec=list(SEVEN), all_named_declared=all(name in declared for name in SEVEN),
            bounds_by_kind=kinds, declared_suites=declared, line_corrections=corrected,
            method='Each part was read by hand from the scan hints in its chunk plus a search of the suite '
                   'file for sleeps, clocks, timeouts, deadlines and waits. Parts 1, 2 and 4 to 8 come from '
                   'the first build run. Part 3 was read again in the continuing build session, in the '
                   'session itself; the first run\'s part 3 was set aside unread and is not an input.',
            gaps=['The graph node unit.confined runs the declared confined suites serially and is not '
                  'marked wall_clock: it holds its claim for about 1,900 s and would keep the ceiling on '
                  'for most of the stage. Left to a later spec.',
                  'Bounds inside product modules and suite helpers under scripts/suites/support are named '
                  'in a suite\'s notes where its rows depend on one; they were not surveyed line by line.',
                  'The decision does not ask whether CPU shortage can fail the row. Some declared windows '
                  'are timers that must fire and cannot fail that way; their notes say so.',
                  'The spec\'s cost estimate covers the seven named suites. The survey declares %d, so the '
                  'time under the ceiling is larger; the replay\'s admission record measures it.' % len(declared)]),
        suites=suites)
    text = json.dumps(summary, indent=1, sort_keys=True) + '\n'
    if not text.isascii() or len(text.encode()) > 1048576:
        raise SystemExit('survey.json is not ASCII or is over the proof size limit')
    OUT.write_text(text)
    print('surveyed %d, declared %d, survey.json %d bytes' % (len(suites), len(declared), len(text)))


if __name__ == '__main__':
    main(*sys.argv[1:4])
