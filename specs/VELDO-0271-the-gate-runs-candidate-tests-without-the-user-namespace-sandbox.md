---
schema: veldo.spec/v1
id: VELDO-0271
title: The gate runs candidate tests in one leg per stage without the user-namespace sandbox, keeps its authority scripts, scope, memory limit, host lock and credential-free candidate runs, and no longer needs a root-installed helper
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0208, VELDO-0216, VELDO-0220, VELDO-0222, VELDO-0267]
placement: [enforcement]
protected_paths: ["scripts/verify.sh", "engine/scripts/verify.sh", ".veldo/policy.yaml", "scripts/gate_candidate.py", "engine/scripts/gate_candidate.py", "scripts/gate_legs.py", "engine/scripts/gate_legs.py", "scripts/gate_unconfined.json", "scripts/agent_sandbox.py", "engine/scripts/agent_sandbox.py", "scripts/agent_sandbox.json", "engine/scripts/agent_sandbox.json", "scripts/mutation_sandbox.py", "engine/scripts/mutation_sandbox.py", "scripts/gate_schedule.py", "engine/scripts/gate_schedule.py", "scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py", "scripts/reuse_worker.py", "engine/scripts/reuse_worker.py", "scripts/case_inputs.py", "engine/scripts/case_inputs.py", "scripts/propose_case_inputs.py", "scripts/mutation_case_inputs.json", "scripts/mutation_selection.json", ".veldo/reuse_evidence.py", "engine/.veldo/reuse_evidence.py", "scripts/selftest.py", "scripts/check_first_use.py", "scripts/run_scope.py", "scripts/suites/shared.py"]
footprint:
  - "scripts/verify.sh"
  - "engine/scripts/verify.sh"
  - ".veldo/policy.yaml"
  - "scripts/gate_candidate.py"
  - "engine/scripts/gate_candidate.py"
  - "scripts/gate_legs.py"
  - "engine/scripts/gate_legs.py"
  - "scripts/gate_unconfined.json"
  - "scripts/agent_sandbox.py"
  - "engine/scripts/agent_sandbox.py"
  - "scripts/agent_sandbox.json"
  - "engine/scripts/agent_sandbox.json"
  - "scripts/mutation_sandbox.py"
  - "engine/scripts/mutation_sandbox.py"
  - "scripts/veldo_userns.c"
  - "engine/scripts/veldo_userns.c"
  - "scripts/veldo-userns.apparmor"
  - "engine/scripts/veldo-userns.apparmor"
  - "docs/veldo-userns-setup.txt"
  - "scripts/gate_schedule.py"
  - "engine/scripts/gate_schedule.py"
  - "scripts/check_gate_mutations.py"
  - "engine/scripts/check_gate_mutations.py"
  - "scripts/reuse_worker.py"
  - "engine/scripts/reuse_worker.py"
  - "scripts/case_inputs.py"
  - "engine/scripts/case_inputs.py"
  - "scripts/propose_case_inputs.py"
  - "scripts/mutation_case_inputs.json"
  - "scripts/mutation_selection.json"
  - ".veldo/reuse_evidence.py"
  - "engine/.veldo/reuse_evidence.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/control_proof.py"
  - "engine/.veldo/control_proof.py"
  - "scripts/selftest.py"
  - "scripts/check_first_use.py"
  - "scripts/check_install_and_run.py"
  - "scripts/migrate_to_veldo.py"
  - "scripts/run_scope.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/**"
  - "specs/VELDO-0271-the-gate-runs-candidate-tests-without-the-user-namespace-sandbox.md"
  - "specs/index.md"
  - "proof/VELDO-0271/**"
behavior_bearing: true
observability:
  logs: >
    Each stage line names the stage only; the confined and unconfined leg names, the leg list and its
    digest are no longer printed. When the gate or factory setup finds a leftover namespace helper
    (/usr/local/lib/veldo/veldo-userns) or its AppArmor profile (/etc/apparmor.d/veldo-userns), it prints
    one report line naming each path found and the owner's removal command; the result is unchanged.
  metrics: >
    The stamp and the gate event lose the unconfined field. The unit stage's measured seconds (VELDO-0214)
    and each node's resource record (VELDO-0216, VELDO-0219) are kept in the same formats, now written by
    gate_schedule.py.
  traces: >
    None added. The case trace (scripts/case_trace.py) becomes the only record of what a mutation case
    read.
  error_taxonomy: >
    Removed: every launcher refusal (no helper, unsupported kernel, socket on a standard stream, nested
    marker), "candidate execution failed in store-denied domain", the leg refusals of run_scope.py and an
    invalid leg list. Added, report only and never red: leftover_namespace_helper. A stamp written before
    this change, with an unconfined field, still validates and is read as before.
acceptance_criteria:
  - id: AC1
    text: >
      Every required stage runs as one leg. verify.sh and gate_schedule.py start each stage's command
      through the authority's gate_candidate.py, which no longer loads or starts a launcher: it runs the
      command in the candidate root with standard input from /dev/null and every inherited descriptor
      closed. scripts/gate_legs.py and scripts/gate_unconfined.json are deleted; the leg variables
      (VELDO_GATE_LEG, VELDO_GATE_UNCONFINED, VELDO_GATE_DECLARATION), the leg selection in selftest.py and
      run_scope.py, and the stamp's unconfined field go with them. What gate_legs.py kept that is not
      confinement moves into gate_schedule.py with its record formats unchanged: the unit stage's measured
      seconds that check_first_use.py reads for its budget (VELDO-0214), the per-node resource record
      (VELDO-0216, VELDO-0219) and the pruning of old timing records. The 46 suites and row groups the
      leg list named run in the same unit stage as every other suite, including the strace rows of suites
      100 and 101 and the systemd user manager suites.
    falsified_by: >
      A new suite runs a fixture gate over a fixture repository whose unit stage holds one suite that starts
      a transient unit with systemd-run in the user manager and one that traces a child with strace: both
      are green in one stage line and the stamp has no unconfined field. A count row requires the unit
      stage to report every suite in scripts/suites/manifest.json. Registered mutations, each from a green
      baseline: (1) selftest.py skips the suites the deleted list named: the count row goes red; (2)
      gate_schedule.py stops recording the unit stage's seconds: suite 111's measured-budget row goes red;
      (3) gate_candidate.py passes the caller's standard input through: the stdin row, which runs the gate
      with a socket on standard input and requires the candidate to read end of file, goes red.
  - id: AC2
    text: >
      What is cheap and real stays and is checked. The gate runs its own scripts from the authority
      checkout (VELDO_AUTHORITY, python3 with isolated mode), never the candidate's copies; it runs inside
      its own systemd scope with the memory limit from scripts/gate_host.json and holds the host lock
      (VELDO-0220); and no credential reaches a candidate's run (VELDO-0254 to VELDO-0258): the
      environment gate_candidate.py builds carries no variable named in the installation's keystore or
      settings and none whose name matches the credential name patterns of VELDO-0254's scan, and the gate
      hands no credential file, descriptor or seeded copy to the candidate. Files the owner's account can
      read stay readable to candidate code, as they are to the builder that wrote it; restricting them, if
      the owner wants it, is Landlock on agent processes and not part of this spec.
    falsified_by: >
      Rows over a fixture repository: a candidate whose own scripts/gate_schedule.py and
      scripts/check_gate_mutations.py always pass still gets red from a failing suite, because the
      authority's copies ran; a gate started while a fixture holder keeps the host lock prints GATE: NOT
      STARTED and exits 75; the gate's scope shows the configured MemoryMax under /sys/fs/cgroup; a suite
      that prints its environment sees none of three canary credential variables set in the caller (one
      keystore name, one settings name, one pattern match such as GH_TOKEN). Registered mutations: (1)
      gate_candidate.py copies the caller's environment unfiltered: the canary row goes red; (2) verify.sh
      resolves gate_schedule.py from the candidate root: the authority row goes red.
  - id: AC3
    text: >
      The mutation stage runs without the sandbox and keeps honest reuse. check_gate_mutations.py and
      reuse_worker.py start every case's worker as a plain child in its own scope, without
      mutation_sandbox.py or agent_sandbox.py, so a case runs the same way whether the gate or a driver
      started it directly. Reuse (VELDO-0205 to VELDO-0226) stays, with one change: every case is held to
      the rules VELDO-0222 applies to an unconfined case today (a per-case snapshot of its declared inputs,
      reads taken from the trace, reuse only when every read was traced and declared), since no namespace
      enforces a declaration any more. The reuse store's records stay digest bound; the spec states plainly
      that they protect against stale and mistaken results, not against hostile candidate code, which the
      single-user model already does not claim. VELDO-0267's declaration adapts here: its canary set covers
      the one leg instead of the confined and the unconfined leg, and its full-sweep trigger list drops
      gate_legs.py and gate_unconfined.json and keeps gate_candidate.py.
    falsified_by: >
      The three suite 62 cases of VELDO-0261 run through scripts/check_teeth_mutations.py directly, the entry
      whose confined run gave invalid baselines, and each shows a green baseline and a killed mutant. A
      fixture case that reads one file it does not declare runs fresh and is never reused. Registered
      mutations: (1) reuse admits a case with an untraced read: the undeclared-read row goes red; (2) the
      worker skips the trace for cases that were confined before: the same row goes red; (3) the canary set
      in scripts/mutation_selection.json is cut below VELDO-0267's bound of six: its declaration row goes
      red.
  - id: AC4
    text: >
      Every removal is mapped and nothing needs root. Deleted, with their engine copies: agent_sandbox.py,
      agent_sandbox.json, mutation_sandbox.py, veldo_userns.c, veldo-userns.apparmor, gate_legs.py,
      gate_unconfined.json and docs/veldo-userns-setup.txt; their protected-path entries leave
      .veldo/policy.yaml. init_scaffold.py, reuse_evidence.py, case_inputs.py, check_install_and_run.py,
      migrate_to_veldo.py, check_first_use.py and control_proof.py stop naming them. Suites 102 (agent
      profile runtime), 103 (borrowed login write-back) and 104 (mutation workers in a launcher tree) are
      removed because they test only the launcher; in suites 65, 100, 101, 111, 114 and selftest.py only
      the rows that test confinement or leg selection are removed or rewritten for one leg; the five
      registered mutation cases on gate_legs.py move to the code they test in gate_schedule.py. The proof
      bundle carries a table with one line per removed suite, row and mutation case, naming the behavior it
      checked and either the row that still checks it or "confinement only". Setup, factory setup and the
      gate never run sudo, never install, call or require /usr/local/lib/veldo/veldo-userns or the AppArmor
      profile, and report a leftover install of either with the owner's removal command
      (sudo rm /usr/local/lib/veldo/veldo-userns; sudo apparmor_parser -R /etc/apparmor.d/veldo-userns; sudo
      rm /etc/apparmor.d/veldo-userns) without changing the result.
    falsified_by: >
      A scan row finds none of the deleted file names in tracked files outside specs/, proof/, plans/ and
      the history of docs/design/. A fixture host root holding a fake helper and profile gets the
      leftover_namespace_helper line from the gate and from factory setup, and both stay green; without
      them no line is printed. A sudo shim first on PATH records no call across factory setup and a full
      fixture gate. A table row requires the proof table to list every suite row and mutation case present
      on main at the base commit and absent after, by name. Registered mutations: (1) factory setup calls
      the shim: the no-sudo row goes red; (2) the gate turns the leftover report into a refusal: the
      leftover row goes red; (3) one removed row is left out of the proof table: the table row goes red.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. The legs, the leg list, the launcher, the helper source and its profile return as
  they were. This spec never touches the installed helper or profile on a host, so on a host where the
  owner has not removed them confinement works again at once; where they were removed, the restored
  docs/veldo-userns-setup.txt line reinstalls them.
---

## Intent

The gate splits every stage into a confined leg, run inside a user namespace made by a root-installed
helper, and an unconfined leg for the suites the namespace cannot serve. The owner decided builders run
unrestricted (Telegram 39154: the mandatory sandbox "proved to be highly problematic"), and the
single-user rule says Veldo never requires a separate OS user, a root-installed helper or a system service;
if protection is wanted, it is Landlock on agent processes. Candidate code is written by a builder that
already runs under the same account without confinement, so confining that code later in the gate does
not close the door it was meant to close, and it costs a large share of the gate's machinery and its
failures. This spec runs each stage as one leg and keeps the protections that are cheap and real.

## Context

Measured on main at afa292f0 and in the weight audit
(~/projects/myday/research/veldo-core-weight-audit-2026-11-07.md item 4):

- scripts/agent_sandbox.py 2,951 lines, scripts/veldo_userns.c 277, scripts/veldo-userns.apparmor 61,
  scripts/mutation_sandbox.py 127, scripts/gate_legs.py 501, scripts/gate_candidate.py 37, and
  scripts/gate_unconfined.json with 46 per-suite entries, each with an engine copy where one exists. The
  audit counts 83 commits on these files since September; every move of a suite between legs is a
  protected-file change.
- A root-owned binary, /usr/local/lib/veldo/veldo-userns, installed 2026-10-07, and an AppArmor profile in
  /etc/apparmor.d, both installed with sudo by the owner following docs/veldo-userns-setup.txt.
- gate_legs.py loads agent_sandbox.py as the confined leg's launcher; gate_candidate.py starts it with the
  gate profile for every candidate command; check_gate_mutations.py, reuse_worker.py and
  mutation_sandbox.py confine every mutation worker the same way.
- VELDO-0261's build note (proof/VELDO-0261/README.md, Still open): run through check_teeth_mutations.py
  directly, the three suite 62 cases ran confined, every dispatch launch was refused and their baselines
  were invalid. The same suite is green through the gate only because the leg list moves it out.
- gate_legs.py also carries duties that are not confinement: the unit stage seconds VELDO-0214's budget
  reads, the node resource records of VELDO-0216 and VELDO-0219, and pruning. Those move, they do not go.

What stays and why it is real: the authority checkout is the source of every gate script, so a candidate
cannot replace its own judge; the gate's scope and memory limit keep one runaway suite from taking the
host; the host lock keeps heavy runs from overlapping; and the gate hands no credential to candidate code,
which is the rule VELDO-0254 to VELDO-0258 set for every run.

## Coordination

Order: VELDO-0267 first, then this spec, then VELDO-0269.

- VELDO-0267 (mutation on changed code, ready): it lands first because its text is approved and it does
  not depend on legs. This spec then edits its protected declaration, scripts/mutation_selection.json: the
  canary set no longer has to cover a confined and an unconfined leg, and the trigger list drops
  gate_legs.py and gate_unconfined.json. If this spec lands first instead, VELDO-0267's build drops those
  two clauses as an owner-approved text change before it starts.
- VELDO-0269 (one engine copy, ready): it lands after, so the engine twins this spec deletes are gone
  before the lay-down is built, and its pair counts and protected list are re-measured from a smaller
  tree. If VELDO-0269 lands first, this spec deletes the engine/ files only and its footprint's root
  entries become laid files.
- VELDO-0254 (in landing-b, not on main): its AC3 names the confined runner of VELDO-0208 for launches
  marked risky. With the launcher gone such a launch is refused as
  confined_runner_unavailable:no_launcher, which AC3 already defines; default launches are unaffected.
  A Landlock-only runner, if the owner wants one, is a later spec.
- myday's builder runners (scripts/claude_work.sh, scripts/codex_work.sh) still source agent_sandbox.sh
  and stop with exit 78 when the launcher is missing unless AGENT_SANDBOX_FALLBACK=1. Switching them to
  the unrestricted path the owner chose is a myday change and must land before this spec's deletions.
- VELDO-0210 (draft, agent profile runtime) has nothing left to build once the launcher is gone; it is
  withdrawn in its own change, not here.

## Out of scope

Landlock or any other confinement of builders or gates. Removing the installed helper or AppArmor profile
from a host: that is the owner's act, prompted by the report line. Any change to the reuse rules beyond
holding every case to VELDO-0222's rules. Renaming or rewriting historical proof bundles that name the
deleted files.

## What the reviewer judges

- No stage, suite or mutation case runs through a namespace, and no code path can start one.
- The authority's scripts, the scope with its memory limit, the host lock and the credential-free
  environment are each shown by a row that goes red when that protection is removed.
- Every removed suite, row and mutation case is in the proof table with the row that still covers its
  behavior, or is marked confinement only, and nothing else lost coverage.
- Nothing Veldo runs calls sudo or needs the root helper, and a leftover install is reported, not refused.

## History

2026-11-07: drafted on the owner's agreement, Telegram 39705 and 39706, to the weight audit's item 4
(~/projects/myday/research/veldo-core-weight-audit-2026-11-07.md): drop the gate's user-namespace
confinement. Consistent with the owner's earlier decision that builders run unrestricted (Telegram 39154,
the mandatory sandbox "proved to be highly problematic") and with the single-user rule (never require a
separate OS user, a root-installed helper or a system service; if protection is wanted, Landlock on agent
processes).
