#!/bin/sh
# VELDO-0274: the two runs still owed, from the checkout root, under the shared gate lock.
set -u
L=/home/dmitry/.local/state/core-gates/.gate.lock
flock -x "$L" sh -c '
python3 proof/VELDO-0274/falsify.py exit-skips-stop
python3 scripts/selftest.py --suite 129_veldo_0274_factory_slices
'
