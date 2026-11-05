# Outside services, credentials and runs

An outside service is anything a run reaches beyond the host: a tracker, a mail provider, a hosted database,
a paid API. Its credential lives only behind the outside gate. This page states the three rules that keep it
there and how an installation turns on the confined runner for risky work.

## 1. No credential is delivered into a run

A run is an engine run, a conversation turn, a workflow step or a project process. None of them is built with
an outside-service credential: the launcher builds a run's files, environment and command line without
resolving any keystore reference or reading any credential. A run reaches an outside service through the
outside gate, which adds the credential on its own side. The engine's own model login stays where it is.

The rule is checked statically. `python3 .veldo/secret_scan.py sites` lists every place in the launch modules
that builds a run's configuration, environment or command, and names each one that resolves a keystore
reference or reads a credential as `credential_delivery_site:<module>:<function>`.

## 2. A secret scan reports credentials left in workspaces and project trees

One scan entry reads:

- a run's workspace when the run ends (its clone's work tree and scratch, its conversation directory and its
  own run directory);
- the changed files of a landing candidate before it lands;
- every project tree at setup, and any project tree on the owner's command:
  `python3 .veldo/secret_scan.py scan --project <name> --root <tree> [--log <file>]`.

It detects credentials by the generic credential formats in `.veldo/secret_scan_patterns.json` and by an exact
match against the credentials held for the gate, compared by digest inside the scan process and never written
out. The engine's own model login in its usual place (`.claude/.credentials.json`, `.codex/auth.json`) is not a
finding.

Each finding is `secret_found:<kind>` with the project, file and line and the masked form only: the kind, the
length and a short digest of the value, never any character of it. The scan writes one log line per finding
and one summary line per scan (files read, findings) to `secret-scan.jsonl` (the receiver configuration's
`secret_scan_log`, else under the state root, else beside the store), and sends the owner one notice per scan
that says to move each credential behind the gate. `python3 .veldo/secret_scan.py metrics --log <file>` counts
scans by trigger, findings by kind and trigger, and the findings still open.

The scan reports. It does not edit files, stop runs or refuse a landing. Moving a found credential behind the
gate is the owner's step.

## 3. Runs keep today's access; the confined runner is opt-in

By default a launch starts as it always has: the host's network, shared databases, container tooling and
local and loopback services. No network fence, namespace, name resolution change or filesystem confinement is
added.

A launch starts in the confined runner only when it is marked risky, by one of:

| Mark | Where |
|:-|:-|
| Installation | receiver configuration `"risky": {"installation": true}` |
| Project | receiver configuration `"risky": {"projects": ["<project>"]}` |
| Dispatch | the dispatch's input context `"risky": true` |

The confined runner is named in the receiver configuration:

```json
"confined_runner": {"program": "<checkout>/scripts/agent_sandbox.py", "config": "<checkout>/scripts/agent_sandbox.json"}
```

A risky launch on a host that cannot provide the confined runner (none configured, its namespace helper
missing, or its own `namespace-selftest` failing) is refused as `confined_runner_unavailable:<reason>`. No other
launch is affected, and no launch that is not marked risky is ever refused for a confinement reason. Each
launch's accepted (or refused) line names the runner it used and why.
