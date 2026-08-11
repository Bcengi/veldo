# Veldo config-schema validation runner (reference)

Real proof for a configuration validator: feeds valid and invalid config samples
through the runner's own validator and asserts that valid config is ACCEPTED and
invalid config is REJECTED with an error that names the offending field and the
reason. A config validator earns trust only by saying no to the config it should
say no to; this runner pins that down so a validator that quietly accepts a
malformed field, or rejects a good one, fails the gate instead of shipping.

## Use

```
config_runner.py <fixture.json>   # exit 0 = every sample's verdict matched its label
test_config_runner.sh             # on-demand self-test over the fixture pair
```

Stdlib only, so a reviewer reruns it with no setup. The validator is
schema-driven and generic: a repo points the runner at its own schema and config
samples, or imports `validate_config` to drive its real config loader.

## Fixture format

A fixture is a JSON object with a `schema` and a list of labeled `samples`:

```json
{
  "name": "service config",
  "schema": {
    "allow_unknown": false,
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
    {"name": "full config", "label": "valid",   "config": {"host": "h", "port": 80}},
    {"name": "no port",     "label": "invalid", "expect_field": "port",
     "config": {"host": "h"}}
  ]
}
```

Field spec keys (`type` is required, the rest are optional constraints):

- `type` - one of `string`, `integer`, `number`, `boolean`, `array`, `object`,
  `null`. Type matching is JSON honest: a bool is not an integer, an integer
  satisfies a declared `number`, and `null` is its own type.
- `required` - when true, a missing field is a violation (default false).
- `enum` - the value must be one of the listed values.
- `pattern` - a regular expression the string value must match.
- `min` / `max` - for a numeric value, bound the value; for a string or array
  value, bound its length.

`allow_unknown` (default false) rejects any config key not declared in `fields`.

A sample carries its `config` and a `label` of `valid` or `invalid`. An invalid
sample may also declare `expect_field` (the field its rejection must name) and
`expect_reason` (a substring its rejection must mention), so the runner proves the
config was rejected for the RIGHT reason rather than merely rejected. A malformed
schema (an unknown type, a bad regex, `min` above `max`, an unknown field-spec
key) fails loud, and a fixture with no samples is a fixture error.

The `fixtures/` pair uses field types present in any config: `pass.schema.json`
exercises accept plus every constraint kind (required, type, enum, pattern, min,
max, length, unknown-field), all verdicts matching, so it exits 0;
`fail.schema.json` carries a sample labeled valid whose port is above the maximum,
so the runner rejects it, the verdict mismatches the label, and the run exits 1
with the offending field named.

## Why it is a reference

The runner drives a real validator, but a repo wires it to its own schema and
config samples, or imports `validate_config` to feed its actual config loader and
points the contract or config gate slot at it. Its control logic (the schema
check, the per-constraint validation, the accept/reject verdict, and the label
comparison) is unit-tested by driving the fixture pair in `scripts/selftest.py`,
so the runner is proven here without depending on any particular config format. It
is marked `reference` in `capabilities.yaml`: the veldo repo ships it but does not
run it in its own gate, because the veldo repo has no product config schema of its
own to validate.
