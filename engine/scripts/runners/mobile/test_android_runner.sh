#!/usr/bin/env bash
# The Android runner's live self-test: needs a booted emulator or device.
# The passing journey must pass (exit 0), the deliberately-broken one must
# fail (exit 1). NOT wired into the every-commit gate - booting an emulator
# per commit is heavy and environment-dependent; the runner's CONTROL LOGIC
# is unit-tested with a fake driver in scripts/selftest.py instead.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/Android/Sdk/platform-tools:$PATH"

if ! command -v adb >/dev/null 2>&1; then
  echo "android runner self-test: SKIP (adb not found)"; exit 0
fi
if [ -z "$(adb devices | sed '1d' | grep -w device)" ]; then
  echo "android runner self-test: SKIP (no booted device/emulator)"; exit 0
fi

fail=0
python3 "$here/veldo_android_runner.py" "$here/fixtures/pass.journey.json" /tmp/veldo-android-pass >/dev/null 2>&1
if [ $? -eq 0 ]; then echo "pass journey: exit 0 (correct)"; else echo "pass journey: FAIL (expected 0)"; fail=1; fi

python3 "$here/veldo_android_runner.py" "$here/fixtures/fail.journey.json" /tmp/veldo-android-fail >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "fail journey: exit 1 (correct - failure caught)"; else echo "fail journey: FAIL (expected 1)"; fail=1; fi

if [ "$fail" -eq 0 ]; then echo "android runner self-test: pass"; else echo "android runner self-test: FAIL"; fi
exit $fail
