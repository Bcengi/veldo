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

## What was built

**`.veldo/control_graph.py`** (standard library only) is the replaceable plain-data interface
over `start`, `advance`, `suspend` and `cancel` and the proposal and failure outcomes, as
before, now with three additions. `resolve_runtime()` and `Adapter.installed()` find the locked
runtime. Each proposal's value is typed: a priority is a non-negative integer, an admission
decision is `admit` or `decline`, and completion evidence is a list of `sha256:` digests. A
suspended answer's resume must be an object. The child's fixed environment now also sets
`LANGSMITH_TRACING`, `LANGSMITH_TRACING_V2`, `LANGCHAIN_TRACING` and `LANGCHAIN_TRACING_V2` to
`false`, so tracing is off by construction, and nothing is inherited from the caller. With no
runtime, the refusal `runtime_unavailable` names the install command.

**`.veldo/control_graph_lock.py`** is the exact lock as a readable data module: 38 packages,
each pinned to one version and to the sha256 of the one wheel resolved for CPython 3.12 on
linux x86_64 (manylinux). `digest()` is the sha256 of the canonical lock data
(`b45d1e37f35885b242f64c70237db350ba3d9037a70b556c85d611b2d2e21c37` today). The Mac needs
its own wheel hashes. VELDO-0045 later makes `engine/runtime/` the canonical lock location and
enforces the hashes at activation; this module is what 0043 carries until then.

**`.veldo/control_graph_install.py`** is the install command, `python3 .veldo/control_graph_install.py`.
It builds a virtual environment at `<account home>/.local/share/veldo/langgraph/<lock digest>/`,
where the account home comes from the password database and never from `$HOME`. It installs
with `pip install --require-hashes --no-deps --only-binary=:all:` from the lock, imports
`langgraph.graph`, and only then renames the environment into place. It strips `PIP_*`,
`PYTHON*`, `VIRTUAL_ENV*` and `CONDA*` from its own environment and refuses a Python other than
the lock's. It was run on this machine: 6.6 s, 38 packages plus pip, 86 MB. A fresh clone with
`HOME` replaced (the gate's mutation stage) finds exactly the runtime matching its lock, and a
lock change finds none.

**`.veldo/control_graph_langgraph.py`** is the runner, and it is the execution environment, not
enforcement. The adapter launches it as a child of the locked interpreter (`-I -B`, empty working
directory, fixed environment, no inherited descriptors) for exactly one exchange. It builds a
nonpersistent `StateGraph` with no checkpointer. The graph is entered at a plain resume position
through a conditional edge from `START`, and every node's output becomes a LangGraph `Command`. A
node may return only `next`, `suspend`, `proposals`, `failure` and `notes`. Any other key is an
untyped assertion and ends the cycle as `node_failed`. Anything that is not exact plain JSON
data is refused as `node_failed` before it is written, naming the offending class. The module
registers no workflows (VELDO-0132 supplies definitions), so production `main` answers
`unsupported_workflow`.

**`.veldo/control_graph_isolation.py`** now records the runner as a launch target when a module
merely names it, instead of following it as an import. An import of it is still a violation.
Its graph-start probe resolves the runtime over an empty account home, so "execution environment
absent" is real resolution, not a `None` argument.

All five modules are in `_FILES` in both `init_scaffold.py` copies. The validator does not
import them, so they are not in `REQUIRED_SUBSTRATE`. Every `.veldo` change is byte-identical in
`engine/.veldo`, and this checkout has no composed pack `.veldo` copies. Enforcement and contract
code stays standard library only; only the runner imports LangGraph.

## Criteria and rows

Suite `scripts/suites/59_veldo_0043_graph.py` has 12 rows (38 assertions with the shared preamble).
The runtime rows register the suite's own workflows through the production runner's `serve()`
and run them on the actual installed LangGraph through the production adapter. `observations.json`
keeps the actual observations of the unmutated run.

| Criterion | Rows | What they observe |
|---|---|---|
| AC1 | `graph/runtime/installed`, `graph/runtime/lifecycle`, `graph/runtime/plain-data` (plus the earlier stub shape rows `graph/shape/lifecycle`, `graph/shape/plain-data`) | The runtime resolves at the passwd home path for this lock digest. Through LangGraph 1.2.12: `start` runs groom then size and suspends at rank (resume `{position: rank, step: 2, notes}`). `suspend` returns the same resume. `advance` with supplied results returns the typed priority proposal. `cancel` answers canceled. A failing node answers `missing_evidence`. The production runner answers `unsupported_workflow`. Every answer names runtime `langgraph 1.2.12`, the lock's pin. A node returning a LangGraph `Command`, or a LangGraph `StateSnapshot`, answers `node_failed` naming `langgraph.types.Command` / `langgraph.types.StateSnapshot`. All 14 accepted answers are exact plain JSON with no `__` keys. |
| AC1 (condition) | `graph/runtime/tracing-off` | The caller's environment sets all four tracing switches to `true`. In each of the 14 runner processes, the switches read `false`, `langsmith.utils.tracing_is_enabled()` is `False` and no network egress event occurs. The runner source contains no `langgraph_sdk`, `RemoteGraph` or `get_client`. |
| AC2 | `graph/authority/no-direct-write`, `graph/authority/typed-proposals-only` (plus the stub boundary row `graph/boundary/no-store-handle`) | A real SQLite store sits at `<repository>/.git/veldo/control/control.sqlite3` in a real Git repository. The domain process runs inside that repository and holds an open, inheritable descriptor on the store. A graph node searches the working directory's parents, `/proc/self/fd`, the environment and the request, then writes to anything it finds. It finds nothing, and the store's tables are identical before and after every graph run. Nodes asserting `admitted`, `priority` and `shipped` answer `node_failed` naming the key. An untyped proposal is refused `invalid_response`. The one typed priority proposal is then committed by the store's `upsert_entity` command as principal `owner`: version 2, priority 1, journal `seed-unit-1` then `commit-p-store`. |
| AC3 | `graph/isolated-enforcement`, `graph/start-unavailable`, `graph/installed-assets` | As before: six installed enforcement entries pass the static closure and the isolated `-I -S` run, graph start refuses `runtime_unavailable`, and the installation now includes the three new modules. |

**When the runtime is absent**, every runtime row fails by name with the install command in its
message. The suite never skips and never installs. This was observed by moving the runtime aside:

```text
SELFTEST FAIL: graph/runtime/installed: runtime absent at /home/dmitry/.local/share/veldo/langgraph/b45d1e37...; install it with: python3 .veldo/control_graph_install.py
(the same message for lifecycle, plain-data, tracing-off, no-direct-write and typed-proposals-only)
```

**Tracing is off by construction, and the suite cannot send.** The suite's runner wrapper records
every egress audit event (`socket.connect`, `socket.getaddrinfo`, `socket.gethostbyname*`,
`socket.sendto`, `socket.sendmsg`) and then refuses it. urllib3's import-time loopback IPv6 probe
is a bind, not egress. The wrapper ends with `os._exit` after writing its answer and its audit line,
so a tracing mutant's exporter cannot stall on its refused retries. **Incident:** the two
finding-43 drives run before the refusal was added let the two tracing mutants reach
`socket.getaddrinfo` and `socket.connect` toward LangSmith's default endpoint. No API key was
set, and the payload was the suite's synthetic trace (node names, `unit-1`). The unmutated
adapter never attempted egress.

## Driven negative controls (finding 43 in `scripts/check_teeth_mutations.py`)

Each mutation edits a temporary production copy. Each named row goes red by a failed assertion,
never by an exception or a hang. The driver also runs an unmutated baseline per case, and the gate's
mutation stage adds an unchanged baseline and a byte-identical no-op copy per control group. The
`.diff` files are the exact edits. `mutations.json` (reproduced by `drive.py`) records every red
row and the observation that explains it.

| Row | Mutation | What happened | Rows red |
|---|---|---|---|
| `graph/isolated-enforcement` | `graph-authorization-imports-langgraph` (**AC3 declared falsifier**) | static closure and isolated run both refuse `langgraph` | `graph/isolated-enforcement` |
| `graph/isolated-enforcement` | `graph-authorization-dynamic-runtime-import` | isolated run only | `graph/isolated-enforcement` |
| `graph/isolated-enforcement` | `graph-authorization-unexercised-runtime-import` | static closure only | `graph/isolated-enforcement` |
| `graph/start-unavailable` | `graph-start-without-runtime-launches` | start crashes (TypeError), recorded as a wrong answer | `graph/start-unavailable`, `graph/isolated-enforcement` |
| `graph/start-unavailable` | `graph-start-unavailable-mislabelled` | wrong refusal name | `graph/start-unavailable`, `graph/isolated-enforcement` |
| `graph/runtime/plain-data` | `graph-runner-emits-langgraph-object` (**AC1 declared falsifier**: the runner writes LangGraph objects into the domain response through a class-tagging encoder) | both foreign workflows answer an encoded `langgraph.types.Command` / `StateSnapshot`, and the adapter refuses `invalid_response` instead of `node_failed` | `graph/runtime/plain-data` |
| `graph/runtime/plain-data` | `graph-runner-tuple-as-plain` (a tuple counts as plain) | the `StateSnapshot` named tuple crosses as an array; refused `invalid_response` | `graph/runtime/plain-data` |
| `graph/authority/no-direct-write` | `graph-child-inherits-working-directory` (**AC2 declared falsifier**: the graph child runs in the caller's repository) | the node finds the store through `.git`, writes priority 99 directly, the tables change | `graph/authority/no-direct-write`, `graph/boundary/no-store-handle` |
| `graph/authority/no-direct-write` | `graph-child-inherits-store-descriptor` (`close_fds=False`) | the node finds the store through its inherited descriptor and writes directly | `graph/authority/no-direct-write`, `graph/boundary/no-store-handle` |
| `graph/authority/typed-proposals-only` | `graph-runner-accepts-untyped-assertion` | assertions end the cycle without a proposal (`missing_evidence`), not `node_failed` | `graph/authority/typed-proposals-only` |
| `graph/authority/typed-proposals-only` | `graph-untyped-proposal-read-as-priority` | the untyped proposal is accepted as a priority | `graph/authority/typed-proposals-only`, `graph/runtime/plain-data`, `graph/shape/plain-data` |
| `graph/runtime/tracing-off` | `graph-child-inherits-caller-environment` (`env=None`) | the child sees the caller's `true` switches; langsmith reports tracing on and attempts `socket.getaddrinfo` (refused) | `graph/runtime/tracing-off`, `graph/boundary/no-store-handle` |
| `graph/runtime/tracing-off` | `graph-tracing-switch-on` (`LANGSMITH_TRACING_V2` set to `true`) | langsmith reports tracing on and attempts egress (refused) | `graph/runtime/tracing-off` |

Result lines from `python3 -B scripts/check_teeth_mutations.py --finding 43` (13 of 13 rejected,
baseline green with 38 assertions each):

```text
graph-authorization-imports-langgraph            red: graph/isolated-enforcement
graph-authorization-dynamic-runtime-import       red: graph/isolated-enforcement
graph-authorization-unexercised-runtime-import   red: graph/isolated-enforcement
graph-start-without-runtime-launches             red: graph/isolated-enforcement, graph/start-unavailable
graph-start-unavailable-mislabelled              red: graph/isolated-enforcement, graph/start-unavailable
graph-runner-emits-langgraph-object              red: graph/runtime/plain-data
graph-runner-tuple-as-plain                      red: graph/runtime/plain-data
graph-child-inherits-working-directory           red: graph/boundary/no-store-handle, graph/authority/no-direct-write
graph-child-inherits-store-descriptor            red: graph/boundary/no-store-handle, graph/authority/no-direct-write
graph-runner-accepts-untyped-assertion           red: graph/authority/typed-proposals-only
graph-untyped-proposal-read-as-priority          red: graph/shape/plain-data, graph/runtime/plain-data, graph/authority/typed-proposals-only
graph-child-inherits-caller-environment          red: graph/boundary/no-store-handle, graph/runtime/tracing-off
graph-tracing-switch-on                          red: graph/runtime/tracing-off
{"mutations_rejected": 13, "green_suites": {"59_veldo_0043_graph.py": 38}}
```

The lifecycle and installed rows have no registered mutation. Neither carries a declared
falsifier, and every lifecycle operation also feeds the driven plain-data and tracing rows.

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
python3 -B scripts/selftest.py --suite 59_veldo_0043_graph
  59_veldo_0043_graph   12 passed   4.66-4.79s
  selftest (PARTIAL, 1 of 67 suites): 38 passed, 0 failed
python3 -B scripts/check_teeth_mutations.py --finding 43     13 of 13 rejected, baseline green (38)
python3 -B proof/VELDO-0043/drive.py                         {"mutations": 13, "all_target_rows_red": true}
python3 .veldo/validate.py all                               exit 0
bash scripts/check_generated.sh                              generated: pass
bash scripts/check_template_sync.sh                          pass (164 pairs)
bash scripts/check_lint.sh                                   pass
python3 .veldo/control_graph_isolation.py                    isolated enforcement: pass
python3 -B scripts/check_install_and_run.py                  install-and-run: pass
python3 -B scripts/secret_inventory.py                       0 outstanding
bash scripts/check_docs.sh                                   docs hygiene: pass
python3 -B scripts/selftest.py --suite 07_warp_1103_completion_mandatory   261 passed, 0 failed
python3 -B scripts/check_gate_mutations.py                   passed, 129 registered, 119.14 s (see below)
```

## Gate cost (`timing.json`)

The suite went from 0.77-0.79 s (6 rows) to 4.66-4.79 s (12 rows), which is about 3.9 s added per
run, well under the 60 s limit. It makes 15 runtime exchanges, each a fresh LangGraph process
of about 0.35 s. The serial driver `check_teeth_mutations.py --finding 43` went from 8.35 s (5
cases) to 125.94 s (13 cases, 26 suite runs).

**The gate's mutation stage is at its budget.** `check_gate_mutations.py` runs every driver's
cases with 8 workers against a combined 120 s deadline. At `b3415d0` it passed in 119.14 s
(129 cases). At the pre-build commit `f346524` it failed `mutation_budget_exceeded` at 120.16 s
(121 cases), under the same machine load (load average 6 to 13 from other agents). Finding 43
adds about 94 worker seconds (13 mutants and 6 controls near 5 s each, against about 7 before),
about 12 s of wall time at 8 workers. The stage was already at the edge before this change, and
the lead needs to decide on the budget or the parallelism. That is outside this footprint.

## Evidence size

The proof is about 86 KB: readable JSON, Markdown, Python and 13 small unified diffs. It holds
no full gate log, no binary or encoded data, no bytecode and no credential-shaped text. The
sha256 values are public wheel digests from PyPI.
