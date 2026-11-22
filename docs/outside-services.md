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

## Service-owned calls

The tracker mirror and initialization, repository provisioning, landing transport,
owner channel and request doorbell run on the service side of the outside gate.
Their credentials are `keychain:<name>` references. Environment, file and literal
references are refused as `invalid_input:control_plane_credential:<caller>:<scheme>`
before that source is read. A run cannot inherit the service's process binding.
Messages and files sent through the owner's activated channel require no additional
per-call approval; channel enrollment and activation still apply.

Tracker routing and doorbell settings belong in the installation repository's
`installation.yaml`, for example:

```yaml
tracker_routing:
  schema: veldo.tracker/v1
  routing: {mechanism: label, label_prefix: 'repo:'}
  repos: [{id: example, tracker: issues, project: EX}]
  trackers:
    issues:
      kind: jira-cloud
      base_url: https://issues.example.com
      email: owner@example.com
      token_ref: keychain:tracker
doorbell:
  origin: https://api.telegram.org
  chat_id: 123456
  token_ref: keychain:doorbell
```

Only a whole commit accepted by the installation loader becomes live. An invalid
commit leaves the previous routing in force. Neither a product `trackers.json`,
an uncommitted installation edit nor a state-root tracker file supplies routing.
The shipped tracker example names no site.

The tracker CLI sends an owner-signed request to the running service. Its `mirror`,
`jira init` and `jira snapshot` commands take `--principal`, `--key` and optionally
`--host-trust` and `--repo-root`; `--dry-run` asks the service for a preview using
accepted settings. Site, email and event-file overrides are not accepted through
this command path. The service chooses the enrolled repository.

Setup accepts an owner-channel `--token-ref keychain:<name>`. The older
`--token-file` setup input performs a one-time import into the keystore; the
installed ingress contains only the resulting reference and never reads that
file. An old ingress configuration naming a file must be migrated before restart.

`control_plane_calls.json` registers the service network modules and their
destination kinds. The static census scans unregistered modules too. Each call
records its caller, destination host, operation, result, latency and accepted
installation commit, with a unit or dispatch identifier where available. Bodies
and credentials are omitted. Counters group calls by caller and result and
credential refusals by scheme.

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
