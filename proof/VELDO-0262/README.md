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
- Suites that drive the adapter, edited only for the label, file names and splice form: 59 (20 rows),
  62 (15 rows), green locally; 65, 128, 92 and the rest pending.

Falsifiers (registered as finding 262 against suite 130; red with the mutation, green without):
1. v262-notes-earlier-win: red, first difference pm-0.2 answer.proposals[0].evidence[1].
2. v262-suspend-with-proposals: red, first difference probe-suspend-proposal-0.1 answer.failure.
3. v262-step-not-advanced: red, first difference qualify-cycle.1 answer.resume.step. Open: the declared
   form ("not advanced for a node that failed") cannot red anything, because a failure answer carries no
   step on LangGraph or here; the registered mutation drops the one increment every node takes.

Retargeted VELDO-0043 and VELDO-0132 rows (same intent, at the step runner): see `removed-rows.json`
`retargeted`. All registered anchors resolve (0 moved). Suite 59's VELDO-0043 rows, driven locally
through the registry's own materialize and worker: 57 of 57 mutants red.

## AC2: parallel branches and Join

Built in the step runner: a fan-out suspends at PARALLEL; an exchange there is one superstep where every
branch not at the join runs its node on a deep copy of the pre-superstep view, entries merged after all
ran, in sorted branch order; one step per branch node that moved; the join runs only when all arrived,
then once as an ordinary node; superstep numbers match LangGraph's (the corpus covers widths 2 to 8).
Equivalence note: a branch failure ends the cycle with the branch's own failure code and detail, exactly
as the LangGraph runner did (the corpus binds this); it does not add the branch name.

Rows (suite 130, green locally): fanout/superstep (both first nodes, one superstep number, step +2),
fanout/join-waits-for-all (one result in: join not run, still suspended; second still out: still not
run; both in: runs once), fanout/branch-isolation (a branch mutating notes, supplied results and
snapshot leaves its sibling's view unchanged), fanout/permuted (identical bytes), fanout/nine-refused.
Suite 128 (VELDO-0247 AC4 save rows, approval walk, forged branch) edited only for label and file names;
run pending.

Falsifiers: v262-join-on-first-input red on fanout/join-waits-for-all; v262-branches-share-state red on
fanout/branch-isolation. VELDO-0247's branch-around-approval falsifier is unchanged (pending in teeth-247).

Open: the row "a forged runner answer naming a land node from inside a branch is refused by the cycle"
is not added; suite 128's existing forged-branch and trace rows cover the cycle side, a new
branch-to-land row was not written in this increment.

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

Rows (suite 130, green locally): leftover/repository, leftover/setup, leftover/upgrade-link.
Falsifiers: v262-lock-restored red (leftover/repository names engine/.veldo/control_graph_lock.py and the
scaffold of that tree refuses leftover_runtime naming it); v262-cycle-imports-langgraph red;
v262-upgrade-follows-link red. `control_runtime.py enforcement` and the isolation probe: pending runs.

NOT DONE, outside the footprint (stopped and reported, not changed):
- The `~/.local/share/veldo/langgraph` read root is still in both agent_sandbox.json copies:
  scripts/suites/101_veldo_0208_landing_reuse.py (not in the footprint) asserts it is present, so removing
  it reds suite 101. Also, main and other branches on this shared host still run LangGraph-based gates.
- The VELDO-0189 factory upgrade and factory setup (control_factory_setup.py,
  control_factory_setup_upgrade.py) are not in the footprint, so the retire and the leftover refusal are
  wired into init_scaffold only. The account runtime directory is judged when a home is given or on
  `--upgrade`; a fresh scaffold without one judges the target only, because this host still holds the
  runtime that main's gate needs.

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
and twice, control_runtime check, qualify, install, enforcement, the isolation probe and enforcement, 27
suites, the teeth findings 262, 43, 45, 132 and 247, requires.json current, and a clean-tree check that
ignores `pending-summary.txt`. Each step appends one line to `pending-summary.txt` with its exit code, the
selftest tally and a /tmp log path. Partial selftest runs never exit 0 by design: read the tally.

Local checks already run without the lock: lint pass; template sync pass; suites 130 (13 rows), 59 (20),
62 (15) green; the nine 262 mutants red on their rows; suite 59's 57 VELDO-0043 mutants red; suite 62's fourteen 0045 mutants red after two
were retargeted; every registered anchor resolves.

## Inherited reds

None observed in the suites run locally. Suites not run locally: see pending_runs.sh.
