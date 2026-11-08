# VELDO-0262 proof: Veldo runs workflow steps on its own step runner, and the LangGraph runtime is removed

Branch agent/claude/veldo-0262, main (918e7c0e, landing-b with the VELDO-0247 runner) merged in first
(dd27ccc3). Build order as the spec states: corpus and timings recorded on the LangGraph runner, step
runner built and wired with LangGraph still present, then the removal in its own commit (829d9a0e).

Status: built and checked locally with suite-only runs (no gate lock). The full gate and every suite and
falsifier run listed in `pending_runs.sh` are pending for the lead. Nothing here is a gate claim.

## AC1: equivalence

Built:
- `.veldo/control_graph_steps.py` (engine copy synced): standard library only (copy, json, math, sys),
  the veldo.graph/v1 runner behind the unchanged adapter. One `Exchange` object per exchange holds
  position, step count, notes, proposals, outcome and label; no global statement; the label
  `{name: veldo-steps, version: VERSION}` is set by the step loop only after a node ran; NO_RUNTIME
  otherwise. MAX_STEPS 64 counts supersteps exactly as LangGraph's recursion limit did (64 node runs, the
  65th refused with today's detail). Failure texts unchanged, including "node raised <type>".
- `.veldo/control_workflow_steps.py`: the step kinds, spliced with one constant literal
  `VELDO_DEFINITION = (<canonical text>, <version>)`; `workflows()` builds the one workflow per exchange,
  nothing is registered into a module table. The PM pipeline (`control_graph_pm.py`) is spliced as before.
- `control_graph.py`: runner `control_graph_steps.py`, interpreter the resolved base interpreter
  (`sys._base_executable`), launch flags `FLAGS = ('-I', '-S', '-B')`, `runtime_evidence()` reads VERSION
  with `ast` (never imports), `runtime_unavailable` names no install command, every observation adds
  `runner_sha256`, `exit`, `elapsed_ms`, and `exchange_durations()` gives count, median, p95 by operation
  and outcome. The LangSmith switches left the fixed environment with the runtime.
- `control_workflow_cycle.py`, `control_workflow_cycle_pm.py`, `control_runtime.py` use the step runner.

Corpus (`corpus.py`, `corpus/`, recorded at ee807309 on LangGraph 1.2.19 before anything was removed):
2508 exchanges, seed 262, 520 generated revisions over grooming, owner_wait, assignment, check (every
field type and comparison), join and result_handling, fan-outs of width 2 to 8, bounded loops through a
check, failing nodes (no answer, unsupplied or mistyped field, a port into a kind the runner does not
run), suspend, cancel and malformed resumes along the way, plus the qualification workload, 6 PM cycles
and probe workflows (step bound, node raises, untyped key, unnamed and named failures, suspend with
proposals or nowhere, non-plain proposal, fan-out of 9 and unsuspended, branch failure, bad branch sets).
`corpus/summary.json` holds the counts. Files are gzip JSON lines, each under 210 KB.

Results (local, no lock):
- Replay on the step runner: identical in canonical JSON with the label replaced, 2508 of 2508.
- Twice: identical bytes (sha256 93271ded...).
- Crossing (`crossing.json`, run while both runners existed): each cycle alternated runners exchange by
  exchange, 933 LangGraph resumes advanced on the step runner and 923 the other way, 0 differences.
- Suite 130 rows replay/corpus, replay/twice, runner/plain: green.
- Suites that drive the adapter: 59 (20 rows), 62 (15 rows), green locally; 65, 128, 92 and the rest
  pending. They were edited for the label, file names and splice form, except suite 59's VELDO-0043 rows
  graph/runtime/installed, lifecycle, plain-data and tracing-off, whose assertions changed, and its row
  graph/runtime/rebuild-swap, which was removed; each with its reason in Premises, P5.

Falsifiers (registered as finding 262 against suite 130; red with the mutation, green without):
1. v262-notes-earlier-win: red, first difference pm-0.2 answer.proposals[0].evidence[1].
2. v262-suspend-with-proposals: red, first difference probe-suspend-proposal-0.1 answer.failure.
3. v262-step-not-advanced: red, first difference qualify-cycle.1 answer.resume.step. The spec's literal
   form cannot be produced as a red; see Premises, P1. The registered mutation drops the one increment
   every node takes, and is the nearest form that reaches an answer.

Retargeted VELDO-0043 and VELDO-0132 rows (same intent, at the step runner): see `removed-rows.json`
`retargeted`. All registered anchors resolve (0 moved). Suite 59's VELDO-0043 rows, driven locally
through the registry's own materialize and worker: 57 of 57 mutants red.

## AC2: parallel branches and Join

Built in the step runner: a fan-out suspends at PARALLEL; an exchange there is one superstep where every
branch not at the join runs its node on a deep copy of the pre-superstep view, entries merged after all
ran, in sorted branch order; one step per branch node that moved; the join runs only when all arrived,
then once as an ordinary node; superstep numbers match LangGraph's (the corpus covers widths 2 to 8).
Equivalence note: a branch failure ends the cycle with the branch's own failure code and detail, exactly
as the LangGraph runner did (the corpus binds this); it does not add the branch name (premise P4).

Rows (suite 130, green locally): fanout/superstep (both first nodes, one superstep number, step +2),
fanout/join-waits-for-all (one result in: join not run, still suspended; second still out: still not
run; both in: runs once), fanout/branch-isolation (a branch mutating notes, supplied results and
snapshot leaves its sibling's view unchanged), fanout/permuted (identical bytes), fanout/nine-refused.
Suite 128 (VELDO-0247 AC4 save rows, approval walk, forged branch) edited only for label and file names;
run pending.

Falsifiers: v262-join-on-first-input red on fanout/join-waits-for-all; v262-branches-share-state red on
fanout/branch-isolation. VELDO-0247's branch-around-approval falsifier is unchanged (pending in teeth-247).

Forged branch to land (suite 128, row fanout/forged-land-in-branch, green locally): a saved revision
`fanned-land` holds a land node reachable only after the join and an owner approval; the cycle is started
through the real Cycles service, and the runner it stages is forged (CY.runner_source swapped, as in
check/forged-branch) so the copy branch's assignment reports moving straight to `land`. The cycle refuses
invalid_response:trace at node assign_copy, branch copy; steps unchanged; no land, approval or join in the
trace; no branch_step, superstep or arrive event. Registered falsifier v262-cycle-branch-trace-unjudged
(the cycle's branch trace check disabled): red on that row only, through the teeth driver locally.

## AC3: removal

Removed in .veldo and engine (no pack carries them): control_graph_langgraph.py,
control_workflow_langgraph.py, control_graph_lock.py, control_graph_install.py,
runtime/langgraph-records.json; init_scaffold's entries and the records `_RUNTIME_ASSETS` entry;
control_runtime.py's activation, licenses, RECORD digests, requirement evaluation and LangGraph
qualification. control_runtime keeps check (assets present, VERSION read statically, interpreter clear of
every repository), qualify (start, suspend, advance, cancel through the production adapter), enforcement
(the step runner asset hidden; the graph probe answers runtime_unavailable absent and hidden); install
answers `runtime_removed` (unsupported_configuration). policy_contract keeps the option id, effect text
updated. mutation_case_inputs.json follows the file changes. Removed rows and mutations, each with its
reason: `removed-rows.json`.

init_scaffold: `retire_runtime` (on `--upgrade`) removes the retired regular files in the target's .veldo
and only plain directories named by a 64 hex digest under ~/.local/share/veldo/langgraph, following no
link, logging each removal and each refusal; `leftover_runtime` refuses before anything is written:
retired files, any installed module importing langgraph, langchain or langsmith (AST: imports at any
depth, literal import_module and __import__), and anything under the runtime directory.

The CLI (`init_scaffold.py <target>`, fresh or `--upgrade`) defaults its home to the account home from the
password database when `--home` is absent, so a fresh scaffold judges ~/.local/share/veldo/langgraph; the
library `scaffold()` keeps home None for a fresh scaffold, so suites pass their own home (as P2 argues for
factory setup).

Rows (suite 130, green locally): leftover/repository, leftover/setup, leftover/upgrade-link,
leftover/fresh-cli (the CLI with no home flag, its account home pointed at a scratch home holding a digest
directory, exits 1 refusing leftover_runtime naming it, nothing written; red before the CLI default: exit 0
and 258 files scaffolded).
Falsifiers: v262-lock-restored red (leftover/repository names engine/.veldo/control_graph_lock.py and the
scaffold of that tree refuses leftover_runtime naming it); v262-cycle-imports-langgraph red;
v262-upgrade-follows-link red; v262-fresh-cli-home-unjudged (the CLI home default back to None) registered
on leftover/fresh-cli, pending in teeth-262. `control_runtime.py enforcement` and the isolation probe: pending runs.

Sandbox read root: `~/.local/share/veldo/langgraph` removed from both agent_sandbox.json copies
(protected, in the footprint). Suite 101's installed-tools row asserted it present; it now asserts it
absent (footprint addition). Suite 101 locally: 214 passed, 2 failed; the same two rows fail identically
with the parent's three files restored (see Inherited reds).

Factory setup and its VELDO-0189 upgrade (control_factory_setup.py, footprint addition):
`check()` (shared by a fresh setup and a re-run, before either writes) on a re-run first retires the
account's runtime directory through `init_scaffold.retire_runtime` (digest-named plain directories only,
no link followed, each logged), then refuses `leftover_runtime:<path>` (all leftovers in `problems`) for
anything under the account's runtime directory, a retired file or retired import in the engine directory
it lays from, and on a fresh setup in an engine already at install_root/bin. A re-run's previous engine
holds the retired files and leaves whole with the VELDO-0189 engine switch (premise P3).
init_scaffold gained `leftover_modules(directory)` for flat engine directories, and `target=None` in
`leftover_runtime` and `retire_runtime` to judge or retire only the account runtime. Rows (suite 86_0189,
62 passed, 0 failed locally): upgrade/retires-langgraph (the re-run retires a scratch account's digest
directory, logs it, writes nothing in the installation; then a digest-named link is not followed and the
re-run refuses naming it, nothing written), setup/leftover-refused (a fresh setup refuses naming the
leftover with nothing written). Registered falsifier v262-factory-leftover-accepted: red on both rows when
run directly (59 passed, 3 failed: the two rows and install/assets, which compares the engine copy); through
the teeth driver its baseline is invalid on this host, as is the existing VELDO-0189 case
upgrade189-runtime-unrecorded (the confined worker cannot run suite 86_0189 here), so it is pending for the
lead in teeth-262.

## Premises

P1 (AC1 falsifier 3, the spec's form cannot be produced). The spec states the mutation "the step count is
not advanced for a node that failed" reds the replay row naming the first differing exchange and field.
It cannot: a failure answer carries no step. The veldo.graph/v1 failure shape is {schema, operation,
cycle_id, command_id, domain_uuid, repository_uuid, outcome, runtime, failure: {code, detail}} on
LangGraph as recorded and on the step runner, and the spec puts that shape out of scope for change. A
failed node also ends the exchange, so no later node sees the step either, and the other failure ends
(a raise, the step bound, a fan-out or suspend refusal, a branch failure) carry no step on either runner.
`falsifier3_literal.py` applies exactly the literal form (the three failure ends of an ordinary node keep
the step they entered with) to a scratch copy and replays the corpus: 2508 replayed, first difference
null, 519 failure answers, every one with failure fields {code, detail} and none carrying a step
(`falsifier3-literal.json`). Producing the red would need a field the spec forbids adding. So the
registered falsifier keeps the nearest form that reaches an answer (the increment every node takes).

P2 (account runtime directory in factory setup). The account's runtime directory is judged and retired
when the setup runs on the default installation (no install_root given, the production command), using
the account home from the password database; a caller naming its own install_root names `runtime_home`
too, or the account directory is not judged. Without this, every suite that runs factory setup with a
scratch install root would retire or refuse on this shared host's real runtime, which main's gate still
uses.

P3 (re-run engine directory). On a re-run the installed engine at install_root/bin is the previous engine,
which carries the retired modules; it is not judged for leftovers because the VELDO-0189 switch replaces
it whole and removes it, and removing files from it before the switch would leave the running service on
an incomplete engine.

P4 (AC2 branch failure, the spec's wording cannot hold). AC2 says a branch failure ends the cycle with
node_failed naming the branch. The step runner answers with the branch's own failure code and detail and
no branch name (`.veldo/control_graph_steps.py:264-267`; a branch node returning
{failure: {code: missing_evidence}} ends as missing_evidence). main's LangGraph runner answered exactly so
(main `.veldo/control_graph_langgraph.py:254-258`), and the corpus records that shape. AC1 requires every
recorded exchange to answer identically, label aside, so changing the code to node_failed or adding the
branch name would break the corpus equivalence AC1 forbids breaking. The failure shape is kept; AC2's
sentence is read as "a branch failure ends the cycle with that branch's failure".

P5 (AC1 "no edit other than the expected runtime label", suite 59's VELDO-0043 rows). AC1 says the suites
pass with no edit other than the label, the VELDO-0043 isolation rows of suite 59 included. These rows
changed their assertions, each because it imported langgraph, read its lock or judged its installer, all
of which AC3 removes:
- graph/runtime/installed (`scripts/suites/59_veldo_0043_graph.py:412`): the interpreter was the locked
  virtual environment under ~/.local/share/veldo/langgraph/<lock digest>, its directory listing and its
  package census were checked against control_graph_lock.PACKAGES; the lock and the environment are
  removed, so the row now checks the base interpreter, the step runner asset and FLAGS == ('-I', '-S', '-B').
- graph/runtime/lifecycle (`:717`): the audit asserted the child invoked
  langgraph.graph.state.CompiledStateGraph; it now asserts Exchange.run, and a no-foreign-modules condition
  (modules == []) was added, since the runner imports nothing outside the standard library.
- graph/runtime/plain-data (`:727`): the foreign objects a node returns were langgraph.types.Command and
  StateSnapshot, which needed langgraph importable; synthetic foreign.types classes of the same names
  replace them, and the expected node_failed answers are unchanged.
- graph/runtime/tracing-off (`:736`): the tracing switches were set to 'false' in the child's environment
  for LangGraph and LangSmith; with no LangGraph the environment no longer carries them, so the row asserts
  them absent (None) in the child and in graph.ENVIRONMENT, adds no-foreign-modules, and the source check
  names langgraph and socket instead of langgraph_sdk.
- graph/runtime/rebuild-swap (removed): it judged control_graph_install.py --rebuild; the installer is
  removed (`removed-rows.json`).

## Footprint additions

For the lead to amend the spec before landing:
- `scripts/suites/101_veldo_0208_landing_reuse.py`: its installed-tools row asserted the langgraph read
  root present in agent_sandbox.json; AC3 removes it, so the row now asserts it absent (one condition).
- `.veldo/control_factory_setup.py`, `engine/.veldo/control_factory_setup.py`: AC3's setup and upgrade
  wiring (the VELDO-0189 upgrade runs through this module's `check()` and `rerun()`).
- Protected paths changed (already listed in the spec's protected_paths): `scripts/agent_sandbox.json`,
  `engine/scripts/agent_sandbox.json` (the read root line removed), `scripts/mutation_case_inputs.json`
  (earlier increment).
- `control_factory_setup_upgrade.py` was not changed.

## AC4: performance

`measure.py` drove both runners through the production adapter, interleaved, 50 samples per case
(`performance.json`: method, host, CPU Intel Core Ultra 7 265K, load about 4.5, Python 3.12.3, every
sample, medians and p95). LangGraph import plus graph build, measured in its own child: about 300 ms.
Medians: LangGraph about 410 ms, step runner 20 to 25 ms; saved about 370 ms against a required 80
percent of import and build (about 248 ms) for code/start, qualification start and advance, fan-4 start
and advance. code/advance is reported not applicable: nothing ran on either runner (the code
definition's kinds are station kinds the runner does not run, so LangGraph never imported); open for the
reviewer.

Falsifiers: (1) a step runner sleeping 312 ms at start: claim false (`performance-falsifier.json`), exit
1. (2) v262-launch-without-S red on launch/stdlib-only, whose child importtime under -I -S -B shows only
standard library modules.

## Pending runs

`pending_runs.sh` (bash -n clean, set -u, no lock, no systemd-run): lint, template sync, corpus replay
and twice, falsifier 3's literal form (P1), control_runtime check, qualify, install, enforcement, the isolation probe and enforcement, 27
suites, the teeth findings 262, 43, 45, 132 and 247, requires.json current, and a clean-tree check that
ignores `pending-summary.txt`. Each step appends one line to `pending-summary.txt` with its exit code, the
selftest tally and a /tmp log path. Partial selftest runs never exit 0 by design: read the tally.

Local checks already run without the lock: lint pass; template sync pass; suites 130 (14 rows), 59 (20),
62 (15), 128 (47 checks), 86_0189 (62) green; 101 as under Inherited reds; falsifier3_literal premise holds; the nine 262 mutants red on their rows; suite 59's 57 VELDO-0043 mutants red; suite 62's fourteen 0045 mutants red after two
were retargeted; every registered anchor resolves.

## Inherited reds

Suite 101: `VELDO-0208 sandbox/unavailable-refuses-before-exec` and `sandbox/old-abi-refuses-before-exec`
fail locally with this branch's files and identically with the parent's agent_sandbox.json copies and
suite 101 restored (214 passed, 2 failed both ways; logs /tmp/v262-s101.log, /tmp/v262-s101-parent.log),
so they are not from this change; likely the nested sandbox of this session. Other suites not run
locally: see pending_runs.sh.
