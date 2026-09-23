# VELDO-0043 proof (partial: AC3 built, AC1 and AC2 blocked)

The specification stays **ready**. This bundle is implementation evidence for AC3 and for the
engine-neutral adapter interface. It is not independent engineering review, owner approval,
service activation, or a full-gate result. The lead runs `bash scripts/verify.sh`; this branch
was checked only with the targeted commands listed under Verification.

## The blocker: the LangGraph dependency closure conflicts with C16

AC1 and AC2 require the actual installed LangGraph runtime. LangGraph was not installed for this
repository or its gate, because its dependency closure breaks the owner's C16 rule. C16 says a
conflicting component needs an owner decision, not an exception hidden in the implementation.

The closure was resolved once, in a throwaway virtual environment outside the repository
(`pip install langgraph`, Python 3.12.3). It pulled in 38 packages, recorded with licenses and
requirements in `dependency-closure.json`. Two of them conflict with C16:

- **xxhash 4.0.1** (Python binding, author Yue Du, `github.com/ifduyue/python-xxhash`). The GitHub
  account's public location is China. `langgraph/types.py` and `langgraph/pregel/_algo.py` import
  it unconditionally, and langsmith requires it too. This conflicts with "No Chinese-origin
  dependency anywhere".
- **langsmith 0.14.0**, required unconditionally by langchain-core. It is the client for the
  LangSmith hosted service, which www.langchain.com/pricing (read 2026-09-23) sells as Developer
  (free), Plus ($39 per seat per month) and Enterprise. LangGraph's own hosted deployment is sold
  only in the paid plans. This conflicts with "no library with free and paid tiers".

The owner needs to decide whether LangGraph may be installed with these dependencies. Nothing
in AC1 or AC2 can be proven until then. The probe environment was deleted afterward.

## What was built

**`.veldo/control_graph.py`**, standard library only, is the replaceable plain-data interface.
It covers `start`, `advance`, `suspend` and `cancel`, and the proposal/failure outcomes. Each
exchange is one versioned JSON request (`veldo.graph/v1`: cycle, command, domain and repository
identities, plus the accepted snapshot and workflow `{id, version, digest}`) and one JSON response.
The response is accepted only if its type is exactly a plain JSON type and it has exactly the
fields its outcome allows. Proposals are typed as `admission`, `priority` or `completion`.
Failures carry a named code. The runner runs as a separate process, started with `-I -B`, a fresh
empty working directory, a fixed five-variable environment and no inherited descriptors. With no
runtime, or an interpreter that is not present, the adapter refuses with `runtime_unavailable`.
A timeout, or an exit with no answer, is `unknown_outcome`, never success. `counts`, `observations`
(operation, identities, accepted input versions, outcome, refusal) and `pending()` provide the
declared observability.

**`.veldo/control_graph_isolation.py`** is the isolated-enforcement command:
`python3 .veldo/control_graph_isolation.py [--root REPOSITORY]`. It checks six installed
enforcement entries: `validate.py all`, `shape_gate.py`, `policy_check.py`, the `authorization.py`
command, `version.py`, and a graph-start probe. Each gets two checks. The first is a static import
closure over every import at any depth, every literal `import_module`/`__import__`, and every
sibling `.py` file named, followed transitively. The second is a real run in a child started with
`-I -S`, with an import finder that refuses and records any module that is neither standard
library nor an installed sibling. An entry passes only if both checks are clean, the run ends with
no uncaught exception, and its exit code is one of that entry's ordinary verdict codes. The graph
probe must report `runtime_unavailable`. Run over this repository, all six entries pass.

Both modules are registered in `_FILES` in both `init_scaffold.py` copies. The validator does not
import them, so they are not in `REQUIRED_SUBSTRATE`. Engine and installed copies are
byte-identical, and this checkout has no composed pack `.veldo` copies.

**Not built:** the LangGraph runner (`control_graph_langgraph.py`), the AC1 runtime rows, and the
AC2 nodes that assert admission, priority and completion or try store access. Also not built:
pinning, locking and installing the runtime. That is VELDO-0045, which depends on this spec.

## Criteria and rows

Suite `scripts/suites/59_veldo_0043_graph.py` has 6 rows. `observations.json` keeps its actual
observations.

| Criterion | Rows | Status |
|---|---|---|
| AC1 | `graph/shape/lifecycle`, `graph/shape/plain-data` (stub runner, shape only) | **Blocked.** Stub rows check the interface shape, which the spec permits. They are not runtime evidence. No actual LangGraph row exists. |
| AC2 | `graph/boundary/no-store-handle` (stub runner) | **Blocked.** The row proves the process boundary: the child sees only the five fixed variables, an empty working directory, descriptors 0-2 plus its own listing descriptor, not a real open SQLite store descriptor held by the parent, and no store path in its request or argv. No graph node exists yet. |
| AC3 | `graph/isolated-enforcement`, `graph/start-unavailable`, `graph/installed-assets` | **Built and driven.** The suite builds an installation from every `.veldo` asset the scaffolder installs, taken from the canonical engine, plus the production copies of the adapter, the isolation command and authorization. It runs the isolation command over that installation. Graph start with no runtime, and with an absent interpreter, both refuse `runtime_unavailable`, with counts and observations to match. |

## Driven negative controls (finding 43 in `scripts/check_teeth_mutations.py`)

Each mutation edits a temporary production copy, and each named row goes red by a failed
assertion, never by an exception or a hang. The gate's mutation stage also drives an unchanged
baseline and a byte-identical no-op copy for each control group. The adjacent `.diff` files are
the exact edits. `mutations.json` (reproduced by `drive.py`) records the isolation verdict each
mutant produced.

| Row | Mutation | What caught it | Rows red |
|---|---|---|---|
| `graph/isolated-enforcement` | `graph-authorization-imports-langgraph` (**declared falsifier**: top-level `import langgraph` in authorization) | static closure and isolated run | `graph/isolated-enforcement` |
| `graph/isolated-enforcement` | `graph-authorization-dynamic-runtime-import` (`__import__('lang' + 'graph')` in `is_authorized`) | isolated run only; the static walk cannot see it | `graph/isolated-enforcement` |
| `graph/isolated-enforcement` | `graph-authorization-unexercised-runtime-import` (`import langgraph.graph` on the two-key path the command never reaches) | static closure only; the run never reaches it | `graph/isolated-enforcement` |
| `graph/start-unavailable` | `graph-start-without-runtime-launches` (availability check removed) | start crashes (TypeError), recorded as a wrong answer | `graph/start-unavailable`, `graph/isolated-enforcement` |
| `graph/start-unavailable` | `graph-start-unavailable-mislabelled` (reports `unknown_outcome`) | wrong refusal name | `graph/start-unavailable`, `graph/isolated-enforcement` |

The AC1 and AC2 declared falsifiers are not driven, because their rows do not exist yet.

## Verification (targeted; the full gate was not run, per the brief)

```text
python3 -B scripts/selftest.py --suite 59_veldo_0043_graph
  59_veldo_0043_graph   6 passed   0.77s
  selftest (PARTIAL, 1 of 67 suites): 32 passed, 0 failed
python3 -B scripts/check_teeth_mutations.py --finding 43
  5 of 5 mutations rejected, baseline green (32 assertions), red rows as in the table
python3 .veldo/validate.py all             exit 0
bash scripts/check_generated.sh            generated: pass
bash scripts/check_template_sync.sh        pass (161 pairs)
bash scripts/check_lint.sh                 pass
python3 -B scripts/selftest.py --suite 07_warp_1103_completion_mandatory   1664 passed, 0 failed (footprint dogfood)
```

Two gate mutation-stage workers were emulated: a baseline, a no-op and two mutants, each run with
`check_gate_mutations.py --worker` inside a frozen-style copy (only `.veldo`, `engine/.veldo`,
`scripts` and `proof`, with the stage's fixed environment). The baseline and no-op were green, and
the mutants turned their target rows red. A frozen copy has no engine templates, so the scaffolder
cannot run there. That is why the suite builds its installation from `_FILES` instead.

## Gate cost and evidence size

`timing.json` measured 0.77-0.79 s per suite run, which is about 1.6 s for the gate's unit and
first-use runs. The mutation stage adds 9 worker invocations (4 controls and 5 mutants). The serial
driver took 8.35 s for 10 suite executions, so the serial upper bound is about 7.5 s. The total
upper bound is about 9.1 s, below the 60 s limit. This is a sum of measured components, not a
whole-gate before-and-after difference. (Exit status 2 in `timing.json` is the designed status of
a passing partial selector run.)

The proof is 44 KB of readable JSON, Markdown, Python and five small unified diffs. It holds no
full gate log, no binary or encoded data, no bytecode and no credential-shaped fixture text.
