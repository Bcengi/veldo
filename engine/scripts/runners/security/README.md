# Veldo security-guard runner (reference)

A generic runner for the security surface: it sends a corpus of known-hostile and
known-benign inputs at a set of security guard predicates and proves that every
hostile input is BLOCKED and every benign input is ALLOWED. A guard is only as
good as the attacks it actually stops, so a happy-path unit test that never feeds
it a real attack string is no proof. This runner drives the guard with the
attacks themselves and fails the run naming any hostile input the guard let
through. It uses only the Python standard library.

## Use

```
security_guard_runner.py <fixture.json>       # exit 0 = every input matched its label
test_security_guard_runner.sh                 # self-contained regression
```

## Fixture format

A fixture is a JSON list of cases. Each case names a guard, an input, and the
required verdict:

```json
[
  {
    "name": "cloud metadata endpoint",
    "guard": "is_ssrf_target",
    "input": "http://169.254.169.254/latest/meta-data/",
    "label": "block"
  },
  {
    "name": "a file inside the sandbox",
    "guard": "is_path_traversal",
    "input": "reports/2026/summary.txt",
    "label": "allow",
    "config": {"allowed_root": "/srv/app/data"}
  }
]
```

The `label` is the required verdict and the corpus is the source of truth: a case
labeled `block` is a hostile input the guard MUST reject, a case labeled `allow`
is a benign input the guard MUST permit. `config` (optional) is passed to the
guard so a repo tunes it per case. The runner applies the named guard, compares
its verdict to the label, and reports:

- a hostile input the guard ALLOWS is a `SECURITY BYPASS` (the dangerous failure)
- a benign input the guard BLOCKS is a `FALSE POSITIVE` (a usability failure)

Exit 0 = every case matched its label; exit 1 = at least one did not, with the
offending input and the direction named on stdout.

## The reference guards

- `is_ssrf_target` blocks a URL or host that targets an internal, loopback,
  link-local (including the `169.254.169.254` cloud metadata endpoint), private,
  or otherwise non-global address, and any non-http(s) scheme (`file:`, `gopher:`,
  `dict:`, and the like). An IP literal is classified with `ipaddress`; a bare
  hostname is blocked when it names a known-internal host (`localhost`,
  `*.internal`, and the like) and otherwise treated as public. `config.allow_hosts`
  is an explicit allowlist a repo may set to permit one named internal host.
- `is_path_traversal` blocks a path that escapes an allowed root, whether by a
  `..` traversal (`../../etc/passwd`) or by an absolute path pointing outside the
  root (`/etc/passwd`). The check is lexical (`normpath`, no filesystem access) so
  it is deterministic; `config.allowed_root` sets the sandbox root.
- `is_secret_leak` blocks text carrying a recognizable credential: an AWS-style
  access key, a Google API key, a GitHub or Slack token, a JWT, a bearer token,
  or a PEM private-key header. `config.patterns` replaces the default set so a
  repo tunes what counts as a secret for its data. Format-specific matchers are
  the reference set because they have far fewer false positives than a generic
  high-entropy heuristic.

Every fixture value here is an obviously-fake example (the canonical AWS example
key, a bare key header, a documentation IP), never a real credential.

## Fixtures

`fixtures/pass.security.json` is a correctly-labeled corpus that exercises all
three guards in both directions (SSRF targets and a public host, a traversal and
an in-root file, secrets and ordinary prose); every input matches its label, so
the runner exits 0. `fixtures/fail.security.json` is the deliberately-failing
fixture: it allowlists the cloud metadata endpoint through `config.allow_hosts`,
a config hole, while the corpus still insists that host must stay blocked, so the
hostile input slips through and the runner exits 1 naming the `SECURITY BYPASS`.

```
security_guard_runner.py fixtures/pass.security.json     # exit 0
security_guard_runner.py fixtures/fail.security.json     # exit 1
```

## Out of scope

The reference guards do no DNS resolution, so DNS rebinding and
resolve-then-connect races are a documented production concern, not something the
deterministic reference covers: a production SSRF guard must resolve the host and
re-check every resolved address, and connect only to a validated one. The
secret-leak guard matches known credential formats, not arbitrary high-entropy
strings. An adopting repo extends the corpus and the patterns for its own threats.

## Why this is a reference

The guard predicates are pure functions `(input, config) -> (blocked, reason)`
with no network or filesystem access, so their control logic (each guard's
verdict in both directions, and the runner's bypass and false-positive grading)
is unit-tested in `scripts/selftest.py` over both fixtures with no external
dependency. But the veldo home repository has no request-taking surface of its own
to guard, so the runner ships `reference`: an adopting repo wires a security gate
slot to its own guards, corpus, and patterns. It is a shipped artifact you wire
in and extend, never a check the veldo gate runs on itself.
