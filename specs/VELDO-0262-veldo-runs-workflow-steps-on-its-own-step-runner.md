---
schema: veldo.spec/v1
id: VELDO-0262
title: Veldo runs workflow steps on its own step runner behind the existing graph adapter, with today's observable behavior and VELDO-0247's parallel branches, and the LangGraph runtime is removed
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0043, VELDO-0045, VELDO-0088, VELDO-0132, VELDO-0186, VELDO-0189, VELDO-0241, VELDO-0247, VELDO-0248]
placement: [contracts, engine, loop]
protected_paths: ["scripts/agent_sandbox.json", "engine/scripts/agent_sandbox.json", "scripts/agent_sandbox.py", "engine/scripts/agent_sandbox.py", "scripts/mutation_sandbox.py", "engine/scripts/mutation_sandbox.py", "scripts/mutation_case_inputs.json"]
footprint:
  - ".veldo/control_graph_steps.py"
  - "engine/.veldo/control_graph_steps.py"
  - "packs/*/.veldo/control_graph_steps.py"
  - ".veldo/control_workflow_steps.py"
  - "engine/.veldo/control_workflow_steps.py"
  - "packs/*/.veldo/control_workflow_steps.py"
  - ".veldo/control_graph*.py"
  - "engine/.veldo/control_graph*.py"
  - "packs/*/.veldo/control_graph*.py"
  - ".veldo/control_workflow*.py"
  - "engine/.veldo/control_workflow*.py"
  - "packs/*/.veldo/control_workflow*.py"
  - ".veldo/control_runtime.py"
  - "engine/.veldo/control_runtime.py"
  - "packs/*/.veldo/control_runtime.py"
  - ".veldo/runtime/langgraph-records.json"
  - "engine/runtime/langgraph-records.json"
  - "packs/*/runtime/langgraph-records.json"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/policy_contract.py"
  - "engine/.veldo/policy_contract.py"
  - "scripts/agent_sandbox.json"
  - "engine/scripts/agent_sandbox.json"
  - "scripts/agent_sandbox.py"
  - "engine/scripts/agent_sandbox.py"
  - "scripts/mutation_sandbox.py"
  - "engine/scripts/mutation_sandbox.py"
  - "scripts/mutation_case_inputs.json"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/*_veldo_0262_*.py"
  - "scripts/suites/29_veldo_0016_policy_boundaries.py"
  - "scripts/suites/59_veldo_0043_graph.py"
  - "scripts/suites/62_veldo_0045_runtime.py"
  - "scripts/suites/65_veldo_0132_workflow.py"
  - "scripts/suites/86_veldo_0186_setup_assets.py"
  - "scripts/suites/86_veldo_0189_engine_upgrade.py"
  - "scripts/suites/92_veldo_0088_pm_cycles.py"
  - "scripts/suites/*_veldo_0247_*.py"
  - "scripts/suites/support/graph_stage.py"
  - "scripts/suites/support/setup_runtime.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0262-veldo-runs-workflow-steps-on-its-own-step-runner.md"
  - "specs/index.md"
  - "proof/VELDO-0262/**"
behavior_bearing: true
observability:
  logs: >
    Every adapter exchange keeps today's observation (operation, cycle, command, accepted inputs, outcome,
    named refusal, runtime label) and adds the sha256 of the staged runner it launched, the child's exit
    status and the exchange's elapsed milliseconds. Setup and the upgrade log each retired file and each
    retired runtime directory they remove, by path, and each leftover they refuse, by path and reason.
  metrics: >
    Exchange duration by operation and outcome (count, median, p95), read from the adapter's
    observations. No other metric is added or removed.
  traces: >
    Unchanged: every exchange joins to its cycle, its bound revision {id, version, digest} and its graph
    command id. The runtime label on every answer now names the step runner, so a cycle's trace shows which
    runner executed each step; labels recorded before the change stay as written.
  error_taxonomy: >
    No runner failure code changes: invalid_input, missing_evidence, node_failed and unsupported_workflow
    keep their meaning and detail text, and the adapter's refusals (invalid_input, path_in_request,
    invalid_response, missing_evidence, runtime_unavailable, unknown_outcome) keep theirs. runtime_unavailable
    now means the step runner asset is absent or its interpreter leads to a repository; its detail no longer
    names an install command, because there is nothing to install. New: leftover_runtime:<path>, refused by
    setup and by the gate for any part of the removed LangGraph runtime still present, classified
    unsupported_configuration; runtime_removed, the answer of control_runtime.py install, also
    unsupported_configuration, whose detail says the step runner needs no install.
acceptance_criteria:
  - id: AC1
    text: >
      Equivalence. A Veldo owned step runner, .veldo/control_graph_steps.py (standard library only), replaces
      control_graph_langgraph.py behind the unchanged veldo.graph/v1 adapter: same request and response
      shapes, plain JSON only, Veldo owns every identity and all state, nonpersistent, one exchange per
      process. It keeps every observable behavior of today: routing by each step's outcome port; one step per
      exchange, suspending at the node the port leads to so the domain side can refuse every transition before
      it runs; `start` runs the intake and reports the bound digest; `suspend` and `cancel` run their control
      steps; only typed proposals leave; a node output key outside {next, suspend, proposals, failure, notes}
      is node_failed; the named failures with today's detail texts, including the step bound of 64 and "node
      raised <type>"; a resume that is not this workflow's plain position is invalid_input. The runner holds no
      mutable module state: the definition is spliced in as one constant literal, never registered into a
      module level table, and each exchange's position, step count, notes, proposals and label live in one
      per exchange object. It is deterministic: no clock, randomness, thread or environment read, branches
      taken in sorted name order, and the same request bytes give the same answer bytes. The runtime label
      (executed_by) is {name: veldo-steps, version: the runner's declared version}, produced only by the step
      loop after a node ran; an answer where nothing ran still says NO_RUNTIME, and runtime_evidence() reads
      the declared version from the runner source statically, never by importing it. The step kinds move to
      control_workflow_steps.py and the project pipeline (control_graph_pm.py) is spliced into the new runner
      exactly as today. Every existing suite that drives the graph adapter, the workflow runner or the PM
      cycles (as of this draft 29, 32, 34, 36, 59, 65, 71, 73, 82, 92, 93, 96, 101, 110, 113 and VELDO-0247's
      suite) passes with no edit other than the expected runtime label, the VELDO-0043 isolation rows of
      suite 59 included; each VELDO-0043 and VELDO-0132 mutation row of check_teeth_mutations.py that targets
      the LangGraph runner is retargeted at the step runner with the same intent and still goes red. A
      recorded corpus, proof/VELDO-0262/corpus/, is captured on the LangGraph runner before anything is
      removed: every exchange those suites send, plus a seeded generated set of at least 500 revisions over
      every registered step kind, check rules, fan-outs of width 2 to 8, bounded loops and failing nodes, each
      driven to its end by a recorded script of supplied results, and resume values crossing in both
      directions (a LangGraph resume advanced on the new runner and the reverse). Replayed on the new runner,
      every answer is byte identical in canonical JSON once the runtime label is replaced by a placeholder: the
      same step sequences, positions, step counts, notes, proposals and failures. A cycle suspended under
      LangGraph continues on the new runner.
    falsified_by: >
      Three registered mutations of the new runner, each with a green baseline: (1) later notes lose to
      earlier ones in the merge; (2) a suspend that carries proposals is accepted; (3) the step count is not
      advanced for a node that failed. Each reds the corpus replay row, naming the first differing exchange
      and field. Replaying the corpus twice on the unmutated runner gives identical bytes. The retargeted
      VELDO-0043 and VELDO-0132 mutation rows still go red.
  - id: AC2
    text: >
      Parallel branches and Join, carried over from VELDO-0247 with its observable behavior. A suspension
      whose next is a mapping {branch: node} is a fan-out of at most FAN_OUT_CEILING (8) branches; the cycle
      suspends at PARALLEL with the plain branch set {branches: {branch: {position, last}}, join}. An exchange
      entered at PARALLEL is one superstep: every branch that has not reached the join runs its one node, each
      against the same pre-superstep state and a private copy of its view, writing only its own branch entry,
      in sorted branch order; no branch reads another's write of the same superstep, and the entries are merged
      only after all have run. One step is counted for each branch node that moved and the step budget counts
      every branch's nodes. The superstep number each entry carries reproduces the number the corpus recorded
      on LangGraph. The join runs only when every branch has reached it, and then once, as an ordinary node.
      A branch failure ends the cycle with node_failed naming the branch; a branch set wider than 8, empty,
      or naming a node or join outside the revision is invalid_input at run, and a fan-out of 9 is still
      refused at save. Branches are parallel in meaning, not in threads: the branch nodes are routing over
      supplied data, and what runs at the same time is the workers the Line dispatches for them, which it
      does without waiting for one another. The owner's approval cannot be gone around: VELDO-0247 AC4's save
      rows and VELDO-0241 AC2's approval walk are unchanged and pass unchanged, and control_workflow_cycle
      still re-evaluates every check's branch (branch_mismatch) and refuses any reported step that is not a
      transition of the bound revision (invalid_response:trace), so no runner answer can lead a branch to an
      outward step. Rows: two assignment branches are dispatched before either result returns and their first
      nodes carry one superstep number; with one result in the join has not run and the cycle stays suspended;
      with both in it runs once; a branch that mutates its view leaves its sibling's view of the same superstep
      unchanged; the same superstep with the branch names permuted in the request gives identical answer
      bytes; a resume of 9 branches is invalid_input; a forged runner answer naming a land node from inside a
      branch is refused by the cycle.
    falsified_by: >
      Two registered mutations, each with a green baseline: (1) the join runs when its first input arrives:
      the join-waits-for-all row goes red; (2) branches run in sequence on one shared state, each seeing the
      previous branch's writes: the branch isolation row goes red. VELDO-0247's own branch-around-approval
      falsifier still reds its row.
  - id: AC3
    text: >
      Removal. After the new runner passes AC1 and AC2, the LangGraph runtime is removed and nothing of it
      remains outside history (proof/, specs/ and docs/design/ stay as written). Removed, in .veldo,
      engine/.veldo and every pack: control_graph_langgraph.py, control_workflow_langgraph.py,
      control_graph_lock.py, control_graph_install.py and runtime/langgraph-records.json; init_scaffold's
      entries for them and its _RUNTIME_ASSETS record; control_runtime.py's LangGraph activation (records,
      licenses, distributions, RECORD digests, requirement evaluation) and its LangGraph qualification, its
      journey reduced to the assets it still reaches; the ~/.local/share/veldo/langgraph read root from both
      agent_sandbox.json copies; the LangGraph rows of suite 62 (VELDO-0045) and the actual-langgraph mutation
      rows, each listed with the reason in proof/VELDO-0262/removed-rows.json. control_runtime.py keeps check
      (the step runner asset present, its interpreter clear of every repository), qualify (the start, suspend,
      advance and cancel workload on the step runner through the production adapter) and enforcement;
      install answers runtime_removed. The step runner still runs in its own child process (see Context):
      the resolved base interpreter of the python3 running the adapter, started -I -S -B, so no site package
      is importable in it at all. The upgrade of an earlier installation (VELDO-0189) removes the retired
      files from the target's .veldo and the account's runtime directories under
      ~/.local/share/veldo/langgraph/, removing only plain directories named by a 64 character hex digest,
      following no link, and logging each. Setup, fresh or upgrade, then refuses before it writes anything,
      leftover_runtime:<path>, for any retired file in the target's .veldo, any installed module that names
      langgraph, langchain or langsmith in an import, or anything still under that runtime directory. A gate
      row in this spec's suite refuses the same in the repository: any of the retired files under .veldo,
      engine or packs, any import of those packages in any Python file outside proof/ and specs/ (every
      import statement at any depth and every literal importlib or __import__ name, the static closure
      control_graph_isolation already walks), and any lock, records or install path naming them. The
      isolated enforcement command still passes and graph start with the runner asset absent still reports
      runtime_unavailable.
    falsified_by: >
      Three registered mutations, each with a green baseline: (1) control_graph_lock.py restored to
      engine/.veldo: the gate's leftover row goes red naming it, and a scaffolded setup of that tree refuses
      leftover_runtime naming it; (2) `import langgraph` added inside a function of control_workflow_cycle.py:
      the leftover row goes red; (3) an account home whose runtime directory holds a link named by a digest:
      the upgrade removes nothing through it and setup refuses leftover_runtime naming the link.
  - id: AC4
    text: >
      Performance, measured and not assumed. Before the removal, proof/VELDO-0262/measure.py drives the same
      exchanges through the production adapter on the LangGraph runner and on the step runner, interleaved on
      one host: at least 50 each of start and advance for the default code definition, the runtime
      qualification workflow and a VELDO-0247 fan-out of 4, plus the child's own start measured with
      python -X importtime. proof/VELDO-0262/performance.json records the method, host, CPU, load, Python
      version, every sample, and the median and p95 of each; the LangGraph runner's import and graph build
      time is taken from its own importtime and timing samples, not estimated. The claim holds when the step
      runner's median exchange is lower than the LangGraph runner's by at least 80 percent of that measured
      import and build time, for every workload. A deterministic gate row guards the cause without timing
      anything: the adapter launches the staged runner with -I -S -B, and under those flags the child's
      importtime shows only standard library modules (judged against sys.stdlib_module_names) and the runner
      itself.
    falsified_by: >
      (1) measure.py run against a mutant step runner that sleeps at start for the measured LangGraph import
      and build time reports the claim false. (2) A registered mutation dropping -S from the adapter's launch
      flags reds the gate row.
required_evidence: [unit, integration]
rollback: >
  Revert the commits. The LangGraph runner, lock, records and installer return; the owner runs
  python3 .veldo/control_runtime.py install once per account to rebuild the locked runtime the upgrade
  removed. Resume values are plain Veldo data and AC1 proves them interchangeable in both directions, so a
  cycle suspended under the step runner continues on LangGraph; its recorded veldo-steps labels stay as
  written. No stored record, journal entry or contract carries a runner specific structure, so nothing needs
  migrating. No automatic rollback, retry or recovery is authorized.
---

## Intent

The owner asked what Veldo gets from LangGraph and whether it is needed. Very little of LangGraph is
used: Veldo owns identity and state, persists nothing in the runtime, runs one exchange per process with
no checkpointer, routes by Command, and handles suspend and resume itself. What it pays is a pinned
dependency closure of about twenty packages with license and provenance records, an isolated install per
account, an activation and qualification journey, setup and upgrade paths for all of it, and a runtime
start on every step. Veldo replaces it with its own small step runner behind the adapter boundary that
VELDO-0043 built to be replaceable, keeps every observable behavior and VELDO-0247's parallel branches,
and removes the runtime.

## Context

Owner, Telegram 39621 to 39623 (2026-11-07): asked what Veldo gets from LangGraph and whether it is
needed; on the recommendation to replace it with Veldo's own small step runner, answered "Yes" (write the
ticket).

What is there today. control_graph.py is the stdlib adapter: it stages the runner content-addressed under
the account's graph stage, launches it as a child with a fixed environment, an empty working directory
outside every repository, no inherited descriptors, its own session and a deadline that kills the whole
group, and refuses any answer that is not exactly a veldo.graph/v1 shape. control_graph_langgraph.py builds
a StateGraph per exchange with no checkpointer and routes every node by Command; control_workflow_cycle.py
splices the step kinds and one revision into it and re-judges every step against the stored revision; the
PM cycles (VELDO-0088) splice control_graph_pm.py the same way. control_graph_lock.py, control_graph_install.py,
runtime/langgraph-records.json and control_runtime.py (VELDO-0045, moved to 1.2.19 by VELDO-0248) lock,
install, activate and qualify the runtime. LangGraph contributes the per exchange graph walk and, in
VELDO-0247, Send and reducers for one superstep of branches. Every one of those is a few dozen lines of
plain Python over data Veldo already owns.

Dependency on landing-b. VELDO-0247's runner changes (PARALLEL, COLLECT, branch reducers, superstep
numbers) are in the landing-b batch, not on main at afa292f0. This spec is built after landing-b lands, on
the main that carries them, so the corpus of AC1 and the branch rows of AC2 are recorded against VELDO-0247
as built.

Decision: the step runner stays in a separate child process; only the lock and the isolated install go.
VELDO-0043 and VELDO-0045 isolate graph execution from enforcement, and the isolation does not hold in
process:
- A node in process shares the address space of the authority's store connection, signer and keys. Today
  a node cannot reach the store by construction: its process holds no handle, path or descriptor (VELDO-0043
  AC2). In process that would hold only by review of every step kind, and the PM pipeline's nodes carry
  model mediated data.
- The PM pipeline installs a process wide audit hook, which Python cannot remove; in process it would stay
  in the authority for its lifetime.
- A deadline in process cannot stop a runaway node, because Python cannot kill a thread; the child's group
  kill gives the deadline teeth, and a crash, a memory blowup or a recursion in a node ends the child, not
  the authority.
- What the isolated install guarded against was third party code in the child. That reason is gone: the
  child is the base interpreter started with -I -S -B, so not even site packages are importable, which is
  stronger than today's locked virtual environment. The remaining cost is one standard library interpreter
  start, which AC4 measures.
The stage, the content addressed runner copies, the repository checks on the interpreter and the working
directory, the fixed environment and the deadline all stay as they are. The /proc limit VELDO-0043 states
stays stated.

Build order, so every claim is measured against the real old runner: record the corpus and the old
timings on the LangGraph runner; build the step runner and pass AC1 and AC2 with LangGraph still
installed; then remove the runtime (AC3) in its own commit.

## Out of scope

Persistent checkpoints and resuming a cycle after a crash (Release 2). Any change to the veldo.graph/v1
request or response, to the definition schema, to the step kinds' meaning, to the save rules of VELDO-0241
and VELDO-0247, or to the dispatch of branch workers by the Line. Running branch nodes on threads. Resource
limits on the child beyond today's deadline. Confining /proc reads (Release 2). Renaming the stored
policy option langgraph-adapter-veldo-owned-state, an identity like a WARP id; only its effect text is
updated. Proof bundles, specs and design provenance that mention LangGraph stay as written.

## What the reviewer judges

- The step runner is plain and small, holds no module level mutable state, reads no clock, randomness,
  thread or environment, and its answers are byte identical on the corpus apart from the label.
- The corpus was recorded on the LangGraph runner before the removal and is large enough to exercise every
  step kind, port, failure, fan-out width and resume crossing; its generator and seed are in the proof.
- Isolation is unchanged or stronger: the same child process boundary, now with -S, and every VELDO-0043
  isolation row passes unedited.
- The removal leaves no import, package, lock, records, install or read root behind, the upgrade removes
  only what Veldo made and follows no link, and setup and the gate refuse a leftover by name.
- The performance claim comes from measured samples with the method recorded, and the gate row guards the
  cause without timing anything.

## History

2026-11-07: drafted under owner Telegram 39621 to 39623 ("Yes", write the ticket), from main at afa292f0
and VELDO-0247 as written in the landing-b batch. Built after landing-b lands.

2026-11-07: ready on the owner's approval, Telegram 39630 ("Ok") to the summary in 39629. Built after landing-b lands.
