#!/usr/bin/env bash
# Invoke this entire batch through myday/scripts/host_heavy.sh.
set -u
cd "$(dirname "$0")/../.." || exit 1
proof=proof/VELDO-launch-wait
python3 scripts/selftest.py \
  --suite 53_veldo_0123_mutations \
  --suite 62_veldo_0039_dispatch \
  --suite 78_veldo_0060_claude_adapter \
  --suite 129_veldo_0254_canary_launch \
  --suite 146_veldo_0308_run_finished \
  --suite 150_veldo_0350_end_write > "$proof/selftests.txt" 2>&1
result=$?
printf 'Focused selftests exit=%s (2 means partial run passed)\n' "$result"
if [ "$result" -ne 2 ]; then exit 1; fi
rg -q '^selftest \(PARTIAL,.*\): [0-9]+ passed, 0 failed in ' "$proof/selftests.txt" || exit 1
python3 scripts/check_gate_mutations.py --finding 60 > "$proof/teeth.txt" 2>&1 || exit 1
tail -1 "$proof/teeth.txt"
python3 "$proof/run_loaded.py" > "$proof/loaded-progress.txt" 2>&1
