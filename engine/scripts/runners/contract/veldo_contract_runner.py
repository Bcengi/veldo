#!/usr/bin/env python3
"""VELDO contract/schema drift runner (reference).

Freezes the shape of a payload as a VERSIONED GOLDEN contract, captures a real
payload, and proves the payload still conforms - and, crucially, signals when it
has DRIFTED: a field quietly removed, a type quietly changed, or a field quietly
added. A happy-path check that a specific field is present misses the field that
vanished and the field that changed type two releases ago. This runner compares
the WHOLE derived shape against the frozen golden, so drift is caught wherever it
happens, and it is versioned so a deliberate breaking change is a new golden
version rather than a silent surprise to a consumer.

  veldo_contract_runner.py <contract.json>

How it differs from the integration/contract runner: that runner asserts a
hand-written per-interaction contract (a listed set of required fields, types,
and forbidden fields) at a live boundary. This runner is a GOLDEN SNAPSHOT: the
full expected shape is a stored, versioned golden, and the runner detects ANY
drift from it, including removals and additions a hand-written required-field
list never enumerated.

The payload is captured through a PRODUCER seam: a callable returning the
payload. This reference defaults to the contract's captured fixture block, so the
runner is replayable with no live producer. An adopting repo passes
producer=its own callable (which calls its real service) unchanged.

Contract format (JSON):
  {
    "name": "order payload",
    "version": "v1",
    "strict": true,
    "schema": {"id": "integer", "total": "number", "items": "array",
               "items[].sku": "string", "customer": "object",
               "customer.name": "string"},
    "captured": {"id": 1, "total": 9.5, "items": [{"sku": "A1"}],
                 "customer": {"name": "sample"}}
  }

The golden schema maps dotted field paths to JSON type names. Nested objects
recurse by key (customer.name), and list element shapes are derived under a
path[] segment (items[].sku), so a typed field inside a list is checked. Type
derivation is JSON-honest: a bool is not an integer or a number, an integer is a
number (an actual integer satisfies a golden number), null is its own type, and
objects and arrays are distinguished.

Drift kinds:
  removed        a golden field is absent from the captured payload (breaking)
  type_changed   a field's captured type does not satisfy the golden type
                 (breaking)
  added          a field is in the captured payload but not the golden; breaking
                 only when the contract is strict, tolerated otherwise

Exit 0 = no breaking drift. Exit 1 = each breaking drift named (path and kind),
a capture error, or an empty golden schema (a contract that asserts nothing is
not proof).
"""
import json
import sys
from pathlib import Path


def json_type(v):
    """The JSON-honest type label. bool is checked before int because a Python
    bool is a subclass of int, and a bool is neither an integer nor a number."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return "unknown"


def derive_schema(value, prefix=""):
    """Derive a flat map of dotted field paths to JSON type names. Objects
    recurse by key; a list records its container type and derives its element
    shape (from the first element) under a path[] segment. The root value itself
    is not recorded (only its named descendants)."""
    schema = {}
    if prefix:
        schema[prefix] = json_type(value)
    if isinstance(value, dict):
        for k in sorted(value.keys()):
            child = f"{prefix}.{k}" if prefix else str(k)
            schema.update(derive_schema(value[k], child))
    elif isinstance(value, list) and value:
        elem = f"{prefix}[]" if prefix else "[]"
        schema.update(derive_schema(value[0], elem))
    return schema


def type_satisfies(golden_type, actual_type):
    """An actual type satisfies a golden type when they match, or when the golden
    is number and the actual is integer (an integer is a number). Every other
    difference is drift."""
    if golden_type == actual_type:
        return True
    if golden_type == "number" and actual_type == "integer":
        return True
    return False


def diff_contract(golden, actual):
    """Compare the golden schema to a derived actual schema. Returns a list of
    drift dicts {path, kind, detail}; kind is removed, type_changed, or added.
    Whether a drift is breaking is decided by the caller (added is breaking only
    under a strict contract)."""
    drifts = []
    for path in sorted(golden):
        gtype = golden[path]
        if path not in actual:
            drifts.append({"path": path, "kind": "removed",
                           "detail": f"golden field {path!r} ({gtype}) is absent from the captured payload"})
        elif not type_satisfies(gtype, actual[path]):
            drifts.append({"path": path, "kind": "type_changed",
                           "detail": f"field {path!r}: golden {gtype}, captured {actual[path]}"})
    for path in sorted(actual):
        if path not in golden:
            drifts.append({"path": path, "kind": "added",
                           "detail": f"field {path!r} ({actual[path]}) is not in the golden contract"})
    return drifts


def run(contract, payload=None, producer=None):
    """Capture a payload, derive its schema, and diff it against the versioned
    golden. producer() is the capture seam; it defaults to the contract's
    captured fixture block so the runner is replayable with no live producer.
    Returns a machine-readable result; passed is False on any breaking drift, a
    capture error, or an empty golden schema."""
    result = {"contract": contract.get("name"), "version": contract.get("version"),
              "strict": bool(contract.get("strict")), "passed": True,
              "drifts": [], "breaking": [], "error": None}
    golden = contract.get("schema") or {}
    if not golden:
        result["passed"] = False
        result["error"] = "contract asserts nothing: an empty golden schema is not proof"
        return result

    if payload is None:
        if producer is not None:
            try:
                payload = producer()
            except Exception as e:
                result["passed"] = False
                result["error"] = f"producer error: {e}"
                return result
        else:
            payload = contract.get("captured")
            if payload is None:
                result["passed"] = False
                result["error"] = "no payload captured and no producer given"
                return result

    actual = derive_schema(payload)
    drifts = diff_contract(golden, actual)
    breaking = [d for d in drifts
                if d["kind"] in ("removed", "type_changed")
                or (d["kind"] == "added" and result["strict"])]
    result["drifts"] = drifts
    result["breaking"] = breaking
    if breaking:
        result["passed"] = False
    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    contract = json.loads(Path(sys.argv[1]).read_text())
    result = run(contract)
    print(f"contract {result['contract']!r} version {result['version']!r} "
          f"(strict={result['strict']})")
    for d in result["drifts"]:
        breaking = d in result["breaking"]
        tag = "BREAKING" if breaking else "note"
        print(f"  {tag} {d['kind']}: {d['detail']}")
    if result["error"]:
        print(f"FAIL - {result['error']}")
    if result["passed"]:
        print("contract PASSED: no breaking drift")
        return 0
    print("contract FAILED: breaking drift or capture error")
    return 1


if __name__ == "__main__":
    sys.exit(main())
