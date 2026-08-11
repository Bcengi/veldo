# Veldo contract/schema drift runner (reference)

A generic runner for the contract/schema surface: it freezes the shape of a
payload as a VERSIONED GOLDEN contract, captures a real payload, and proves the
payload still conforms - and signals when it has DRIFTED (a field quietly
removed, a type quietly changed, or a field quietly added). A happy-path check
that a specific field is present misses the field that vanished and the field
that changed type two releases ago. This runner compares the whole derived shape
against the frozen golden, and it is versioned so a deliberate breaking change is
a new golden version rather than a silent surprise to a consumer. It uses only
the Python standard library.

## Use

```
veldo_contract_runner.py <contract.json>   # exit 0 = no breaking drift
test_contract_runner.sh                    # self-contained regression
```

The payload is captured through a PRODUCER seam: a callable returning the
payload. This reference defaults to the contract's `captured` fixture block, so
the runner is replayable with no live producer. An adopting repo imports `run()`
and passes `producer=` its own callable (which calls its real service) unchanged.

## Contract format

```json
{
  "name": "order payload",
  "version": "v1",
  "strict": true,
  "schema": {
    "id": "integer", "total": "number", "items": "array",
    "items[].sku": "string", "customer": "object", "customer.name": "string"
  },
  "captured": {"id": 1, "total": 9.5, "items": [{"sku": "A1"}],
               "customer": {"name": "sample"}}
}
```

The golden `schema` maps dotted field paths to JSON type names. Nested objects
recurse by key (`customer.name`), and list element shapes are derived under a
`path[]` segment (`items[].sku`), so a typed field inside a list is checked. Type
derivation is JSON-honest: a bool is not an integer or a number, an integer is a
number (an actual integer satisfies a golden `number`), `null` is its own type,
and objects and arrays are distinguished.

## Drift

- `removed` - a golden field is absent from the captured payload (breaking).
- `type_changed` - a field's captured type does not satisfy the golden type
  (breaking).
- `added` - a field is in the captured payload but not the golden; breaking only
  when the contract is `strict`, tolerated otherwise. A non-strict contract
  reports an addition as a note and still fails on any removal or type change.

The `version` is recorded in the result, so a captured payload is always graded
against a pinned golden version. A contract with an empty golden `schema` asserts
nothing and is a contract error, not a vacuous pass, and a producer that raises
is a named capture error.

## How it differs from the integration/contract runner

The integration/contract runner asserts a hand-written per-interaction contract
(a listed set of required fields, types, and forbidden fields) at a live
boundary. This runner is a golden snapshot: the full expected shape is a stored,
versioned golden, and it detects ANY drift from it, including removals and
additions a hand-written required-field list never enumerated. The two are
complementary.

The `fixtures/` pair demonstrates both outcomes: `pass.contract.json` (a payload
conforming to golden v1) exits 0, and `fail.contract.json` (a payload that
dropped a field, changed a type, and added a field) exits 1 with each drift
named.

## Why it is a reference

It ships working and self-tested, but a repository wires it to ITS producer and
ITS versioned golden contracts, then points the gate's contract slot at it. The
runner's control logic - schema derivation, the drift diff, strict versus
tolerant additions, and the versioned grading - is unit-tested in
`scripts/selftest.py` with a captured fixture payload, so the every-commit gate
proves the logic with no live producer. The veldo home repository ships no
versioned payload contract of its own, so it does not run the runner in its own
gate; it ships it for repos that do.
