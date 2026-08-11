# Veldo iOS journey runner (reference, macOS-gated)

Real mobile UI proof for iOS: drives a booted iOS simulator over `xcrun simctl`
through a journey, asserts against live device state, captures named states as
screenshots and the whole run as a video, and RE-DRIVES the flow through the
lifecycle events that actually break mobile apps. A flow that works once but
does not come back after the process is killed is not proven here. It is the
iOS sibling of the Android journey runner and mirrors its structure.

## Reference-honest, macOS-gated

This runner REQUIRES macOS and a booted iOS simulator to drive live. The Veldo
home repository is Linux with no macOS and no simulator, so the runner is NOT
run in the home gate. What the home gate proves is the runner's CONTROL LOGIC -
journey sequencing, lifecycle re-drive orchestration (with a provable restart),
device-matrix completeness, and first-failure-named - by driving `run()`
against a FAKE driver with no simulator (see `scripts/selftest.py` and
`test_ios_runner.sh`). No live-simulator run is faked or claimed on Linux. An
adopting repo on macOS points the runner at its own app and a booted simulator.

## Use

```
veldo_ios_runner.py <journey.json> [outdir]   # exit 0 = flow + all re-drives pass
test_ios_runner.sh                           # control-logic self-test (fake driver, no macOS)
```

`test_ios_runner.sh` runs on any host: it drives the runner with an in-file fake
driver and never shells out to `xcrun`. Driving a real simulator needs macOS and
the Xcode command-line tools (`xcrun simctl`).

## What simctl does vs. what needs a bridge

`xcrun simctl` honestly does: boot, launch, terminate, screenshot, video
recording, home-screen (SpringBoard) backgrounding, and interface-style toggles
(light and dark). Coordinate taps, text entry, and reading the live
accessibility hierarchy are NOT simctl features: they need an accessibility
bridge (an XCUITest runner or WebDriverAgent) on the macOS host. The driver
methods for those (`tap`, `type_text`, `current_label`, `ui_text`) route through
that bridge (its base URL is the journey's `a11y_url`) and fail loudly when it
is absent, so a UI assertion never passes vacuously.

## Journey format

```json
{
  "name": "checkout survives the lifecycle",
  "bundle_id": "com.example.app",
  "udid": "booted",
  "a11y_url": "http://127.0.0.1:8100",
  "device_profiles": ["iPhone-15-iOS-17-0"],
  "recovery_assertion": {"action": "expect_label", "value": "HomeScreen"},
  "steps": [
    {"action": "launch", "bundle_id": "com.example.app"},
    {"action": "tap", "x": 200, "y": 640},
    {"action": "expect_text", "value": "Order placed"},
    {"action": "state", "name": "confirmation"}
  ],
  "lifecycle_redrives": ["process_death", "background_foreground", "appearance"]
}
```

Actions: `launch`, `tap`, `type`, `wait`, `expect_label`, `expect_text`,
`state`. After the happy path, each entry in `lifecycle_redrives` induces that
event and re-checks `recovery_assertion`, and the app must still be in a good
state:

- `process_death` terminates the app and re-launches it, and proves a REAL
  restart: the launch token (the pid `simctl launch` returns) must change, so a
  no-op terminate whose relaunch returns the same token is caught, never a
  vacuous pass.
- `background_foreground` sends the app to the home screen and re-launches it.
- `appearance` toggles the interface style (dark then light) and re-asserts.

Only the re-drives `xcrun simctl` can honestly induce are offered. Rotation and
network loss are deliberately absent: they need the accessibility bridge or
host-network control, not simctl, so offering them here would over-claim.

`device_profiles` declares the matrix the feature must cover; the runner records
the connected simulator's profile and FAILS if a declared profile is not
covered, so a partial matrix cannot pass silently.

## Why it is a reference

It drives a REAL simulator on macOS, but a repo wires it to its own app,
journeys, device matrix, and accessibility bridge. Because the home repository
is Linux with no macOS, the runner is not in the every-commit gate; its control
logic is unit-tested with a fake driver in `scripts/selftest.py`, and a repo on
macOS runs it against a live simulator.
