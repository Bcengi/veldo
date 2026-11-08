#!/usr/bin/env bash
# VELDO-0275: every suite and falsifier run this build could not run (the shared gate lock was busy).
# The lead runs it unattended inside the lock. Each step appends one line to pending-summary.txt:
# <step> exit=<code> log=<path under /tmp>. Logs stay in /tmp and are never committed.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 2
SUMMARY="proof/VELDO-0275/pending-summary.txt"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
: > "$SUMMARY"

step() {
  local name="$1"
  shift
  local log="/tmp/veldo-0275-${STAMP}-${name}.log"
  "$@" > "$log" 2>&1
  local code=$?
  echo "${name} exit=${code} log=${log}" >> "$SUMMARY"
}

# The tree must be clean before and after (the summary file this script writes is ignored).
step clean-before bash -c "test -z \"\$(git status --porcelain | grep -v -e 'proof/VELDO-0275/pending-summary.txt')\""

step lint bash scripts/check_lint.sh

# AC1: the new suite (approved/stays-on-approved, approved/changed-bytes), green on the fix.
step suite-130_veldo_0275_approved_engine python3 scripts/selftest.py --suite 130_veldo_0275_approved_engine
# AC3: the new suite (probe/unknown-frame, probe/accepted), green on the fix.
step suite-131_veldo_0275_stream_probe python3 scripts/selftest.py --suite 131_veldo_0275_stream_probe

# Suites whose refusal codes or setup path this change moved, and every suite that loads the engine or setup modules.
for suite in 78_veldo_0060_claude_adapter 79_veldo_0061_codex_adapter 86_veldo_0186_setup_assets \
    86_veldo_0189_engine_upgrade 73_veldo_0139_factory_setup 74_veldo_0140_standing_delegation \
    75_veldo_0062_accounts 78_veldo_0160_account_pool 80_veldo_0155_claude_baseline 81_veldo_0156_codex_baseline \
    82_veldo_0129_worker_wiring 82_veldo_0141_execution_record 82_veldo_0165_launch_hygiene \
    82_veldo_0173_tool_registry 83_veldo_0154_factory_loop 83_veldo_0166_usage_windows \
    85_veldo_0158_credential_delivery 85_veldo_0171_setup_api 86_veldo_0127_agent_configuration \
    86_veldo_0148_re_land 86_veldo_0168_text 87_veldo_0127_codex_delivery 87_veldo_0170_receiver_trust \
    88_veldo_0127_feature_defaults 89_veldo_0127_feature_listing 90_veldo_0127_feature_profile \
    91_veldo_0167_setup_records 92_veldo_0088_pm_cycles 103_veldo_0142_git_identities 105_veldo_0182_memory \
    106_veldo_0185_dispatch_setup 109_veldo_0161_adoption 110_veldo_0143_new_project 116_veldo_0188_project_lines \
    117_veldo_0227_ui_location 125_veldo_0230_engine_census 126_veldo_0230_qualify_reproduces \
    127_veldo_0234_https_port 127_veldo_0254_secret_scan 127_veldo_0259_installation 129_veldo_0254_canary_launch \
    70_veldo_0073_activation 101_veldo_0208_landing_reuse 102_veldo_0210_agent_profile_runtime \
    123_veldo_0174_conversations 93_veldo_0152_intake_routes 82_veldo_0172_live_formats \
    60_veldo_0052_eligibility 60_veldo_0053_architecture 94_veldo_0162_configuration_routes 95_veldo_0203_owner_revisions; do
  step "suite-${suite}" python3 scripts/selftest.py --suite "$suite"
done

# AC1 falsifiers: each registered mutation must turn its named row red (the driver reports it rejected).
for case in approved275-claude-newest-installed approved275-codex-newest-installed \
    approved275-claude-digest-skipped approved275-codex-digest-skipped; do
  step "mutation-${case}" python3 scripts/check_teeth_mutations.py --case "$case"
done
# AC3 falsifiers: the launch skips the probe (Claude Code's Guard, the receiver's Codex step): probe/unknown-frame red.
for case in probe275-claude-skipped probe275-codex-skipped; do
  step "mutation-${case}" python3 scripts/check_teeth_mutations.py --case "$case"
done
# Registered mutations whose anchors this change rewrote (refusal codes now engine_not_approved).
for case in claude-pin-digest-unchecked claude-unknown-version-accepted upgrade189-codex-refusal-differs \
    setup186-claude-unlisted-taxonomy setup186-codex-unlisted-taxonomy setup186-claude-digest-unchecked \
    setup186-codex-digest-unchecked; do
  step "mutation-${case}" python3 scripts/check_teeth_mutations.py --case "$case"
done

step clean-after bash -c "test -z \"\$(git status --porcelain | grep -v -e 'proof/VELDO-0275/pending-summary.txt')\""
exit 0
