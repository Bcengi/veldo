#!/usr/bin/env python3
"""WARP W12 dogfood: live API journey runner for the companion home.

Drives the REAL tripdesk backend (GET /api/v1/home/) as the system under test
and asserts each journey against the live response. No product code is touched;
this only exercises the running backend and reports pass/fail.

  run_companion_journeys.py [journeys.json]   (default: companion_home_journeys.json beside this file)

Exit 0 = every journey passed. Exit 1 = any journey failed, with the failure
named. Assertions supported: status, max_seconds, json_keys (top-level present),
json_equals (top-level key == value), json_path_present (dotted path present),
json_path_equals (dotted path == value). Stdlib only, so the reviewer can rerun
it with no setup.
"""
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path


def _dig(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return (False, None)
    return (True, cur)


def run_journey(base_url, j):
    url = base_url.rstrip("/") + j["path"]
    req = urllib.request.Request(url, method=j.get("method", "GET"))
    for k, v in (j.get("headers") or {}).items():
        req.add_header(k, v)
    exp = j.get("expect") or {}
    fails = []
    t0 = time.time()
    status = None
    body = None
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read()
    except Exception as e:
        return False, [f"request error: {e}"], None, 0.0
    elapsed = time.time() - t0
    try:
        body = json.loads(raw) if raw else None
    except Exception:
        body = None

    if "status" in exp and status != exp["status"]:
        fails.append(f"status {status} != expected {exp['status']}")
    if "max_seconds" in exp and elapsed > exp["max_seconds"]:
        fails.append(f"took {elapsed:.3f}s > budget {exp['max_seconds']}s")
    if "json_keys" in exp:
        missing = [k for k in exp["json_keys"] if not (isinstance(body, dict) and k in body)]
        if missing:
            fails.append(f"missing top-level keys: {missing}")
    for k, v in (exp.get("json_equals") or {}).items():
        got = body.get(k) if isinstance(body, dict) else None
        if got != v:
            fails.append(f"json[{k!r}] = {got!r} != expected {v!r}")
    for path in exp.get("json_path_present") or []:
        ok, _ = _dig(body, path)
        if not ok:
            fails.append(f"path {path} not present")
    for path, v in (exp.get("json_path_equals") or {}).items():
        ok, got = _dig(body, path)
        if not ok or got != v:
            fails.append(f"path {path} = {got!r} != expected {v!r}")
    return (len(fails) == 0), fails, status, elapsed


def main():
    here = Path(__file__).resolve().parent
    spec_path = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "companion_home_journeys.json"
    cfg = json.loads(spec_path.read_text())
    base_url = cfg.get("base_url", "http://localhost:8002")
    print(f"SUT: {cfg.get('system_under_test')}")
    print(f"base_url: {base_url}\n")
    passed = 0
    total = 0
    for j in cfg["journeys"]:
        total += 1
        ok, fails, status, elapsed = run_journey(base_url, j)
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {j['id']} ({j.get('spec')}) {j['title']}")
        print(f"       -> HTTP {status} in {elapsed:.3f}s")
        if ok:
            passed += 1
        else:
            for f in fails:
                print(f"       !! {f}")
    print(f"\n{passed}/{total} journeys passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
