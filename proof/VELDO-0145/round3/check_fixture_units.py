#!/usr/bin/env python3
"""VELDO-0145 round 3 (N4): every seeded run record's wrapper line names that run's own unit and station.

Run: python3 -B proof/VELDO-0145/round3/check_fixture_units.py <harness.py> <organs dir> <ui build dir>
Builds the harness's real factory in a temporary directory, records each line the seed appends per run, and
prints one line per run; exits 1 when any wrapper line names another unit or station.
"""
import importlib.util
from pathlib import Path
import sys
import tempfile

spec = importlib.util.spec_from_file_location('harness_under_check', sys.argv[1])
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
seen = []
append = harness.Factory._append


def recording(self, key, lines):
    seen.append((key, list(lines)))
    return append(self, key, lines)


harness.Factory._append = recording
bad = 0
with tempfile.TemporaryDirectory(prefix='v145-units-') as directory:
    factory = harness.Factory(Path(directory), Path(sys.argv[3]), Path(sys.argv[2]))
    try:
        for key, lines in seen:
            entry = factory.recorders[key]
            station = entry['data']['contract']['station']
            for stream, text in lines:
                if stream == 'wrapper':
                    ok = ('unit %s,' % entry['unit']) in text and text.endswith('station %s' % station)
                    bad += not ok
                    print('%s %s (%s, %s): %s' % ('ok ' if ok else 'BAD', key, entry['unit'], station, text))
    finally:
        factory.pool.shutdown()
print('mismatched wrapper lines: %d' % bad)
sys.exit(1 if bad else 0)
