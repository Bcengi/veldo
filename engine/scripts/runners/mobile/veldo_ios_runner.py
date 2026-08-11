#!/usr/bin/env python3
"""VELDO iOS journey runner (reference, macOS-gated).

Drives a REAL iOS simulator over `xcrun simctl`: launches the app, runs a
journey of taps and assertions, captures named states as screenshots, records
a video, and RE-DRIVES the flow through the lifecycle events that break mobile
apps: process death, background/foreground, and an interface-style change. A
flow that passes once but does not come back after the process is killed is not
proven; the re-drives are first-class, not an afterthought.

  veldo_ios_runner.py <journey.json> [outdir]

HONEST scope. This is a REFERENCE runner. It REQUIRES macOS and a booted iOS
simulator to drive live, so it is NOT run in this Linux home repository's gate.
What is gate-tested here is the CONTROL LOGIC - journey sequencing, re-drive
orchestration (with a provable restart), device-matrix completeness, and
first-failure-named - driven against a FakeDriver with no simulator (see
scripts/selftest.py). An adopting repo on macOS runs the same runner against a
real simulator. No live-simulator run is faked or claimed here.

What simctl can do on its own vs. what needs a bridge. simctl honestly does
boot, launch, terminate, screenshot, video recording, home-screen (SpringBoard)
backgrounding, and interface-style toggles. Coordinate taps, text entry, and
reading the live accessibility hierarchy are NOT simctl features: they need an
accessibility bridge (an XCUITest runner or WebDriverAgent) on the macOS host.
The SimctlDriver methods for those (tap, type_text, current_label, ui_text)
route through that bridge and say so loudly when it is absent, so a UI
assertion never passes vacuously. A driver abstraction (SimctlDriver) wraps all
of this so the control logic is testable with a fake driver and no simulator.

Exit 0 = every asserted step AND every lifecycle re-drive passed on every
declared device profile. Exit 1 = any failure, with the failing step or
re-drive named and a failure screenshot captured.
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


class SettleWaiter:
    """An UNCONDITIONAL settle: a wait whose length was CHOSEN, injected so a
    caller can decide it instead of paying it.

    The defaults ARE the real clock and the real sleep, so a runner constructed
    without arguments waits exactly as it did before this seam existed.

    THIS SEAM IS FOR SETTLES ONLY. A wait that exists because some OTHER AGENT
    must reach a state - a device property becoming true, an external recorder
    flushing its file - is a CONDITION wait. It belongs in the driver class as a
    predicate loop against the real time module and must never be routed through
    here, because skipping it would skip the state change the runner then reads.
    There is deliberately no predicate, no deadline and no poll primitive here,
    so a condition wait cannot be expressed in this API at all.
    """

    def __init__(self, clock=time.monotonic, sleep=time.sleep, record=None):
        self._clock = clock
        self._sleep = sleep
        self._record = record

    def settle(self, seconds, reason):
        """Wait `seconds` for the interface to settle after `reason`."""
        if self._record is None:
            self._sleep(seconds)
            return
        t0 = self._clock()
        self._sleep(seconds)
        self._record(reason, seconds, t0, self._clock())


class SimctlDriver:
    """Real `xcrun simctl` (plus an accessibility bridge for tap/type/UI reads).
    Every method is a thin, named wrapper so a fake driver can stand in for
    tests without a simulator."""

    def __init__(self, udid=None, a11y_url=None):
        # udid of a booted simulator, or "booted" to target the sole booted one.
        self.udid = udid or "booted"
        # base URL of an accessibility bridge (XCUITest runner / WebDriverAgent)
        # on the macOS host; required for tap, type, and UI-state assertions.
        self.a11y_url = a11y_url
        self._token = None

    def _run(self, args, **kw):
        return subprocess.run(["xcrun", "simctl"] + args, capture_output=True, text=True, **kw)

    def _need_bridge(self, what):
        if not self.a11y_url:
            raise RuntimeError(
                f"{what} needs an accessibility bridge (XCUITest/WebDriverAgent) "
                "on macOS; set a11y_url to its base endpoint")

    def boot(self):
        # Idempotent: booting an already-booted device is not an error here.
        self._run(["boot", self.udid])

    def profile(self):
        # Device name + iOS runtime for the target udid, e.g. "iPhone-15-iOS-17-0".
        out = self._run(["list", "devices", "--json"]).stdout
        try:
            data = json.loads(out)
        except Exception:
            return "unknown"
        for runtime, devices in (data.get("devices") or {}).items():
            for dev in devices or []:
                is_target = dev.get("udid") == self.udid or (
                    self.udid == "booted" and dev.get("state") == "Booted")
                if is_target:
                    ver = runtime.split(".")[-1].replace("iOS-", "iOS-")
                    name = str(dev.get("name", "unknown")).replace(" ", "-")
                    return f"{name}-{ver}"
        return "unknown"

    def launch(self, bundle_id):
        # `simctl launch` prints "<bundle_id>: <pid>"; the pid is the launch
        # token that proves a restart. Launching an already-running app returns
        # its existing pid (no restart), which is exactly how a no-op terminate
        # is caught: the token does not change.
        out = self._run(["launch", self.udid, bundle_id]).stdout
        token = out.strip().split(":")[-1].strip()
        self._token = token or None
        return self._token

    def launch_token(self):
        return self._token

    def terminate(self, bundle_id):
        self._run(["terminate", self.udid, bundle_id])

    def home(self):
        # Background the foreground app by bringing up the home screen. A true
        # hardware home-button press needs the accessibility bridge; launching
        # SpringBoard (the iOS home screen) is the simctl-only equivalent.
        self._run(["launch", self.udid, "com.apple.springboard"])

    def set_appearance(self, mode):
        # mode is "light" or "dark"; a real, simctl-native trait change.
        self._run(["ui", self.udid, "appearance", mode])

    def tap(self, x, y):
        self._need_bridge("tap")
        self._bridge_post("/tap", {"x": x, "y": y})

    def type_text(self, s):
        self._need_bridge("type")
        self._bridge_post("/type", {"text": s})

    def current_label(self):
        # Accessibility label of the frontmost element. Requires the bridge.
        self._need_bridge("expect_label")
        return self._bridge_get("/frontmost")

    def ui_text(self):
        # Full accessibility source of the current screen. Requires the bridge.
        self._need_bridge("expect_text")
        return self._bridge_get("/source")

    def _bridge_get(self, path):
        with urllib.request.urlopen(self.a11y_url.rstrip("/") + path, timeout=10) as r:
            return r.read().decode("utf-8", "replace")

    def _bridge_post(self, path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.a11y_url.rstrip("/") + path, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read().decode("utf-8", "replace")

    def screenshot(self, path):
        # simctl can screenshot with no bridge, so a failure screenshot is
        # always capturable.
        r = self._run(["io", self.udid, "screenshot", str(path)])
        return r.returncode == 0 and Path(path).exists()

    def start_recording(self, local="/tmp/veldo_ios_rec.mp4"):
        self._rec_path = local
        self._rec = subprocess.Popen(["xcrun", "simctl", "io", self.udid,
                                      "recordVideo", local])
        return self._rec

    def stop_recording(self, local):
        rec = getattr(self, "_rec", None)
        if not rec:
            return False
        rec.send_signal(2)  # SIGINT stops recordVideo cleanly and flushes the file
        try:
            rec.wait(timeout=10)
        except Exception:
            rec.terminate()
        src = getattr(self, "_rec_path", local)
        if src != local and Path(src).exists():
            Path(local).write_bytes(Path(src).read_bytes())
        return Path(local).exists()


def assert_step(driver, step):
    """Return (ok, detail). Assertions read real device state via the bridge."""
    a = step["action"]
    if a == "expect_label":
        label = driver.current_label()
        if step["value"] not in label:
            return False, f"label {label!r} does not contain {step['value']!r}"
        return True, label
    if a == "expect_text":
        src = driver.ui_text()
        if step["value"] not in src:
            return False, f"text {step['value']!r} not found in accessibility source"
        return True, "found"
    return True, ""


def apply_step(driver, step, outdir, result, waiter=None):
    if waiter is None:
        waiter = SettleWaiter()
    a = step["action"]
    if a == "launch":
        driver.launch(step["bundle_id"]); waiter.settle(step.get("settle", 2), "launch")
    elif a == "tap":
        driver.tap(step["x"], step["y"]); waiter.settle(step.get("settle", 1), "tap")
    elif a == "type":
        driver.type_text(step["value"]); waiter.settle(0.5, "type")
    elif a == "wait":
        waiter.settle(step.get("seconds", 1), "wait")
    elif a in ("expect_label", "expect_text"):
        ok, detail = assert_step(driver, step)
        if not ok:
            raise AssertionError(f"{a}: {detail}")
    elif a == "state":
        f = str(Path(outdir) / f"{step['name']}.png")
        driver.screenshot(f)
        result["states"].append({"name": step["name"], "file": f})
    else:
        raise ValueError(f"unknown action: {a}")


def redrive(driver, journey, kind, outdir, result, waiter=None):
    """Re-establish the app after a lifecycle event and re-assert it survived.
    This is what separates real mobile proof from a happy-path screenshot."""
    if waiter is None:
        waiter = SettleWaiter()
    bundle = journey["bundle_id"]
    try:
        if kind == "process_death":
            before = driver.launch_token()
            driver.terminate(bundle); waiter.settle(1, "redrive.process_death.after_terminate")
            after = driver.launch(bundle); waiter.settle(2, "redrive.process_death.relaunch")
            if not after:
                return False, "process_death: app did not relaunch after terminate"
            if before is not None and after == before:
                return False, f"process_death: launch token unchanged ({before}) - not a real restart"
            result.setdefault("redrive_detail", {})["process_death"] = {
                "token_before": before, "token_after": after}
        elif kind == "background_foreground":
            driver.home(); waiter.settle(1, "redrive.background_foreground.home")
            driver.launch(bundle); waiter.settle(2, "redrive.background_foreground.relaunch")
        elif kind == "appearance":
            driver.set_appearance("dark"); waiter.settle(1, "redrive.appearance.dark")
            driver.set_appearance("light"); waiter.settle(1, "redrive.appearance.light")
        else:
            raise ValueError(f"unknown lifecycle re-drive: {kind}")
        # after the event, the recovery assertion must still hold
        ra = journey.get("recovery_assertion")
        if ra:
            ok, detail = assert_step(driver, ra)
            if not ok:
                return False, f"after {kind}: {detail}"
        f = str(Path(outdir) / f"redrive-{kind}.png")
        driver.screenshot(f)
        result["states"].append({"name": f"redrive-{kind}", "file": f})
        return True, "survived"
    except Exception as e:
        return False, f"{kind}: {e}"


def run(journey, driver, outdir, waiter=None):
    if waiter is None:
        waiter = SettleWaiter()
    Path(outdir).mkdir(parents=True, exist_ok=True)
    result = {"journey": journey["name"], "passed": True, "device_profile": None,
              "steps": [], "redrives": [], "states": [], "matrix": {}, "error": None}
    result["device_profile"] = driver.profile()
    recording = False
    try:
        driver.start_recording()
        recording = True
    except Exception:
        recording = False

    # device-matrix completeness: every declared profile must be covered
    declared = journey.get("device_profiles") or [result["device_profile"]]
    covered = result["device_profile"]
    result["matrix"] = {p: (p == covered) for p in declared}
    missing = [p for p, done in result["matrix"].items() if not done]

    try:
        for i, step in enumerate(journey.get("steps", [])):
            label = f"{i}:{step['action']}"
            try:
                apply_step(driver, step, outdir, result, waiter)
                result["steps"].append({"step": label, "ok": True})
            except Exception as e:
                result["steps"].append({"step": label, "ok": False, "detail": str(e)})
                result["passed"] = False
                fpath = str(Path(outdir) / f"FAILURE-step-{i}.png")
                driver.screenshot(fpath)
                result["states"].append({"name": f"FAILURE-step-{i}", "file": fpath})
                break
        if result["passed"]:
            for kind in journey.get("lifecycle_redrives", []):
                ok, detail = redrive(driver, journey, kind, outdir, result, waiter)
                result["redrives"].append({"kind": kind, "ok": ok, "detail": detail})
                if not ok:
                    result["passed"] = False
    except Exception as e:
        result["error"] = str(e); result["passed"] = False

    if recording:
        vid = str(Path(outdir) / "journey.mp4")
        if driver.stop_recording(vid):
            result["video"] = vid

    if missing:
        result["passed"] = False
        result["matrix_missing"] = missing

    Path(outdir, "result.json").write_text(json.dumps(result, indent=2))
    return result


def main():
    # A live run needs macOS and a booted simulator; on any other host this
    # will fail at the first simctl call. The home gate proves the control
    # logic via the fake driver in scripts/selftest.py, not through this path.
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    journey = json.loads(Path(sys.argv[1]).read_text())
    outdir = sys.argv[2] if len(sys.argv) > 2 else str(Path(sys.argv[1]).parent / "_out")
    driver = SimctlDriver(journey.get("udid"), journey.get("a11y_url"))
    result = run(journey, driver, outdir)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
