---
schema: veldo.spec/v1
id: VELDO-0254
title: Every run and every process Veldo launches for a project starts in the unprivileged sandbox, its network leads only to the outside gate and to the engine's qualified model hosts, and only the engine process can read the engine's model login
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0040, VELDO-0208, VELDO-0211, VELDO-0230]
placement: [engine, enforcement, distribution]
protected_paths: ["scripts/agent_sandbox.py", "engine/scripts/agent_sandbox.py", "scripts/agent_sandbox.json", "engine/scripts/agent_sandbox.json", "scripts/veldo_userns.c", "engine/scripts/veldo_userns.c", "scripts/veldo-userns.apparmor", "engine/scripts/veldo-userns.apparmor", ".veldo/qualify.py", "engine/.veldo/qualify.py"]
footprint:
  - "scripts/agent_sandbox.py"
  - "engine/scripts/agent_sandbox.py"
  - "scripts/agent_sandbox.json"
  - "engine/scripts/agent_sandbox.json"
  - "scripts/veldo_userns.c"
  - "engine/scripts/veldo_userns.c"
  - "scripts/veldo-userns.apparmor"
  - "engine/scripts/veldo-userns.apparmor"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_engine_*.py"
  - "engine/.veldo/control_engine_*.py"
  - ".veldo/control_step_*.py"
  - "engine/.veldo/control_step_*.py"
  - ".veldo/control_service_projects.py"
  - "engine/.veldo/control_service_projects.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/qualify.py"
  - "engine/.veldo/qualify.py"
  - "engine/runtime/*-qualification.json"
  - ".veldo/runtime/*-qualification.json"
  - "docs/veldo-userns-setup.txt"
  - "scripts/suites/*_veldo_0254_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0254-every-run-starts-in-the-unprivileged-sandbox-with-a-gate-only-network.md"
  - "specs/index.md"
  - "proof/VELDO-0254/**"
behavior_bearing: true
observability:
  logs: >
    The launcher writes one line per launch: dispatch id, launch kind (engine run, conversation turn,
    workflow step, project process), the tree's init pid, the network namespace inode, the address of the
    one socket handed to the host side, the engine and version whose model hosts were allowed and the host
    list's qualification digest. It writes one line per refused attempt it can see from outside the tree
    (a tunnel to a host not in the list, an open of the login by a process that is not the engine), naming
    the process and the target, never a credential value. Setup writes one line per host prerequisite it
    checked, with the command the owner runs when one is missing.
  metrics: >
    Count launches by kind and outcome; launches refused by refusal name; refused tunnels by engine and
    host; refused login opens by engine; tree start latency.
  traces: >
    The dispatch id joins the run's execution record to its tree (init pid, namespace inode), to the host
    side of its socket and to the qualification record whose host list was in force.
  error_taxonomy: >
    sandbox_unavailable:<reason> (the namespace helper or its host setup is missing or unusable; the
    message names the owner's setup command), network_namespace_failed:<step>, launch_unconfined:<site> (a
    launch path that does not go through the sandbox, found by the static row), engine_hosts_unqualified:
    <engine>:<version> (the qualification record lists no model hosts for the pinned version),
    engine_tunnel_refused:<host>, engine_login_unconfinable:<engine>:<version> (the engine reads its login
    from a process the sandbox cannot tell from a tool child). Each refuses the launch before any engine or
    project code runs; none falls back to an unconfined start.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: every process Veldo starts for a run or a project starts inside the sandbox tree the agent
      launcher makes, and a host that cannot make that tree refuses the launch instead of running
      unconfined. Set: the engine and every tool child of a project run and of a conversation turn,
      catalog servers started inside the run, workflow step commands, and the project processes Veldo
      launches. Each goes through one launcher entry (prepared_launch, inside the dispatch's containment
      group of VELDO-0040), so its first process is the namespace's init with the child label, every
      capability set empty and no_new_privs set, under the agent profile's Landlock and seccomp grants.
      Completeness: a static row lists every place in the engine that starts a process for a dispatch and
      fails on any that does not call the launcher entry (launch_unconfined:<site>); there is no switch that
      starts a run unconfined. Setup and every launch check the namespace helper and its host setup and
      refuse by name (sandbox_unavailable:<reason>) with the owner's one-time setup command when either is
      missing. Rows: one launch of each kind on each engine the engines record names reports PID 1 as the
      init, the child label and empty capability sets; a host without the helper refuses each kind by name
      and nothing starts.
    falsified_by: >
      Start the engine worker with subprocess.Popen as the receiver does today instead of through the
      launcher entry; the each-kind row reads a host PID 1 and fails, and the static row names the site.
  - id: AC2
    text: >
      Claim: a run's network leads only to one socket the launcher hands to the host side, so nothing
      inside can reach any other address. Set: the namespace helper creates a network namespace for the
      tree holding only a loopback interface it brings up before dropping its capabilities; no other
      interface, route or DNS resolver exists inside. Before the tree is confined the launcher creates one
      listening socket on that loopback and passes its descriptor out of the tree to the host side named in
      the launch (the relay of VELDO-0251), so the socket stays in the run's namespace while its accepting
      end runs outside; the run is told only its address. Completeness: the namespace is created for every
      launch kind of AC1 by the same helper step; nothing inside the tree holds the capability to add an
      interface or a route. Rows against a fixture service on a routable address and on host loopback: a
      TCP connection by IPv4, by IPv6 and by a name, a UDP send, a raw socket, a connection to a host
      loopback port and to a host abstract Unix socket all fail and the fixture records nothing; a
      connection to the handed socket's address reaches the fixture host end.
    falsified_by: >
      Leave the tree in the host's network namespace; the direct IPv4 row reaches the fixture service and
      fails.
  - id: AC3
    text: >
      Claim: the engine reaches exactly the model hosts its pinned version is qualified for, and no other
      process in the tree reaches them. Set: the qualify command of VELDO-0230 records, for each engine
      version, the host and port pairs the engine opened during qualification as a list in the
      qualification record, and the engine adapter takes its tunnel list only from the pinned version's
      record; a version whose record lists none is refused as engine_hosts_unqualified:<engine>:<version>.
      The host side of the handed socket accepts a tunnel to a listed host only from the engine process the
      launcher started and refuses every other tunnel and every tunnel from a tool child as
      engine_tunnel_refused:<host>. Completeness: the list is read in one place for every engine the
      engines record names, including any engine added later. Rows: a qualification of a fixture engine
      records its hosts; a run of that engine reaches a listed host; a tunnel to an unlisted host, and a
      tunnel to a listed host opened by a tool child of the engine, are refused and the fixture records
      nothing; a version with an empty list refuses the launch.
    falsified_by: >
      Accept a tunnel to a listed host from any process in the tree; the tool-child tunnel row reaches the
      fixture model host and fails.
  - id: AC4
    text: >
      Claim: the engine's own model login is the only credential present where a run executes, and only the
      engine process can read it, never its tool children, with unprivileged means in a single-user setup.
      Set: the login files the launcher places in the run's scratch (the client credential files and their
      write-back of VELDO-0211) are opened only by the engine process the launcher started; an open, a copy,
      a read through /proc/<engine pid>/fd or /proc/<engine pid>/mem, and an environment read by any other
      process in the tree are refused. No other credential file, keystore item or token is placed in the
      tree. An engine version that reads its login from a process the sandbox cannot tell from a tool child
      is refused as engine_login_unconfinable:<engine>:<version>, and its runs wait for a version that does
      not. Completeness: one grant decides which process may open the login, for every engine the engines
      record names; a refreshed login is still written back after the run. Rows, on each engine: the
      engine starts and answers on its subscription; a tool child that tries each read path above is
      refused; a login refreshed during the run is written back as VELDO-0211 requires; a scan of the
      tree's readable files and environments finds no other credential.
    falsified_by: >
      Grant the login files to the whole tree, as the agent profile does today; the tool-child read row
      reads the login and fails.
required_evidence: [unit, integration]
rollback: >
  Revert the change. Runs start again in their containment group without the sandbox tree and with the
  host's network, as they do today; the qualification records keep their host lists, unused. The helper and
  its host setup stay installed and keep serving the gate and worker profiles. No automatic rollback, retry
  or recovery is authorized.
---

## Intent

The decision that every outside call goes through one gate holds only if a run has no other way out and no
credential to use if it found one. Today the factory starts its engine runs in a containment group for
resources but not in the sandbox, and the sandbox it has allows outbound TCP and lets every process read
the engine's login. This ticket makes every run start in the unprivileged sandbox with a network that
leads only to the gate and the engine's own model hosts, and with the engine's login readable by the
engine alone, so the gate of VELDO-0251 can rely on it.

## Context

- The sandbox mechanism is already on main: the namespace helper (veldo_userns.c) and its host policy,
  the user, mount and PID namespaces with the init's checks, the agent, gate and worker profiles'
  Landlock and seccomp grants, and the login write-back (VELDO-0208, VELDO-0211). The gate and worker
  profiles use it. The factory's engine launch does not: the receiver starts the engine in a containment
  group of VELDO-0040 and never calls the launcher.
- The helper unshares user, mount and PID namespaces only, and every profile allows outbound TCP and TLS.
- The agent profile copies the selected client's credential files into the scratch, where every process
  of the run can read them.
- VELDO-0251 builds the relay, the caller assertion and the gate behind the socket this ticket hands out,
  and depends on this ticket.

## Design

1. One launch entry. Every spawn site for a dispatch calls prepared_launch with the launch kind; the
   containment group wraps the launcher as it wraps the engine today.
2. Network namespace. The helper adds the network namespace to the ones it creates, brings loopback up
   while it still holds the namespace's capabilities, and the launcher creates the one listening socket
   there before confinement, passing its descriptor out over a socket pair made before the unshare.
3. Model hosts. Qualification observes the host and port pairs each engine version opens and records them;
   the adapter's tunnel list is read from the pinned record, never written in code.
4. Engine-only access. The host side of the socket and the login files each need to tell the engine
   process from its descendants. Candidate unprivileged means: a seccomp user-notification supervisor
   outside the tree that opens the login for the engine's own thread group and injects the descriptor,
   and peer identification of a tunnel's connecting process in the run's namespace. The build proves one
   with the rows; if neither holds for an engine, that engine is refused by name, never run with a
   readable login.

## Out of scope

- The relay, the caller assertion, the gate, the declarations and the check (VELDO-0251, VELDO-0252).
- Read routes for web pages, package registries and git (VELDO-0256).
- Moving the engine's model traffic behind the gate.
- A separate OS user or a privileged service.

## What the reviewer judges

- Normal use: a project unit and a conversation turn run on each engine exactly as before, inside the tree,
  and reach their model; a workflow step and a project process start inside the tree too.
- Threat model: a script opening a direct socket, resolving a name, using IPv6 or UDP, reaching a host
  loopback service or a host abstract socket; a tool child reading the engine login or opening a tunnel to
  the model host; a new engine version that adds a host; a spawn site added later that skips the launcher.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); attacks from host
  processes outside Veldo's launch path.

## Notes

VELDO-0209 is withdrawn and is not a dependency. VELDO-0210 (draft) is not a dependency either: the parts
of its mechanism this ticket uses are already on main under VELDO-0208 and VELDO-0211, and its remaining
open scope is replaced here (see History).

## History

2026-11-04: new draft, Telegram 39145, from research/veldo-plan-consistency-review-2026-11-04.md (D1, A8,
C9, C10, C12) and the lead's rulings research/veldo-plan-rulings-2026-11-04.md (R14, R5, R7, R13). Answers
which section (c) findings are recorded in proof/VELDO-0254/review-dispositions-2026-11-04.md. VELDO-0210
is superseded by this ticket: its open claim that the agent profile keeps today's capabilities, the open
outbound network and the login readable by every process of the run among them, conflicts with R5 and R7,
and its remaining purpose, a real builder running in the agent profile, is this ticket's AC1; the parts of
its mechanism already on main are reused, not specified again, and marking VELDO-0210 superseded is the
owner's call. VELDO-0251 is to depend on this ticket (R14). Standalone; no plan work item.
