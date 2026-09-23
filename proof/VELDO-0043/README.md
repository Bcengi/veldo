# VELDO-0043 proof

The specification stays **ready**. This bundle is implementation evidence for AC1, AC2 and AC3.
It is not independent engineering review, owner approval of the work, service activation, or a
full-gate result. The lead runs `bash scripts/verify.sh`; this branch was checked only with the
targeted commands under Verification.

## Owner decisions this build rests on

- **xxhash** (Chinese origin) and **langsmith** (client of a service sold in free and paid tiers)
  are named exceptions to C16, relayed by the lead on 2026-09-23: exact version pins, LangSmith
  tracing off.
- **langgraph-sdk** and **orjson** are named exceptions on the same terms, owner Telegram 28927
  ("Allow", answering 28926), with one more condition: the SDK client is never pointed at
  LangChain's hosting. Nothing in the adapter or runner constructs an SDK client.
- Owner Telegram 28929: dependencies of software we chose are approved automatically; only new
  software introduced on purpose is checked for origin and licensing.
- Owner Telegram 28931: LangGraph and every package in its closure are pinned to the latest stable
  release PyPI serves that satisfies the closure's own requirements.

## Stated limit (Release 2): same-account confinement

Under the owner's standing rulings (same-account threat model, no OS-user boundary, hardening
later), **what the adapter hands the graph child leads nowhere near the repository**, and that is
built and tested. The child gets a fixed environment, no inherited descriptors, a request that
carries no filesystem location, and a runner copy outside every repository. It runs in a working
directory outside every repository. **A deliberately hostile node can still reach the domain
process through `/proc/<parent>/cwd` and `/proc/<parent>/fd` as the same account, and write the
store.** Row `graph/authority/proc-limit` records that this is still true, so the limit is
visible, not a hidden pass. Real confinement (a separate mount and process view, or a separate
account) is Release 2.

## What was built

**`.veldo/control_graph.py`** (standard library only) is the replaceable plain-data interface
over `start`, `advance`, `suspend` and `cancel` and the proposal and failure outcomes.

- **Closed request.** Every digest must be exactly `sha256:<64 lowercase hex>`. Each supplied
  result is plain versioned data (`{id, version, digest, value}`). A resume is exactly
  `{position, step, notes}`, with the notes as text. A filesystem location anywhere in a request
  (after http(s) URLs are removed: any `/` or `\`, or a leading `~`) is the named refusal
  `path_in_request`. A request nested deeper than 32 is refused.
- **Closed answer.** The adapter accepts only declared keys, each of a declared plain type.
  Proposals are typed (a priority is a non-negative integer, an admission is `admit` or
  `decline`, completion evidence is well-formed digests). A resume is exactly
  `{position, step, notes as text}`, and a failure detail is bounded text. An answer nested deeper
  than 32 or larger than 1 MB is refused as `invalid_response` before parsing. The nesting is
  scanned without recursion. Every refusal is counted and observed.
- **Runtime evidence.** `Adapter.installed()` binds the adapter to the locked LangGraph's label
  (`runtime_evidence()`, langgraph 1.2.12). An answer with any other label is refused as
  `missing_evidence`. A failure may instead say that nothing ran (`{name: none}`), because a
  failure confers nothing.
- **Nothing handed leads to the repository.** Before each launch the runner is copied,
  content-addressed, to `<runtime>/veldo/runners/<sha256>.py`. It is launched from there with a
  fresh working directory under `<runtime>/veldo/work/`. A stage inside a Git repository is
  refused. The fixed environment sets all four LangSmith tracing switches to `false`, so tracing
  is off by construction.

**`.veldo/control_graph_lock.py`** is the exact lock as a readable data module: 38 packages,
each pinned to one version and to the sha256 of the one wheel resolved for CPython 3.12 on linux
x86_64 (manylinux). `digest()` is `b45d1e37f35885b242f64c70237db350ba3d9037a70b556c85d611b2d2e21c37`.
The Mac needs its own wheel hashes. VELDO-0045 later makes `engine/runtime/` the canonical lock
location and enforces the hashes at activation.

**`.veldo/control_graph_install.py`** (`python3 .veldo/control_graph_install.py`) builds the
runtime at `<account home>/.local/share/veldo/langgraph/<lock digest>/`. The account home comes
from the password database, never from `$HOME`. The runtime is a virtual environment **without
pip**. A throwaway tool environment's pip (the interpreter's bundled copy, deleted afterward)
runs `pip --python <runtime python> install --require-hashes --no-deps --only-binary=:all:` from
the lock. The runtime then holds exactly the 38 locked distributions. This machine's runtime was
deleted and rebuilt with it (7.3 s).

**`.veldo/control_graph_langgraph.py`** is the runner and the execution environment, not
enforcement. It builds a nonpersistent `StateGraph` with no checkpointer. **Every operation
executes the compiled graph.** `start` and `advance` enter it at the cycle's position, and
`suspend` and `cancel` enter its control nodes. The answer's runtime label is produced by the
nodes that ran: `executed_by()` calls `langgraph.config.get_config()`, which raises outside a
running graph. An answer where nothing ran (unsupported workflow, LangGraph not importable) says
`{name: none}`. Node output is limited to `next`, `suspend`, `proposals`, `failure` and `notes`.
Any other key is an untyped assertion (`node_failed`). The single emit gate turns the answer into
exact plain data with the notes as text, and refuses anything else as `node_failed`, naming the
class.

**`.veldo/control_graph_isolation.py`** records the runner as a launch target, never as an
import. Its graph-start probe resolves the runtime over an empty account home.

All five modules are in `_FILES` in both `init_scaffold.py` copies, not in `REQUIRED_SUBSTRATE`.
Every `.veldo` change is byte-identical in `engine/.veldo`. Enforcement code stays standard
library only.

## Review findings addressed (independent review of 456284a)

Each item is in its own commits: the row went red first, by a failed assertion, then the fix
turned it green.

| Item | Red commit (row red at the pre-fix code) | Fix commit | Rows |
|---|---|---|---|
| N1 runtime held an unlocked pip | `a2a8567` (census found pip 24.0) | `397b1f6` (install without pip; runtime rebuilt) | `graph/runtime/installed` |
| F5 over-deep answer escaped as RecursionError | `f2685cf` | `82a8c91` | `graph/shape/deep-answer` |
| F4 paths and loose digests accepted in requests | `0e0e153` (all 16 cases accepted) | `5dce564` | `graph/shape/closed-request` |
| F3 open answer schema; a LangGraph object in notes was accepted | `bd1ec9e` | `4479a3c` | `graph/shape/closed-response`, `graph/runtime/plain-data` (new notes-path workflow) |
| F2 suspend and cancel never ran LangGraph; label read from metadata | `85cf9e4` (suspend and cancel invoked no graph) | `0d5f212`, `d41c4e4` | `graph/runtime/lifecycle` |
| F1 the runner's own path and Git common directory led to the store | `3094a5f` (node wrote priority 99 through the runner's location in a linked worktree) | `23bd4f9` | `graph/authority/no-direct-write`, `graph/authority/proc-limit` |

The review's own reproductions were rerun against the fixed tree, adapted only to the new
interface (text notes, the `stage` key, the moved emit anchor). r1b, r2, r3, r4, r8 and r9 no
longer show their bug. r1's argv route is closed. Its two `/proc` routes still write, and that is
the stated limit above.

## Criteria and rows

Suite `scripts/suites/59_veldo_0043_graph.py` has 16 rows (42 assertions with the shared preamble).
The runtime rows run the suite's workflows, spliced into a copy of the production runner, on the
actual installed LangGraph through the production adapter. Because the runner is installed in
the domain's linked worktree, what the adapter stages and launches is exactly what production
would. The domain process works inside that checkout, keeps its own store connection and an
extra inheritable descriptor open, and the caller's environment turns all tracing switches on.
`observations.json` holds the unmutated run.

| Criterion | Rows | What they observe |
|---|---|---|
| AC1 | `graph/runtime/installed` | The runtime resolves at the passwd home path for this lock digest, with the stage set. Its distributions are exactly the 38 locked `(name, version)` pairs, with no `bin/pip`. |
| AC1 | `graph/runtime/lifecycle` | Start runs groom then size and suspends at rank. Suspend returns the same resume, advance with a versioned result returns the typed priority proposal, and cancel answers canceled. A failing node answers `missing_evidence`. Every one of these six answers is labelled langgraph 1.2.12, and **each of their six runner processes executed exactly one `CompiledStateGraph`** (counted at `Pregel.invoke`). The production runner (no workflows) answers `unsupported_workflow` labelled `none`. A stub answer through an adapter requiring runtime evidence is refused `missing_evidence`. |
| AC1 | `graph/runtime/plain-data` | A LangGraph `Command` or `StateSnapshot` in a proposal, and a `Command` in graph notes, each answer `node_failed` naming the class. No accepted non-failure answer carries `langgraph.` or `__class__`. All 16 accepted answers are exact plain JSON. |
| AC1 | `graph/runtime/tracing-off` | In each of the 16 runner processes the switches read `false`, langsmith reports tracing off, and no egress event occurs. The runner source has no SDK client use. |
| AC1 | `graph/shape/closed-response`, `graph/shape/deep-answer` (stub runner) | Notes that are an object (an encoded Command), an open resume, a resume without notes, and a position containing `/` are all refused `invalid_response`. A 20,000-deep answer is refused `invalid_response`, counted and observed. |
| AC2 | `graph/shape/closed-request` | Five malformed digests (a path after `sha256:`, a relative path, uppercase, short, malformed evidence) are refused. Unversioned or badly digested results, an open resume and object notes are refused `invalid_input`. Four paths (absolute, in notes, `~/`, `../`) are refused `path_in_request`. A result carrying an https URL is accepted. |
| AC2 | `graph/authority/no-direct-write` | The store lives in the Git common directory of a main repository; the runner source sits in the domain's linked worktree. A node searches from `argv[0]`, `__file__`, its working directory (ancestry, `.git` files followed to the common directory, and `git rev-parse --git-common-dir`), its own descriptors, its environment and its request, and writes to anything it finds. It finds nothing, and the store's tables are unchanged. Every runner ran from outside the suite's tree, and a stage inside the checkout is refused `runtime_unavailable`. |
| AC2 | `graph/authority/typed-proposals-only` | Admission, priority and completion assertions answer `node_failed` naming the key. An untyped proposal is refused. The one typed priority proposal is committed by the store's `upsert_entity` command as `owner`: version 2, priority 1, journal `seed-unit-1` then `commit-p-store`. |
| AC2 (stated limit) | `graph/authority/proc-limit` | A node reads `/proc/<parent>/cwd` (the domain checkout) and `/proc/<parent>/fd` (the parent's own store connection). It records both and writes nothing. The row asserts they are still reachable. |
| AC2 | `graph/boundary/no-store-handle` (stub) | The child sees the fixed nine variables, an empty working directory, descriptors 0 to 3, and no store path in its request or argv. |
| AC3 | `graph/isolated-enforcement`, `graph/start-unavailable`, `graph/installed-assets` | Unchanged: six enforcement entries pass the static closure and the isolated run, and graph start with no runtime refuses `runtime_unavailable`. |
| (shape) | `graph/shape/lifecycle`, `graph/shape/plain-data` | The stub interface shapes, as before. |

**When the runtime is absent**, every runtime row fails by name with the install command in its
message, for example `graph/runtime/installed: runtime absent at <path>; install it with:
python3 .veldo/control_graph_install.py`. The suite never skips and never installs.

**Tracing and egress.** The suite's runner block records every egress audit event and refuses it,
so no packet leaves even under a tracing mutant. It then ends with `os._exit` after its answer and
audit record. Before that refusal existed, two earlier drives let the tracing mutants attempt
`socket.getaddrinfo` and `socket.connect` toward LangSmith. No key was set, and the payload was
synthetic.

## Driven negative controls (finding 43, 24 mutations)

Each mutation edits a temporary production copy, and each named row goes red by a failed
assertion. `mutations.json` (reproduced by `drive.py`) records every red row and the observation
that explains it. The `.diff` files are the exact edits.

| Target row | Mutation | Rows red |
|---|---|---|
| `graph/isolated-enforcement` | `graph-authorization-imports-langgraph` (**AC3 declared**), `graph-authorization-dynamic-runtime-import`, `graph-authorization-unexercised-runtime-import` | `isolated-enforcement` |
| `graph/start-unavailable` | `graph-start-without-runtime-launches`, `graph-start-unavailable-mislabelled` | `start-unavailable`, `isolated-enforcement` |
| `graph/runtime/plain-data` | `graph-runner-emits-langgraph-object` (**AC1 declared**: the emit gate replaced by a class-tagging encoder; the notes-path object now reaches the adapter as a structure and is refused `invalid_response`, so the row reds on its named expectation) | plain-data, and every row that reads suspended notes |
| `graph/runtime/plain-data` | `graph-runner-tuple-as-plain` | plain-data |
| `graph/runtime/lifecycle` | `graph-suspend-without-graph` (suspend answers with a forged label and no graph; seen by the invocation count), `graph-runtime-evidence-unchecked` (the stub label accepted) | lifecycle |
| `graph/runtime/tracing-off` | `graph-child-inherits-caller-environment`, `graph-tracing-switch-on` | tracing-off (plus the boundary row for the first) |
| `graph/authority/no-direct-write` | `graph-child-inherits-working-directory` (**AC2 declared**: the node writes priority directly), `graph-child-inherits-store-descriptor`, `graph-runner-launched-in-place` (the runner run from the checkout; found through Git's common directory) | no-direct-write, and the rows downstream of the refused follow-up |
| `graph/authority/typed-proposals-only` | `graph-runner-accepts-untyped-assertion`, `graph-untyped-proposal-read-as-priority` | typed-proposals-only (plus plain-data rows for the second) |
| `graph/authority/proc-limit` | `graph-suspended-notes-dropped`, `graph-node-notes-ignored` (the row's observation channel) | proc-limit, lifecycle and the notes readers |
| `graph/shape/deep-answer` | `graph-deep-answer-unbounded`, `graph-deep-answer-unnamed` | deep-answer |
| `graph/shape/closed-request` | `graph-digest-prefix-only`, `graph-request-path-unchecked` | closed-request |
| `graph/shape/closed-response` | `graph-answer-resume-open`, `graph-answer-notes-any-plain` | closed-response (plus closed-request for the second) |

Result of `python3 -B scripts/check_teeth_mutations.py --finding 43`: 24 of 24 rejected, each
baseline green with 42 assertions (`{"mutations_rejected": 24, "green_suites": {"59_veldo_0043_graph.py": 42}}`).
The installed row has no registered mutation: it checks this machine's installed state, which
the suite never changes. The proc-limit row's two mutations target its observation channel,
because no production edit short of confinement changes what `/proc` exposes.

## The dependency closure

Resolved on 2026-09-23 with `pip install --dry-run --only-binary=:all: --report langgraph==1.2.12`
(Python 3.12.3, pip 24.0, linux x86_64). "Latest on PyPI" is the highest non-prerelease, non-yanked
release in `https://pypi.org/pypi/<name>/json`, checked 2026-09-23. Licenses come from PyPI
metadata and origin from the GitHub owner profiles. `dependency-closure.json` holds the same rows
with each package's requirements, wheel and sha256. Under owner Telegram 28929, every package
without a named exception is approved automatically as a dependency of software we chose.

| Package | Pinned | Latest on PyPI (2026-09-23) | License | Maintainer origin | Approval |
|---|---|---|---|---|---|
| annotated-types | 0.8.0 | 0.8.0 | MIT | github.com/annotated-types (org, no location); author Adrian Garcia Badaracco, Chicago, IL, US | dependency of software we chose: approved automatically (owner Telegram 28929) |
| anyio | 4.15.1 | 4.15.1 | MIT | github.com/agronholm, Alex Gronholm, Nurmijarvi, Finland | dependency of software we chose: approved automatically (owner Telegram 28929) |
| certifi | 2026.7.22 | 2026.7.22 | MPL-2.0 | github.com/certifi (org, no location); PyPI author Kenneth Reitz | dependency of software we chose: approved automatically (owner Telegram 28929) |
| charset-normalizer | 3.5.1 | 3.5.1 | MIT | github.com/jawah (org, France); Ahmed R. Tahri (Ousret), France | dependency of software we chose: approved automatically (owner Telegram 28929) |
| distro | 1.9.0 | 1.9.0 | Apache-2.0 | github.com/python-distro (org, no location); author Nir Cohen (nir0s, no location) | dependency of software we chose: approved automatically (owner Telegram 28929) |
| h11 | 0.16.0 | 0.16.0 | MIT | github.com/python-hyper (org, no location); author Nathaniel J. Smith (no location) | dependency of software we chose: approved automatically (owner Telegram 28929) |
| httpcore | 1.0.9 | 1.0.9 | BSD-3-Clause | github.com/encode (org, no location); author Tom Christie (no location) | dependency of software we chose: approved automatically (owner Telegram 28929) |
| httpcore2 | 2.13.1 | 2.13.1 | BSD-3-Clause | github.com/pydantic/httpx2; maintainer Pydantic Services Inc.; Samuel Colvin, London, UK | dependency of software we chose: approved automatically (owner Telegram 28929) |
| httpx | 0.28.1 | 0.28.1 | BSD-3-Clause | github.com/encode (org, no location); author Tom Christie (no location) | dependency of software we chose: approved automatically (owner Telegram 28929) |
| httpx2 | 2.13.1 | 2.13.1 | BSD-3-Clause | github.com/pydantic/httpx2; maintainer Pydantic Services Inc.; Samuel Colvin, London, UK | dependency of software we chose: approved automatically (owner Telegram 28929) |
| idna | 3.20 | 3.20 | BSD-3-Clause | github.com/kjd, Kim Davies (ICANN/IANA, no location) | dependency of software we chose: approved automatically (owner Telegram 28929) |
| jsonpatch | 1.33 | 1.33 | BSD (Modified BSD License) | github.com/stefankoegl, Stefan Koegl, Austria | dependency of software we chose: approved automatically (owner Telegram 28929) |
| jsonpointer | 3.1.1 | 3.1.1 | BSD (Modified BSD License) | github.com/stefankoegl, Stefan Koegl, Austria | dependency of software we chose: approved automatically (owner Telegram 28929) |
| langchain-core | 1.6.4 | 1.6.4 | MIT | github.com/langchain-ai, LangChain, United States | dependency of software we chose: approved automatically (owner Telegram 28929) |
| langchain-protocol | 0.0.19 | 0.0.19 | MIT | github.com/langchain-ai, LangChain, United States | dependency of software we chose: approved automatically (owner Telegram 28929) |
| langgraph | 1.2.12 | 1.2.12 | MIT | github.com/langchain-ai, LangChain, United States | dependency of software we chose: approved automatically (owner Telegram 28929) |
| langgraph-checkpoint | 4.2.0 | 4.2.0 | MIT | github.com/langchain-ai, LangChain, United States | dependency of software we chose: approved automatically (owner Telegram 28929) |
| langgraph-prebuilt | 1.1.0 | 1.1.0 | MIT | github.com/langchain-ai, LangChain, United States | dependency of software we chose: approved automatically (owner Telegram 28929) |
| langgraph-sdk | 0.4.5 | 0.4.5 | MIT | github.com/langchain-ai, LangChain, United States | named exception, owner Telegram 28927 "Allow" answering 28926; client never pointed at LangChain hosting |
| langsmith | 0.14.0 | 0.14.0 | MIT | github.com/langchain-ai, LangChain, United States | named exception (client of a free and paid tier service), owner approval relayed by the lead 2026-09-23; tracing off |
| orjson | 3.12.0 | 3.12.0 | MPL-2.0 AND (Apache-2.0 OR MIT) | github.com/ijl, no public name or location (commit mail at mailbox.org); origin NOT verified | named exception (origin not verified), owner Telegram 28927 "Allow" answering 28926 |
| ormsgpack | 1.12.2 | 1.12.2 | Apache-2.0 OR MIT | github.com/ormsgpack (org); Aviram Hassan, Tel Aviv, Israel; Emanuele Giaquinta (exg, no location) | dependency of software we chose: approved automatically (owner Telegram 28929) |
| packaging | 26.3 | 26.3 | Apache-2.0 OR BSD-2-Clause | github.com/pypa, Python Packaging Authority, United States | dependency of software we chose: approved automatically (owner Telegram 28929) |
| pydantic | 2.13.5 | 2.13.5 | MIT | github.com/pydantic (org, no location); Samuel Colvin, London, UK | dependency of software we chose: approved automatically (owner Telegram 28929) |
| pydantic_core | 2.46.5 | 2.49.0 | MIT | github.com/pydantic (org, no location); Samuel Colvin, London, UK | dependency of software we chose: approved automatically (owner Telegram 28929) |
| PyYAML | 6.0.3 | 6.0.3 | MIT | github.com/yaml, The YAML Project (org, no location) | dependency of software we chose: approved automatically (owner Telegram 28929) |
| requests | 2.34.2 | 2.34.2 | Apache-2.0 | github.com/psf, Python Software Foundation; maintainer Ian Stapleton Cordasco, Madison, WI, US | dependency of software we chose: approved automatically (owner Telegram 28929) |
| requests-toolbelt | 1.0.0 | 1.0.0 | Apache-2.0 | github.com/requests (org); Ian Stapleton Cordasco, Madison, WI, US | dependency of software we chose: approved automatically (owner Telegram 28929) |
| sniffio | 1.3.1 | 1.3.1 | MIT OR Apache-2.0 | github.com/python-trio (org, no location); author Nathaniel J. Smith | dependency of software we chose: approved automatically (owner Telegram 28929) |
| tenacity | 9.1.4 | 9.1.4 | Apache-2.0 | github.com/jd, Julien Danjou, Toulouse, France | dependency of software we chose: approved automatically (owner Telegram 28929) |
| truststore | 0.10.4 | 0.10.4 | MIT | github.com/sethmlarson, Seth Larson, Minneapolis, MN, US | dependency of software we chose: approved automatically (owner Telegram 28929) |
| typing-inspection | 0.4.4 | 0.4.4 | MIT | github.com/pydantic; Victorien Plot (Viicos), Amsterdam, Netherlands | dependency of software we chose: approved automatically (owner Telegram 28929) |
| typing_extensions | 4.16.0 | 4.16.0 | PSF-2.0 | github.com/python, Python (org) | dependency of software we chose: approved automatically (owner Telegram 28929) |
| urllib3 | 2.8.0 | 2.8.0 | MIT | github.com/urllib3 (org); Andrey Petrov, Toronto, Canada; Seth Larson, Minneapolis, MN, US | dependency of software we chose: approved automatically (owner Telegram 28929) |
| uuid_utils | 0.17.1 | 1.0.0 | BSD-3-Clause | github.com/aminalaee, Amin Alaee, Netherlands | dependency of software we chose: approved automatically (owner Telegram 28929) |
| websockets | 16.1.1 | 17.1 | BSD-3-Clause | github.com/python-websockets (org); Aymeric Augustin, Paris, France | dependency of software we chose: approved automatically (owner Telegram 28929) |
| xxhash | 4.0.1 | 4.0.1 | BSD-2-Clause | github.com/ifduyue, Yue Du, location China | named exception (Chinese origin), owner approval relayed by the lead 2026-09-23 |
| zstandard | 0.25.0 | 0.25.0 | BSD-3-Clause | github.com/indygreg, Gregory Szorc, San Francisco, CA, US | dependency of software we chose: approved automatically (owner Telegram 28929) |

Three pins are below the latest release, each because of a requirement in the closure itself:

- **pydantic_core 2.46.5** (latest 2.49.0): pydantic 2.13.5, the latest pydantic, requires
  `pydantic-core==2.46.5`.
- **uuid_utils 0.17.1** (latest 1.0.0): langchain-core 1.6.4 and langsmith 0.14.0 both require
  `uuid-utils<1.0,>=0.12.0`.
- **websockets 16.1.1** (latest 17.1): langgraph-sdk 0.4.5 requires `websockets<17,>=14`.

## Verification (targeted; the full gate was not run, per the brief)

```text
python3 -B scripts/selftest.py --suite 59_veldo_0043_graph    16 passed, 5.64-5.79 s (42 assertions)
python3 -B scripts/check_teeth_mutations.py --finding 43      24 of 24 rejected, baseline green, 277.5 s
python3 -B proof/VELDO-0043/drive.py                          {"mutations": 24, "all_target_rows_red": true}
python3 .veldo/validate.py all                                exit 0
bash scripts/check_generated.sh                               generated: pass
bash scripts/check_template_sync.sh                           pass
bash scripts/check_lint.sh                                    pass
python3 .veldo/control_graph_isolation.py                     isolated enforcement: pass
```

## Gate cost (`timing.json`)

The suite takes 5.6-5.8 s (16 rows; 0.77 s before the runtime rows), about 5 s added per run, under
the 60 s limit. It makes 17 LangGraph runner processes and 17 stub processes. The serial driver
`--finding 43` takes 277.5 s for 24 cases (48 suite runs), against 8.35 s for 5 cases before this
work. In the gate's mutation stage (8 workers; after the merge of main, a combined cap of 2 s per
registered case), finding 43 contributes 24 mutants and 6 controls near 5.7 s each, about 170
worker seconds. That is about 22 s of wall time at 8 workers, against the 48 s of cap its 24 cases
add.

Runner copies accumulate under `<runtime>/veldo/runners/`, one per distinct runner content (22
after this work, about 15 KB each). Collecting them is hardening, left for later. Working
directories and audit records are removed after each exchange and each run.

## Evidence size

The proof is about 160 KB: readable JSON, Markdown, Python and 24 small unified diffs. There is no
full log, no binary or encoded data, no bytecode and no credential-shaped text. The sha256
values are public wheel digests.
