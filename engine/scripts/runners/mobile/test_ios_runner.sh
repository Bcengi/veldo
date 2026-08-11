#!/usr/bin/env bash
# The iOS runner's CONTROL-LOGIC self-test. Unlike the Android live self-test,
# this needs NO macOS and NO simulator: it drives the runner with an in-file
# fake driver and never shells out to xcrun, so it runs on any host (the VELDO
# home repo is Linux). Driving a real simulator needs macOS + `xcrun simctl`;
# that path is exercised by an adopting repo, not here. The passing journey must
# pass and the deliberately-broken one must fail, both against the fake.
set -u
here="$(cd "$(dirname "$0")" && pwd)"

python3 - "$here" <<'PY'
import importlib.util, json, sys, tempfile
from pathlib import Path

here = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("veldo_ios", here / "veldo_ios_runner.py")
IOS = importlib.util.module_from_spec(spec); spec.loader.exec_module(IOS)


class FakeIosDriver:
    """Scripted stand-in for SimctlDriver: a launch token that changes on a real
    restart, a scripted frontmost label, screenshots written as stub files."""
    _tokctr = 900

    def __init__(self, label="HomeScreen", profile="iPhone-15-iOS-17-0"):
        self._label = label; self._profile = profile
        self._running = None; self._screen = "SpringBoard"; self.calls = []

    def profile(self): return self._profile

    def launch(self, bundle):
        self.calls.append(("launch", bundle))
        if self._running is None:
            FakeIosDriver._tokctr += 1
            self._running = str(FakeIosDriver._tokctr)
        self._screen = self._label
        return self._running

    def launch_token(self): return self._running
    def terminate(self, bundle): self.calls.append(("terminate", bundle)); self._running = None; self._screen = "SpringBoard"
    def home(self): self.calls.append(("home",)); self._screen = "SpringBoard"
    def set_appearance(self, mode): self.calls.append(("appearance", mode))
    def tap(self, x, y): self.calls.append(("tap", x, y))
    def type_text(self, s): self.calls.append(("type", s))
    def current_label(self): return self._screen if self._running else "SpringBoard"
    def ui_text(self): return f'<XCUIElementTypeStaticText label="{self._screen}"/>'
    def screenshot(self, path): Path(path).write_bytes(b"PNG"); return True
    def start_recording(self, *a): return None
    def stop_recording(self, local): return False


fail = 0
with tempfile.TemporaryDirectory() as d:
    passj = json.loads((here / "fixtures" / "ios" / "pass.journey.ios.json").read_text())
    r = IOS.run(passj, FakeIosDriver(), d + "/pass")
    if r["passed"] and len(r["redrives"]) == 3 and all(x["ok"] for x in r["redrives"]):
        print("pass journey: exit 0 (correct)")
    else:
        print("pass journey: FAIL (expected pass with all re-drives green)"); fail = 1

    failj = json.loads((here / "fixtures" / "ios" / "fail.journey.ios.json").read_text())
    r = IOS.run(failj, FakeIosDriver(), d + "/fail")
    if (not r["passed"]) and any("FAILURE" in s["name"] for s in r["states"]):
        print("fail journey: exit 1 (correct - failure caught, screenshot captured)")
    else:
        print("fail journey: FAIL (expected failure with a captured screenshot)"); fail = 1

sys.exit(fail)
PY
rc=$?

if [ "$rc" -eq 0 ]; then echo "ios runner self-test: pass"; else echo "ios runner self-test: FAIL"; fi
exit $rc
