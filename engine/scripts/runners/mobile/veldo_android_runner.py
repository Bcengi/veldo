#!/usr/bin/env python3
"""VELDO Android journey runner (reference).

Drives a REAL Android emulator or device over adb: launches the app, runs a
journey of taps and assertions, captures named states as screencaps, records
a video, and - the part mobile testing usually skips and the founder called
out - RE-DRIVES the flow through the lifecycle events that break mobile apps:
rotation, process death, background/foreground, and network loss. A flow that
passes once but breaks after the process is killed is not proven; the
re-drives are first-class, not an afterthought.

  veldo_android_runner.py <journey.json> [outdir]

Assertions come from real device state: uiautomator XML (expect_text) and the
focused window (expect_focus). A driver abstraction (AdbDriver) wraps adb so
the control logic - journey sequencing, re-drive orchestration, device-matrix
completeness - is testable with a fake driver and no device (see selftest).

Exit 0 = every asserted step AND every lifecycle re-drive passed on every
declared device profile. Exit 1 = any failure, with the failing step or
re-drive named and a failure screencap captured.
"""
import json
import subprocess
import sys
import time
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


class AdbDriver:
    """Real adb. Every method is a thin, named wrapper so a fake driver can
    stand in for tests without a device."""

    def __init__(self, serial=None):
        self.serial = serial
        base = ["adb"]
        if serial:
            base += ["-s", serial]
        self.base = base

    def _run(self, args, **kw):
        return subprocess.run(self.base + args, capture_output=True, text=True, **kw)

    def _shell(self, cmd):
        return self._run(["shell"] + cmd)

    def profile(self):
        model = self._shell(["getprop", "ro.product.model"]).stdout.strip()
        api = self._shell(["getprop", "ro.build.version.sdk"]).stdout.strip()
        return f"{model or 'unknown'}-api{api or '?'}"

    def launch(self, package, activity):
        comp = f"{package}/{activity}" if activity else package
        self._shell(["am", "start", "-n", comp])

    def stop(self, package):
        self._shell(["am", "force-stop", package])

    def kill(self, package):
        # am kill is a no-op on foreground processes; use force_stop for a real
        # process death. Kept only for background-kill scenarios.
        self._shell(["am", "kill", package])

    def force_stop(self, package):
        self._shell(["am", "force-stop", package])

    def pid(self, package):
        out = self._shell(["pidof", package]).stdout.strip()
        return out.split()[0] if out else None

    def home(self):
        self._shell(["input", "keyevent", "KEYCODE_HOME"])

    def tap(self, x, y):
        self._shell(["input", "tap", str(x), str(y)])

    def text(self, s):
        self._shell(["input", "text", s])

    def key(self, k):
        self._shell(["input", "keyevent", k])

    def rotate(self, value):
        # 0 = portrait, 1 = landscape; disable auto-rotate first so it sticks
        self._shell(["settings", "put", "system", "accelerometer_rotation", "0"])
        self._shell(["settings", "put", "system", "user_rotation", str(value)])

    def set_network(self, on):
        state = "enable" if on else "disable"
        self._shell(["svc", "wifi", state])
        self._shell(["svc", "data", state])

    def current_focus(self):
        out = self._shell(["dumpsys", "window"]).stdout
        for line in out.splitlines():
            if "mCurrentFocus" in line:
                return line.strip()
        return ""

    def ui_text(self):
        self._shell(["uiautomator", "dump", "/sdcard/veldo_ui.xml"])
        return self._shell(["cat", "/sdcard/veldo_ui.xml"]).stdout

    def screencap(self, path):
        r = self._run(["exec-out", "screencap", "-p"])
        Path(path).write_bytes(r.stdout.encode("latin-1") if isinstance(r.stdout, str) else r.stdout)

    def screencap_bytes(self, path):
        with open(path, "wb") as f:
            p = subprocess.run(self.base + ["exec-out", "screencap", "-p"], stdout=f)
        return p.returncode == 0

    def start_recording(self, remote="/sdcard/veldo_rec.mp4"):
        self._shell(["rm", "-f", remote])
        self._rec_remote = remote
        self._rec = subprocess.Popen(self.base + ["shell", "screenrecord",
                                     "--time-limit", "180", remote])
        return self._rec

    def stop_recording(self, local):
        rec = getattr(self, "_rec", None)
        if not rec:
            return False
        self._shell(["pkill", "-INT", "screenrecord"])
        try:
            rec.wait(timeout=10)
        except Exception:
            rec.terminate()
        time.sleep(1)
        r = self._run(["pull", getattr(self, "_rec_remote", "/sdcard/veldo_rec.mp4"), local])
        return r.returncode == 0 and Path(local).exists()

    def wait_boot(self, timeout=120):
        end = time.time() + timeout
        while time.time() < end:
            if self._shell(["getprop", "sys.boot_completed"]).stdout.strip() == "1":
                return True
            time.sleep(2)
        return False


def assert_step(driver, step):
    """Return (ok, detail). Assertions read real device state."""
    a = step["action"]
    if a == "expect_focus":
        foc = driver.current_focus()
        if step["value"] not in foc:
            return False, f"focus {foc!r} does not contain {step['value']!r}"
        return True, foc
    if a == "expect_text":
        xml = driver.ui_text()
        if step["value"] not in xml:
            return False, f"text {step['value']!r} not found on screen"
        return True, "found"
    return True, ""


def apply_step(driver, step, outdir, result, waiter=None):
    if waiter is None:
        waiter = SettleWaiter()
    a = step["action"]
    if a == "launch":
        driver.launch(step["package"], step.get("activity"))
        waiter.settle(step.get("settle", 2), "launch")
    elif a == "tap":
        driver.tap(step["x"], step["y"]); waiter.settle(step.get("settle", 1), "tap")
    elif a == "text":
        driver.text(step["value"]); waiter.settle(0.5, "text")
    elif a == "key":
        driver.key(step["value"]); waiter.settle(0.5, "key")
    elif a == "wait":
        waiter.settle(step.get("seconds", 1), "wait")
    elif a in ("expect_focus", "expect_text"):
        ok, detail = assert_step(driver, step)
        if not ok:
            raise AssertionError(f"{a}: {detail}")
    elif a == "state":
        f = str(Path(outdir) / f"{step['name']}.png")
        driver.screencap_bytes(f)
        result["states"].append({"name": step["name"], "file": f})
    else:
        raise ValueError(f"unknown action: {a}")


def redrive(driver, journey, kind, outdir, result, waiter=None):
    """Re-establish the app after a lifecycle event and re-assert it survived.
    This is what separates real mobile proof from a happy-path screenshot."""
    if waiter is None:
        waiter = SettleWaiter()
    pkg = journey["package"]
    act = journey.get("activity")
    try:
        if kind == "rotation":
            driver.rotate(1); waiter.settle(1, "redrive.rotation.landscape")
            driver.rotate(0); waiter.settle(1, "redrive.rotation.portrait")
        elif kind == "process_death":
            before = driver.pid(pkg)
            driver.force_stop(pkg); waiter.settle(1, "redrive.process_death.after_force_stop")
            if driver.pid(pkg):
                return False, "process_death: app still running after force-stop (not killed)"
            driver.launch(pkg, act); waiter.settle(2, "redrive.process_death.relaunch")
            after = driver.pid(pkg)
            if not after:
                return False, "process_death: app did not relaunch after being killed"
            if before and after == before:
                return False, f"process_death: pid unchanged ({before}) - not a real restart"
            result.setdefault("redrive_detail", {})["process_death"] = {"pid_before": before, "pid_after": after}
        elif kind == "background_foreground":
            driver.home(); waiter.settle(1, "redrive.background_foreground.home")
            driver.launch(pkg, act); waiter.settle(2, "redrive.background_foreground.relaunch")
        elif kind == "network_loss":
            driver.set_network(False); waiter.settle(1, "redrive.network_loss.off")
            driver.set_network(True); waiter.settle(1, "redrive.network_loss.on")
        else:
            raise ValueError(f"unknown lifecycle re-drive: {kind}")
        # after the event, the recovery assertion must still hold
        ra = journey.get("recovery_assertion")
        if ra:
            ok, detail = assert_step(driver, ra)
            if not ok:
                return False, f"after {kind}: {detail}"
        f = str(Path(outdir) / f"redrive-{kind}.png")
        driver.screencap_bytes(f)
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
                driver.screencap_bytes(fpath)
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
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    journey = json.loads(Path(sys.argv[1]).read_text())
    outdir = sys.argv[2] if len(sys.argv) > 2 else str(Path(sys.argv[1]).parent / "_out")
    driver = AdbDriver(journey.get("serial"))
    result = run(journey, driver, outdir)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
