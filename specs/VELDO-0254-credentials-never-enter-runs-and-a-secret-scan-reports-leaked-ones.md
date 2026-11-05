---
schema: veldo.spec/v1
id: VELDO-0254
title: No outside-service credential is ever delivered into a run, a secret scan of workspaces and project trees reports any such credential it finds there, masked, so it is moved behind the outside gate, and the confined runner stays opt-in for risky work
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0251, VELDO-0252, VELDO-0253]
placement: [engine, enforcement]
protected_paths: [".veldo/secret_scan.py", "engine/.veldo/secret_scan.py", ".veldo/secret_scan_patterns.json", "engine/.veldo/secret_scan_patterns.json"]
footprint:
  - ".veldo/secret_scan.py"
  - "engine/.veldo/secret_scan.py"
  - ".veldo/secret_scan_patterns.json"
  - "engine/.veldo/secret_scan_patterns.json"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_service_projects.py"
  - "engine/.veldo/control_service_projects.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - "docs/outside-services.md"
  - "scripts/suites/*_veldo_0254_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0254-credentials-never-enter-runs-and-a-secret-scan-reports-leaked-ones.md"
  - "specs/index.md"
  - "proof/VELDO-0254/**"
behavior_bearing: true
observability:
  logs: >
    The scan writes one line per finding: the scan's trigger (run end, landing candidate, setup, command),
    the project, the file and line, the credential kind and the finding's masked form (kind, length and a
    short digest of the value), never any character of the value. It writes one summary line per scan with
    the files read and the findings. The launcher writes one line per launch naming whether it used the
    confined runner and why (opted in by the installation, the project or the dispatch).
  metrics: >
    Scans by trigger; findings by kind and trigger; findings still open; launches by runner (default or
    confined).
  traces: >
    A finding joins the scan that found it, the dispatch whose workspace it was in (when the trigger is a
    run end or a landing candidate) and the owner notice that reported it.
  error_taxonomy: >
    credential_delivery_site:<site> (a static row found a launch path that writes an outside-service
    credential into a run's files, environment or command line), secret_found:<kind> (a scan finding,
    reported masked), confined_runner_unavailable:<reason> (a launch that opted into the confined runner on
    a host that cannot provide it; only that launch is refused). No launch that did not opt in is refused
    for any confinement reason.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: no outside-service credential is ever delivered into a run, a workspace, an environment or a
      command a run executes; the engine's own model login stays where it is today. Set: every launch kind
      Veldo has (engine run, conversation turn, workflow step, project process) builds the run's files,
      environment and command line without resolving any keystore reference or reading any outside-service
      credential; an outside service is reached through the outside gate of VELDO-0251, which adds the
      credential on its side. Completeness: a static row lists every place in the engine that builds a
      run's configuration, environment or command and fails on any that resolves a keystore reference or
      reads a credential as credential_delivery_site:<site>. Rows: with canary credentials in the keystore
      for each declared fixture service, one launch of each kind on each engine the engines record names
      runs, and a scan of every file the run can read under its workspace and scratch, its environment and
      its command line finds no canary; the engine's model login is used as before.
    falsified_by: >
      Resolve one fixture service's keystore reference into a run's environment; the canary row finds it
      and the static row names the site.
  - id: AC2
    text: >
      Claim: a secret scan of workspaces and project trees reports any outside-service credential it finds,
      masked, so the owner moves it behind the gate. Set: the scan reads a run's workspace when the run ends,
      the changed files of a landing candidate before it lands, and every project tree at setup and on the
      owner's command; it detects credentials by the product's generic list of credential formats and by
      an exact match against the outside-service credentials held for the gate (compared by digest inside
      the scan process, never written out); the engine's own model login in its usual place is not a
      finding. Each finding is logged and sent to the owner through Veldo's own channel as
      secret_found:<kind> with the project, file and line and the masked form only, and the notice says to
      move the credential behind the gate. The scan reports; it does not edit files, stop runs or refuse a
      landing. Completeness: the three triggers call one scan entry; no other code reports a found
      credential. Rows: a fixture workspace holding a canary in a config file, an environment file and a
      script is reported once per occurrence at run end; a landing candidate that adds a canary is reported
      before it lands; a project tree scanned on command reports a credential of a known format; no report,
      log line or notice contains any character of a canary value; the engine login fixture is not
      reported.
    falsified_by: >
      Print the matched value in the finding line; the masking row finds canary characters in the log and
      fails.
  - id: AC3
    text: >
      Claim: runs keep today's access, and the confined runner is used only when a launch opts into it for
      risky work. Set: by default a launch starts as today, with the host's network, shared databases,
      container tooling and local and loopback services; no network fence, namespace, name resolution
      change or filesystem confinement is added. A launch uses the confined runner of VELDO-0208 only when
      the installation, the project or the dispatch marks it risky; such a launch on a host that cannot
      provide the confined runner is refused as confined_runner_unavailable:<reason>, and no other launch is
      affected. Completeness: one launcher decision reads the risky mark for every launch kind. Rows: a
      default run reaches a fixture database on host loopback and a fixture public service; a run marked
      risky starts in the confined runner; on a host without the confined runner's setup a default run
      starts and a risky run is refused by name.
    falsified_by: >
      Make the confined runner the default; the default-run row cannot reach the loopback fixture database
      and fails.
required_evidence: [unit, integration]
rollback: >
  Revert the change. The scan stops running and reporting; open findings stay in the log. Launches keep
  today's access, which this ticket does not change. No automatic rollback, retry or recovery is
  authorized.
---

## Intent

The gate protects outside services because the credentials for them live only behind it. That holds as
long as no credential is handed into a run and none is left lying in a workspace or a project tree. This
ticket makes the first a checked rule and catches the second with a scan that reports, masked, what it
finds, so the owner moves it behind the gate. Runs are not fenced: they keep today's access, and the
confined runner stays available for risky work.

## Context

- A mandatory sandbox for every run was tried in the design and withdrawn: different executions need
  different things that are not clear upfront, for example a shared database instead of a new server per
  run.
- VELDO-0251 serves outside services behind the gate with credentials held gate side and refuses a
  credential-bearing record in a run; VELDO-0257 removes the existing delivery paths.
- The confined runner exists (VELDO-0208, VELDO-0211) and is used today only for risky work.

## Design

1. One rule, checked statically and by canaries: launch paths never resolve credentials.
2. One scan entry with three triggers (run end, landing candidate, setup and command), generic credential
   formats plus digest matches against the gate's own credentials, masked findings, reports only.
3. One launcher decision for the confined runner, off unless a launch is marked risky.

## Out of scope

- Removing the existing delivery paths (VELDO-0257).
- The gate, its declarations and its check (VELDO-0251, VELDO-0252).
- Moving a found credential behind the gate automatically.
- Any network fence, namespace or engine confinement for ordinary runs.

## What the reviewer judges

- Normal use: runs build, test and query shared services as today; a credential pasted into a workspace
  file is reported to the owner, masked, and moved behind the gate.
- Threat model: a launch path added later that resolves a credential; a credential written into a
  workspace or committed in a project tree; a report that leaks the value it found.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a run that
  obtains a credential the gate never held and that matches no known format.

## Notes

VELDO-0209 is withdrawn and VELDO-0210 is a draft; neither is a dependency.

## History

2026-11-04: new draft, Telegram 39145, made every run start in the unprivileged sandbox with a gate-only
network and an engine-only model login (rulings R14, R5, R7, R13 as first written).

2026-11-05: replaced, Telegram 39154 (owner: a mandatory sandbox is highly problematic because different
executions need different things that are not clear upfront) and 39155 (lead: no mandatory sandbox;
protection comes from where the keys live). Under the revised rulings R5, R7 and R14 this ticket is now the
small one: credentials are never delivered into runs, a secret scan reports leaked ones masked, and the
confined runner stays opt-in for risky work. The sandbox launch, network namespace, model host list and
engine-only login criteria are removed; the file is renamed to match. VELDO-0210 is no longer superseded
by this ticket. Changes recorded in proof/VELDO-0254/no-sandbox-revision-2026-11-05.md.

2026-11-05: the review amendments and new tickets approved by the owner, Telegram 39157 ("Yes", to 39156). Status ready.
