# Veldo authorization runner (reference)

A generic authorization runner: it drives a real endpoint as more than one
identity and asserts the boundary between them. The owner reaches their own
resource, and no other identity can. It is the authorization peer of the
HTTP/API journey runner, and it uses only the Python standard library
(`urllib`), so there is nothing to install.

Authorization defects (cross-tenant reads, insecure direct object references)
are among the most common and most damaging product bugs, and they are
invisible to a runner that only exercises the happy path as one user.

## Use

```
veldo_auth_runner.py <journey.json> [base_url]     # exit 0 = every check held
test_auth_runner.sh                               # self-contained regression
```

`[base_url]` (or the `BASE_URL` environment variable) overrides the journey's
`base_url`, so the same journey runs against local, staging, or a test server
unchanged. `test_auth_runner.sh` stands up the bundled stdlib mock server and
drives both fixtures against it, so the whole demonstration runs with no setup.

## Journey format

```json
{
  "name": "owner-scoped orders",
  "base_url": "https://api.example.test",
  "timeout": 10,
  "identities": {
    "alice": {"headers": {"Authorization": "Bearer alice-token"}},
    "bob": {"headers": {"Authorization": "Bearer bob-token"}}
  },
  "checks": [
    {
      "name": "owner reads own order",
      "as": "alice",
      "request": {"method": "GET", "path": "/orders/ord-1"},
      "expect": "allow",
      "allow_status": [200],
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
```

An `identities` map names the request headers that establish each identity
(a bearer token, a cookie, or a signed header all reduce to "these headers make
the request this identity"). Each `check` drives one `request` as the named
identity (`as`; omit it for an anonymous caller) with the identity headers
merged with any check-level `headers` (the check wins), and declares an
authorization `expect`:

- `allow` - the identity must be authorized. By default any 2xx passes; pin
  `allow_status` to require exact codes. `body_must_contain` names owner data
  that must appear, so an empty 200 does not masquerade as success.
- `deny` - the identity must be refused. Any 2xx response is an authorization
  bypass and fails on its own; otherwise the status must fall in `deny_status`
  (default `401, 403, 404`). `body_must_not_contain` names owner data that must
  NOT appear - any occurrence is a cross-tenant leak, checked even on a proper
  denial status.

`max_seconds` is an optional per-request latency budget. A failed check stops
the run and exits 1 with the failing check and every failed assertion named;
a runner that pressed on past an authorization bypass and reported green would
be worse than none.

The `fixtures/` pair demonstrates both outcomes against `mock_server.py`, whose
`/orders/<id>` resource enforces owner-scoping (owner 200, other user 403,
anonymous 401) and whose `/leaky/orders/<id>` resource is deliberately
vulnerable (no owner check). `pass.journey.json` asserts owner-allow,
cross-tenant-deny, and anonymous-deny against the secure resource and passes;
`fail.journey.json` points the same cross-tenant deny check at the vulnerable
resource, so the runner catches the 2xx bypass and the leaked owner data and
fails with the violation named.

## Why it is a reference

It ships working and self-tested, but a repository wires it to ITS endpoint and
ITS identities, then points the gate's `authorization` (or `contract`) slot at
it. The runner's control logic - identity resolution, request driving, and the
authorization evaluation - is unit-tested in `scripts/selftest.py` against an
in-process stdlib server, so the every-commit gate proves the logic with no
external service. The veldo home repository has no authenticated HTTP surface of
its own, so it does not run the runner in its own gate; it ships it for repos
that do.
