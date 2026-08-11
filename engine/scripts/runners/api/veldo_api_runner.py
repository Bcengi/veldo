#!/usr/bin/env python3
"""VELDO HTTP/API journey runner (reference).

Drives a REAL HTTP endpoint through a journey: a sequence of requests, each
with a method, path, headers, and body, and an "expect" block asserting the
response. This is the API equivalent of the flow-first UI proof - the journey
is driven end to end and the response is asserted at every step, so a passing
run is evidence the API behaves, not merely that a port answered. A step whose
assertions fail stops the journey (later steps in a journey usually depend on
earlier state, so they are unproven from there) and the run exits 1 with the
failing step and every failed assertion named.

  veldo_api_runner.py <journey.json> [base_url]

Uses only the standard library (urllib), so a consuming repo drops it in and
points it at its own endpoint with no install. The optional [base_url] (or the
BASE_URL environment variable) overrides the journey's base_url, so the same
journey runs against local, staging, or a test server unchanged.

Journey format (JSON):
  {
    "name": "health and echo",
    "base_url": "https://api.example.test",
    "timeout": 10,
    "steps": [
      {
        "method": "GET",
        "path": "/health",
        "headers": {"Accept": "application/json"},
        "expect": {
          "status": 200,
          "max_seconds": 2,
          "json_keys": ["status", "version"],
          "json_equals": {"status": "ok"},
          "json_path_present": ["data.items.0.id"],
          "json_path_equals": {"data.count": 2}
        }
      },
      {
        "method": "POST",
        "path": "/echo",
        "body": {"ping": "hello"},
        "expect": {"status": 200, "json_path_equals": {"received.ping": "hello"}}
      }
    ]
  }

Expect block (every key optional; all present keys must hold):
  status              exact HTTP status code
  max_seconds         latency budget for the request (float seconds)
  json_keys           top-level keys that must be present in the JSON body
  json_equals         {top_level_key: value} that must match exactly
  json_path_present   dotted paths that must resolve (integer segments index
                      into lists, e.g. "data.items.0.id")
  json_path_equals    {dotted_path: value} that must resolve and match exactly

Exit 0 = every step's assertions passed. Exit 1 = a step failed (the failing
step and its failed assertions are named) or a request errored.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _get_path(obj, path):
    """Resolve a dotted JSON path. An integer segment indexes into a list.
    Returns (found, value); found is False if any segment does not resolve."""
    cur = obj
    for seg in path.split("."):
        if isinstance(cur, dict):
            if seg not in cur:
                return False, None
            cur = cur[seg]
        elif isinstance(cur, list):
            try:
                idx = int(seg)
            except ValueError:
                return False, None
            if idx < 0 or idx >= len(cur):
                return False, None
            cur = cur[idx]
        else:
            return False, None
    return True, cur


def assert_expect(expect, status, body_text, elapsed):
    """Evaluate an expect block against an observed response.

    Returns a list of failure strings; an empty list means the step passed.
    Keeping this pure (no I/O) is what makes the control logic unit-testable
    with no server, and keeps a failing assertion named rather than swallowed.
    """
    failures = []
    if not expect:
        return failures

    if "status" in expect and status != expect["status"]:
        failures.append(f"status: expected {expect['status']}, got {status}")

    if "max_seconds" in expect and elapsed > expect["max_seconds"]:
        failures.append(
            f"max_seconds: {elapsed:.3f}s exceeds budget {expect['max_seconds']}s")

    needs_json = any(k in expect for k in
                     ("json_keys", "json_equals", "json_path_present", "json_path_equals"))
    if not needs_json:
        return failures

    try:
        body = json.loads(body_text)
    except Exception as e:
        failures.append(f"json: response body is not valid JSON ({e})")
        return failures

    for key in expect.get("json_keys") or []:
        if not isinstance(body, dict) or key not in body:
            failures.append(f"json_keys: missing top-level key {key!r}")

    for key, want in (expect.get("json_equals") or {}).items():
        if not isinstance(body, dict) or key not in body:
            failures.append(f"json_equals: missing top-level key {key!r}")
        elif body[key] != want:
            failures.append(f"json_equals: {key} expected {want!r}, got {body[key]!r}")

    for path in expect.get("json_path_present") or []:
        found, _ = _get_path(body, path)
        if not found:
            failures.append(f"json_path_present: path {path!r} did not resolve")

    for path, want in (expect.get("json_path_equals") or {}).items():
        found, got = _get_path(body, path)
        if not found:
            failures.append(f"json_path_equals: path {path!r} did not resolve")
        elif got != want:
            failures.append(f"json_path_equals: {path} expected {want!r}, got {got!r}")

    return failures


def do_request(base_url, step, timeout):
    """Issue one HTTP request and return (status, body_text, elapsed).

    A 4xx/5xx is a real, assertable response (returned, not raised) so a
    journey can expect an error status. A transport failure (no server, DNS,
    timeout) raises, and the caller records the step as failed.
    """
    method = (step.get("method") or "GET").upper()
    url = base_url.rstrip("/") + "/" + str(step.get("path", "")).lstrip("/")
    data = None
    if step.get("body") is not None:
        body = step["body"]
        data = body.encode("utf-8") if isinstance(body, str) else json.dumps(body).encode("utf-8")
    headers = dict(step.get("headers") or {})
    if data is not None and not any(h.lower() == "content-type" for h in headers):
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            text = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
        text = e.read().decode("utf-8", "replace")
    elapsed = time.monotonic() - start
    return status, text, elapsed


def run(journey, base_url=None, timeout=None):
    """Drive the journey and return a machine-readable result dict.

    base_url (or journey['base_url']) is the endpoint; the argument wins so the
    same fixture can be aimed at any environment. Stops at the first failing
    step: a broken step leaves the rest of the flow unproven.
    """
    base = base_url or journey.get("base_url")
    result = {"journey": journey.get("name"), "base_url": base,
              "passed": True, "steps": [], "error": None}
    if not base:
        result["passed"] = False
        result["error"] = "no base_url (set journey.base_url or pass an override)"
        return result
    to = timeout if timeout is not None else journey.get("timeout", 10)
    for i, step in enumerate(journey.get("steps", [])):
        label = f"{i}:{(step.get('method') or 'GET').upper()} {step.get('path', '')}"
        try:
            status, text, elapsed = do_request(base, step, to)
            failures = assert_expect(step.get("expect") or {}, status, text, elapsed)
        except Exception as e:
            failures = [f"request error: {e}"]
        if failures:
            result["steps"].append({"step": label, "ok": False, "failures": failures})
            result["passed"] = False
            break
        result["steps"].append({"step": label, "ok": True})
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    journey = json.loads(Path(sys.argv[1]).read_text())
    base_url = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("BASE_URL")
    result = run(journey, base_url=base_url)
    for s in result["steps"]:
        if s["ok"]:
            print(f"PASS {s['step']}")
        else:
            print(f"FAIL {s['step']}")
            for f in s["failures"]:
                print(f"     - {f}")
    if result["error"]:
        print(f"ERROR: {result['error']}")
    if result["passed"]:
        print(f"api journey PASSED: {result['journey']}")
        return 0
    print(f"api journey FAILED: {result['journey']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
