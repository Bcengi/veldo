#!/usr/bin/env bash
# VELDO-0292 heavy runs. The lead queues this through the gate lock; it takes no lock itself and
# works from the worktree root whatever directory it is called from. Four steps, each writing one
# small summary (veldo.proof-summary/v1) under proof/VELDO-0292/. Logs, worker logs and the scratch
# copy of the old guard go under a fresh directory in /tmp and are not stored; each summary records
# its log by name, size and sha256.
#
#   1. red-before.summary.json   suite 141 over the guard and policy_check as they were at 646ff7c8
#   2. green-after.summary.json  suite 141 over this tree
#   3. teeth-292.summary.json    the 36 mutations registered as finding 292, each killed
#   4. teeth-268.summary.json    the mutations registered as finding 268, which this change must
#                                leave killed (their anchors sit in the file this change edits)
#
# The script exits 0 only when all four verdicts hold.
set -u
cd "$(dirname "$0")/../.." || exit 1
OUT=proof/VELDO-0292
BASE=646ff7c8
SUITE=141_veldo_0268_protected_refs
LOGS=$(mktemp -d /tmp/veldo-0292-heavy-XXXXXX)
failed=0

# Step 1. The suite's own diagnostic (VELDO_0268_UNDER_TEST) runs this tree's rows over another
# pair of files. The pair is read from the base commit into the scratch directory. Expected: the
# 18 rows the spec calls red at 646ff7c8 (live/plain-runs among them since the build check) and all
# 39 VELDO-0292 mutation rows red (their anchors are absent from the old guard); live/scanner-edges
# and live/git-args green; every older row green.
mkdir "$LOGS/before"
git show "$BASE:scripts/veldo-guard.sh" > "$LOGS/before/veldo-guard.sh" || failed=1
git show "$BASE:.veldo/policy_check.py" > "$LOGS/before/policy_check.py" || failed=1
RED_CMD="VELDO_0268_DETAILS=1 VELDO_0268_UNDER_TEST=<scratch copy of scripts/veldo-guard.sh and .veldo/policy_check.py at $BASE> python3 scripts/selftest.py --suite $SUITE"
VELDO_0268_DETAILS=1 VELDO_0268_UNDER_TEST="$LOGS/before" python3 scripts/selftest.py --suite "$SUITE" \
  > "$LOGS/red-before.log" 2>&1
python3 "$OUT/summarize.py" red-before "$?" "$LOGS/red-before.log" "$RED_CMD" || failed=1

# Step 2. Expected: 143 rows, none red (84 older rows, 20 VELDO-0292 rows, 39 mutation rows).
GREEN_CMD="VELDO_0268_DETAILS=1 python3 scripts/selftest.py --suite $SUITE"
VELDO_0268_DETAILS=1 python3 scripts/selftest.py --suite "$SUITE" > "$LOGS/green-after.log" 2>&1
python3 "$OUT/summarize.py" green-after "$?" "$LOGS/green-after.log" "$GREEN_CMD" || failed=1

# Steps 3 and 4. The teeth driver writes its own summary: per case the expected and observed
# verdict. Its full receipt goes to the log only.
for finding in 292 268; do
  python3 scripts/check_teeth_mutations.py --finding "$finding" --summary "$OUT/teeth-$finding.summary.json" \
    --worker-log-dir "$LOGS/teeth-$finding-workers" > "$LOGS/teeth-$finding.log" 2>&1
  rc=$?
  echo "teeth --finding $finding: exit $rc; $(grep '^mutations:' "$LOGS/teeth-$finding.log" | tail -1)"
  [ "$rc" = 0 ] || failed=1
done

echo "VELDO-0292 heavy runs done: $([ "$failed" = 0 ] && echo all four verdicts hold || echo AT LEAST ONE VERDICT FAILED); summaries in $OUT, logs in $LOGS"
exit "$failed"
