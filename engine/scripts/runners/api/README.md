# Veldo HTTP/API journey runner (reference)

A generic, flow-first HTTP/API runner: it drives a real endpoint through a
journey of requests and asserts the response at every step. A passing run is
evidence the API behaves, not merely that a port answered. It is the API peer
of the web and mobile journey runners, and it uses only the Python standard
library (`urllib`), so there is nothing to install.

## Use

```
veldo_api_runner.py <journey.json> [base_url]     # exit 0 = every step passed
test_api_runner.sh                               # self-contained regression
```

`[base_url]` (or the `BASE_URL` environment variable) overrides the journey's
`base_url`, so the same journey runs against local, staging, or a test server
unchanged. `test_api_runner.sh` stands up the bundled stdlib mock server and
drives both fixtures against it, so the whole demonstration runs with no setup.

## Journey format

```json
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
```

Each step names a `method`, `path`, optional `headers` and `body` (a JSON
value is serialized and sent as `application/json` unless a content type is
set; a string body is sent verbatim), and an `expect` block. Every `expect`
key is optional and all present keys must hold:

- `status` - exact HTTP status code.
- `max_seconds` - latency budget for the request.
- `json_keys` - top-level keys that must be present in the JSON body.
- `json_equals` - `{top_level_key: value}` that must match exactly.
- `json_path_present` - dotted paths that must resolve; an integer segment
  indexes into a list (for example `data.items.0.id`).
- `json_path_equals` - `{dotted_path: value}` that must resolve and match.

A 4xx or 5xx is a real, assertable response (a journey may expect an error
status). A failed assertion stops the journey and exits 1 with the failing
step and every failed assertion named: later steps usually depend on earlier
state, so they are unproven once one breaks, and a runner that pressed on and
reported green would be worse than none.

The `fixtures/` pair demonstrates both outcomes against `mock_server.py`:
`pass.journey.json` (a GET health check and a POST echo, every assertion kind
green) and `fail.journey.json` (asserts status 404 where the server returns
200, so the run fails with the mismatch named).

## Why it is a reference

It ships working and self-tested, but a repository wires it to ITS endpoint
and ITS journeys, then points the gate's `contract` (or `integration`) slot at
it. The runner's control logic - request building, the JSON-path resolver, and
every assertion kind - is unit-tested in `scripts/selftest.py` against an
in-process stdlib server, so the every-commit gate proves the logic with no
external service. The veldo home repository has no HTTP surface of its own, so
it does not run the runner in its own gate; it ships it for repos that do.
