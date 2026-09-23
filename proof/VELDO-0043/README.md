# VELDO-0043 proof (partial: AC3 built, AC1 and AC2 blocked on langgraph-sdk)

The specification stays **ready**. This bundle is implementation evidence for AC3 and for the
engine-neutral adapter interface. It is not independent engineering review, owner approval,
service activation, or a full-gate result. The lead runs `bash scripts/verify.sh`; this branch
was checked only with the targeted commands listed under Verification.

## The blocker: a third dependency, langgraph-sdk, conflicts with C16

AC1 and AC2 require the actual installed LangGraph runtime. The owner has approved two named
exceptions to C16 for it: **xxhash** (Chinese origin) and **langsmith** (client of a service
sold in free and paid tiers), on condition that each is pinned to an exact version and that
LangSmith tracing stays off. A fresh review of the whole closure on 2026-09-23 found a third
component in the same position as langsmith, so LangGraph is still not installed. C16 says a
conflicting component needs an owner decision, not an exception hidden in the implementation.

**langgraph-sdk 0.4.5** (MIT, `github.com/langchain-ai`, United States) is the Python client for
the LangGraph Agent Server, the server behind LangSmith Deployment. That server
(`langgraph-api`) is licensed Elastic-2.0, and www.langchain.com/pricing (read 2026-09-23)
sells LangSmith Deployment in the Plus plan ($39 per seat per month, one free small serverless
deployment, then usage charges) and the Enterprise plan. langgraph 1.2.12 requires it, and
imports it on every graph run, not only for remote graphs: `langgraph/runtime.py` line 8 is
`from langgraph_sdk.auth.types import BaseUser`. Installing LangGraph without it would be
installing around the rule, so nothing was installed. The adapter itself would never call the
SDK's client, and PLAN-0019 already excludes a LangGraph server, but that is a fact for the owner's
decision, not a reason to proceed without one.

The owner needs to decide whether langgraph-sdk may be installed as a third named exception. One
more point needs his attention: **orjson** (required by langgraph-sdk and langsmith) is
maintained by the GitHub account `ijl`, which states no name or location, so its origin is not
verified either way. No other component was found to be of Chinese origin or to be sold in tiers.
Pydantic Services Inc. maintains pydantic, pydantic_core, typing-inspection, httpx2 and
httpcore2 and separately sells Logfire, but none of these libraries is tiered or a Logfire
client.

## The dependency closure

Resolved on 2026-09-23 with `pip install --dry-run --report langgraph==1.2.12` (1.2.12 is the
latest stable release on PyPI) in a throwaway virtual environment under the session scratchpad,
Python 3.12.3, pip 24.0. Nothing was installed. It is 38 packages, the same set the first probe
found; httpx2 and httpcore2 moved from 2.13.0 to 2.13.1. Licenses come from PyPI metadata and
origin from the GitHub owner profiles. `dependency-closure.json` holds the same rows with each
package's requirements.

| Package | Version | License | Maintainer origin | C16 |
|---|---|---|---|---|
| annotated-types | 0.8.0 | MIT | github.com/annotated-types (org, no location); author Adrian Garcia Badaracco, Chicago, IL, US | no conflict found |
| anyio | 4.15.1 | MIT | github.com/agronholm, Alex Gronholm, Nurmijarvi, Finland | no conflict found |
| certifi | 2026.7.22 | MPL-2.0 | github.com/certifi (org, no location); PyPI author Kenneth Reitz | no conflict found |
| charset-normalizer | 3.5.1 | MIT | github.com/jawah (org, France); Ahmed R. Tahri (Ousret), France | no conflict found |
| distro | 1.9.0 | Apache-2.0 | github.com/python-distro (org, no location); author Nir Cohen (nir0s, no location) | no conflict found |
| h11 | 0.16.0 | MIT | github.com/python-hyper (org, no location); author Nathaniel J. Smith (no location) | no conflict found |
| httpcore | 1.0.9 | BSD-3-Clause | github.com/encode (org, no location); author Tom Christie (no location) | no conflict found |
| httpcore2 | 2.13.1 | BSD-3-Clause | github.com/pydantic/httpx2; maintainer Pydantic Services Inc.; Samuel Colvin, London, UK | no conflict found |
| httpx | 0.28.1 | BSD-3-Clause | github.com/encode (org, no location); author Tom Christie (no location) | no conflict found |
| httpx2 | 2.13.1 | BSD-3-Clause | github.com/pydantic/httpx2; maintainer Pydantic Services Inc.; Samuel Colvin, London, UK | no conflict found |
| idna | 3.20 | BSD-3-Clause | github.com/kjd, Kim Davies (ICANN/IANA, no location) | no conflict found |
| jsonpatch | 1.33 | BSD (Modified BSD License) | github.com/stefankoegl, Stefan Koegl, Austria | no conflict found |
| jsonpointer | 3.1.1 | BSD (Modified BSD License) | github.com/stefankoegl, Stefan Koegl, Austria | no conflict found |
| langchain-core | 1.6.4 | MIT | github.com/langchain-ai, LangChain, United States | no conflict found |
| langchain-protocol | 0.0.19 | MIT | github.com/langchain-ai, LangChain, United States | no conflict found |
| langgraph | 1.2.12 | MIT | github.com/langchain-ai, LangChain, United States | no conflict found |
| langgraph-checkpoint | 4.2.0 | MIT | github.com/langchain-ai, LangChain, United States | no conflict found |
| langgraph-prebuilt | 1.1.0 | MIT | github.com/langchain-ai, LangChain, United States | no conflict found |
| langgraph-sdk | 0.4.5 | MIT | github.com/langchain-ai, LangChain, United States | CONFLICT: client of the LangSmith Deployment / LangGraph Agent Server service, sold in free and paid tiers; not approved |
| langsmith | 0.14.0 | MIT | github.com/langchain-ai, LangChain, United States | owner-approved exception (client of a free and paid tier service) |
| orjson | 3.12.0 | MPL-2.0 AND (Apache-2.0 OR MIT) | github.com/ijl, no public name or location (commit mail at mailbox.org); origin NOT verified | origin not verified |
| ormsgpack | 1.12.2 | Apache-2.0 OR MIT | github.com/ormsgpack (org); Aviram Hassan, Tel Aviv, Israel; Emanuele Giaquinta (exg, no location) | no conflict found |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | github.com/pypa, Python Packaging Authority, United States | no conflict found |
| pydantic | 2.13.5 | MIT | github.com/pydantic (org, no location); Samuel Colvin, London, UK | no conflict found |
| pydantic_core | 2.46.5 | MIT | github.com/pydantic (org, no location); Samuel Colvin, London, UK | no conflict found |
| PyYAML | 6.0.3 | MIT | github.com/yaml, The YAML Project (org, no location) | no conflict found |
| requests | 2.34.2 | Apache-2.0 | github.com/psf, Python Software Foundation; maintainer Ian Stapleton Cordasco, Madison, WI, US | no conflict found |
| requests-toolbelt | 1.0.0 | Apache-2.0 | github.com/requests (org); Ian Stapleton Cordasco, Madison, WI, US | no conflict found |
| sniffio | 1.3.1 | MIT OR Apache-2.0 | github.com/python-trio (org, no location); author Nathaniel J. Smith | no conflict found |
| tenacity | 9.1.4 | Apache-2.0 | github.com/jd, Julien Danjou, Toulouse, France | no conflict found |
| truststore | 0.10.4 | MIT | github.com/sethmlarson, Seth Larson, Minneapolis, MN, US | no conflict found |
| typing-inspection | 0.4.4 | MIT | github.com/pydantic; Victorien Plot (Viicos), Amsterdam, Netherlands | no conflict found |
| typing_extensions | 4.16.0 | PSF-2.0 | github.com/python, Python (org) | no conflict found |
| urllib3 | 2.8.0 | MIT | github.com/urllib3 (org); Andrey Petrov, Toronto, Canada; Seth Larson, Minneapolis, MN, US | no conflict found |
| uuid_utils | 0.17.1 | BSD-3-Clause | github.com/aminalaee, Amin Alaee, Netherlands | no conflict found |
| websockets | 16.1.1 | BSD-3-Clause | github.com/python-websockets (org); Aymeric Augustin, Paris, France | no conflict found |
| xxhash | 4.0.1 | BSD-2-Clause | github.com/ifduyue, Yue Du, location China | owner-approved exception (Chinese origin) |
| zstandard | 0.25.0 | BSD-3-Clause | github.com/indygreg, Gregory Szorc, San Francisco, CA, US | no conflict found |

## Where the lock and the runtime would live (for the next run)

Three placement points came up before the stop. The first two are findings; the third is open.

**The lock.** The only non-Python path this specification's footprint allows is
`proof/VELDO-0043/*`, so an exact, hashed requirements lock for the proof runtime can be checked in
there as evidence of what the rows ran against. The distributed runtime lock belongs to
VELDO-0045 (`engine/runtime/*`, `.veldo/runtime/*`), whose AC2 falsifier is omitting it.

**The virtual environment.** It cannot sit under `.veldo`, `engine/.veldo`, `scripts` or
`proof`: the gate's mutation stage copies those trees file by file and refuses any symbolic link,
and a virtual environment's `bin/python` is one. At the repository root it is untracked noise
that `.gitignore` (outside this footprint) does not cover. Under the Git common directory it is
inside the main checkout's `.git`.

**Open question: rows when the runtime is absent.** The gate's mutation stage runs suites in a
fresh clone with `HOME` replaced, and it requires every baseline row green. A runtime found
relative to the checkout or through `HOME` is absent there, so AC1 and AC2 rows would turn the
baseline red. The specification is silent on what a runtime row does in a fresh clone. Failing
by name is the only behavior that does not pass vacuously; the lead needs to decide whether the
runtime is located at a fixed per-account path (found through the password database, not
`HOME`), or whether the mutation stage gets the runtime some other way.

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
AC2 nodes that assert admission, priority and completion or try store access, and the proof
runtime lock. Distributing and activating the runtime is VELDO-0045, which depends on this spec.

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
