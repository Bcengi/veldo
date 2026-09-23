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
visible, not a hidden pass. **A grandchild a node starts in its own session leaves the child's
process group** and outlives the exchange; the adapter kills the whole process group, not
descendants that leave it. Real confinement and containment (a separate mount and process view,
or a separate account) are Release 2.

## What was built

**`.veldo/control_graph.py`** (standard library only) is the replaceable plain-data interface
over `start`, `advance`, `suspend` and `cancel` and the proposal and failure outcomes.

- **Closed request.** Every digest must be exactly `sha256:<64 lowercase hex>`. Each supplied
  result is plain versioned data (`{id, version, digest, value}`). A resume is exactly
  `{position, step, notes}`, with the notes as text. Identifiers refuse `/`, `\`, `..` and control
  characters. A value or key naming a filesystem location is the named refusal
  `path_in_request`: an ASCII path separator, one of the listed look-alikes (such as U+2215) or
  an NFKC compatibility form of one (such as U+FF0F), a percent-encoded separator, or a leading
  `~`. Encodings a reader must decode first (base64, double percent-encoding, a path split across
  fields) are not seen. **There is no URL exemption.** The closed request schema declares no URL
  field, and a key name the author writes cannot switch the check off. A request nested deeper
  than 32, larger than 1 MB, or not serializable (for example an integer past the conversion
  limit) is refused `invalid_input`. The bound is walked without recursion and stops early.
- **Closed answer.** The adapter accepts only declared keys, each of a declared plain type.
  Proposals are typed (a priority is a non-negative integer, an admission is `admit` or
  `decline`, completion evidence is well-formed digests). A resume is exactly
  `{position, step, notes as text}`, and a failure detail is bounded text. An answer must be
  strict UTF-8 (json would otherwise accept UTF-16 and UTF-32, which a byte scan cannot follow).
  An answer nested deeper than 32 or larger than 1 MB is refused as `invalid_response` before
  parsing, and a parser RecursionError is also `invalid_response`. The nesting is scanned
  without recursion. Every refusal is counted and observed.
- **Runtime evidence.** `Adapter.installed()` binds the adapter to the locked LangGraph's label
  (`runtime_evidence()`, langgraph 1.2.12). An answer with any other label is refused as
  `missing_evidence`. A failure may instead say that nothing ran (`{name: none}`), because a
  failure confers nothing.
- **Nothing handed or resolved leads to the repository.** Staging lives in a per-account
  directory, `<passwd home>/.local/state/veldo/graph-stage/`, separate from the runtime, which
  holds only what the lock installed. Before each launch the runner is copied, content-addressed,
  to `<stage>/runners/<sha256>.py`. It is launched from there with a fresh working directory
  under `<stage>/work/`. The child's stdin and stdout are anonymous files under `<stage>/work/`,
  never the domain process's TMPDIR. **Below the stage root, the adapter follows no link it did
  not make. The stage root and its ancestors are trusted**, except that the root is judged, as
  written and as resolved, to lie outside every repository and outside the runtime. Each of
  these is refused by name as `runtime_unavailable`, counted and observed:
  - a link at `runners/`, `work/` or the staged runner;
  - any of them not resolving under the resolved stage root;
  - `runners/` inside a repository;
  - a working directory, under `work/`, that fails `inside_repository()` immediately before
    launch (it is then removed);
  - any non-link bad shape (a file where a stage directory belongs, a directory where the staged
    runner belongs, a file at the root), any other stage OSError, and a symlink loop or a NUL
    byte, each with its reason;
  - a runtime whose interpreter, or any `pyvenv.cfg` value, lies inside a repository, or cannot
    be judged. The interpreter is resolved component by component the way the kernel does: a link
    at any component, a relative target from the link's own directory, and a later `..` taken
    after the link. Every run end on the way is judged. `pyvenv.cfg` values are parsed as
    `key = value` lines and judged whole, with surrounding quotes removed. The command line is
    split with shlex, each option's `=value` is judged too, and so is every run of
    space-separated words starting with `/`. Judging runs is quadratic in candidates and cubic in
    characters for a command of n words; the installer writes one short command line, so this
    stays small. Each problem is reported once, and the refusal names the recovery command,
    `python3 .veldo/control_graph_install.py --rebuild`.

  **`inside_repository()` asks Git.** It runs `git rev-parse --absolute-git-dir` through the
  shared Git boundary (`.veldo/git_process.py`), under a fixed environment. It asks from the path
  as written and as resolved, and from the first directory on every other filesystem above it,
  because Git's discovery stops at a filesystem boundary and a child's Git can be told not to.
  Git's own discovery covers every ancestor between. The earlier shape checks stay as a second
  opinion: a `.git` entry (even one Git cannot read), a directory named `.git`, or `HEAD` with
  `objects/`. A Git directory planted as `HEAD` + `refs/` + `commondir`, a shape only Git
  recognizes, is refused in `runners/`, `work/` and at the stage root. The fixed environment
  sets all four LangSmith tracing switches to `false`.
- **Process group.** The child runs in its own session, reading its request from and writing its
  answer to anonymous files, not pipes. It is waited on without reaping, and its whole process
  **process group** is killed on the deadline and on every exit path: a normal answer, a
  nonzero exit, a refused answer, and an exception or interrupt inside the adapter while it
  waits. A grandchild that starts its own session leaves the group and outlives the exchange.
  That is a stated limit; real containment is Release 2.

**`.veldo/control_graph_lock.py`** is the exact lock as a readable data module: 38 packages,
each pinned to one version and to the sha256 of the one wheel resolved for CPython 3.12 on linux
x86_64 (manylinux). `digest()` is `b45d1e37f35885b242f64c70237db350ba3d9037a70b556c85d611b2d2e21c37`.
The Mac needs its own wheel hashes. VELDO-0045 later makes `engine/runtime/` the canonical lock
location and enforces the hashes at activation.

**`.veldo/control_graph_install.py`** (`python3 .veldo/control_graph_install.py [--rebuild]`) builds the
runtime at `<account home>/.local/share/veldo/langgraph/<lock digest>/`. The account home comes
from the password database, never from `$HOME`. The runtime is created from the **resolved base
interpreter** (`realpath(sys._base_executable)`), so `pyvenv.cfg` never names a repository's
virtual environment. A creating interpreter or prefix inside a repository is refused by name.
The runtime is a virtual environment **without pip**. A throwaway tool environment's pip (the interpreter's bundled copy, deleted afterward)
runs `pip --python <runtime python> install --require-hashes --no-deps --only-binary=:all:` from
the lock. The runtime then holds exactly the 38 locked distributions. This machine's runtime was
deleted and rebuilt with it (7.3 s), then rebuilt again with `--rebuild`, which builds beside the
old runtime, swaps it in and only then removes the old one (7.7 s). Its old in-runtime stage
directory was removed when
staging moved out. A test install from a repository's virtual environment into a temporary home
recorded `command = /usr/bin/python3.12 -m venv ...`.

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

## Second review findings addressed (fresh review of ccfebdb..29271b8)

origin/main was merged first (`92e8588`: both sides of the scaffold and driver registry
conflicts kept, `requires.json` regenerated with 73 suites). Each item has its own commits: the
row went red first, by a failed assertion, then the fix turned it green.

| Item | Red commit | Fix commit | Rows |
|---|---|---|---|
| 1, 2, 7: stage links followed; stage inside the runtime; suite wrote into the account stage | `7585c4e` (a node's `work` link moved the next child into the checkout, which wrote priority; a `runners` link made the adapter write its runner copy there) | `b948abe` | `graph/authority/stage-links`, `graph/runtime/installed` (runtime holds only the lock's files; the stage is separate) |
| 3: runtime `pyvenv.cfg` named the repository that created it | `379ffe1`, then `63cf20f` (the creator reached through a link) | `798323b`, `41568da` | `graph/runtime/pyvenv-clean` |
| 4: over-deep UTF-16 answer escaped as RecursionError | `d5a48b4` | `850991b` | `graph/shape/deep-answer` |
| 5: URL exemption, look-alike separators, unsafe identifiers, unbounded request size | `e7f771f` (11 of 14 new cases accepted) | `ee9e22a`, `c5f143d` | `graph/shape/closed-request` |
| 6: proc-limit mutants broke an adjacent channel | none (driver only) | `9cec78d` (real falsifier: the adapter made non-dumpable; the two notes-path mutants retired, recorded in History) | `graph/authority/proc-limit` |
| 8: files under the runtime not verified against RECORD | not built | recorded below as a VELDO-0045 open item | none |
| 9: a node's subprocess outlived the deadline | `e41d1a4` (both leftovers outlived the exchange) | `3c03cc6` | `graph/boundary/process-group` |

The review's r10, r11, r12, r13, r14 and r16 were rerun against the fixed tree, adapted only to
the moved stage path. r10 and r11 now refuse `runtime_unavailable`. r12 refuses, and nothing is
written into the checkout. r14 is refused `invalid_response`. r16's leftover no longer runs. r13
prints only its two NOTE cases, which no text check can see: a path split across list items, and
256 KB of astral characters inside the 64K-character notes bound.

**Open item for VELDO-0045 (review item 8, not built here).** The census checks distribution
metadata only. A file planted under the runtime (for example a `.pth` in site-packages) is not
detected. VELDO-0045's runtime integrity check must verify every file under the runtime against
the lock and each distribution's RECORD before use.

## Third review findings addressed (fresh review of cef2552)

origin/main was merged first (`abed2bf`, no conflicts; the faster mutation driver was not on main
yet). The same discipline applies: red commit first, then the fix.

| Item | Red commit | Fix commit | Row |
|---|---|---|---|
| 1 (p2): pyvenv.cfg split on whitespace, missing paths with spaces and quotes | `8ba9ed6` (none of five value cases caught) | `9952954` | `graph/runtime/pyvenv-clean` |
| 2 (p3): the interpreter judged only at its realpath | `8ba9ed6` (the link-chain case) | `b2587ae` | `graph/runtime/pyvenv-clean` |
| 3 (p1): a gitfile planted in `runners/` | `8269e90` (the next child wrote priority) | `f250061` (and a refused working directory is removed) | `graph/authority/stage-links` |
| 4 (p4): non-link bad stage shapes escaped as bare OSErrors | `500cecc` (all five) | `f27b328`, `683e913` | new `graph/authority/stage-shapes` |
| 5 (p6): stdin and stdout in the parent's TMPDIR | `d0ebc75` (they named the checkout) | `c441b61`, `683e913` | `graph/authority/no-direct-write` |
| 6 (p7): unserializable values escaped | `01cdd2a` | `4140d6a` | `graph/shape/closed-request` |
| URL exemption removed (the lead's decision) | `f648076` (an author-named `source_url` accepted) | `511aab5` | `graph/shape/closed-request` |
| Minor: the refusal names the recovery command; installer `--rebuild` | `86a942b` | `7236143` | `graph/runtime/pyvenv-clean` |
| p5 (found on rerun): a stage root written inside a repository, or linked into the runtime | `3389e01` | `d68131f` | `graph/authority/stage-shapes` |

The review's p1 to p8 were rerun against the fixed tree:
- p1 through p4 and p6 no longer show their bug.
- p5 shows only its NOTE cases: a stage root or an ancestor that is a link to an ordinary directory, which is trusted.
- p7 shows only its NOTE cases: encodings a reader must decode first.
- p8: the process group dies on every exit path (normal, deadline, exception, KeyboardInterrupt, nonzero exit, refused answer). The only survivor is the new-session grandchild, which is the stated limit.

## Round 5 findings addressed (review of cef2552..f770b91)

origin/main was merged twice (`eb36415`, and `193076b`, which brings the parallel mutation
driver). Red commit first, then the fix, as before.

| Item | Red commit | Fix commit | Row |
|---|---|---|---|
| 1 (d2, d6b): the adapter re-implemented Git's repository rules; `HEAD` + `refs/` + `commondir` planted in `runners/`, `work/` or the stage root was not recognized | `d52c1ac` (all three launched and wrote priority) | `2c758ad` (ask Git; the shape checks stay as a second opinion; `work/` is judged through the child's working directory) | `graph/authority/stage-links` |
| 2 (d3): the interpreter was judged link by link, not component by component | `5f4fcce` (the relative-`..` case; the directory-link case was already caught by asking Git) | `af02d40` | `graph/runtime/pyvenv-clean` |
| 3 (d4, d6a): symlink loops and NUL bytes escaped | `0779089` (RuntimeError and ValueError escaped, and a loop in a pyvenv.cfg path launched) | `31b344b` | `graph/authority/stage-shapes` |
| d5: venv `--prompt="<path>"` not judged; repeated problems | `ea439f6` | `5001f9b` | `graph/runtime/pyvenv-clean` |
| Undriven behaviors: quote stripping, the stage-in-runtime check as written and against the resolved prefix, removal of a refused working directory, relative-link joining | cases added in `5001f9b`, `d52c1ac` and `af02d40` | the reviewer's ten mutants registered, nine as they were (the relative-join one is re-targeted to the new walker) | pyvenv-clean, stage-shapes, stage-links |
| Minor: rebuild swap and restore on a failed second rename; request file OSError; each problem once | `798bfbf` | `c422738`, `5001f9b` | new `graph/runtime/rebuild-swap` |

The review's d2, d3, d4, d6, p1, p3 and p5 were rerun against the fixed tree. The only adaptations
were the probe harness now copying `git_process.py`, which the adapter needs beside it, and d3
calling the new walker. Results:
- d2, d3 (A and B), d6a, d6b, p1 and p3 are refused by name.
- d4's loop is refused by name. d4's NUL NOTE remains: `runtime_problems()` itself raises there, and the adapter names it.
- d5 keeps only NOTE cases that Python does not read as paths, such as an unquoted `--opt=` path containing a space.
- p5 keeps only its NOTE cases for a trusted stage root that is a link.

**The installer's `--rebuild` in a row.** Row `graph/runtime/rebuild-swap` runs the rebuild's own
swap step, `swap_in()`, on temporary directories. It checks that the new runtime goes in and the
old one leaves, and that a failed second rename puts the old runtime back. A full `--rebuild`
downloads the locked wheels from PyPI and installs them. That is what the earlier ruling keeps out
of the gate and the suite, so it was run by hand on this machine instead.

**Not given a row.** An OSError while writing the request file now refuses `runtime_unavailable`
and removes the working directory, but no row forces it. It needs the stage's `work/` to fail
after the working directory inside it was created, which only a full disk or a race produces.

## Criteria and rows

Suite `scripts/suites/59_veldo_0043_graph.py` has 21 rows (47 assertions with the shared preamble).
The runtime rows run the suite's workflows, spliced into a copy of the production runner, on the
actual installed LangGraph through the production adapter. Because the runner is installed in
the domain's linked worktree, what the adapter stages and launches is exactly what production
would. The domain process works inside that checkout, keeps its own store connection and an
extra inheritable descriptor open, and the caller's environment turns all tracing switches on.
Every adapter in the suite stages into a temporary directory. The row `graph/authority/stage-links`
checks that the account's runtime and stage are left untouched, entry by entry.
`observations.json` holds the unmutated run.

| Criterion | Rows | What they observe |
|---|---|---|
| AC1 | `graph/runtime/installed` | The runtime resolves at the passwd home path for this lock digest, and its stage at `<passwd home>/.local/state/veldo/graph-stage`. The runtime directory holds only `bin`, `include`, `lib`, `lib64`, `pyvenv.cfg` and `veldo-lock.txt`. Its distributions are exactly the 38 locked `(name, version)` pairs, with no `bin/pip`. |
| AC1 | `graph/runtime/pyvenv-clean` | The installed runtime's `pyvenv.cfg` paths lie outside every repository. A runtime whose `pyvenv.cfg` `command` names a repository's `.venv/bin/python3` (itself a link to the system python) is refused `runtime_unavailable`, and nothing launches. Each `pyvenv.cfg` value is judged whole: a command whose repository path has a space (unquoted and quoted), `home`, `executable` and `base-prefix` naming a repository `.venv`. The interpreter is judged at every hop of its link chain: a runtime python linking through a repository `.venv` to the system python is caught. The refusal names `python3 .veldo/control_graph_install.py --rebuild`. The interpreter is resolved the way the kernel does: runtimes reaching the system python through a repository `.venv` by a directory link on a hop, or by a relative `inner/../python3` whose `..` follows a link first, are refused. A quoted `home`, and a venv `--prompt="<path>"` option naming a repository, are judged. Each problem is reported once. |
| AC1 | `graph/runtime/rebuild-swap` | The installer's rebuild swap puts the new runtime in and removes the old one. When the second rename fails, the old runtime is back in place, and no retired copy is left. |
| AC1 | `graph/runtime/lifecycle` | Start runs groom then size and suspends at rank. Suspend returns the same resume, advance with a versioned result returns the typed priority proposal, and cancel answers canceled. A failing node answers `missing_evidence`. Every one of these six answers is labelled langgraph 1.2.12, and **each of their six runner processes executed exactly one `CompiledStateGraph`** (counted at `Pregel.invoke`). The production runner (no workflows) answers `unsupported_workflow` labelled `none`. A stub answer through an adapter requiring runtime evidence is refused `missing_evidence`. |
| AC1 | `graph/runtime/plain-data` | A LangGraph `Command` or `StateSnapshot` in a proposal, and a `Command` in graph notes, each answer `node_failed` naming the class. No accepted non-failure answer carries `langgraph.` or `__class__`. All 23 accepted answers are exact plain JSON. |
| AC1 | `graph/runtime/tracing-off` | In each of the 23 launched runner processes the switches read `false`, langsmith reports tracing off, and no egress event occurs. The runner source has no SDK client use. |
| AC1 | `graph/shape/closed-response`, `graph/shape/deep-answer` (stub runner) | Notes that are an object (an encoded Command), an open resume, a resume without notes, and a position containing `/` are all refused `invalid_response`. A 20,000-deep UTF-8 answer is refused by the bounded scan itself (`answer nests deeper than 32`). A 5,000-deep UTF-16-LE answer, built to desynchronize a byte scanner, is refused `invalid_response`. Both are counted and observed. |
| AC2 | `graph/shape/closed-request` | Five malformed digests (a path after `sha256:`, a relative path, uppercase, short, malformed evidence) are refused. Unversioned or badly digested results, an open resume and object notes are refused `invalid_input`. Paths are refused `path_in_request` in every case tried: absolute, in notes, `~/`, `../`, `http://` or `https://x` followed by a path, a path inside JSON notes, `xhttp://`, `file://`, U+2215, U+FF0F, `%2F`, a path used as a dict key, and https URLs under author-named `source_url` or nested `x_url` keys. The closed request schema declares no URL field, so no value is exempt. Identifiers with NUL and newline, or `..`, a 2 MB value, a self-referential list, and an integer past the conversion limit (as a value or a version) are refused `invalid_input`. |
| AC2 | `graph/authority/no-direct-write` | The store lives in the Git common directory of a main repository; the runner source sits in the domain's linked worktree. A node searches from `argv[0]`, `__file__`, its working directory (ancestry, `.git` files followed to the common directory, and `git rev-parse --git-common-dir`), its own descriptors, its environment and its request, and writes to anything it finds. It finds nothing, and the store's tables are unchanged. Every runner ran from outside the suite's tree, and a stage inside the checkout is refused `runtime_unavailable`. With the domain process's TMPDIR inside the checkout, the child's own stdin and stdout still resolve under `<stage>/work/`. |
| AC2 | `graph/authority/stage-links` | Knowing only its own `argv[0]`, a node swaps `<stage>/work`, and later `<stage>/runners`, for a link to `/proc/self/cwd`. The next exchange is refused `runtime_unavailable` each time. Nothing is written into the checkout, the store is unchanged, and the account's runtime and stage are untouched. A gitfile a node plants at `<stage>/runners/.git`, pointing at the authority repository, gets the next exchange refused before the child's script directory can reach it. `HEAD` + `refs/` + `commondir` planted in `runners/`, in `work/` and at the stage root is refused each time, because the adapter asks Git. The `work/` case is refused through the child working directory, and nothing is left behind in `work/`. A `.git` entry Git itself cannot read is caught by the shape check. |
| AC2 | `graph/authority/stage-shapes` (stub) | Each non-link bad shape at the stage is refused `runtime_unavailable` with its own reason, counted and observed: `runners` a file, `work` a file, the staged runner a directory, the stage root a file, and `runners` unwritable with a tampered runner. So are a stage root written inside a repository that resolves outside one, and a stage root linked into the runtime. Each of these is refused by name, counted and observed: a stage root that is a self-link, a `pyvenv.cfg` path that is a symlink loop, a NUL byte in a `pyvenv.cfg` value, a stage written inside the runtime that resolves outside it, and a stage placed inside the real runtime when the runtime is named through a link. |
| AC2 | `graph/authority/typed-proposals-only` | Admission, priority and completion assertions answer `node_failed` naming the key. An untyped proposal is refused. The one typed priority proposal is committed by the store's `upsert_entity` command as `owner`: version 2, priority 1, journal `seed-unit-1` then `commit-p-store`. |
| AC2 (stated limit) | `graph/authority/proc-limit` | A node reads `/proc/<parent>/cwd` (the domain checkout) and `/proc/<parent>/fd` (the parent's own store connection). It records both and writes nothing. The row asserts they are still reachable. |
| AC2 | `graph/boundary/process-group` (stub) | A node's own background subprocess, left behind at a 0.5 s deadline (`unknown_outcome`) or after a normal answer, never writes its marker: the whole group died with the exchange. |
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

## Driven negative controls (finding 43, 61 mutations)

Each mutation edits a temporary production copy, and each named row goes red by a failed
assertion. `mutations.json` (reproduced by `drive.py`) records every red row and the observation
that explains it; the `.diff` files are the exact edits. The driver runs one unmutated baseline per
suite, and the gate's mutation stage adds a baseline and a byte-identical no-op per control group.

The three declared falsifiers are marked:
- **AC1**: the runner writes LangGraph objects into the domain response through a class-tagging
  encoder. The notes-path object reaches the adapter as a structure and is refused.
- **AC2**: the graph child runs in the caller's checkout and writes priority directly.
- **AC3**: authorization imports LangGraph.

The proc-limit row's one mutation, `graph-proc-closed-by-nondumpable`, makes the adapter
non-dumpable, which closes `/proc/<parent>` to a same-account child. It is the only production
change short of confinement that alters that limit. The installed row has no mutation, because it
checks this machine's installed state, which the suite never changes. The mutations named
`graph-command-runs-removed` through `graph-root-file-check-dropped` are the round 5 reviewer's own.

| Target row | Mutations | Rows red |
|---|---|---|
| `graph/isolated-enforcement` | `graph-authorization-imports-langgraph` (**AC3 declared**), `graph-authorization-dynamic-runtime-import`, `graph-authorization-unexercised-runtime-import` | the target row |
| `graph/start-unavailable` | `graph-start-without-runtime-launches`, `graph-start-unavailable-mislabelled` | the target row; also `isolated-enforcement` |
| `graph/runtime/plain-data` | `graph-runner-emits-langgraph-object` (**AC1 declared**), `graph-runner-tuple-as-plain` | the target row; also `authority/no-direct-write`, `authority/proc-limit`, `authority/typed-proposals-only`, `runtime/lifecycle`, `runtime/tracing-off` |
| `graph/authority/no-direct-write` | `graph-child-inherits-working-directory` (**AC2 declared**), `graph-child-inherits-store-descriptor`, `graph-runner-launched-in-place`, `graph-descriptors-in-parent-tmpdir` | the target row; also `authority/stage-links`, `authority/typed-proposals-only`, `boundary/no-store-handle`, `runtime/plain-data`, `runtime/pyvenv-clean`, `runtime/tracing-off` |
| `graph/authority/typed-proposals-only` | `graph-runner-accepts-untyped-assertion`, `graph-untyped-proposal-read-as-priority` | the target row; also `runtime/plain-data`, `shape/plain-data` |
| `graph/runtime/tracing-off` | `graph-child-inherits-caller-environment`, `graph-tracing-switch-on` | the target row; also `boundary/no-store-handle` |
| `graph/shape/deep-answer` | `graph-deep-answer-unbounded`, `graph-deep-answer-unnamed`, `graph-answer-utf16-unguarded` | the target row |
| `graph/shape/closed-request` | `graph-digest-prefix-only`, `graph-request-path-unchecked`, `graph-unserializable-escapes`, `graph-path-check-skips-keys`, `graph-request-size-unbounded` | the target row |
| `graph/shape/closed-response` | `graph-answer-resume-open`, `graph-answer-notes-any-plain` | the target row; also `shape/closed-request` |
| `graph/runtime/lifecycle` | `graph-suspend-without-graph`, `graph-runtime-evidence-unchecked` | the target row |
| `graph/authority/proc-limit` | `graph-proc-closed-by-nondumpable` | the target row |
| `graph/authority/stage-links` | `graph-stage-links-unchecked`, `graph-stage-link-checks-off`, `graph-runners-repository-unchecked`, `graph-git-not-asked`, `graph-refused-workdir-kept`, `graph-shape-opinion-dropped` | the target row; also `authority/no-direct-write`, `authority/stage-shapes`, `runtime/tracing-off` |
| `graph/authority/stage-shapes` | `graph-runtime-loop-escapes`, `graph-stage-loop-escapes`, `graph-nul-path-judged`, `graph-stage-written-place-dropped`, `graph-stage-resolved-place-dropped`, `graph-prefix-resolve-dropped`, `graph-root-file-check-dropped`, `graph-stage-oserror-unnamed`, `graph-staged-runner-shape-unchecked`, `graph-stage-root-judged-resolved-only`, `graph-stage-inside-runtime-allowed` | the target row |
| `graph/runtime/pyvenv-clean` | `graph-command-runs-removed`, `graph-command-shlex-removed`, `graph-quote-strip-removed`, `graph-rebuild-message-dropped`, `graph-option-values-unjudged`, `graph-problems-repeated`, `graph-pyvenv-unchecked`, `graph-pyvenv-command-ignored`, `graph-pyvenv-values-split`, `graph-interpreter-final-hop-only`, `graph-relative-link-misjoined`, `graph-repository-judged-resolved-only` | the target row; also `authority/stage-shapes` |
| `graph/runtime/rebuild-swap` | `graph-rebuild-no-restore`, `graph-rebuild-old-left` | the target row |
| `graph/boundary/process-group` | `graph-child-shares-session`, `graph-group-kept-on-exit` | the target row |

Result of `python3 -B scripts/check_teeth_mutations.py --finding 43 --jobs 6`: 61 of 61 rejected,
baseline green with 47 assertions (`{"mutations_rejected": 61, "green_suites": {"59_veldo_0043_graph.py": 47}}`).

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
python3 -B scripts/selftest.py --suite 59_veldo_0043_graph    20 passed, 9.58-10.37 s (46 assertions)
python3 -B scripts/check_teeth_mutations.py --finding 43      42 of 42 rejected, baseline green, 752.8 s
python3 -B proof/VELDO-0043/drive.py                          {"mutations": 42, "all_target_rows_red": true}
python3 -B scripts/check_gate_mutations.py                    passed: 280 cases, 206.8 s of a 560 s cap
python3 .veldo/validate.py all                                exit 0
bash scripts/check_generated.sh                               generated: pass
bash scripts/check_template_sync.sh                           pass
bash scripts/check_lint.sh                                    pass
python3 .veldo/control_graph_isolation.py                     isolated enforcement: pass
```

## Gate cost (`timing.json`)

These runs were measured under a load average of 11 to 14 from other agents. The suite takes 9.6
to 10.4 s for 20 rows, against 0.77 s before the runtime rows, and stays under the 60 s limit.
About 2 s of that is the process-group row's deliberate wait. The serial driver `--finding 43`
takes 752.8 s for 42 cases (84 suite runs). The whole gate mutation stage passed in 206.8 s:
280 cases against its scaled 560 s cap, with finding 43's 42 mutants taking 389.5 worker seconds.

Runner copies accumulate in the account stage, one per distinct runner content (the suite never
writes there). Collecting them is hardening, left for later. Working directories are removed
after every exchange, and the suite's temporary stages go with its temporary directory.

## Evidence size

The proof is about 290 KB: readable JSON, Markdown, Python and 42 small unified diffs. There is no
full log, no binary or encoded data, no bytecode and no credential-shaped text. The sha256
values are public wheel digests.
