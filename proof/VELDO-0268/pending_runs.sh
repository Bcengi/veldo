#!/usr/bin/env bash
# VELDO-0268 fix round 1: the runs left pending because the gate lock was not free within the
# 20 minute budget. The lead runs this already inside the gate lock (no flock here). Each step
# appends one line to proof/VELDO-0268/pending-summary.txt; logs go under /tmp, never the repo.
set -u
cd /home/dmitry/projects/veldo-worktrees/veldo-0268 || exit 1
SUMMARY=proof/VELDO-0268/pending-summary.txt
HEAD_SHA=$(git rev-parse --short HEAD)

# Step 1: suite 141 (30 behaviour rows and 10 in-suite mutation rows expected green).
python3 scripts/selftest.py --suite 141_veldo_0268_protected_refs > /tmp/v268-fix1-suite.log 2>&1
rc=$?
echo "suite 141 at ${HEAD_SHA}: exit ${rc}; $(grep -c 'VELDO-0268 .* detail' /tmp/v268-fix1-suite.log) red rows; $(tail -1 /tmp/v268-fix1-suite.log)" >> "$SUMMARY"

# Step 2: the ten registered falsifiers in the teeth driver (baseline green, each mutant red).
python3 scripts/check_teeth_mutations.py --finding 268 > /tmp/v268-fix1-teeth.log 2>&1
rc=$?
echo "teeth --finding 268 at ${HEAD_SHA}: exit ${rc}; $(grep '^mutations:' /tmp/v268-fix1-teeth.log | tail -1)" >> "$SUMMARY"
