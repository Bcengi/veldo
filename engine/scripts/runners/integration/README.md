# Veldo integration/external-service runner (reference)

A generic integration runner: it drives an integration against a sandbox
endpoint and asserts the CONTRACT of the response, not merely that the call
answered. It is the contract-conformance peer of the HTTP/API journey runner,
and it uses only the Python standard library (`urllib`), so there is nothing to
install.

A payload-shape or type drift (a number that arrives as a string, a required
field that vanished, an internal field that leaked) is a real integration
defect that a happy-path "it returned 200" check sails straight past. This
runner reads the expected contract as data and fails loud when the response
breaks it.

## Use

```
veldo_integration_runner.py <journey.json> [base_url]   # exit 0 = every interaction conformed
test_integration_runner.sh                             # self-contained regression
```

`[base_url]` (or the `BASE_URL` environment variable) overrides the journey's
`base_url`, so the same journey runs against a local stub, a vendor sandbox, or
a contract server unchanged. `test_integration_runner.sh` stands up the bundled
stdlib mock server on a free port and drives both fixtures against it, so the
whole demonstration runs with no setup.

## Journey format

```json
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
```

Each `interaction` performs its `request`, parses the JSON response body, and is
checked against its `contract`:

- `expect_status` - the response status must be in this list.
- `contract.required` - a map of dotted-path to declared type; each path must be
  present AND its value must match the type.
- `contract.forbidden` - a list of dotted-paths that must NOT be present.

Declared types are the JSON value kinds: `string`, `number` (an int or a float),
`integer` (an int, never a bool), `boolean`, `array`, `object`, and `null` (an
explicit JSON null). Because a bool is a subclass of int in Python, an `integer`
or `number` type rejects `true`/`false` - a boolean is not an integer.

A dotted path indexes objects by key and lists by integer segment, e.g.
`customer.email` or `items.0.qty`. A path is ABSENT if any segment does not
resolve; a path that resolves to an explicit null is PRESENT (its type is
`null`), so a required field set to null is present-but-wrong-type against a
non-null type, not silently missing.

An interaction that declares no `expect_status` AND no `required` AND no
`forbidden` asserts nothing, which is not proof: it is a journey error and fails
loud. A non-conforming interaction stops the run and exits 1 with the
interaction and every violation named; a runner that pressed on past a contract
violation and reported green would be worse than none.

The `fixtures/` pair demonstrates both outcomes against `mock_server.py`, whose
`/order/1` resource returns a payload that conforms to the contract and whose
`/order/broken` resource deliberately breaks it (`amount` arrives as a string,
`currency` is missing, and a forbidden `internal_debug` field is present).
`pass.journey.json` asserts the full contract against the conforming resource
and passes; `fail.journey.json` points the same kind of contract at the broken
resource, so the runner catches the wrong type, the missing required field, and
the leaked forbidden field, and exits 1 with each violation named.

## Why it is a reference

It ships working and self-tested, but a repository wires it to ITS sandbox and
ITS contract, then points the gate's `integration` (or `contract`) slot at it.
The runner's control logic - the contract check, the type matching, and the
dotted-path resolution - is unit-tested in `scripts/selftest.py` against an
in-process stdlib server, so the every-commit gate proves the logic with no
external service. The veldo home repository has no external integration of its
own to run, so it does not run the runner in its own gate; it ships it for repos
that do.
