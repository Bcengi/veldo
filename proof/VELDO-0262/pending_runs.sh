#!/usr/bin/env bash
# VELDO-0262: every suite and falsifier run this ticket needs, as exact commands, for the lead to run
# unattended inside the gate lock. No lock and no systemd-run here. Each step appends one line to
# proof/VELDO-0262/pending-summary.txt: the step name, its exit code, the selftest summary when there is
# one, and its log path under /tmp. A partial selftest run never exits 0 by design (PARTIAL_RUN), so its
# line carries the "N passed, M failed" summary, which is what to read.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 2
SUMMARY="proof/VELDO-0262/pending-summary.txt"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOGS="/tmp/veldo-0262-pending-$STAMP"
mkdir -p "$LOGS"
: > "$SUMMARY"
echo "# VELDO-0262 pending runs at $(git rev-parse HEAD) ($STAMP)" >> "$SUMMARY"

step() {
    local name="$1"
    shift
    local log="$LOGS/$name.log"
    "$@" > "$log" 2>&1
    local code=$?
    local tally
    tally="$(grep -o 'selftest (PARTIAL[^)]*): [0-9]* passed, [0-9]* failed' "$log" | tail -1)"
    local fails
    fails="$(grep -c 'SELFTEST FAIL' "$log")"
    echo "$name exit=$code${tally:+ [$tally]} selftest_fail_lines=$fails log=$log" >> "$SUMMARY"
}

# Lint and the engine copies.
step lint bash scripts/check_lint.sh
step template-sync bash scripts/check_template_sync.sh

# AC1: the corpus recorded on the LangGraph runner, replayed on the step runner, and twice.
step corpus-replay python3 proof/VELDO-0262/corpus.py replay
step corpus-twice python3 proof/VELDO-0262/corpus.py twice
# AC1 falsifier 3 in the spec's literal form, on a scratch copy: exit 0 means the recorded premise holds (the
# literal mutation changes no replayed answer and no failure answer carries a step).
step falsifier3-literal python3 proof/VELDO-0262/falsifier3_literal.py

# AC3: the runtime journey that remains: check, qualify, install answering runtime_removed, enforcement.
step runtime-check python3 .veldo/control_runtime.py check
step runtime-qualify python3 .veldo/control_runtime.py qualify
step runtime-install-removed bash -c '! python3 .veldo/control_runtime.py install | grep -q "\"outcome\": \"accepted\""'
step runtime-enforcement python3 .veldo/control_runtime.py enforcement
step isolation-probe python3 .veldo/control_graph_isolation.py --probe-graph
step isolation-enforcement python3 .veldo/control_graph_isolation.py

# The suites: this ticket's own, every suite that drives the graph adapter, the workflow runner or the PM
# cycles, and the ones the spec names.
for suite in \
    130_veldo_0262_step_runner \
    59_veldo_0043_graph \
    62_veldo_0045_runtime \
    65_veldo_0132_workflow \
    128_veldo_0247_check_join \
    129_veldo_0247_line \
    92_veldo_0088_pm_cycles \
    86_veldo_0186_setup_assets \
    86_veldo_0189_engine_upgrade \
    29_veldo_0016_policy_boundaries \
    32_veldo_0019_combined_graph \
    34_veldo_0022_admission \
    36_veldo_0023_journal \
    66_veldo_0047_authority \
    71_veldo_0076_projects \
    71_veldo_0130_api \
    73_veldo_0078_backlog \
    73_veldo_0139_factory_setup \
    82_veldo_0085_decomposition \
    93_veldo_0152_intake_routes \
    96_veldo_0204_reservation_policies \
    101_veldo_0208_landing_reuse \
    110_veldo_0143_new_project \
    113_veldo_0115_authority_store \
    113_veldo_0220_gate_host \
    129_veldo_0239_batch_landing \
    129_veldo_0254_canary_launch
do
    step "suite-$suite" python3 scripts/selftest.py --suite "$suite"
done

# The falsifiers through the gate's mutation driver: this ticket's eleven (finding 262: the nine declared, the
# suite 128 forged-land row and the suite 86_0189 factory leftover rows), then every
# VELDO-0043, VELDO-0045, VELDO-0132 and VELDO-0247 row, the retargeted ones among them.
step teeth-262 python3 scripts/check_teeth_mutations.py --finding 262 --worker-log-dir "$LOGS/teeth-262"
step teeth-43 python3 scripts/check_teeth_mutations.py --finding 43 --worker-log-dir "$LOGS/teeth-43"
step teeth-45 python3 scripts/check_teeth_mutations.py --finding 45 --worker-log-dir "$LOGS/teeth-45"
step teeth-132 python3 scripts/check_teeth_mutations.py --finding 132 --worker-log-dir "$LOGS/teeth-132"
step teeth-247 python3 scripts/check_teeth_mutations.py --finding 247 --worker-log-dir "$LOGS/teeth-247"

# requires.json is current, and the run left the tree clean apart from this script's own summary.
step requires-current bash -c 'python3 scripts/run_scope.py --emit-requires && git diff --exit-code -- scripts/suites/requires.json'
step clean-tree bash -c 'test -z "$(git status --porcelain -- . ":(exclude)proof/VELDO-0262/pending-summary.txt")"'

echo "# done $(date +%Y%m%d-%H%M%S)" >> "$SUMMARY"
