#!/usr/bin/env bash
# VELDO-0270 pending runs. The lead runs this from the worktree root, already inside the gate lock.
# Each step appends one line to proof/VELDO-0270/pending-summary.txt; logs go under /tmp only.
set -u
cd "$(git rev-parse --show-toplevel)"
OUT=proof/VELDO-0270/pending-summary.txt
LOGS=$(mktemp -d /tmp/veldo-0270-pending-XXXXXX)
HEAD_ID=$(git rev-parse --short HEAD)

step () {
  # step NAME COMMAND...: run, record exit code and the log path in one line.
  name=$1; shift
  log="$LOGS/$name.log"
  start=$(date +%s)
  "$@" > "$log" 2>&1
  rc=$?
  tailline=$(grep -E 'selftest \(|mutations: |veldo contracts|GATE|pass|FAIL' "$log" | tail -1 | tr -d '\n' | cut -c1-200)
  echo "$name head=$HEAD_ID exit=$rc seconds=$(( $(date +%s) - start )) log=$log last=\"$tailline\"" >> "$OUT"
}

# AC1 to AC4 rows (suite 129); exit 2 with 0 failed is the PARTIAL-run convention, not a red.
step suite-129 python3 scripts/selftest.py --suite 129_veldo_0270_small_proof

# Falsifiers: the five teeth mutations of finding 270, each must be killed (status passed).
# The last attempt failed at the noop controls (worker exit 1); the worker logs say why.
step teeth-270 python3 scripts/check_teeth_mutations.py --finding 270 --worker-log-dir "$LOGS/teeth-270-workers"

# Suites this ticket edited or whose inputs it changed.
for s in 45_veldo_0106_policyread 51_parser_boundary 52_writer_boundary 86_veldo_0189_engine_upgrade \
         93_veldo_0152_intake_routes 06_capabilities_manifest_honesty_veldo 50_git_environment \
         107_veldo_0153_identity_push 109_veldo_0161_adoption 58_veldo_0028_effects 86_veldo_0148_re_land; do
  step "suite-$s" python3 scripts/selftest.py --suite "$s"
done

# Contracts over the whole tree (zero files over the limit, zero archives, zero dangling references).
step contracts python3 .veldo/validate.py all
step proof-files python3 .veldo/validate.py proof-files
# Docs and template sync over the edited CLAUDE.md, VELDO.md, engine/VELDO.md and synced copies.
step check-docs bash scripts/check_docs.sh
step template-sync bash scripts/check_template_sync.sh
step git-boundary python3 scripts/check_git_boundary.py

echo "pending runs done; summary in $OUT, logs in $LOGS"
