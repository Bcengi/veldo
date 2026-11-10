---
schema: veldo.spec/v1
id: VELDO-0271
title: The gate runs candidate tests in one leg per stage without the user-namespace sandbox, keeps its authority scripts, scope, memory limit, host lock and credential-free candidate runs, and no longer needs a root-installed helper
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0208, VELDO-0216, VELDO-0220, VELDO-0267]
placement: [enforcement]
protected_paths: ["scripts/mutation_selection.json", "scripts/mutation_selection.py", "engine/scripts/mutation_selection.py", "scripts/parked/estimation/check_first_use.py"]
footprint:
  - "scripts/verify.sh"
  - "engine/scripts/verify.sh"
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
  - "scripts/gate_graph.json"
  - "scripts/check_gate_mutations.py"
  - "engine/scripts/check_gate_mutations.py"
  - "scripts/reuse_worker.py"
  - "engine/scripts/reuse_worker.py"
  - "scripts/case_inputs.py"
  - "engine/scripts/case_inputs.py"
  - "scripts/propose_case_inputs.py"
  - "scripts/mutation_case_inputs.json"
  - "scripts/mutation_selection.json"
  - "scripts/mutation_selection.py"
  - "engine/scripts/mutation_selection.py"
  - "scripts/mutation_ownership.py"
  - "engine/scripts/mutation_ownership.py"
  - ".veldo/reuse_evidence.py"
  - "engine/.veldo/reuse_evidence.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/control_proof.py"
  - "engine/.veldo/control_proof.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_factory_setup.py"
  - "engine/.veldo/control_factory_setup.py"
  - "docs/outside-services.md"
  - "scripts/selftest.py"
  - "scripts/parked/estimation/check_first_use.py"
  - "scripts/parked/estimation/111_veldo_0214_first_use_budget.py"
  - "scripts/parked/estimation/manifest.json"
  - "scripts/check_install_and_run.py"
  - "scripts/migrate_to_veldo.py"
  - "scripts/run_scope.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/**"
  - "specs/VELDO-0271-the-gate-runs-candidate-tests-without-the-user-namespace-sandbox.md"
  - "specs/index.md"
  - "proof/VELDO-0271/**"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "proof/VELDO-0127/resources-*.json"
  - "proof/VELDO-0127/claude-live.json"
  - "proof/VELDO-0127/codex-live.json"
behavior_bearing: true
observability:
  logs: >
    Each stage line names the stage only; the confined and unconfined leg names, the leg list and its
    digest are no longer printed. When the gate or factory setup finds a leftover namespace helper
    (/usr/local/lib/veldo/veldo-userns) or its AppArmor profile (/etc/apparmor.d/veldo-userns), it prints
    one report line naming each path found and the owner's removal command; the result is unchanged.
  metrics: >
    The stamp and the gate event lose the unconfined field. Each node's resource record (VELDO-0216,
    VELDO-0219) is kept in the same format, now written by gate_schedule.py.
  traces: >
    None added. The case trace (scripts/case_trace.py) becomes the only record of what a mutation case
    read.
  error_taxonomy: >
    Removed: every launcher refusal (no helper, unsupported kernel, socket on a standard stream, nested
    marker), "candidate execution failed in store-denied domain", the leg refusals of run_scope.py and an
    invalid leg list. Added, report only and never red: leftover_namespace_helper. A stamp written before
    this change, with an unconfined field, still validates and is read as before. Unchanged:
    confined_runner_unavailable:<reason> (VELDO-0254 AC3), which every launch marked risky now gets
    because no confined runner ships.
acceptance_criteria:
  - id: AC1
    text: >
      Every required stage runs as one leg. verify.sh and gate_schedule.py start each stage's command
      through the authority's gate_candidate.py, which no longer loads or starts a launcher: it runs the
      command in the candidate root with standard input from /dev/null and every inherited descriptor
      closed. scripts/gate_legs.py and scripts/gate_unconfined.json are deleted; the leg variables
      (VELDO_GATE_LEG, VELDO_GATE_UNCONFINED, VELDO_GATE_DECLARATION), the leg selection in selftest.py and
      run_scope.py, and the stamp's unconfined field go with them. What gate_legs.py kept that is not
      confinement moves into gate_schedule.py with its record format unchanged: the per-node resource record
      (VELDO-0216, VELDO-0219) and the pruning of old records. The 49 suites and row groups the
      leg list named run in the same unit stage as every other suite, including the strace rows of suites
      100 and 101 and the systemd user manager suites.
    falsified_by: >
      A new suite runs a fixture gate over a fixture repository whose unit stage holds one suite that starts
      a transient unit with systemd-run in the user manager and one that traces a child with strace: both
      are green in one stage line and the stamp has no unconfined field. A count row requires the unit
      stage to report every suite in scripts/suites/manifest.json. Registered mutations, each from a green
      baseline: (1) selftest.py skips the suites the deleted list named: the count row goes red; (2) record_resources, moved into gate_schedule.py, returns before it writes: the
      measured-claims row of suite 114_veldo_0216_concurrent_stages, which records and reads back
      node unit, goes red;
      (3) gate_candidate.py passes the caller's standard input through: the stdin row, which runs the gate
      with a socket on standard input and requires the candidate to read end of file, goes red.
  - id: AC2
    text: >
      What is cheap and real stays and is checked. The gate runs its own scripts from the authority
      checkout (VELDO_AUTHORITY, python3 with isolated mode), never the candidate's copies; it runs inside
      its own systemd scope with the memory limit from scripts/gate_host.json and holds the host lock
      (VELDO-0220); and no credential reaches a candidate's run (VELDO-0254 to VELDO-0258): the
      environment gate_candidate.py builds carries no variable named in the installation's keystore or
      settings and none whose name is in control_launch.py's EXEC_STRIPPED or matches the secret-name pattern
      _SECRET_NAMES of .veldo/substrate.py, and the gate
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
      The mutation stage runs without the sandbox and every case runs fresh. check_gate_mutations.py and
      reuse_worker.py start every case's worker as a plain child in its own scope, without
      mutation_sandbox.py or agent_sandbox.py, so a case runs the same way whether the gate or a driver
      started it directly. No case result is reused: with no namespace enforcing a case's declared inputs,
      a stored result cannot be trusted, and the reuse count was 0 in every recorded gate (audit
      2026-11-07, item 11), so running fresh costs nothing measured. The reuse machinery itself is
      deleted by VELDO-0279, which lands after this spec; this spec only turns reuse off. VELDO-0267's
      declaration adapts here: its canary set covers the one leg instead of the confined and the
      unconfined leg, and its full-sweep trigger list drops gate_legs.py and gate_unconfined.json and
      keeps gate_candidate.py.
    falsified_by: >
      The three suite 62 cases of VELDO-0261 run through scripts/check_teeth_mutations.py directly, the entry
      whose confined run gave invalid baselines, and each shows a green baseline and a killed mutant.
      Registered mutations: (1) the worker returns a stored result for a case whose inputs are unchanged:
      the fresh-run row, which runs one case twice and checks both runs executed, goes red; (2) the canary
      set in scripts/mutation_selection.json is cut below VELDO-0267's bound of six: its declaration row
      goes red.
  - id: AC4
    text: >
      Every removal is mapped, the login lease stays and nothing needs root. Deleted, with their engine
      copies where one exists: agent_sandbox.json, mutation_sandbox.py, veldo_userns.c,
      veldo-userns.apparmor, gate_legs.py, gate_unconfined.json and docs/veldo-userns-setup.txt.
      scripts/agent_sandbox.py and its engine copy stay under the same name, cut down to the login lease
      of VELDO-0211, because proof/VELDO-0127/live.py loads the lease from that path and the owner's
      runners use the same lease. What stays: take_lease and release; borrowed_credentials with Borrow, borrow_journal,
      settle_borrow, write_back and keep_recovery; recover_orphans; restore_login and the restore-login
      command; CredentialRecovery, recovery_message, RECOVERY_EXIT and borrow_root; Stop, Interrupted and
      STOP_SIGNALS; and the private helpers these call. Everything in the file that confines or launches
      is removed (the list is under Decision), and no gate script, suite helper or .veldo module loads
      the file. No confined runner ships after this: a launch marked risky (VELDO-0254 AC3) is refused
      as confined_runner_unavailable:<reason>, default launches are unaffected, and the decision and
      refusal code in control_launch.py do not change; only its two comments and section 3 of
      docs/outside-services.md change, to say so and to stop naming the deleted configuration.
      init_scaffold.py, reuse_evidence.py, case_inputs.py, check_install_and_run.py, migrate_to_veldo.py
      and control_proof.py stop naming or loading what is gone, and the trigger list in
      scripts/mutation_selection.json drops its two agent_sandbox.json entries. Suites 102 (agent
      profile runtime), 104 (mutation workers in a launcher tree) and 128 (a risky run starts in the
      confined runner) are removed because they test only the launcher. Suite 103 (borrowed login)
      keeps every row that drives the lease through live.py and loses the rows that start the
      launcher. Suite 127 builds its no-runner-host and cached self-test rows on a fixture runner
      program it writes itself. In selftest.py and in suites 53, 64, 69, 98, 99, 100, 101, 112, 114, 126, 127_veldo_0259,
      129_veldo_0274 and 140, only the rows that test the gate's namespace confinement, the launcher
      or leg selection are removed; every other row there is rewritten for one leg and a process
      tree with no launcher in it. Suite 65_veldo_0067_edges is unchanged: its rows test the edge
      key's own Landlock fence, not the gate's. concurrent216-lost-leg-record, the one case that mutates gate_legs.py on this tree, is removed
      and listed as confinement only, because the leg record it truncates leaves with the stamp's
      unconfined field. deadline215-no-prune keeps its intent with its anchor rewritten to the
      pruning that moves into gate_schedule.py. scope272-gate-legs-added-back and its suite
      129_veldo_0272_approval_scope row use scripts/gate_schedule.py as the unprotected sample path. The parked suite
      scripts/parked/estimation/111_veldo_0214_first_use_budget.py is deleted with its entry in the
      parked manifest: it tests only the unit-leg handoff in gate_legs.py, which VELDO-0278 already
      removed, and nothing runs it except the hand-run parked selector of selftest.py; suite
      129_veldo_0278_parked_estimation drops its name. The parked check_first_use.py stays and loses
      its launcher_fds helper and its reader of the handoff variable, which nothing has set since
      VELDO-0278, so its budget is the fixed 1,800 seconds it already falls back to. The proof bundle
      carries a table with one line per removed suite, row and mutation case, naming the behavior it
      checked and either the row that still checks it or "confinement only". Setup, factory setup and
      the gate never run sudo, never install, call or require /usr/local/lib/veldo/veldo-userns or the
      AppArmor profile, and report a leftover install of either with the owner's removal command
      (sudo rm /usr/local/lib/veldo/veldo-userns; sudo apparmor_parser -R /etc/apparmor.d/veldo-userns; sudo
      rm /etc/apparmor.d/veldo-userns) without changing the result.
    falsified_by: >
      A scan row finds none of these seven names in tracked files outside specs/, proof/, plans/ and
      docs/design/, other than the suite file that holds the scan and suite 127's config_missing
      row: agent_sandbox.json, mutation_sandbox.py, veldo_userns.c, veldo-userns.apparmor,
      gate_legs.py, gate_unconfined.json, veldo-userns-setup.txt. A second scan row finds no load of
      scripts/agent_sandbox.py, by import or by command line, in verify.sh, any scripts/gate_*.py,
      check_gate_mutations.py, reuse_worker.py, selftest.py, check_install_and_run.py,
      migrate_to_veldo.py, scripts/suites/shared.py or any .veldo module, and a third loads the file and requires that it defines none of landlock,
      fork_gate_domain, Broker, launch, run_tree, namespace_init, namespace_selftest, launcher_fds,
      remove_stale_scratch and NAMESPACE_HELPER.
      Suite 103's live rows (rotation, locking, recovery, restore, the two killed-run recovery rows
      and the killed-capture guard) are green against the cut-down file. The two killed-run rows
      keep their recover_orphans assertions, read the unsettled journal directly instead of through
      pending_borrow, and lose their scratch-removal clause; the row
      recovery/scratch-swept-once-recovered is removed. Both changes are in the proof table, because
      the scratch sweep served only the removed launcher. A suite 127 row requires a launch marked risky to be refused
      as confined_runner_unavailable:not_configured when the receiver configuration names no runner, and
      an unmarked launch to start its argv as before. A fixture host root holding a fake helper and
      profile gets the leftover_namespace_helper line from the gate and from factory setup, and both
      stay green; without them no line is printed. A sudo shim first on PATH records no call across
      factory setup and a full fixture gate. A table row requires the proof table to list every suite
      row and mutation case present at 24c9f5b4 and absent after, by name. Registered mutations: (1)
      factory setup calls the shim: the no-sudo row goes red; (2) the gate turns the leftover report
      into a refusal: the leftover row goes red; (3) one removed row is left out of the proof table:
      the table row goes red; (4) take_lease returns without taking the lock: the suite 103 row that
      requires a borrow of a login another run holds to be refused goes red.
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

Measured on this tree, landing-c 24c9f5b4 plus this spec's own commits, on 2026-11-10. The weight audit
is veldo-core-weight-audit-2026-11-07.md, item 4.

- scripts/agent_sandbox.py 2,951 lines, scripts/veldo_userns.c 277, scripts/veldo-userns.apparmor 61,
  scripts/mutation_sandbox.py 127, scripts/gate_legs.py 374, scripts/gate_candidate.py 37,
  scripts/agent_sandbox.json 105, docs/veldo-userns-setup.txt 24, and scripts/gate_unconfined.json with
  49 entries (47 whole suites and the strace row groups of suites 100 and 101). Each has an engine copy
  except gate_unconfined.json and the setup text. 104 commits since 2026-09-01 touch these files; the
  audit counted 83 on main.
- The root-owned helper /usr/local/lib/veldo/veldo-userns and the profile /etc/apparmor.d/veldo-userns
  are both installed on the owner's host today. The owner installed them with sudo by following
  docs/veldo-userns-setup.txt.
- gate_legs.py loads agent_sandbox.py as the confined leg's launcher; gate_candidate.py starts it with
  the gate profile for every candidate command; check_gate_mutations.py, reuse_worker.py and
  mutation_sandbox.py confine every mutation worker the same way. scripts/gate_graph.json carries two
  unit nodes, unit.confined and unit.unconfined, and mutation_selection.py refuses a canary set that
  does not cover both legs.
- 52 tracked files outside specs/, proof/, plans/ and docs/design/ name at least one of the seven files
  AC4 deletes. Six of them were outside the footprint before this revision: control_launch.py and its
  engine copy, docs/outside-services.md, and three files in scripts/parked/estimation/.
- VELDO-0261's build note (proof/VELDO-0261/README.md, Still open): run through check_teeth_mutations.py
  directly, the three suite 62 cases ran confined, every dispatch launch was refused and their baselines
  were invalid. The same suite is green through the gate only because the leg list moves it out.
- gate_legs.py also carries one duty that is not confinement: the node resource records of VELDO-0216
  and VELDO-0219, with their pruning. That moves into gate_schedule.py. The unit-leg seconds handoff of
  VELDO-0214 is already gone: VELDO-0278 removed it and parked suite 111 and check_first_use.py.
- None of the files this spec deletes is on the protected list any more. VELDO-0272 took the sandbox
  and leg machinery off it, so this build does not change .veldo/policy.yaml. Still protected in the
  footprint: scripts/mutation_selection.json, mutation_selection.py with its engine copy, and the parked
  check_first_use.py.

What stays and why it is real: the authority checkout is the source of every gate script, so a candidate
cannot replace its own judge; the gate's scope and memory limit keep one runaway suite from taking the
host; the host lock keeps heavy runs from overlapping; and the gate hands no credential to candidate code,
which is the rule VELDO-0254 to VELDO-0258 set for every run.

## Decision

agent_sandbox.json is deleted. agent_sandbox.py is kept, cut down to the login lease.

Two things outside the gate use agent_sandbox.py, and they come out differently.

The login lease stays. A login is a directory holding an engine's subscription credential, and the lease
is a lock on the file .runner-lease inside it that every user of that login takes first, so two runs
never rotate the same credential at once. proof/VELDO-0127/live.py loads scripts/agent_sandbox.py for
this and nothing else: it borrows a login under the lease, writes a rotated credential back before it
lets go, and recovers what a killed run left behind. The owner's runners take the same lease and call
the same restore-login command. None of that needs a namespace, Landlock or root, and about 700 of the
file's 2,951 lines carry it. The file keeps its name and path because live.py is evidence in a proof
bundle and cannot be edited to load another one. AC4 lists the functions that stay.

The confined runner goes. control_launch.py starts a launch marked risky inside agent_sandbox.py's agent
profile (VELDO-0254 AC3). That profile runs only through the root helper: control_launch.py itself
refuses the launch as helper_missing when the helper is absent, and suite 128, which proves the runner
works, is green only on a host where the helper is installed. A gate that needs no root helper cannot
keep a suite that needs one, and code no suite can run is not worth keeping. So the runner's code
leaves the file, suite 128 goes, and a risky launch is refused until a runner that needs no root exists.
The refusal already exists and is already tested in suite 127: confined_runner_unavailable:not_configured
when the receiver configuration names no runner, and config_missing when it still names the deleted
agent_sandbox.json. control_launch.py's decision and refusal code are not touched; only the two comments
that name the launcher files are reworded, in both copies.

What leaves agent_sandbox.py: the Landlock and seccomp rules with their socket broker (landlock,
ipc_program, install_filter, Handoff, Broker, fork_brokered, fork_gate_domain); the namespace start and
its checks (helper_problem, launcher_marker, launcher_fds, nested_namespace, namespace_init,
namespace_selftest, confined_init, confined_agent, run_tree, worker_tree); launch and prepared_launch
with the agent, gate and worker profiles; the grant and client state builders (grants_for, client_files,
state_grants, clean_state, toolchain_environment); the agent repository commands prepare and integrate;
the scratch sweep (remove_stale_scratch, remove_tree, pending_borrow); and every command of main except
restore-login.

Smaller choices that follow:

- control_proof.py's own launcher_fds, and its one caller in the protected control_verification.py, stay
  as they are. Handing on an inherited namespace descriptor does nothing once no launcher checks it, and
  removing the call would put a protected file in this footprint for a comment's sake. Only the comment
  in control_proof.py that names the launcher's marker check is reworded.
- scripts/gate_graph.json gets one unit node in place of unit.confined and unit.unconfined. It takes the
  exclusive manager claim, because the systemd user manager suites now run in it, and its estimate comes
  from a measured run recorded in the proof bundle.
- mutation_selection.py stops requiring canaries in both legs; the canary note in
  scripts/mutation_selection.json is rewritten for one leg. The trigger list keeps its two
  agent_sandbox.py entries. Dropping them would shrink a protected list further than AC3 and the deleted
  configuration require.
- control_factory_setup.py and its engine copy are in the footprint because AC4 puts the leftover report
  there and its first mutation changes that file. mutation_ownership.py is there for one comment that
  describes the unconfined leg.
- docs/outside-services.md section 3 keeps the three risky marks and says that Veldo ships no confined
  runner, so a marked launch is refused by name and an unmarked one is never affected.

## Coordination

VELDO-0267, VELDO-0254, VELDO-0272, VELDO-0274 and VELDO-0278 are on this tree. VELDO-0279 and
VELDO-0273 depend on this spec and land after it.

- VELDO-0267 (mutation on changed code): this spec edits its protected declaration,
  scripts/mutation_selection.json, and its reader mutation_selection.py, as AC3 and Decision say.
- VELDO-0254: its AC3 keeps the risky marks and the named refusal. The half that says a risky run
  starts confined has no runner behind it after this spec. A Landlock-only runner, if the owner wants
  one, is a later spec, and it brings its own suite in place of 128.
- VELDO-0208 and VELDO-0211: this spec removes the agent confinement of VELDO-0208 and keeps
  VELDO-0211's borrowed-login lease unchanged. VELDO-0208 stays in depends_on because this spec
  edits the files it built.
- VELDO-0278: its AC3 parked suite 111. This spec deletes that suite and edits suite
  129_veldo_0278_parked_estimation, which requires the name in the parked manifest. If Tokens of Effort
  is unparked later, the budget of the first-use check needs a new measurement source, because the leg
  that measured it is gone.
- VELDO-0269 (one engine copy) is not on this tree. If it lands first, this spec deletes and edits the
  engine/ files only and its footprint's root entries become laid files.
- The owner's runners (claude_work.sh and codex_work.sh in his own repository) still source
  agent_sandbox.sh, which starts the launcher with agent_sandbox.json and calls its prepare and
  integrate commands; they stop with exit 78 when the launcher refuses unless AGENT_SANDBOX_FALLBACK=1.
  They must move to the unrestricted path the owner chose before this spec lands. After that they may
  keep taking the lease and calling restore-login, which stay.
- VELDO-0210 (draft, agent profile runtime) has nothing left to build once the launcher is gone; it is
  withdrawn in its own change, not here.

## Out of scope

Landlock or any other confinement of builders or gates. Removing the installed helper or AppArmor profile
from a host: that is the owner's act, prompted by the report line. Any change to the reuse rules beyond
running every case fresh (reuse off; VELDO-0279 deletes the machinery). Renaming or rewriting historical proof bundles that name the
deleted files. Any change to how the login lease behaves, or to control_launch.py's runner decision and
refusal code. A replacement confined runner.

## What the reviewer judges

- No stage, suite or mutation case runs through a namespace, and no code path can start one.
- The authority's scripts, the scope with its memory limit, the host lock and the credential-free
  environment are each shown by a row that goes red when that protection is removed.
- Every removed suite, row and mutation case is in the proof table with the row that still covers its
  behavior, or is marked confinement only, and nothing else lost coverage.
- Nothing Veldo runs calls sudo or needs the root helper, and a leftover install is reported, not refused.
- The login lease behaves as before: live.py loads it from the same path and suite 103's live rows are
  green. What was cut from agent_sandbox.py is only what confines or launches.
- A launch marked risky is refused by name and an unmarked launch starts as before, with no change to
  control_launch.py beyond two comments.

## History

2026-11-07: drafted on the owner's agreement, Telegram 39705 and 39706, to the weight audit's item 4
(veldo-core-weight-audit-2026-11-07.md): drop the gate's user-namespace
confinement. Consistent with the owner's earlier decision that builders run unrestricted (Telegram 39154,
the mandatory sandbox "proved to be highly problematic") and with the single-user rule (never require a
separate OS user, a root-installed helper or a system service; if protection is wanted, Landlock on agent
processes).

2026-11-07: ready by the lead under the owner's narrowed approval scope (Telegram 39708); the decision to remove the gate sandbox was his, 39706. Landing order 0267, 0271, 0269. Before it lands, myday's claude_work.sh and codex_work.sh move to the unrestricted runners (lead task).

2026-11-07: AC3 amended by the lead (Telegram 39708 scope, test machinery): reuse is turned off instead of kept under VELDO-0222's rules, and the dependency on the unbuilt VELDO-0222 is dropped, because VELDO-0279 (agent/claude/veldo-cleanups) deletes the reuse machinery and supersedes 0222; landing order 0267, 0271, 0279.

2026-11-07: footprint gains the suite registration files (scripts/suites/manifest.json, requires.json and scripts/check_teeth_mutations.py where missing), by the lead under Telegram 39708 (mechanical, ACs unchanged): selftest refuses a suite file the manifest does not enumerate, so a ticket that adds a suite must register it (VELDO-0272 build stopped on this, proof/VELDO-0272/README.md).

2026-11-10: revision 3 by the lead's writer: rebased onto landing-c 24c9f5b4, after two builds stopped correctly because AC4's scan could not pass inside the footprint. Decision: agent_sandbox.json is deleted and agent_sandbox.py is kept, cut down to the login lease of VELDO-0211, because proof/VELDO-0127/live.py loads the lease from that path and the owner's runners use the same lease; the confined runner in it is removed, because it runs only through the root helper and its suite 128 passes only where that helper is installed, so a launch marked risky is refused by the existing confined_runner_unavailable code and control_launch.py changes in two comments only. AC4 changed for that decision: the kept functions are named, the scan covers the seven deleted file names and is joined by a no-load scan and a content row for the kept file, suite 103 keeps its lease rows, suite 128 is removed, suite 127 moves to a fixture runner program, parked suite 111 is deleted, and a fourth mutation covers take_lease. AC1 changed only where the tree forced it, not the decision: VELDO-0278 already removed the unit-seconds handoff and parked suite 111, so that clause is dropped and mutation (2) now targets the node resource record and suite 114's measured-claims row; the leg list count is 49, was 46. AC2 and AC3 are unchanged. Footprint gains control_launch.py and control_factory_setup.py with their engine copies, docs/outside-services.md, scripts/gate_graph.json, mutation_selection.py and mutation_ownership.py with their engine copies, and three files in scripts/parked/estimation/ (check_first_use.py, the deleted suite 111, manifest.json); it loses .veldo/policy.yaml, which VELDO-0272 already cleared of these files, and scripts/check_first_use.py, which VELDO-0278 moved. Context numbers re-measured on this tree and the audit's home path replaced by its file name.

2026-11-10: revision 3 review findings 1 to 7 applied verbatim by the lead (suite 103 sweep rows, concurrent216 removed and the two other gate_legs cases re-anchored, AC1 mutation (2) on record_resources, AC4 suite list, AC2 credential names from EXEC_STRIPPED and _SECRET_NAMES, scan exemptions and wider second and third scans, protected_paths trimmed, VELDO-0208/0211 coordination). Status stays ready.

2026-11-10: footprint gains the VELDO-0127 resource records and the two live captures (lead, Telegram 39708 scope): AC4 edits .veldo/control_launch.py, whose digest these records bind, so suite 126 row VELDO-0230 qualify/reproduces stays red until they are regenerated by qualify.py and live.py for the edited file, as landing-c and landing-d2 did.
