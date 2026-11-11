#!/bin/bash
# VELDO-0290: every heavy run of this specification, for the lead to queue. The caller holds the
# host gate lock; nothing here takes it. Run from anywhere: the checkout is found from this path.
#
#   bash proof/VELDO-0290/heavy_runs.sh            all steps
#   bash proof/VELDO-0290/heavy_runs.sh 3 4        only the steps named
#
# Steps, each writing a small summary under proof/VELDO-0290/ and dropping its raw output:
#   1  red-before: suites 115 and 114 with this checkout's suite files in a scratch clone at
#      646ff7c8                         -> red-before-115.summary.json, red-before-114.summary.json
#   2  green-after: suites 115 and 114 here   -> green-115.summary.json, green-114.summary.json
#   3  teeth: the seven registered mutants of finding 290
#                                       -> teeth.summary.json, teeth-raw.summary.json, diffs/
#   4  AC4 quiet reference: every declared control alone, one at a time
#                                       -> replay-quiet.summary.json
#   5  AC4 off arm (ceiling off)        -> replay-off.summary.json
#   6  AC4 on arm (ceiling on)          -> replay-on.summary.json
#   7  AC4 verdict over 4 to 6          -> replay.json
#
# None of these has been run by the builder. Steps 4 to 6 launch real workers in a scope of their
# own with the gate's memory limit (scripts/gate_host.json); the others run in a 10G scope. Step 4
# runs about fifty suites one after another and is the longest. Options for steps 4 to 6 are read
# from REPLAY_OPTIONS, for example REPLAY_OPTIONS="--bulk 200". If step 7 says the ceiling is not
# low enough, lower it and run step 6 again with ON_OPTIONS="--ceiling 9", then step 7; record the
# value and the runs behind it in the spec's History and set it in scripts/gate_graph.json.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)" || exit 1
cd "$ROOT" || exit 1
OUT=proof/VELDO-0290
BEFORE=646ff7c8
SCOPE="systemd-run --user --scope -q -p MemoryMax=10G"
WORK="$(mktemp -d /tmp/v290-heavy.XXXXXX)" || exit 1
STEPS="${*:-1 2 3 4 5 6 7}"
status=0

wanted() { case " $STEPS " in *" $1 "*) return 0 ;; esac; return 1; }
note() { echo "step $1 rc=$2 wall=$(( $(date +%s) - $3 ))s load=$(cut -d' ' -f1 /proc/loadavg) $4"; [ "$2" = 0 ] || status=1; }

# One suite run in the checkout $1, summarized to $OUT/$3. The rest are options of summarize.py.
suite() {
  local where="$1" name="$2" out="$3"; shift 3
  local log="$WORK/$out.log" command="python3 scripts/selftest.py --suite $name"
  ( cd "$where" && $SCOPE python3 scripts/selftest.py --suite "$name" ) > "$log" 2>&1
  local rc=$?
  python3 "$OUT/summarize.py" suite "$OUT/$out" "$where" "$command" "$log" "$rc" "$@"
}

if wanted 1; then
  s=$(date +%s)
  git clone -q "$ROOT" "$WORK/before" && git -C "$WORK/before" checkout -q --detach "$BEFORE"
  rc=$?
  if [ $rc = 0 ]; then
    copied="scripts/suites/115_veldo_0219_measured_admission.py scripts/suites/114_veldo_0216_concurrent_stages.py"
    for file in $copied; do cp "$ROOT/$file" "$WORK/before/$file"; done
    suite "$WORK/before" 115_veldo_0219_measured_admission red-before-115.summary.json \
      --red wall-clock-ceiling wall-clock-waiting-bars declared-bounds wall-clock-end-to-end stall-recorded \
      --copied $copied
    a=$?
    suite "$WORK/before" 114_veldo_0216_concurrent_stages red-before-114.summary.json \
      --red wall-clock-graph-node wall-clock-node-withdraws --copied $copied
    rc=$(( a | $? ))
  fi
  rm -rf "$WORK/before"
  note 1 $rc $s "red-before at $BEFORE"
fi

if wanted 2; then
  s=$(date +%s)
  suite "$ROOT" 115_veldo_0219_measured_admission green-115.summary.json
  a=$?
  suite "$ROOT" 114_veldo_0216_concurrent_stages green-114.summary.json
  note 2 $(( a | $? )) $s "green-after here"
fi

if wanted 3; then
  s=$(date +%s)
  # The diffs are written outside the checkout and copied in after the run: the stage reads its
  # input closure (every file Git does not ignore) before and after, and a diff written under
  # proof/ during the run fails it with "inputs changed during stage".
  command="python3 scripts/check_teeth_mutations.py --finding 290 --jobs 3 --worker-log-dir <work>/teeth-workers --diff-dir <work>/diffs --summary $OUT/teeth.summary.json"
  $SCOPE python3 scripts/check_teeth_mutations.py --finding 290 --jobs 3 --worker-log-dir "$WORK/teeth-workers" \
    --diff-dir "$WORK/diffs" --summary "$OUT/teeth.summary.json" > "$WORK/teeth.log" 2>&1
  rc=$?
  if [ -d "$WORK/diffs" ]; then
    rm -rf "$OUT/diffs" && cp -r "$WORK/diffs" "$OUT/diffs" && rm -rf "$WORK/diffs"
  fi
  line="$(grep -m1 '^mutations:' "$WORK/teeth.log")"
  # The receipt's error and detail, which the summary format drops: a failed stage carries its cause.
  cause="$(python3 -c '
import json, sys
receipt = {}
for text in open(sys.argv[1], errors="replace"):
    if text.startswith("{"):
        try:
            receipt = json.loads(text)
        except ValueError:
            pass
print("error=%s detail=%s" % (receipt.get("error"), str(receipt.get("detail"))[:300]))
' "$WORK/teeth.log" 2>/dev/null)"
  python3 "$OUT/summarize.py" raw "$OUT/teeth-raw.summary.json" "$ROOT" "$command" "$rc" "$WORK/teeth.log" "$WORK/teeth-workers"
  note 3 $rc $s "teeth finding 290: $line $cause"
fi

for pair in 4:quiet 5:off 6:on; do
  step="${pair%%:*}" mode="${pair##*:}"
  if wanted "$step"; then
    s=$(date +%s)
    extra="$REPLAY_OPTIONS"
    [ "$mode" = on ] && extra="$extra $ON_OPTIONS"
    python3 "$OUT/replay.py" "$mode" $extra > "$WORK/replay-$mode.log" 2>&1
    rc=$?
    note "$step" $rc $s "replay $mode: $(tail -1 "$WORK/replay-$mode.log" | cut -c1-300)"
    [ $rc = 0 ] && rm -f "$WORK/replay-$mode.log"
  fi
done

if wanted 7; then
  s=$(date +%s)
  python3 "$OUT/replay.py" verdict > "$WORK/verdict.log" 2>&1
  rc=$?
  note 7 $rc $s "$(tail -1 "$WORK/verdict.log" | cut -c1-300)"
  [ $rc = 0 ] && rm -f "$WORK/verdict.log"
fi

rmdir "$WORK" 2>/dev/null || echo "left for inspection: $WORK"
python3 .veldo/validate.py proof-files > /dev/null 2>&1 || { echo "proof-files check reports a problem; run python3 .veldo/validate.py proof-files"; status=1; }
ls -1 "$OUT"
exit $status
