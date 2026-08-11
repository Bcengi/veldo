# Veldo Android journey runner (reference)

Real mobile UI proof: drives an Android emulator or device over adb through a
journey, asserts against live device state (the focused window and the
uiautomator dump), captures named states as screencaps and the whole run as a
video, and RE-DRIVES the flow through the lifecycle events that actually break
mobile apps - rotation, process death, background/foreground, and network
loss. The founder's own experience is the reason this exists: mobile testing
that only walks the happy path misses exactly the failures that ship. A flow
that works once but breaks after the process is killed is not proven here.

## Use

```
veldo_android_runner.py <journey.json> [outdir]   # exit 0 = flow + all re-drives pass
test_android_runner.sh                           # live self-test (needs a device)
```

Requires the Android platform-tools (`adb`) and a booted emulator or attached
device. The runner is app-agnostic: the journey names the package and
activity, so a repo points it at its own APK. The `fixtures/` pair drives the
built-in Settings app (always present, no APK to build): `pass.journey.json`
(launch, assert focus, capture, then survive all four lifecycle re-drives) and
`fail.journey.json` (asserts a screen that is not there, so the run fails and
captures a FAILURE screencap).

## Journey format

```json
{
  "name": "checkout survives the lifecycle",
  "package": "com.example.app",
  "activity": ".MainActivity",
  "device_profiles": ["pixel-6-api34"],
  "recovery_assertion": {"action": "expect_focus", "value": "com.example.app"},
  "steps": [
    {"action": "launch", "package": "com.example.app", "activity": ".MainActivity"},
    {"action": "tap", "x": 540, "y": 1200},
    {"action": "expect_text", "value": "Order placed"},
    {"action": "state", "name": "confirmation"}
  ],
  "lifecycle_redrives": ["rotation", "process_death", "background_foreground", "network_loss"]
}
```

Actions: `launch`, `tap`, `text`, `key`, `wait`, `expect_focus`,
`expect_text`, `state`. After the happy path, each entry in
`lifecycle_redrives` induces that event and re-checks `recovery_assertion` -
the app must still be in a good state. `device_profiles` declares the matrix
the feature must cover; the runner records the connected device's profile and
FAILS if a declared profile is not covered, so a partial matrix cannot pass
silently.

## Why it is a reference

It drives a REAL device (proven here against a live emulator: happy path, all
four re-drives, screencaps, and a video), but a repo wires it to its own app,
journeys, and device matrix. Booting an emulator on every commit is heavy and
environment-dependent, so the runner is NOT in the every-commit gate; its
control logic (journey sequencing, re-drive orchestration, matrix
completeness, assertion evaluation) is unit-tested with a fake driver in
`scripts/selftest.py`, and the live self-test runs where a device exists.
