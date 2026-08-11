#!/usr/bin/env python3
"""VELDO integration/external-service runner (reference).

Drives an integration against a sandbox endpoint and asserts the CONTRACT of
what comes back: not just that the call answered, but that the response has the
declared shape - the expected status, the required fields present and of the
right type, and the forbidden fields absent. A payload-shape or type drift (a
number that arrives as a string, a required field that vanished, an internal
field that leaked) is a real integration defect that a happy-path "it returned
200" check sails straight past. This runner reads the contract as data and
fails loud when the response breaks it.

  veldo_integration_runner.py <journey.json> [base_url]

Uses only the standard library (urllib), so a consuming repo drops it in and
points it at its own sandbox with no install. The optional [base_url] (or the
BASE_URL environment variable) overrides the journey's base_url, so the same
journey runs against a local stub, a vendor sandbox, or a contract server
unchanged.

Journey format (JSON):
  {
    "name": "order service contract",
    "base_url": "https://sandbox.example.test",
    "timeout": 10,
    "interactions": [
      {
        "name": "create order returns a conforming record",
        "request": {
          "method": "POST",
          "path": "/order",
          "headers": {"Accept": "application/json"},
          "body": {"sku": "sku-1", "qty": 2}
        },
        "expect_status": [200, 201],
        "contract": {
          "required": {
            "id": "string",
            "amount": "number",
            "items": "array",
            "customer.email": "string",
            "items.0.qty": "integer"
          },
          "forbidden": ["internal_debug", "customer.password"]
        }
      }
    ]
  }

Each interaction performs its request, parses the JSON response body, and is
checked against its contract:

  expect_status   the response status must be in this list
  contract.required  a map of dotted-path -> declared type; each path must be
                     present AND its value must match the type
  contract.forbidden a list of dotted-paths that must NOT be present

Declared types (JSON value kinds):
  string   a JSON string          array    a JSON list
  number   an int or a float       object   a JSON object (dict)
  integer  an int (not a bool)     null     an explicit JSON null
  boolean  a JSON true/false
Note: because bool is a subclass of int in Python, an integer or number type
rejects true/false - a boolean is not an integer.

A dotted path indexes objects by key and lists by integer segment, e.g.
"customer.email" or "items.0.qty". A path is ABSENT if any segment does not
resolve; a path that resolves to an explicit null is PRESENT (its type is
"null"), so a required field set to null is present-but-wrong-type against a
non-null declared type, not silently missing.

An interaction that declares NO expect_status AND NO required AND NO forbidden
asserts nothing, which is not proof: it is a journey error and fails loud.

Exit 0 = every interaction conformed. Exit 1 = an interaction violated its
contract (the interaction and every violation are named) or a request errored.
The run stops at the first non-conforming interaction.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _is_integer(value):
    """An integer, but not a bool (bool is a subclass of int in Python)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    """An int or a float, but not a bool."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "number": _is_number,
    "integer": _is_integer,
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


def type_name(value):
    """The declared-type name of an observed value, for a clear violation."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def resolve_path(body, path):
    """Resolve a dotted path against a parsed JSON body.

    Returns (found, value). found is False if any segment does not resolve; a
    segment whose value is an explicit null resolves as (True, None), so a
    present-but-null field is distinguished from an absent one. An integer
    segment indexes into a list.
    """
    cur = body
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


def check_contract(status, body, expect_status, required, forbidden):
    """Evaluate a response against a declared contract.

    Returns a list of violation strings; an empty list means the response
    conformed. Pure (no I/O) so the contract logic is unit-testable with no
    server and every violation is named rather than swallowed. An interaction
    that asserts nothing (no expected status, no required field, no forbidden
    field) is a journey error, because a check that asserts nothing is not proof.
    """
    if not expect_status and not required and not forbidden:
        return ["asserts nothing: declare an expect_status, a required field, "
                "or a forbidden field (a check that asserts nothing is not proof)"]

    violations = []

    if expect_status and status not in expect_status:
        violations.append(f"status: expected one of {expect_status}, got {status}")

    for path, want_type in (required or {}).items():
        found, value = resolve_path(body, path)
        if not found:
            violations.append(
                f"required field {path!r} is absent (expected type {want_type})")
            continue
        checker = TYPE_CHECKS.get(want_type)
        if checker is None:
            violations.append(
                f"required field {path!r} declares unknown type {want_type!r} "
                f"(known: {', '.join(sorted(TYPE_CHECKS))})")
            continue
        if not checker(value):
            violations.append(
                f"required field {path!r} expected type {want_type}, "
                f"got {type_name(value)}")

    for path in forbidden or []:
        found, _ = resolve_path(body, path)
        if found:
            violations.append(f"forbidden field {path!r} is present")

    return violations


def do_request(base_url, request, timeout):
    """Issue one HTTP request and return (status, body): the parsed JSON body.

    A 4xx/5xx is a real, assertable response (returned, not raised) so a
    contract can expect an error status. A transport failure raises and the
    caller records the interaction as failed. A response body that is not valid
    JSON is an error, not a silent empty body.
    """
    method = (request.get("method") or "GET").upper()
    url = base_url.rstrip("/") + "/" + str(request.get("path", "")).lstrip("/")
    data = None
    if request.get("body") is not None:
        body = request["body"]
        data = body.encode("utf-8") if isinstance(body, str) else json.dumps(body).encode("utf-8")
    hdrs = dict(request.get("headers") or {})
    if data is not None and not any(h.lower() == "content-type" for h in hdrs):
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            text = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
        text = e.read().decode("utf-8", "replace")
    try:
        parsed = json.loads(text) if text.strip() else None
    except ValueError as e:
        raise ValueError(f"response body is not valid JSON ({e})")
    return status, parsed


def run(journey, base_url=None, timeout=None, caller=None):
    """Drive the contract journey and return a machine-readable result.

    The transport is a seam: caller(interaction) -> (status, body) defaults to a
    urllib request against base_url (journey['base_url'] unless overridden), so a
    selftest or an adopting repo can inject its own caller with no network. Stops
    at the first non-conforming interaction.
    """
    base = base_url or journey.get("base_url")
    result = {"journey": journey.get("name"), "base_url": base,
              "passed": True, "interactions": [], "error": None}
    to = timeout if timeout is not None else journey.get("timeout", 10)
    if caller is None:
        if not base:
            result["passed"] = False
            result["error"] = "no base_url (set journey.base_url or pass an override)"
            return result

        def caller(interaction):
            return do_request(base, interaction.get("request") or {}, to)

    interactions = journey.get("interactions") or []
    if not interactions:
        result["passed"] = False
        result["error"] = ("no interactions: a contract journey that drives nothing "
                            "asserts nothing, which is not proof (declare at least one interaction)")
        return result

    for i, interaction in enumerate(interactions):
        req = interaction.get("request") or {}
        name = interaction.get("name") or f"{(req.get('method') or 'GET').upper()} {req.get('path', '')}"
        label = f"{i}:{name}"
        expect_status = interaction.get("expect_status")
        contract = interaction.get("contract") or {}
        required = contract.get("required") or {}
        forbidden = contract.get("forbidden") or []
        try:
            status, body = caller(interaction)
            violations = check_contract(status, body, expect_status, required, forbidden)
        except Exception as e:
            violations = [f"request error: {e}"]
        if violations:
            result["interactions"].append(
                {"interaction": label, "ok": False, "violations": violations})
            result["passed"] = False
            break
        result["interactions"].append({"interaction": label, "ok": True})
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    journey = json.loads(Path(sys.argv[1]).read_text())
    base_url = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("BASE_URL")
    result = run(journey, base_url=base_url)
    for c in result["interactions"]:
        if c["ok"]:
            print(f"PASS {c['interaction']}")
        else:
            print(f"FAIL {c['interaction']}")
            for v in c["violations"]:
                print(f"     - {v}")
    if result["error"]:
        print(f"ERROR: {result['error']}")
    if result["passed"]:
        print(f"integration contract journey PASSED: {result['journey']}")
        return 0
    print(f"integration contract journey FAILED: {result['journey']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
