#!/usr/bin/env python3
"""VELDO authorization runner (reference).

Drives a REAL endpoint as more than one identity and asserts the authorization
boundary between them: the owner reaches their own resource, and no other
identity can. Authorization defects (cross-tenant reads, insecure direct object
references) are among the most common and most damaging product bugs, and they
are invisible to a runner that only exercises the happy path as one user. This
runner takes the headers that establish each identity as given and checks what
that identity is allowed to reach.

  veldo_auth_runner.py <journey.json> [base_url]

Uses only the standard library (urllib), so a consuming repo drops it in and
points it at its own endpoint with no install. The optional [base_url] (or the
BASE_URL environment variable) overrides the journey's base_url, so the same
journey runs against local, staging, or a test server unchanged.

Journey format (JSON):
  {
    "name": "owner-scoped orders",
    "base_url": "https://api.example.test",
    "timeout": 10,
    "identities": {
      "alice": {"headers": {"Authorization": "Bearer alice-token"}},
      "bob":   {"headers": {"Authorization": "Bearer bob-token"}}
    },
    "checks": [
      {
        "name": "owner reads own order",
        "as": "alice",
        "request": {"method": "GET", "path": "/orders/ord-1"},
        "expect": "allow",
        "allow_status": [200],
        "max_seconds": 2,
        "body_must_contain": ["owner-secret"]
      },
      {
        "name": "cross-tenant read is denied",
        "as": "bob",
        "request": {"method": "GET", "path": "/orders/ord-1"},
        "expect": "deny",
        "deny_status": [403],
        "body_must_not_contain": ["owner-secret"]
      },
      {
        "name": "anonymous is rejected",
        "request": {"method": "GET", "path": "/orders/ord-1"},
        "expect": "deny"
      }
    ]
  }

A check drives one request as the named identity (its headers merged with any
check-level headers, the check winning; omit "as" for an anonymous caller) and
declares an authorization expectation:

  allow   the identity must be authorized. By default any 2xx passes; pin
          allow_status to require exact codes. body_must_contain names owner
          data that must appear, so an empty 200 does not masquerade as success.
  deny    the identity must be refused. ANY 2xx response is an authorization
          bypass and fails on its own; otherwise the status must fall in
          deny_status (default 401, 403, 404). body_must_not_contain names owner
          data that must NOT appear - any occurrence is a cross-tenant leak,
          checked even on a proper denial status.

max_seconds is an optional per-request latency budget.

Exit 0 = every check held. Exit 1 = a check failed (the failing check and every
failed assertion are named) or a request errored. The run stops at the first
failing check.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def resolve_headers(journey, check):
    """Merge the named identity's headers with the check's own headers.

    The check's headers win. Returns (headers, error): error names an unknown
    identity so a typo in "as" fails loud instead of silently going anonymous.
    A check with no "as" is an anonymous caller (identity headers empty).
    """
    identities = journey.get("identities") or {}
    name = check.get("as")
    headers = {}
    if name is not None:
        if name not in identities:
            return None, f"unknown identity {name!r} (not in journey.identities)"
        headers.update((identities[name] or {}).get("headers") or {})
    headers.update(check.get("headers") or {})
    return headers, None


def evaluate_check(check, status, body_text, elapsed):
    """Evaluate an authorization check against an observed response.

    Returns a list of failure strings; an empty list means the check held.
    Pure (no I/O) so the authorization logic is unit-testable with no server and
    a failing assertion is named rather than swallowed. The load-bearing rule is
    the deny path: a 2xx for a non-owner is a bypass by itself, and any owner
    data in the body is a cross-tenant leak.
    """
    expect = check.get("expect")
    if expect not in ("allow", "deny"):
        return [f"invalid check: 'expect' must be 'allow' or 'deny', got {expect!r}"]

    failures = []
    if "max_seconds" in check and elapsed > check["max_seconds"]:
        failures.append(
            f"max_seconds: {elapsed:.3f}s exceeds budget {check['max_seconds']}s")

    authorized = 200 <= status < 300

    if expect == "allow":
        allow_status = check.get("allow_status")
        if allow_status is not None:
            if status not in allow_status:
                failures.append(
                    f"allow_status: expected an authorized status in {allow_status}, got {status}")
        elif not authorized:
            failures.append(f"allow: expected an authorized (2xx) response, got {status}")
        for s in check.get("body_must_contain") or []:
            if s not in body_text:
                failures.append(
                    f"body_must_contain: authorized response is missing expected owner data {s!r}")
    else:  # deny
        deny_status = check.get("deny_status") or [401, 403, 404]
        if authorized:
            failures.append(
                f"authorization bypass: expected a denial in {deny_status}, got {status} "
                "(a non-owner reached the resource)")
        elif status not in deny_status:
            failures.append(f"deny_status: expected a denial in {deny_status}, got {status}")
        for s in check.get("body_must_not_contain") or []:
            if s in body_text:
                failures.append(f"cross-tenant data leak: denied response still contains {s!r}")

    return failures


def do_request(base_url, request, headers, timeout):
    """Issue one HTTP request as the resolved identity and return
    (status, body_text, elapsed).

    A 4xx/5xx is a real, assertable response (returned, not raised) so a deny
    check can read it. A transport failure raises and the caller records the
    check as failed.
    """
    method = (request.get("method") or "GET").upper()
    url = base_url.rstrip("/") + "/" + str(request.get("path", "")).lstrip("/")
    data = None
    if request.get("body") is not None:
        body = request["body"]
        data = body.encode("utf-8") if isinstance(body, str) else json.dumps(body).encode("utf-8")
    hdrs = dict(headers or {})
    if data is not None and not any(h.lower() == "content-type" for h in hdrs):
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
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
    """Drive the authorization journey and return a machine-readable result.

    base_url (or journey['base_url']) is the endpoint; the argument wins so the
    same fixture can be aimed at any environment. Stops at the first failing
    check.
    """
    base = base_url or journey.get("base_url")
    result = {"journey": journey.get("name"), "base_url": base,
              "passed": True, "checks": [], "error": None}
    if not base:
        result["passed"] = False
        result["error"] = "no base_url (set journey.base_url or pass an override)"
        return result
    to = timeout if timeout is not None else journey.get("timeout", 10)
    for i, check in enumerate(journey.get("checks", [])):
        req = check.get("request") or {}
        who = check.get("as") or "anonymous"
        name = check.get("name") or f"{(req.get('method') or 'GET').upper()} {req.get('path', '')}"
        label = f"{i}:{name} as {who} (expect {check.get('expect')})"
        headers, herr = resolve_headers(journey, check)
        if herr:
            failures = [herr]
        else:
            try:
                status, text, elapsed = do_request(base, req, headers, to)
                failures = evaluate_check(check, status, text, elapsed)
            except Exception as e:
                failures = [f"request error: {e}"]
        if failures:
            result["checks"].append({"check": label, "ok": False, "failures": failures})
            result["passed"] = False
            break
        result["checks"].append({"check": label, "ok": True})
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    journey = json.loads(Path(sys.argv[1]).read_text())
    base_url = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("BASE_URL")
    result = run(journey, base_url=base_url)
    for c in result["checks"]:
        if c["ok"]:
            print(f"PASS {c['check']}")
        else:
            print(f"FAIL {c['check']}")
            for f in c["failures"]:
                print(f"     - {f}")
    if result["error"]:
        print(f"ERROR: {result['error']}")
    if result["passed"]:
        print(f"authorization journey PASSED: {result['journey']}")
        return 0
    print(f"authorization journey FAILED: {result['journey']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
