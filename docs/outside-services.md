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

It is also checked at every launch. Runs keep the environment they inherit today, so the launcher scans what a
run is about to start with: its final environment (as the engine will receive it) and its command line, with
the same formats as the secret scan below. Whatever put a value there (the host's own environment, a literal in
an adapter's configuration, a file read into the environment) does not matter. A credential found there is
logged masked with the trigger `launch`, the owner is told, and the launch is refused by name:
`credential_delivery_site:environment:<name>` or `credential_delivery_site:command:<position>`. The engine's
own model login, where the launcher hands it over, is not a finding.

## 2. A secret scan reports credentials left in workspaces and project trees

One scan entry reads:

- the files a run added or changed in its workspace (its clone's work tree and scratch, its conversation
  directory), read once the run's end is recorded, so the scan never delays the end and does not report again
  what was there before the run;
- the changed files of a landing candidate before it lands;
- every project tree at setup, and any project tree on the owner's command:
  `python3 .veldo/secret_scan.py scan --project <name> --root <tree> [--log <file>]`.

It detects credentials by the generic credential formats listed in `.veldo/secret_scan.py` itself (so every
installed copy carries them) and by an exact
match against the credentials held for the gate, compared by digest inside the scan process and never written
out. The engine's own model login in its usual place (`.claude/.credentials.json`, `.codex/auth.json`) is not a
finding.

Each finding is `secret_found:<kind>` with the project, file and line and the masked form only: the kind, the
length and a short digest of the value, never any character of it. The scan writes one log line per finding
and one summary line per scan (files read, findings) to `secret-scan.jsonl` (the receiver configuration's
`secret_scan_log`, else under the state root, else beside the store). A setup scan that finds nothing writes
nothing, so a re-run of setup changes nothing. The running service's channel reads those logs and tells the
owner, in the enrolled chat and once per scan, of each scan that found a credential, masked, with the advice to
move it behind the gate. A scan that fails is never silent: it is logged as `secret_scan_failed` with its
trigger and the error's name, and the owner is told what was not checked. `python3 .veldo/secret_scan.py metrics --log <file>` counts
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
