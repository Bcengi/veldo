#!/usr/bin/env bash
# VELDO-0268 fix round 7: the runs left pending because the gate lock was not free within the
# 20 minute budget. The lead runs this already inside the gate lock (no flock here). Each step
# appends one line to proof/VELDO-0268/pending-summary.txt; logs go under /tmp, never the repo.
set -u
cd "$HOME/projects/veldo-worktrees/veldo-0268" || exit 1
SUMMARY=proof/VELDO-0268/pending-summary.txt
HEAD_SHA=$(git rev-parse --short HEAD)

# Step 1: suite 141 (48 behaviour rows and 36 in-suite mutation rows expected green). Details on,
# so each row's observed line is in the log.
VELDO_0268_DETAILS=1 python3 scripts/selftest.py --suite 141_veldo_0268_protected_refs > /tmp/v268-fix7-suite.log 2>&1
rc=$?
red=$(grep -o 'VELDO-0268 [^ ]* detail' /tmp/v268-fix7-suite.log | sed 's/^VELDO-0268 //; s/ detail$//' | tr '\n' ' ')
echo "suite 141 at ${HEAD_SHA}: exit ${rc}; red rows: ${red:-none}; $(grep -E '[0-9]+ passed' /tmp/v268-fix7-suite.log | tail -1)" >> "$SUMMARY"

# Step 2: the 36 registered falsifiers in the teeth driver (baseline green, each mutant red).
python3 scripts/check_teeth_mutations.py --finding 268 > /tmp/v268-fix7-teeth.log 2>&1
rc=$?
echo "teeth --finding 268 at ${HEAD_SHA}: exit ${rc}; $(grep '^mutations:' /tmp/v268-fix7-teeth.log | tail -1)" >> "$SUMMARY"
