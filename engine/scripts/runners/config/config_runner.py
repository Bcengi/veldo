#!/usr/bin/env python3
"""VELDO config-schema validation runner (reference).

Proves a configuration validator actually rejects bad config. It reads a fixture
(a JSON object holding a schema and a list of labeled config samples), feeds each
sample through the runner's own validator, and asserts that every sample labeled
valid is ACCEPTED and every sample labeled invalid is REJECTED with an error that
names the offending field and the reason. A validator is only trustworthy if it
says no to the config it should say no to, so a fixture whose samples all pass is
not enough on its own: the suite ships a deliberately-mislabeled fixture that must
exit 1.

  config_runner.py <fixture.json>

A fixture is a JSON object:

  {
    "name": "service config",
    "schema": {
      "allow_unknown": false,               # reject undeclared keys (default false)
      "fields": {
        "host":      {"type": "string",  "required": true},
        "port":      {"type": "integer", "required": true, "min": 1, "max": 65535},
        "mode":      {"type": "string",  "enum": ["dev", "prod"]},
        "log_level": {"type": "string",  "pattern": "^(debug|info|warn|error)$"},
        "tags":      {"type": "array",   "min": 1, "max": 5},
        "verbose":   {"type": "boolean"}
      }
    },
    "samples": [
      {"name": "full config",   "label": "valid",   "config": {"host": "h", "port": 80}},
      {"name": "no port",       "label": "invalid", "expect_field": "port",
       "config": {"host": "h"}}
    ]
  }

Field spec keys (type is required; the rest are optional constraints):
  type       one of string, integer, number, boolean, array, object, null. Type
             matching is JSON honest: a bool is not an integer, an integer
             satisfies a declared number, null is its own type.
  required   when true, a missing field is a violation (default false).
  enum       the value must be one of the listed values.
  pattern    a regular expression the string value must match (string fields).
  min / max  for a numeric value, bound the value; for a string or array value,
             bound its length.

A sample declares its config and a label ("valid" or "invalid"). An invalid
sample may also declare expect_field (the field its rejection must name) and
expect_reason (a substring its rejection must mention), so the runner proves the
config was rejected for the RIGHT reason, not merely rejected.

Exit 0 when every sample's accept/reject verdict matches its label. Exit 1 when a
verdict mismatches its label (naming the sample and the offending field), when the
schema is malformed, or when the fixture asserts nothing. The schema and the
validator are pure control logic driven over the fixtures with no external
dependency in scripts/selftest.py, so the runner is gate-tested without any live
config source.
"""
import json
import re
import sys
from pathlib import Path

ALLOWED_TYPES = {"string", "integer", "number", "boolean", "array", "object", "null"}
ALLOWED_FIELD_KEYS = {"type", "required", "enum", "pattern", "min", "max", "description"}
BOUNDED_TYPES = {"integer", "number", "string", "array"}


def json_type(value):
    """The JSON type name of a Python value, JSON honest: a bool is boolean (not
    integer), an int is integer, a float is number, null is its own type."""
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
    return "unknown"


def type_satisfies(declared, actual):
    """An observed type satisfies a declared type on an exact match, plus the one
    widening rule JSON allows: an integer satisfies a declared number."""
    if declared == actual:
        return True
    if declared == "number" and actual == "integer":
        return True
    return False


def validate_schema(schema):
    """Return a list of reasons the schema itself is malformed (empty = well
    formed). A malformed schema is a loud failure, never a silent pass: a runner
    that validates config against garbage stamps the garbage green."""
    errors = []
    if not isinstance(schema, dict):
        return ["schema must be a JSON object"]
    if "allow_unknown" in schema and not isinstance(schema["allow_unknown"], bool):
        errors.append("allow_unknown must be a boolean")
    fields = schema.get("fields")
    if not isinstance(fields, dict) or not fields:
        return errors + ["schema must declare a non-empty 'fields' object"]
    for name, spec in fields.items():
        if not isinstance(spec, dict):
            errors.append(f"field {name!r}: field spec must be an object")
            continue
        unknown = set(spec) - ALLOWED_FIELD_KEYS
        if unknown:
            errors.append(f"field {name!r}: unknown field-spec key(s) {sorted(unknown)}")
        declared = spec.get("type")
        if declared is None:
            errors.append(f"field {name!r}: missing required 'type'")
        elif declared not in ALLOWED_TYPES:
            errors.append(f"field {name!r}: unknown type {declared!r} (allowed: {sorted(ALLOWED_TYPES)})")
        if "required" in spec and not isinstance(spec["required"], bool):
            errors.append(f"field {name!r}: 'required' must be a boolean")
        if "enum" in spec and (not isinstance(spec["enum"], list) or not spec["enum"]):
            errors.append(f"field {name!r}: 'enum' must be a non-empty list")
        if "pattern" in spec:
            if declared != "string":
                errors.append(f"field {name!r}: 'pattern' applies only to a string field")
            try:
                re.compile(spec["pattern"])
            except re.error as e:
                errors.append(f"field {name!r}: invalid regex pattern {spec['pattern']!r}: {e}")
        for bound in ("min", "max"):
            if bound in spec:
                if isinstance(spec[bound], bool) or not isinstance(spec[bound], (int, float)):
                    errors.append(f"field {name!r}: {bound!r} must be a number")
                elif declared not in BOUNDED_TYPES:
                    errors.append(f"field {name!r}: {bound!r} applies only to {sorted(BOUNDED_TYPES)}")
        if "min" in spec and "max" in spec and isinstance(spec["min"], (int, float)) \
                and isinstance(spec["max"], (int, float)) and spec["min"] > spec["max"]:
            errors.append(f"field {name!r}: min {spec['min']} is above max {spec['max']}")
    return errors


def validate_config(schema, config):
    """Feed one config through the validator. Returns a list of violations; each
    is {"field": <name>, "reason": <str>}. An empty list means the config is
    accepted. This is the pure predicate under test: clean on a conforming config,
    loud and field-naming on every kind of violation."""
    fields = schema.get("fields", {})
    allow_unknown = schema.get("allow_unknown", False)
    violations = []
    for name, spec in fields.items():
        declared = spec.get("type")
        if name not in config:
            if spec.get("required", False):
                violations.append({"field": name, "reason": "required field is missing"})
            continue
        value = config[name]
        actual = json_type(value)
        if not type_satisfies(declared, actual):
            violations.append({"field": name, "reason": f"expected type {declared}, got {actual}"})
            continue  # remaining constraints assume the declared type
        if "enum" in spec and value not in spec["enum"]:
            violations.append({"field": name,
                               "reason": f"value {value!r} is not one of the allowed values {spec['enum']}"})
        if "pattern" in spec and re.search(spec["pattern"], value) is None:
            violations.append({"field": name,
                               "reason": f"value {value!r} does not match pattern {spec['pattern']!r}"})
        if "min" in spec or "max" in spec:
            if actual in ("integer", "number"):
                magnitude, unit = value, "value"
            else:
                magnitude, unit = len(value), "length"
            if "min" in spec and magnitude < spec["min"]:
                violations.append({"field": name,
                                   "reason": f"{unit} {magnitude} is below the minimum {spec['min']}"})
            if "max" in spec and magnitude > spec["max"]:
                violations.append({"field": name,
                                   "reason": f"{unit} {magnitude} is above the maximum {spec['max']}"})
    if not allow_unknown:
        for name in config:
            if name not in fields:
                violations.append({"field": name, "reason": "unknown field not declared in the schema"})
    return violations


def run(fixture):
    """Drive every sample through the validator and grade its verdict against its
    label. Returns a machine-readable result. passed is False on a malformed
    schema, a fixture that asserts nothing, a bad sample label, or any sample
    whose accept/reject verdict does not match its label."""
    result = {"name": fixture.get("name"), "passed": True, "checked": 0,
              "mismatches": [], "samples": [], "error": None}

    schema = fixture.get("schema")
    schema_errors = validate_schema(schema)
    if schema_errors:
        result["passed"] = False
        result["error"] = "malformed schema: " + "; ".join(schema_errors)
        return result

    samples = fixture.get("samples")
    if not isinstance(samples, list) or not samples:
        result["passed"] = False
        result["error"] = "fixture declares no samples: a validation run with nothing to check is not proof"
        return result

    for sample in samples:
        sname = sample.get("name") or "<sample>"
        label = sample.get("label")
        if label not in ("valid", "invalid"):
            result["passed"] = False
            result["error"] = f"sample {sname!r}: label must be 'valid' or 'invalid', got {label!r}"
            return result
        if not isinstance(sample.get("config"), dict):
            result["passed"] = False
            result["error"] = f"sample {sname!r}: missing a 'config' object to validate"
            return result

        violations = validate_config(schema, sample["config"])
        accepted = not violations
        fmt = [f"field {v['field']!r}: {v['reason']}" for v in violations]
        result["checked"] += 1
        result["samples"].append({"name": sname, "label": label, "accepted": accepted, "violations": fmt})

        if label == "valid":
            if not accepted:
                result["passed"] = False
                result["mismatches"].append({"sample": sname,
                    "reason": "labeled valid but the runner REJECTED it: " + "; ".join(fmt)})
        else:  # invalid
            if accepted:
                result["passed"] = False
                result["mismatches"].append({"sample": sname,
                    "reason": "labeled invalid but the runner ACCEPTED it (the validator found no violation)"})
            else:
                ef = sample.get("expect_field")
                if ef is not None and not any(v["field"] == ef for v in violations):
                    result["passed"] = False
                    result["mismatches"].append({"sample": sname,
                        "reason": f"labeled invalid and rejected, but not for the expected field {ef!r} "
                                  f"(rejected for: {'; '.join(fmt)})"})
                er = sample.get("expect_reason")
                if er is not None and not any(er in v["reason"] for v in violations):
                    result["passed"] = False
                    result["mismatches"].append({"sample": sname,
                        "reason": f"labeled invalid and rejected, but no violation mentioned {er!r} "
                                  f"(rejected for: {'; '.join(fmt)})"})
    return result


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    fixture_path = Path(argv[1])
    try:
        fixture = json.loads(fixture_path.read_text())
    except Exception as e:
        print(f"cannot read fixture {fixture_path}: {e}")
        return 2
    result = run(fixture)
    print(f"config schema {result['name']!r}: {result['checked']} sample(s) checked")
    if result["error"]:
        print(f"FAIL - {result['error']}")
        print("config schema run FAILED")
        return 1
    if result["passed"]:
        print("config schema PASSED: every sample's verdict matched its label")
        return 0
    for m in result["mismatches"]:
        print(f"FAIL - sample {m['sample']!r}: {m['reason']}")
    print("config schema run FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
